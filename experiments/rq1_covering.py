"""RQ1: read cost with and without a covering index, on one engine.

python -m experiments.rq1_covering {mysql,tidb} ROWS

Each query reads the same rows through design A (not covering) and B (covering).
The index is forced by a hint and every plan is checked before it is timed. Baselines
(SELECT 1, primary key lookup) and the Q2R sizes let rq1_summary split the fixed cost
of a query from the cost of each row.
"""

import argparse
import gc
import hashlib
import json
import re
import time
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from statistics import fmean, median

import docker
import MySQLdb

from bench.config import get_engine_config, get_machine_id
from bench.db import analyze, checksum, connect, engine_settings
from bench.environment import (
    ROOT,
    SERVICES,
    assert_engine,
    compose,
    operation_lock,
    wait_ready,
)
from bench.rq4 import config_fingerprint, save_row, settle, wait_replicas, wait_settings
from bench.schema import create_index_sql, drop_index_sql

SEED = 20261116
QUERIES = {
    "SELECT1": "SELECT 1",
    "PK": "SELECT status,updated_at FROM shipments WHERE id={0}",
    "Q1": "SELECT status,updated_at FROM shipments {hint} WHERE tracking_code={0}",
    "Q2": "SELECT id,created_at,status,cod_amount FROM shipments {hint} "
    "WHERE sender_id={0} AND created_at>={1} ORDER BY created_at DESC LIMIT 20",
    "Q2R": "SELECT id,created_at,status,cod_amount FROM shipments {hint} "
    "WHERE sender_id={0} AND created_at>={1} ORDER BY created_at DESC",
    "Q3": "SELECT status,COUNT(*) FROM shipments {hint} "
    "WHERE dest_hub_id={0} GROUP BY status",
}
LEVELS = (10, 100, 1000, 10000)
Q2_SINCE = datetime(2026, 8, 1)
# design A2 is A' in the plan: same key as B, not unique, not covering.
Case = namedtuple("Case", "query design index covering")
CASES = [
    Case("SELECT1", "base", None, None),
    Case("PK", "base", None, None),
    Case("Q1", "A", "idx_code", False),
    Case("Q1", "A2", "idx_code_nonuniq", False),
    Case("Q1", "B", "idx_code_cov", True),
    Case("Q2", "A", "idx_sender_created", False),
    Case("Q2", "B", "idx_sender_cov", True),
    Case("Q2R", "A", "idx_sender_created", False),
    Case("Q2R", "B", "idx_sender_cov", True),
    Case("Q3", "A", "idx_hub", False),
    Case("Q3", "B", "idx_hub_status", True),
]
RQ1_INDEXES = list(dict.fromkeys(c.index for c in CASES if c.index))
TIDB_OPS = r"(IndexLookUp|IndexReader|IndexMerge|TableReader|Batch_Point_Get|Point_Get)"
EXPLAIN_SAMPLES = 10


def literal(value):
    return f"'{value}'" if isinstance(value, (str, datetime)) else str(int(value))


def render(case, params):
    hint = f"FORCE INDEX ({case.index})" if case.index else ""
    return QUERIES[case.query].format(*map(literal, params), hint=hint)


# ---- parameters -----------------------------------------------------------------


def sample_params(conn, k, seed=SEED):
    """Return {(query, level): [(params, R)]}. Same data and seed give the same list."""
    rng = Random(seed)
    cur = conn.cursor()

    def fetch(sql, args=()):
        cur.execute(sql, args)
        return cur.fetchall()

    rows = fetch("SELECT MAX(id) FROM shipments")[0][0]
    ids = sorted(rng.sample(range(1, rows + 1), min(k, rows)))
    rng.shuffle(ids)
    out = {("SELECT1", 0): [((), 1)] * k, ("PK", 0): [((i,), 1) for i in ids]}
    marks = ",".join(["%s"] * len(ids))
    codes = dict(fetch(f"SELECT id,tracking_code FROM shipments WHERE id IN ({marks})", ids))
    out["Q1", 0] = [((codes[i],), 1) for i in ids]

    recent = fetch(
        "SELECT sender_id FROM shipments WHERE created_at>=%s GROUP BY sender_id "
        "HAVING COUNT(*)>=20 ORDER BY sender_id",
        (Q2_SINCE,),
    )
    if recent:
        senders = rng.choices([r[0] for r in recent], k=k)
        out["Q2", 0] = [((s, Q2_SINCE), 20) for s in senders]

    counts = fetch(
        "SELECT sender_id,COUNT(*) FROM shipments GROUP BY sender_id ORDER BY sender_id"
    )
    for level in LEVELS:
        # A start time is chosen so that exactly r rows match. Orders never share a
        # created_at, and r varies by 5% so that repeated senders get different ranges.
        pool = [s for s, n in counts if n >= level * 1.05]
        if not pool:
            print(f"Q2R R={level}: no sender is large enough, level skipped", flush=True)
            continue
        params = []
        for _ in range(k):
            sender = rng.choice(pool)
            r = rng.randint(round(level * 0.95), round(level * 1.05))
            since = fetch(
                "SELECT created_at FROM shipments WHERE sender_id=%s "
                "ORDER BY created_at DESC LIMIT 1 OFFSET %s",
                (sender, r - 1),
            )[0][0]
            params.append(((sender, since), r))
        out["Q2R", level] = params

    hubs = dict(
        fetch("SELECT dest_hub_id,COUNT(*) FROM shipments GROUP BY dest_hub_id ORDER BY 1")
    )
    order = sorted(hubs)
    rng.shuffle(order)
    out["Q3", 0] = [((order[i % len(order)],), hubs[order[i % len(order)]]) for i in range(k)]
    cur.close()
    return out


def params_digest(params):
    text = json.dumps([[list(k), v] for k, v in sorted(params.items())], default=str)
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ---- plans ----------------------------------------------------------------------


def expected_ops(case):
    """Access paths allowed for a case. Anything else stops the run."""
    if case.query == "SELECT1":
        return None
    if case.query == "PK" or (case.query, case.design) == ("Q1", "A"):
        return {"Point_Get"}
    return {"IndexReader"} if case.covering else {"IndexLookUp"}


def tidb_plan(rows):
    """(access operator, index) from EXPLAIN or EXPLAIN ANALYZE rows of TiDB."""
    text = "\n".join(" ".join(str(c) for c in row) for row in rows)
    op = re.search(TIDB_OPS, text)
    index = re.search(r"index:(\w+)\([^)]*\)", text)
    return op and op[1], index and index[1]


def mysql_plan(rows):
    """(access operator, index) from one traditional MySQL EXPLAIN row (a dict)."""
    if len(rows) != 1:
        return None, None
    row = rows[0]
    extra = (row["Extra"] or "").split("; ")
    if row["type"] == "ALL":
        return "TableScan", None
    op = "CoveringIndex" if "Using index" in extra else f"IndexAndRow({row['type']})"
    return op, row["key"]


def check_plan(conn, engine, case, sql):
    """Fail unless the hinted index and access path are the planned ones."""
    if case.query == "SELECT1":
        return "none"
    with conn.cursor(dictionary=engine == "mysql") as cur:
        cur.execute("EXPLAIN " + sql)
        rows = cur.fetchall()
    op, index = (mysql_plan if engine == "mysql" else tidb_plan)(rows)
    if engine == "tidb":
        ok = op in expected_ops(case) and (case.index is None or index == case.index)
    elif case.query == "PK":
        ok = index == "PRIMARY"
    else:
        ok = index == case.index and (op == "CoveringIndex") == case.covering
    if not ok:
        raise RuntimeError(f"Unexpected plan for {case}: {op} on {index}\n{rows}")
    return op


def milliseconds(text):
    """Convert a TiDB duration such as 1m2.3s, 4.86ms, 593.2µs or 510ns."""
    factors = {"h": 3.6e6, "m": 6e4, "s": 1e3, "ms": 1.0, "µs": 1e-3, "us": 1e-3, "ns": 1e-6}
    parts = re.findall(r"([\d.]+)(ms|µs|us|ns|h|m|s)", text)
    return sum(float(v) * factors[u] for v, u in parts)


def parse_execution_info(text):
    """Sum the KV counters of every reader in a TiDB v8.5 EXPLAIN ANALYZE.

    Times add up over parallel tasks, so they can exceed the elapsed time.
    """

    def ints(pattern):
        return sum(int(v) for v in re.findall(pattern, text))

    def times(pattern):
        return sum(milliseconds(v) for v in re.findall(pattern, text))

    out = dict(
        cop_tasks=ints(r"cop_task: \{num: (\d+)"),
        rpcs=ints(r"num_rpc:(\d+)"),
        process_keys=ints(r"total_process_keys: (\d+)"),
        rpc_ms=times(r"num_rpc:\d+, total_time:([^,}]+)"),
        # time_detail is printed once per reader for both Get and Cop requests.
        process_ms=times(r"total_process_time: ([^,}]+)"),
        wait_ms=times(r"total_wait_time: ([^,}]+)"),
        block_reads=ints(r"\bread_count: (\d+)"),
    )
    out["rest_ms"] = out["rpc_ms"] - out["process_ms"] - out["wait_ms"]
    return out


def explain_sample(conn, engine, sqls, folder, name):
    """Run EXPLAIN ANALYZE on a few queries, keep the raw text, return TiDB medians."""
    texts = []
    with conn.cursor() as cur:
        for sql in sqls:
            cur.execute("EXPLAIN ANALYZE " + sql)
            texts.append("\n".join("\t".join(str(c) for c in r) for r in cur.fetchall()))
    blocks = [f"{s}\n{t}" for s, t in zip(sqls, texts)]
    (folder / f"{name}.txt").write_text("\n\n".join(blocks), encoding="utf-8")
    fields = parse_execution_info("")
    if engine == "mysql":
        return dict.fromkeys(fields, "")
    if any("copr_cache_hit_ratio" in t for t in texts):
        raise RuntimeError("The TiDB coprocessor cache is on. Timings would be wrong.")
    parsed = [parse_execution_info(t) for t in texts]
    return {f: round(median(p[f] for p in parsed), 4) for f in fields}


# ---- timing ---------------------------------------------------------------------


def fast_connect(engine):
    """C client: a pure Python one costs more per row than the server does."""
    cfg = get_engine_config(engine)
    # Without autocommit, every read would share the first transaction's snapshot.
    return MySQLdb.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"], passwd=cfg["password"],
        db=cfg["database"], autocommit=True, ssl_mode="DISABLED", conv={},
    )


def run_queries(conn, sqls):
    """Return (latency ns, rows) per query. Time ends when all rows have arrived."""
    out = []
    clock = time.perf_counter_ns
    gc.disable()
    try:
        for sql in sqls:
            start = clock()
            conn.query(sql)
            result = conn.store_result()
            out.append((clock() - start, result.num_rows()))
    finally:
        gc.enable()
    return out


def result_digest(conn, sqls):
    """Hash of every returned row, independent of the order of groups."""
    digest = hashlib.sha256()
    for sql in sqls:
        conn.query(sql)
        rows = conn.store_result().fetch_row(0)
        text = sorted("|".join(str(c) for c in row) for row in rows)
        digest.update("\n".join(text).encode())
    return digest.hexdigest()[:12]


def mysql_counters(cur):
    cur.execute("SHOW SESSION STATUS LIKE 'Handler_read%'")
    values = {k: int(v) for k, v in cur.fetchall()}
    cur.execute("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_reads'")
    # Handler_read_rnd_next is left out because SHOW STATUS itself changes it.
    keys = ("Handler_read_key", "Handler_read_next", "Handler_read_prev")
    return sum(values[k] for k in keys), int(cur.fetchone()[1])


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))]


# ---- run ------------------------------------------------------------------------


def existing_indexes(cur):
    cur.execute("SHOW INDEX FROM shipments")
    return {r[2] for r in cur.fetchall()}.intersection(RQ1_INDEXES)


def drop_indexes(conn):
    with conn.cursor() as cur:
        for name in existing_indexes(cur):
            cur.execute(drop_index_sql("shipments", name))


def build_indexes(conn, engine):
    with conn.cursor() as cur:
        present = existing_indexes(cur)
        for name in RQ1_INDEXES:
            if name not in present:
                start = time.monotonic()
                cur.execute(create_index_sql("shipments", name))
                print(f"{name}: {time.monotonic() - start:.1f} s", flush=True)
    analyze(conn, "shipments", engine=engine)


def completed(path, engine, rows, config_id, params_sha):
    """Trials already recorded, refusing to mix configurations or parameters."""
    if not path.exists() or path.stat().st_size == 0:
        return set()
    import csv

    with path.open(encoding="utf-8-sig", newline="") as stream:
        done = [
            r for r in csv.DictReader(stream)
            if r["engine"] == engine and int(r["rows"]) == rows
        ]
    if any((r["config_id"], r["params_sha"]) != (config_id, params_sha) for r in done):
        raise ValueError(f"{path} holds {engine} trials from another setup. Use --output.")
    return {(r["query"], r["design"], int(r["level"]), int(r["rep"])) for r in done}


def run(args):
    engine = args.engine
    assert_engine(engine)
    if engine == "tidb":
        # Same containers and limits, with the coprocessor result cache switched off.
        override = str(ROOT / "docker/tidb-rq1.yml")
        compose("-f", override, "up", "-d", "--no-deps", "tidb")
    wait_ready(engine)
    client = docker.from_env()
    conn = connect(engine)
    try:
        if engine == "tidb":
            wait_settings(conn)
        rows, cod = checksum(conn, "shipments")
        if rows != args.rows:
            raise ValueError(f"shipments has {rows} rows, expected {args.rows}")
        build_indexes(conn, engine)
        if engine == "tidb":
            wait_replicas(conn, 3)
        settings = engine_settings(conn, engine)
        containers = {
            s: compose("ps", "-q", s, capture=True).strip() for s in SERVICES[engine]
        }
        config_id = config_fingerprint(client, containers)
        params = sample_params(conn, args.params)
        params_sha = params_digest(params)
        trials = [(c, lv) for c in CASES for (q, lv) in params if q == c.query]
        done = completed(args.output, engine, rows, config_id, params_sha)
        started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{started}_{settings['machine']}_rq1_{engine}"
        folder = ROOT / "results/raw" / run_id
        folder.mkdir(parents=True)
        (folder / "params.json").write_text(
            json.dumps({f"{q}/{lv}": v for (q, lv), v in params.items()}, default=str),
            encoding="utf-8",
        )
        sqls = {t: [render(t[0], p) for p, _ in params[t[0].query, t[1]]] for t in trials}
        # A baseline without parameters is one query repeated, so one plan is enough.
        ops = {
            t: {check_plan(conn, engine, t[0], sql) for sql in dict.fromkeys(sqls[t])}
            for t in trials
        }
        with fast_connect(engine) as fast:
            # Unmeasured pass: warms the caches and proves A and B return the same rows.
            digests = {t: result_digest(fast, sqls[t]) for t in trials}
            for query, level in params:
                found = {digests[t] for t in trials if (t[0].query, t[1]) == (query, level)}
                if len(found) != 1:
                    raise ValueError(f"{query} {level}: designs return different rows")
            print(f"{run_id}: {len(trials)} cases, params {params_sha}", flush=True)
            for rep in range(1, args.reps + 1):
                todo = [t for t in trials if (t[0].query, t[0].design, t[1], rep) not in done]
                if not todo:
                    continue
                # A different fixed order each round, as in RQ4.
                Random(rep).shuffle(todo)
                settle_s, settled = settle(client, containers, SERVICES[engine])
                if not settled:
                    raise SystemExit("The disk did not settle. Run the same command again.")
                for trial in todo:
                    case, level = trial
                    expected = [r for _, r in params[case.query, level]]
                    run_queries(fast, sqls[trial][: args.warmup])
                    before = mysql_counters(fast.cursor()) if engine == "mysql" else None
                    measured = run_queries(fast, sqls[trial])
                    handlers = disk_reads = ""
                    if before:
                        after = mysql_counters(fast.cursor())
                        handlers = (after[0] - before[0]) / len(measured)
                        disk_reads = after[1] - before[1]
                    if case.query != "Q3" and [n for _, n in measured] != expected:
                        raise ValueError(f"{case} {level}: unexpected number of rows")
                    ms = [t / 1e6 for t, _ in measured]
                    name = f"{case.query}_{case.design}_{level}_{rep}"
                    info = explain_sample(
                        conn, engine, sqls[trial][:EXPLAIN_SAMPLES], folder, name
                    )
                    row = dict(
                        run_id=run_id,
                        machine=settings["machine"],
                        profile=settings["profile"],
                        engine=engine,
                        version=settings["version"].splitlines()[0],
                        replica_config=settings.get("replica_config", ""),
                        block_cache=settings.get("block_cache", ""),
                        buffer_pool=settings.get("buffer_pool", ""),
                        rows=rows,
                        sum_cod=cod,
                        query=case.query,
                        design=case.design,
                        index=case.index or "",
                        level=level,
                        rep=rep,
                        access_op="/".join(sorted(ops[trial])),
                        n_queries=len(ms),
                        rows_mean=round(fmean(expected), 2),
                        p50_ms=round(median(ms), 4),
                        p95_ms=round(percentile(ms, 0.95), 4),
                        p99_ms=round(percentile(ms, 0.99), 4),
                        mean_ms=round(fmean(ms), 4),
                        handler_reads_per_query=handlers,
                        buffer_pool_reads=disk_reads,
                        **info,
                        result_sha=digests[trial],
                        params_sha=params_sha,
                        config_id=config_id,
                        settle_s=settle_s,
                        settled=int(settled),
                    )
                    save_row(args.output, row)
                    print(f"{name} p50={row['p50_ms']} ms {row['access_op']}", flush=True)
    finally:
        try:
            if not args.keep_indexes:
                drop_indexes(conn)
            conn.close()
        finally:
            if engine == "tidb":
                # Back to the shared configuration that RQ4 uses.
                compose("up", "-d", "--no-deps", "tidb")
                wait_ready("tidb")
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["mysql", "tidb"])
    parser.add_argument("rows", type=int, nargs="?", default=1_000_000)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--params", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--keep-indexes", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=ROOT / f"results/rq1_{get_machine_id()}.csv"
    )
    args = parser.parse_args()
    if min(args.reps, args.params, args.warmup) < 1:
        raise SystemExit("reps, params and warmup must be positive")
    with operation_lock():
        run(args)


if __name__ == "__main__":
    main()
