"""RQ2: selectivity threshold between an index range scan and a full table scan.

python -m experiments.rq2_selectivity {mysql,tidb} ROWS

One query, `cod_amount BETWEEN lo AND hi`, at ten selectivities from 0.001% to 50%.
Each selectivity is run three ways: the index is forced (`FORCE INDEX`), ignored
(`IGNORE INDEX`, so the table is scanned), or left to the optimizer. The query is not
covered by idx_cod, so the index path pays one table lookup per matching row. That makes
the crossover the place where per-row lookups cost more than a sequential scan.

The projection is five columns, not `SELECT *`, so that returning up to 1.5 million rows
does not make transfer the main cost. Pure helpers (cod_range, find_crossover, plan_ok)
need no database driver; the run itself imports the RQ1 helpers lazily.
"""

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from statistics import fmean, median

from bench.datagen import COD_MAX

SEED = 20261116
LEVELS_PCT = (0.001, 0.01, 0.1, 0.5, 1, 2, 5, 10, 25, 50)
MODES = ("index", "scan", "auto")
HINTS = {"index": "FORCE INDEX (idx_cod)", "scan": "IGNORE INDEX (idx_cod)", "auto": ""}
SQL = (
    "SELECT id,tracking_code,status,cod_amount,created_at FROM shipments {hint} "
    "WHERE cod_amount BETWEEN {lo} AND {hi}"
)
INDEX_OPS = {"IndexLookUp", "IndexAndRow(range)"}
SCAN_OPS = {"TableReader", "TableScan"}
EXPLAIN_SAMPLES = 10
EXPLAIN_SAMPLES_BIG = 3


def cod_range(pct, u, cod_max=COD_MAX):
    """Inclusive (lo, hi) covering pct percent of cod_amount values. u in [0, 1)."""
    if not 0 < pct <= 100 or not 0 <= u < 1:
        raise ValueError((pct, u))
    width = max(1, round(pct / 100 * cod_max))
    lo = int(u * (cod_max - width + 1))
    return lo, lo + width - 1


def level_params(pct, k, seed=SEED):
    """k ranges for one selectivity. The same seed always gives the same list."""
    rng = Random(f"{seed}:{pct}")
    return [cod_range(pct, rng.random()) for _ in range(k)]


def params_for(pct, small, big):
    """Cheap levels get many ranges; the heavy ones (above 2%) only a few."""
    return level_params(pct, small if pct <= 2 else big)


def render(mode, lo, hi):
    return SQL.format(hint=HINTS[mode], lo=lo, hi=hi)


def plan_ok(mode, op, index):
    """True when the plan matches what the mode demands. Auto accepts either path."""
    if mode == "index":
        return op in INDEX_OPS and index == "idx_cod"
    if mode == "scan":
        return op in SCAN_OPS
    return op in INDEX_OPS | SCAN_OPS


def find_crossover(xs, index_ms, scan_ms):
    """Selectivity where the index path stops being faster than the scan.

    xs must be ascending. Interpolates linearly in log(x) and log(index/scan) between the
    first pair of points whose ratio crosses 1. Returns None when it never crosses.
    """
    if not len(xs) == len(index_ms) == len(scan_ms) or len(xs) < 2:
        raise ValueError("Need at least two matching points")
    ratio = [math.log(i / s) for i, s in zip(index_ms, scan_ms)]
    for k in range(1, len(xs)):
        if ratio[k - 1] < 0 <= ratio[k]:
            frac = (0 - ratio[k - 1]) / (ratio[k] - ratio[k - 1])
            lx0, lx1 = math.log10(xs[k - 1]), math.log10(xs[k])
            return 10 ** (lx0 + frac * (lx1 - lx0))
    return None


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))]


def counts_digest(counts):
    return hashlib.sha256(json.dumps(counts).encode()).hexdigest()[:12]


# ---- run ------------------------------------------------------------------------


def done_trials(path, engine, rows, config_id, params_sha):
    import csv

    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        done = [
            r for r in csv.DictReader(stream)
            if r["engine"] == engine and int(r["rows"]) == rows
        ]
    if any((r["config_id"], r["params_sha"]) != (config_id, params_sha) for r in done):
        raise ValueError(f"{path} holds {engine} trials from another setup. Use --output.")
    return {(float(r["pct"]), r["mode"], int(r["rep"])) for r in done}


def check_plans(conn, engine, mode, sqls):
    from experiments.rq1_covering import mysql_plan, tidb_plan

    ops = set()
    for sql in sqls:
        with conn.cursor(dictionary=engine == "mysql") as cur:
            cur.execute("EXPLAIN " + sql)
            rows = cur.fetchall()
        op, index = (mysql_plan if engine == "mysql" else tidb_plan)(rows)
        if not plan_ok(mode, op, index):
            raise RuntimeError(f"{mode}: plan is {op} on {index}\n{sql}\n{rows}")
        ops.add(op)
    return ops


def run(args):
    import docker

    from bench.db import analyze, checksum, connect, engine_settings
    from bench.environment import (
        ROOT, SERVICES, assert_engine, compose, operation_lock, wait_ready,
    )
    from bench.rq4 import config_fingerprint, save_row, settle, wait_replicas, wait_settings
    from bench.schema import create_index_sql, drop_index_sql
    from experiments.rq1_covering import (
        explain_sample, fast_connect, mysql_counters, run_queries,
    )

    engine = args.engine
    assert_engine(engine)
    if engine == "tidb":
        # Same containers and limits as RQ1, coprocessor result cache switched off.
        compose("-f", str(ROOT / "docker/tidb-rq1.yml"), "up", "-d", "--no-deps", "tidb")
    wait_ready(engine)
    client = docker.from_env()
    conn = connect(engine)
    levels = [p for p in LEVELS_PCT if p <= args.max_pct]
    try:
        if engine == "tidb":
            wait_settings(conn)
        rows, cod = checksum(conn, "shipments")
        if rows != args.rows:
            raise ValueError(f"shipments has {rows} rows, expected {args.rows}")
        with conn.cursor() as cur:
            cur.execute("SHOW INDEX FROM shipments")
            if "idx_cod" not in {r[2] for r in cur.fetchall()}:
                cur.execute(create_index_sql("shipments", "idx_cod"))
        analyze(conn, "shipments", engine=engine)
        if engine == "tidb":
            wait_replicas(conn, 3)
        settings = engine_settings(conn, engine)
        containers = {
            s: compose("ps", "-q", s, capture=True).strip() for s in SERVICES[engine]
        }
        config_id = config_fingerprint(client, containers)
        params = {p: params_for(p, args.params, args.big_params) for p in levels}
        params_sha = hashlib.sha256(json.dumps(params).encode()).hexdigest()[:12]
        done = done_trials(args.output, engine, rows, config_id, params_sha)
        started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{started}_{settings['machine']}_rq2_{engine}"
        folder = ROOT / "results/raw" / run_id
        folder.mkdir(parents=True)
        (folder / "params.json").write_text(json.dumps(params), encoding="utf-8")
        sqls = {
            (p, m): [render(m, lo, hi) for lo, hi in params[p]] for p in levels for m in MODES
        }
        ops = {k: check_plans(conn, engine, k[1], v[:3]) for k, v in sqls.items()}
        fast = fast_connect(engine)
        # Unmeasured pass: warms the caches and proves every mode returns the same rows.
        counts = {}
        for p in levels:
            per_mode = {m: [n for _, n in run_queries(fast, sqls[p, m])] for m in MODES}
            if len({tuple(v) for v in per_mode.values()}) != 1:
                raise ValueError(f"{p}%: the three modes return different row counts")
            counts[p] = per_mode["index"]
            print(f"{p}%: R={fmean(counts[p]):.0f}, plans {sorted(ops[p, 'auto'])}", flush=True)
        failures = folder / "failures.txt"
        print(f"{run_id}: {len(levels)} levels, params {params_sha}", flush=True)
        for rep in range(1, args.reps + 1):
            todo = [(p, m) for p in levels for m in MODES if (p, m, rep) not in done]
            if not todo:
                continue
            Random(rep).shuffle(todo)
            settle_s, settled = settle(client, containers, SERVICES[engine])
            if not settled:
                raise SystemExit("The disk did not settle. Run the same command again.")
            for pct, mode in todo:
                name = f"{pct}_{mode}_{rep}"
                try:
                    warm = 5 if pct <= 2 else 1
                    run_queries(fast, sqls[pct, mode][:warm])
                    before = mysql_counters(fast.cursor()) if engine == "mysql" else None
                    measured = run_queries(fast, sqls[pct, mode])
                    handlers = disk_reads = ""
                    if before:
                        after = mysql_counters(fast.cursor())
                        handlers = (after[0] - before[0]) / len(measured)
                        disk_reads = after[1] - before[1]
                    if [n for _, n in measured] != counts[pct]:
                        raise ValueError(f"{name}: unexpected number of rows")
                    sample = EXPLAIN_SAMPLES if pct <= 2 else EXPLAIN_SAMPLES_BIG
                    info = explain_sample(conn, engine, sqls[pct, mode][:sample], folder, name)
                except Exception as exc:  # a level that cannot run is a result, not a crash
                    failures.open("a", encoding="utf-8").write(f"{name}: {exc!r}\n")
                    print(f"{name}: FAILED {exc!r}", flush=True)
                    wait_ready(engine)
                    fast = fast_connect(engine)
                    conn = connect(engine)
                    continue
                ms = [t / 1e6 for t, _ in measured]
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
                    pct=pct,
                    mode=mode,
                    rep=rep,
                    access_op="/".join(sorted(ops[pct, mode])),
                    n_queries=len(ms),
                    rows_mean=round(fmean(counts[pct]), 2),
                    p50_ms=round(median(ms), 4),
                    p95_ms=round(percentile(ms, 0.95), 4),
                    p99_ms=round(percentile(ms, 0.99), 4),
                    mean_ms=round(fmean(ms), 4),
                    handler_reads_per_query=handlers,
                    buffer_pool_reads=disk_reads,
                    **info,
                    counts_sha=counts_digest(counts[pct]),
                    params_sha=params_sha,
                    config_id=config_id,
                    settle_s=settle_s,
                    settled=int(settled),
                )
                save_row(args.output, row)
                print(f"{name} p50={row['p50_ms']} ms {row['access_op']}", flush=True)
        fast.close()
    finally:
        try:
            if not args.keep_index:
                with conn.cursor() as cur:
                    cur.execute(drop_index_sql("shipments", "idx_cod"))
            conn.close()
        finally:
            if engine == "tidb":
                compose("up", "-d", "--no-deps", "tidb")
                wait_ready("tidb")
            client.close()


def main():
    from bench.config import get_machine_id

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["mysql", "tidb"])
    parser.add_argument("rows", type=int, nargs="?", default=3_000_000)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--params", type=int, default=20, help="ranges per level up to 2%%")
    parser.add_argument("--big-params", type=int, default=3, help="ranges per level above 2%%")
    parser.add_argument("--max-pct", type=float, default=50.0)
    parser.add_argument("--keep-index", action="store_true")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--output", type=Path, default=root / f"results/rq2_{get_machine_id()}.csv")
    args = parser.parse_args()
    if min(args.reps, args.params, args.big_params) < 1:
        raise SystemExit("reps, params and big-params must be positive")
    from bench.environment import operation_lock

    with operation_lock():
        run(args)


if __name__ == "__main__":
    main()
