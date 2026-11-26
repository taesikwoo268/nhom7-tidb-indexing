"""RQ3: how the primary key variant changes secondary index size and lookups.

python -m experiments.rq3_pk {mysql,tidb} ROWS

Every variant table holds the same rows and the same logical keys: a unique key on
id, a unique key on tracking_code and idx_sender_created. Only the clustered key
changes. TiDB has three variants, MySQL two (InnoDB always clusters on the PK).

Size of idx_sender_created (one copy of the data):
  MySQL  pages of the index in mysql.innodb_index_stats (after ANALYZE).
  TiDB   the index is split into Regions of its own, every Region is checked to lie
         inside the index key range, and `tikv-ctl size` reads the size of each
         Region from the SST range properties of the store holding its leader.
         PD statistics are not used: they are refreshed only when a Region changes.
Lookups by id, by tracking_code and through idx_sender_created are timed as in RQ1.
"""

import argparse
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from statistics import fmean, median

from bench import config
from bench.config import get_machine_id

SEED = 20261116
DATABASE = "logistics_rq3"
VARIANTS = {
    "tidb": ["bigint_clustered", "bigint_nonclustered", "code_clustered"],
    "mysql": ["bigint_clustered", "code_clustered"],
}
INDEX = "idx_sender_created"
QUERIES = {
    "by_id": "SELECT status,updated_at FROM {table} WHERE id={0}",
    "by_code": "SELECT status,updated_at FROM {table} WHERE tracking_code='{0}'",
    "secondary": "SELECT id,created_at,status,cod_amount FROM {table} "
    "FORCE INDEX (" + INDEX + ") WHERE sender_id={0} AND created_at>='{1}' "
    "ORDER BY created_at DESC LIMIT 20",
}
EXPECTED_ROWS = {"by_id": 1, "by_code": 1, "secondary": 20}
Q2_SINCE = "2026-08-01 00:00:00"
EXPLAIN_SAMPLES = 10
# Split points below every value, so the index and the rows start new Regions.
INDEX_FLOOR = "(0, '1970-01-01 00:00:00')"
ROW_FLOOR = {"bigint_clustered": "(0)", "bigint_nonclustered": "(0)", "code_clustered": "('0')"}
# One schema for both engines; fields that do not apply stay empty.
SIZE_FIELDS = [
    "load_s", "fast_reorg", "build_s", "index_bytes", "index_entries", "bytes_per_entry",
    "index_leaf_pages", "primary_bytes", "other_unique_bytes", "regions", "isolated",
]
UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}


def table_name(variant):
    return f"rq3_{variant}"


def extra_unique(variant):
    """The unique key that the DDL does not create, so every table has both."""
    return None if variant == "code_clustered" else "idx_code"


def render(query, variant, params):
    return QUERIES[query].format(*params, table=table_name(variant))


# ---- sizes ----------------------------------------------------------------------


def parse_ctl_size(text):
    """Bytes in all column families from `tikv-ctl size -r` output."""
    found = re.findall(r"cf \w+ region size: ([\d.]+)\s*(TiB|GiB|MiB|KiB|B)", text)
    if not found:
        raise ValueError(f"Unexpected tikv-ctl output: {text!r}")
    return round(sum(float(v) * UNITS[u] for v, u in found))


def inside_index(start, end, table_id, index_id):
    """True if a Region [start, end) holds keys of this index only.

    Keys are shown as t_<table>_i_<index>_<value>. The index has the highest id of
    the table, so up to the first row key t_<table>_r nothing else can sit.
    """
    prefix = f"t_{table_id}_i_{index_id}_"
    return start.startswith(prefix) and bool(end) and end <= f"t_{table_id}_r"


def tidb_index_size(cur, table):
    """(bytes, Regions, isolated) of INDEX, read from TiKV for one copy."""
    cur.execute(
        "SELECT t.tidb_table_id, i.index_id FROM information_schema.tables t "
        "JOIN information_schema.tidb_indexes i ON i.table_schema=t.table_schema "
        "AND i.table_name=t.table_name WHERE t.table_schema=DATABASE() "
        "AND t.table_name=%s AND i.key_name=%s LIMIT 1",
        (table, INDEX),
    )
    table_id, index_id = cur.fetchone()
    cur.execute("SELECT store_id, address FROM information_schema.tikv_store_status")
    hosts = {int(s): a for s, a in cur.fetchall()}
    cur.execute(f"SHOW TABLE {table} INDEX {INDEX} REGIONS")
    cols = [d[0] for d in cur.description]
    regions = [dict(zip(cols, r)) for r in cur.fetchall()]
    total, isolated = 0, True
    for region in regions:
        isolated &= inside_index(region["START_KEY"], region["END_KEY"], table_id, index_id)
        host = hosts[int(region["LEADER_STORE_ID"])]
        container = f"{config_project()}-{host.split(':')[0]}-1"
        out = subprocess.run(
            ["docker", "exec", container, "/tikv-ctl", "--host", host, "size", "-r",
             str(region["REGION_ID"])],
            capture_output=True, text=True, check=True,
        )
        total += parse_ctl_size(out.stdout + out.stderr)
    return total, len(regions), int(isolated)


def config_project():
    from bench.environment import PROJECT

    return PROJECT


def mysql_index_pages(cur, table):
    """{index: (size pages, leaf pages)} from persistent statistics."""
    cur.execute(
        "SELECT index_name, stat_name, stat_value FROM mysql.innodb_index_stats "
        "WHERE database_name=DATABASE() AND table_name=%s "
        "AND stat_name IN ('size','n_leaf_pages')",
        (table,),
    )
    out = {}
    for index, stat, value in cur.fetchall():
        out.setdefault(index, {})[stat] = int(value)
    return {k: (v.get("size", 0), v.get("n_leaf_pages", 0)) for k, v in out.items()}


# ---- run ------------------------------------------------------------------------


def dataset(rows):
    """Path, row count and SUM(cod_amount) of the shared TSV (generated if missing)."""
    from bench.datagen import write_csv
    from bench.environment import ROOT

    path = ROOT / f"data/shipments_{rows}_{SEED}.tsv"
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        temp = path.with_suffix(".tmp")
        write_csv(rows, temp, SEED)
        temp.replace(path)
    count = total = 0
    with path.open("rb") as stream:
        for line in stream:
            count += 1
            total += int(line.split(b"\t", 7)[6])
    return path, count, total


def build_variant(conn, engine, variant, path, rows, total):
    """Create and load one variant table. Return its size row (without run fields)."""
    from bench.db import analyze, checksum
    from bench.loader import load_tsv
    from bench.rq4 import wait_replicas
    from bench.schema import create_index_sql, shipments_ddl

    table = table_name(variant)
    cur = conn.cursor()
    cur.execute(f"DROP TABLE IF EXISTS {table}")
    cur.execute(shipments_ddl(engine, variant, table))
    start = time.monotonic()
    load_tsv(cur, path, table)
    load_s = round(time.monotonic() - start, 1)
    if checksum(conn, table) != (rows, total):
        raise ValueError(f"{table}: row count or SUM(cod_amount) differs from the TSV")
    if extra_unique(variant):
        cur.execute(create_index_sql(table, extra_unique(variant)))
    row = {"load_s": load_s, "index_entries": rows}
    if engine == "tidb":
        cur.execute("SELECT @@tidb_ddl_enable_fast_reorg")
        row["fast_reorg"] = cur.fetchone()[0]
    start = time.monotonic()
    cur.execute(create_index_sql(table, INDEX))
    row["build_s"] = round(time.monotonic() - start, 1)
    analyze(conn, table, engine=engine)
    if engine == "tidb":
        for sql in (
            f"SPLIT TABLE {table} INDEX {INDEX} BY {INDEX_FLOOR}",
            f"SPLIT TABLE {table} BY {ROW_FLOOR[variant]}",
        ):
            cur.execute(sql)
            cur.fetchall()
        wait_replicas(conn, 3)
        size, regions, isolated = tidb_index_size(cur, table)
        row.update(index_bytes=size, regions=regions, isolated=isolated)
    else:
        cur.execute("SELECT @@innodb_page_size")
        page = int(cur.fetchone()[0])
        pages = mysql_index_pages(cur, table)
        size, leaf = pages[INDEX]
        row.update(
            index_bytes=size * page,
            index_leaf_pages=leaf,
            primary_bytes=pages["PRIMARY"][0] * page,
            other_unique_bytes=pages["idx_code" if extra_unique(variant) else "uk_id"][0] * page,
        )
    row["bytes_per_entry"] = round(row["index_bytes"] / rows, 1)
    cur.close()
    return row


def sample_params(conn, k, seed=SEED):
    """Same ids, codes and senders for every variant (taken from the first table)."""
    rng = Random(seed)
    cur = conn.cursor()
    table = table_name("bigint_clustered")
    cur.execute(f"SELECT MAX(id) FROM {table}")
    ids = rng.sample(range(1, cur.fetchone()[0] + 1), k)
    marks = ",".join(["%s"] * len(ids))
    cur.execute(f"SELECT id,tracking_code FROM {table} WHERE id IN ({marks})", ids)
    codes = dict(cur.fetchall())
    cur.execute(
        f"SELECT sender_id FROM {table} WHERE created_at>=%s GROUP BY sender_id "
        "HAVING COUNT(*)>=20 ORDER BY sender_id",
        (Q2_SINCE,),
    )
    senders = rng.choices([r[0] for r in cur.fetchall()], k=k)
    cur.close()
    return {
        "by_id": [(i,) for i in ids],
        "by_code": [(codes[i],) for i in ids],
        "secondary": [(s, Q2_SINCE) for s in senders],
    }


def plan_of(conn, engine, sql):
    """Access operator and index chosen for one query."""
    from experiments.rq1_covering import tidb_plan

    with conn.cursor(dictionary=engine == "mysql") as cur:
        cur.execute("EXPLAIN " + sql)
        rows = cur.fetchall()
    if engine == "mysql":
        # One row per table access: join type and index, e.g. const:PRIMARY.
        return "/".join(f"{r['type']}:{r['key']}" for r in rows)
    op, index = tidb_plan(rows)
    return f"{op}:{index}"


def run(args):
    import docker
    from bench.config import get_engine_config
    from bench.db import connect, engine_settings
    from bench.environment import ROOT, SERVICES, assert_engine, compose, wait_ready
    from bench.rq4 import config_fingerprint, save_row, settle, wait_settings
    from experiments.rq1_covering import (
        explain_sample,
        fast_connect,
        percentile,
        result_digest,
        run_queries,
    )

    engine = args.engine
    assert_engine(engine)
    if get_engine_config(engine)["database"] != DATABASE:
        raise SystemExit(f"Refusing to run outside {DATABASE}")
    for path in (args.output, args.size_output):
        if path.exists() and any(
            f",{engine}," in line and f",{args.rows}," in line
            for line in path.read_text(encoding="utf-8").splitlines()[1:]
        ):
            raise SystemExit(f"{path} already has {engine} rows at {args.rows}. Use --output.")
    if engine == "tidb":
        # Coprocessor result cache off, as in RQ1.
        compose("-f", str(ROOT / "docker/tidb-rq1.yml"), "up", "-d", "--no-deps", "tidb")
    wait_ready(engine)
    path, rows, total = dataset(args.rows)
    with connect(engine, server_only=True) as server, server.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    client = docker.from_env()
    conn = connect(engine)
    try:
        if engine == "tidb":
            wait_settings(conn)
        settings = engine_settings(conn, engine)
        containers = {s: compose("ps", "-q", s, capture=True).strip() for s in SERVICES[engine]}
        config_id = config_fingerprint(client, containers)
        started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{started}_{settings['machine']}_rq3_{engine}"
        folder = ROOT / "results/raw" / run_id
        folder.mkdir(parents=True)
        common = {
            "run_id": run_id,
            "machine": settings["machine"],
            "profile": settings["profile"],
            "engine": engine,
            "version": settings["version"].splitlines()[0],
            "replica_config": settings.get("replica_config", ""),
            "rows": rows,
            "sum_cod": total,
            "config_id": config_id,
        }
        variants = VARIANTS[engine]
        for variant in variants:
            print(f"{variant}: loading {rows} rows", flush=True)
            size = build_variant(conn, engine, variant, path, rows, total)
            size = {f: size.get(f, "") for f in SIZE_FIELDS}
            save_row(args.size_output, {**common, "pk_variant": variant, **size})
            print(f"{variant}: {INDEX} {size['index_bytes'] / 1024**2:.1f} MiB, "
                  f"{size['bytes_per_entry']} B/entry", flush=True)

        params = sample_params(conn, args.params)
        sqls = {(v, q): [render(q, v, p) for p in params[q]] for v in variants for q in QUERIES}
        ops = {t: plan_of(conn, engine, sqls[t][0]) for t in sqls}
        with fast_connect(engine) as fast:
            digests = {t: result_digest(fast, s) for t, s in sqls.items()}
            for q in QUERIES:
                if len({digests[v, q] for v in variants}) != 1:
                    raise ValueError(f"{q}: variants return different rows")
            for rep in range(1, args.reps + 1):
                todo = list(sqls)
                Random(rep).shuffle(todo)
                settle_s, settled = settle(client, containers, SERVICES[engine])
                for variant, query in todo:
                    batch = sqls[variant, query]
                    run_queries(fast, batch[: args.warmup])
                    measured = run_queries(fast, batch)
                    if any(n != EXPECTED_ROWS[query] for _, n in measured):
                        raise ValueError(f"{variant} {query}: unexpected number of rows")
                    ms = [t / 1e6 for t, _ in measured]
                    name = f"{variant}_{query}_{rep}"
                    info = explain_sample(conn, engine, batch[:EXPLAIN_SAMPLES], folder, name)
                    row = dict(
                        **common,
                        pk_variant=variant,
                        query=query,
                        rep=rep,
                        access_op=ops[variant, query],
                        n_queries=len(ms),
                        p50_ms=round(median(ms), 4),
                        p95_ms=round(percentile(ms, 0.95), 4),
                        mean_ms=round(fmean(ms), 4),
                        **info,
                        result_sha=digests[variant, query],
                        settle_s=settle_s,
                        settled=int(settled),
                    )
                    save_row(args.output, row)
                    print(f"{name} p50={row['p50_ms']} ms {row['access_op']}", flush=True)
    finally:
        conn.close()
        if engine == "tidb":
            compose("up", "-d", "--no-deps", "tidb")
            wait_ready("tidb")
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["mysql", "tidb"])
    parser.add_argument("rows", type=int, nargs="?", default=1_000_000)
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--params", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=50)
    machine = get_machine_id()
    parser.add_argument("--output", type=Path, default=Path(f"results/rq3_{machine}.csv"))
    parser.add_argument(
        "--size-output", type=Path, default=Path(f"results/rq3_size_{machine}.csv")
    )
    args = parser.parse_args()
    if min(args.reps, args.params, args.warmup, args.rows) < 1:
        raise SystemExit("rows, reps, params and warmup must be positive")
    # Separate database: the RQ1 and RQ4 tables stay untouched. bench.config reads
    # DB_NAME when it is imported, so the parsed settings are changed here.
    for settings in config.ENGINES.values():
        settings["database"] = DATABASE
    from bench.environment import operation_lock

    with operation_lock():
        run(args)


if __name__ == "__main__":
    main()
