"""B.1: measured size of the table and of each secondary index, and the cost of
building each index.

python -m experiments.b1_storage {mysql,tidb} [ROWS ...]

For every scale a fresh table b1_<rows> is loaded in database logistics_b1. The
indexes of set 5 are then created one at a time, followed by idx_sender_cov.

MySQL  pages from mysql.innodb_index_stats after ANALYZE: allocated pages (size)
       and leaf pages (n_leaf_pages). One copy, 16 KiB pages, no compression.
TiDB   one copy, read on store tikv1 with `tikv-ctl size` per Region. This is the
       logical size of the key-value pairs in SST files, before compression.
       Rows are loaded by normal transactions, so tikv1 is compacted first to flush
       its memtables; indexes are built by ingest and land in SST files directly.
       Every Region holding data must lie inside the range of that table or index.
Build cost: wall time, average CPUs used and bytes written by the database
containers between the start and the end of CREATE INDEX.
"""

import argparse
import re
import subprocess
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

from bench import config
from bench.config import get_machine_id

SEED = 20261116
DATABASE = "logistics_b1"
ORDER = ["idx_code", "idx_sender_created", "idx_hub_status", "idx_cod", "idx_status",
         "idx_sender_cov"]
SET5 = ORDER[:5]
# Split points below every value of each index, so each index starts a Region.
FLOOR = {
    "idx_code": "('0')",
    "idx_sender_created": "(-1, '1970-01-01 00:00:00')",
    "idx_sender_cov": "(-1, '1970-01-01 00:00:00', -1, -1)",
    "idx_hub_status": "(-1, -1)",
    "idx_cod": "(-1)",
    "idx_status": "(-1)",
}
UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
STORE = "tikv1"
FIELDS = [
    "run_id", "machine", "profile", "engine", "version", "replica_config", "rows",
    "sum_cod", "object", "bytes", "leaf_bytes", "regions", "isolated", "build_s",
    "cpus", "memory_before_mib", "memory_peak_mib", "memory_after_mib",
    "read_mib", "write_mib", "config_id",
]


def table_name(rows):
    return f"b1_{rows}"


def parse_ctl_size(text):
    """Bytes in all column families from `tikv-ctl size -r` output."""
    found = re.findall(r"cf \w+ region size: ([\d.]+)\s*(TiB|GiB|MiB|KiB|B)", text)
    if not found:
        raise ValueError(f"Unexpected tikv-ctl output: {text!r}")
    return round(sum(float(v) * UNITS[u] for v, u in found))


def region_inside(start, end, table_id, index_id=None):
    """True if [start, end) holds keys of this table's rows, or of this index, only.

    Index ids grow in creation order, so an index ends where the next id or the
    rows begin. Rows end where the next table begins.
    """
    if index_id is None:
        own = f"t_{table_id}_r"
        return start.startswith(own) and (end == "" or end.startswith(own)
                                          or not end.startswith(f"t_{table_id}_"))
    own = f"t_{table_id}_i_{index_id}_"
    return start.startswith(own) and (
        end.startswith((own, f"t_{table_id}_r")) or end == f"t_{table_id}_i_{index_id + 1}_"
    )


def ctl(*args):
    out = subprocess.run(
        ["docker", "exec", f"nhom7xs-{STORE}-1", "/tikv-ctl", "--host", f"{STORE}:20160",
         *args],
        capture_output=True, text=True, check=True,
    )
    return out.stdout + out.stderr


def tidb_ids(cur, table, index=None):
    cur.execute(
        "SELECT tidb_table_id FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=%s", (table,))
    table_id = cur.fetchone()[0]
    if index is None:
        return table_id, None
    cur.execute(
        "SELECT index_id FROM information_schema.tidb_indexes WHERE table_schema=DATABASE() "
        "AND table_name=%s AND key_name=%s LIMIT 1", (table, index))
    return table_id, cur.fetchone()[0]


def tidb_size(cur, table, index=None):
    """(bytes, Regions, isolated) of the rows or of one index, one copy on STORE."""
    table_id, index_id = tidb_ids(cur, table, index)
    cur.execute("SELECT store_id FROM information_schema.tikv_store_status WHERE address=%s",
                (f"{STORE}:20160",))
    store_id = str(cur.fetchone()[0])
    cur.execute(f"SHOW TABLE {table} REGIONS" if index is None
                else f"SHOW TABLE {table} INDEX {index} REGIONS")
    cols = [d[0] for d in cur.description]
    regions = [dict(zip(cols, r)) for r in cur.fetchall()]
    if index is None:
        regions = [r for r in regions if r["START_KEY"].startswith(f"t_{table_id}_r")]
    total, isolated = 0, bool(regions)
    for region in regions:
        cur.execute("SELECT store_id FROM information_schema.tikv_region_peers "
                    "WHERE region_id=%s", (region["REGION_ID"],))
        if store_id not in {str(r[0]) for r in cur.fetchall()}:
            raise RuntimeError(f"Region {region['REGION_ID']} has no peer on {STORE}")
        size = parse_ctl_size(ctl("size", "-r", str(region["REGION_ID"])))
        # An empty Region may start outside the range; one holding data may not.
        inside = region_inside(region["START_KEY"], region["END_KEY"], table_id, index_id)
        isolated &= inside or size == 0
        total += size
    return total, len(regions), int(isolated)


def mysql_pages(cur, table):
    """{index: (allocated pages, leaf pages)} from persistent statistics."""
    cur.execute(
        "SELECT index_name, stat_name, stat_value FROM mysql.innodb_index_stats "
        "WHERE database_name=DATABASE() AND table_name=%s "
        "AND stat_name IN ('size','n_leaf_pages')", (table,))
    out = {}
    for index, stat, value in cur.fetchall():
        out.setdefault(index, {})[stat] = int(value)
    return {k: (v["size"], v["n_leaf_pages"]) for k, v in out.items()}


def dataset(rows):
    from bench.environment import ROOT

    path = ROOT / f"data/shipments_{rows}_{SEED}.tsv"
    if not path.exists():
        from bench.datagen import write_csv

        temp = path.with_suffix(".tmp")
        write_csv(rows, temp, SEED)
        temp.replace(path)
    total = count = 0
    with path.open("rb") as stream:
        for line in stream:
            count += 1
            total += int(line.split(b"\t", 7)[6])
    return path, count, total


def run(args):
    import docker
    from bench.config import get_engine_config
    from bench.db import analyze, checksum, connect, engine_settings
    from bench.environment import SERVICES, assert_engine, compose, wait_ready
    from bench.loader import load_tsv
    from bench.resources import resource_snapshot
    from bench.rq4 import config_fingerprint, save_row, wait_replicas, wait_settings
    from bench.schema import create_index_sql, shipments_ddl

    engine = args.engine
    assert_engine(engine)
    if get_engine_config(engine)["database"] != DATABASE:
        raise SystemExit(f"Refusing to run outside {DATABASE}")
    if args.output.exists() and any(
        f",{engine}," in line for line in args.output.read_text(encoding="utf-8").splitlines()[1:]
    ):
        raise SystemExit(f"{args.output} already has {engine} rows. Use --output.")
    wait_ready(engine)
    with connect(engine, server_only=True) as server, server.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    client = docker.from_env()
    conn = connect(engine)
    cur = conn.cursor()
    try:
        if engine == "tidb":
            wait_settings(conn)
        settings = engine_settings(conn, engine)
        containers = {s: compose("ps", "-q", s, capture=True).strip() for s in SERVICES[engine]}
        config_id = config_fingerprint(client, containers)
        started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        common = {
            "run_id": f"{started}_{settings['machine']}_b1_{engine}",
            "machine": settings["machine"],
            "profile": settings["profile"],
            "engine": engine,
            "version": settings["version"].splitlines()[0],
            "replica_config": settings.get("replica_config", ""),
            "config_id": config_id,
        }

        def save(rows, total, obj, **values):
            row = {**common, "rows": rows, "sum_cod": total, "object": obj, **values}
            save_row(args.output, {f: row.get(f, "") for f in FIELDS})
            mib = values.get("bytes", 0) / 1024**2
            print(f"{engine} {rows} {obj}: {mib:.1f} MiB {values}", flush=True)

        loaded = []
        for rows in args.rows:
            path, count, total = dataset(rows)
            table = table_name(rows)
            print(f"{table}: loading {count} rows", flush=True)
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            cur.execute(shipments_ddl(engine, "bigint_clustered", table))
            start = time.monotonic()
            load_tsv(cur, path, table)
            print(f"{table}: loaded in {time.monotonic() - start:.0f} s", flush=True)
            if checksum(conn, table) != (count, total):
                raise ValueError(f"{table}: row count or SUM(cod_amount) differs from the TSV")
            if engine == "tidb":
                cur.execute(f"SPLIT TABLE {table} BY (0)")
                cur.fetchall()
            loaded.append((rows, total, table))

        if engine == "tidb":
            wait_replicas(conn, 3)
            # Rows written by transactions may still sit in memtables. A manual
            # compaction flushes them, so the SST sizes below include every row.
            for cf in ("default", "write"):
                start = time.monotonic()
                print(ctl("compact", "-d", "kv", "-c", cf).strip(), flush=True)
                print(f"compact {cf}: {time.monotonic() - start:.0f} s", flush=True)

        for rows, total, table in loaded:
            if engine == "tidb":
                size, regions, isolated = tidb_size(cur, table)
                save(rows, total, "rows", bytes=size, regions=regions, isolated=isolated)
            else:
                analyze(conn, table, engine=engine)
                cur.execute("SELECT @@innodb_page_size")
                page = int(cur.fetchone()[0])
                size, leaf = mysql_pages(cur, table)["PRIMARY"]
                save(rows, total, "rows", bytes=size * page, leaf_bytes=leaf * page)
            for index in ORDER:
                before = resource_snapshot(client, containers)
                start = time.monotonic()
                stop_monitor = threading.Event()
                during = {}

                def monitor_resources():
                    peak = 0
                    while not stop_monitor.is_set():
                        try:
                            snapshot = resource_snapshot(client, containers)
                            peak = max(
                                peak,
                                sum(s["memory_bytes"] for s in snapshot["services"].values()),
                            )
                            during["memory_peak_bytes"] = peak
                        except Exception:
                            pass
                        stop_monitor.wait(0.2)

                monitor = threading.Thread(target=monitor_resources, daemon=True)
                monitor.start()
                try:
                    cur.execute(create_index_sql(table, index))
                finally:
                    stop_monitor.set()
                    monitor.join(timeout=2)
                build_s = time.monotonic() - start
                after = resource_snapshot(client, containers)
                wall = after["time_ns"] - before["time_ns"]

                def delta(field, a=after, b=before):
                    return sum(a["services"][s][field] - b["services"][s][field]
                               for s in containers)

                cost = {
                    "build_s": round(build_s, 1),
                    "cpus": round(delta("cpu_ns") / wall, 2),
                    "memory_before_mib": round(
                        sum(s["memory_bytes"] for s in before["services"].values()) / 1024**2, 1
                    ),
                    "memory_peak_mib": round(
                        during.get("memory_peak_bytes", sum(
                            s["memory_bytes"] for s in after["services"].values()
                        )) / 1024**2, 1
                    ),
                    "memory_after_mib": round(
                        sum(s["memory_bytes"] for s in after["services"].values()) / 1024**2, 1
                    ),
                    "read_mib": round(delta("read_bytes") / 1024**2, 1),
                    "write_mib": round(delta("write_bytes") / 1024**2, 1),
                }
                if engine == "tidb":
                    cur.execute(f"SPLIT TABLE {table} INDEX {index} BY {FLOOR[index]}")
                    cur.fetchall()
                    wait_replicas(conn, 3)
                    size, regions, isolated = tidb_size(cur, table, index)
                    save(rows, total, index, bytes=size, regions=regions,
                         isolated=isolated, **cost)
                else:
                    analyze(conn, table, engine=engine)
                    size, leaf = mysql_pages(cur, table)[index]
                    save(rows, total, index, bytes=size * page, leaf_bytes=leaf * page, **cost)
    finally:
        cur.close()
        conn.close()
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["mysql", "tidb"])
    parser.add_argument("rows", type=int, nargs="*", default=[1_000_000, 3_000_000])
    parser.add_argument(
        "--output", type=Path, default=Path(f"results/b1_storage_{get_machine_id()}.csv"))
    args = parser.parse_args()
    if not args.rows or min(args.rows) < 1:
        raise SystemExit("rows must be positive")
    # bench.config reads DB_NAME when it is imported, so the parsed settings change here.
    for settings in config.ENGINES.values():
        settings["database"] = DATABASE
    from bench.environment import operation_lock

    with operation_lock():
        run(args)


if __name__ == "__main__":
    main()
