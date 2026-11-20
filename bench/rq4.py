"""Run the RQ4 matrix on disposable copies of the verified baseline."""

import csv
import json
import math
import re
import signal
import subprocess
import time
from contextlib import contextmanager
from itertools import product
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

import docker

from .config import get_engine_config
from .db import analyze, checksum, connect, engine_settings
from .environment import ROOT, SERVICES, assert_engine, compose
from .resources import resource_snapshot
from .schema import RQ4_INDEX_SETS, create_index_sql, shipments_ddl


def parse_sysbench(log):
    trx = re.search(r"transactions:\s+(\d+)\s+\(([\d.]+) per sec", log)
    if not trx or int(trx[1]) == 0:
        raise ValueError("Missing completed transactions in sysbench output")
    buckets = [
        (float(ms), int(count))
        for ms, count in re.findall(r"^\s*([\d.]+)\s+\|[^\d\n]*?(\d+)\s*$", log, re.M)
    ]
    total = sum(count for _, count in buckets)
    if total != int(trx[1]):
        raise ValueError(
            f"Latency histogram has {total} samples for {trx[1]} transactions"
        )

    def percentile(p):
        target, seen = math.ceil(total * p), 0
        for ms, count in buckets:
            seen += count
            if seen >= target:
                return ms

    return dict(
        transactions=int(trx[1]),
        tps=float(trx[2]),
        p95_ms=percentile(0.95),
        p99_ms=percentile(0.99),
    )


def set_replicas(conn, count):
    with conn.cursor() as cur:
        cur.execute(f"SET CONFIG pd `replication.max-replicas` = {count}")
    deadline = time.monotonic() + 300
    while True:
        actual = engine_settings(conn, "tidb")["max_replicas"]
        # The PD setting changes before placement has necessarily converged.
        with urlopen("http://127.0.0.1:2379/pd/api/v1/regions", timeout=10) as response:
            regions = json.load(response)["regions"]
        if (
            actual == count
            and regions
            and all(
                len(r["peers"]) == count
                and not r.get("pending_peers")
                and not r.get("down_peers")
                for r in regions
            )
        ):
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Region placement did not converge to {count} replicas")
        time.sleep(2)


@contextmanager
def measured_table(conn, engine, rows, total_cod, index_count):
    table = "rq4_" + uuid4().hex
    with conn.cursor() as cur:
        cur.execute(shipments_ddl(engine, table=table))
        try:
            for lo in range(0, rows, 10000):
                cur.execute(
                    f"INSERT INTO {table} SELECT * FROM shipments WHERE id > %s AND id <= %s",
                    (lo, min(lo + 10000, rows)),
                )
            if checksum(conn, table) != (rows, total_cod):
                raise ValueError("Trial table differs from the baseline")
            for idx in RQ4_INDEX_SETS[index_count]:
                cur.execute(create_index_sql(table, idx))
            analyze(conn, table, engine=engine)
            yield table
        finally:
            cur.execute(f"DROP TABLE {table}")


def measure(args, client, containers, table, threads, mode, run_id):
    folder = ROOT / "results/raw" / run_id
    folder.mkdir(parents=True)
    config = get_engine_config(args.engine)
    port = 4000 if args.engine == "tidb" else 3306
    command = [
        "docker",
        "exec",
        containers["sysbench"],
        "sysbench",
        "/work/shipments_write.lua",
        f"--mysql-host={args.engine}",
        f"--mysql-port={port}",
        f"--mysql-user={config['user']}",
        f"--mysql-db={config['database']}",
        f"--table-name={table}",
        f"--max-id={args.rows}",
        f"--threads={threads}",
        f"--mode={mode}",
        f"--time={args.seconds}",
        "--report-interval=1",
        "--histogram=on",
        "run",
    ]
    log = folder / "sysbench.log"
    with log.open("w", encoding="utf-8") as output, (folder / "resources.jsonl").open(
        "w"
    ) as samples:

        def capture():
            snapshot = resource_snapshot(client, containers)
            samples.write(json.dumps(snapshot) + "\n")
            samples.flush()
            return snapshot

        first = capture()
        proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None:
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    capture()
            if proc.returncode:
                raise RuntimeError(f"sysbench failed, see {log}")
            last = capture()
        finally:
            if proc.poll() is None:
                compose("stop", "sysbench")
                proc.wait(timeout=20)
    values = parse_sysbench(log.read_text(encoding="utf-8"))

    def delta(service, field):
        diff = last["services"][service][field] - first["services"][service][field]
        if diff < 0:
            raise ValueError(f"Counter reset: {service}/{field}")
        return diff

    values["sysbench_cpu_pct"] = (
        100 * delta("sysbench", "cpu_ns") / (last["time_ns"] - first["time_ns"])
    )
    values["disk_write_bytes"] = sum(
        delta(s, "write_bytes") for s in SERVICES[args.engine]
    )
    values["bytes_per_transaction"] = (
        values["disk_write_bytes"] / values["transactions"]
    )
    return values


def save_row(path: Path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    if exists:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            if next(csv.reader(stream)) != list(row):
                raise ValueError(f"Existing CSV has a different schema: {path}")
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def benchmark(args):
    if min(args.seconds, args.reps, args.rows, *args.threads) < 1:
        raise ValueError("rows, seconds, repetitions and threads must be positive")
    assert_engine(args.engine)
    with connect(args.engine) as conn, conn.cursor() as cur:
        rows, cod = checksum(conn, "shipments")
        cur.execute("SELECT MIN(id), MAX(id) FROM shipments")
        if rows != args.rows or cur.fetchone() != (1, rows):
            raise ValueError(
                "RQ4 requires the requested number of contiguous baseline IDs from 1"
            )
        compose("up", "-d", "--build", "sysbench")
        client = docker.from_env()

        def interrupt(signum, frame):
            raise KeyboardInterrupt

        previous = signal.signal(signal.SIGTERM, interrupt)
        try:
            containers = {
                s: compose("ps", "-q", s, capture=True).strip()
                for s in [*SERVICES[args.engine], "sysbench"]
            }
            replica_values = args.replicas if args.engine == "tidb" else [1]
            if args.engine == "mysql":
                cur.execute("SET SESSION information_schema_stats_expiry=0")
            for rf in replica_values:
                if args.engine == "tidb":
                    set_replicas(conn, rf)
                for ix, th, mode, rep in product(
                    args.indexes, args.threads, args.mode, range(1, args.reps + 1)
                ):
                    with measured_table(conn, args.engine, rows, cod, ix) as table:
                        settings = engine_settings(conn, args.engine)
                        if args.engine == "tidb" and settings["max_replicas"] != rf:
                            raise RuntimeError(
                                "Replica setting changed before measurement"
                            )
                        run_id = table + "_" + mode
                        metrics = measure(
                            args, client, containers, table, th, mode, run_id
                        )
                        after_rows, _ = checksum(conn, table)
                        expected = rows + (
                            metrics["transactions"] if mode == "insert" else 0
                        )
                        if after_rows != expected:
                            raise ValueError(
                                f"Expected {expected} rows after {mode}, got {after_rows}"
                            )
                        analyze(conn, table, engine=args.engine)
                        cur.execute(
                            "SELECT data_length,index_length FROM information_schema.tables "
                            "WHERE table_schema=DATABASE() AND table_name=%s",
                            (table,),
                        )
                        data_bytes, index_bytes = cur.fetchone()
                        row = dict(
                            run_id=run_id,
                            machine=settings["machine"],
                            profile=settings["profile"],
                            engine=args.engine,
                            version=settings["version"].splitlines()[0],
                            replicas=rf,
                            max_replicas=settings.get("max_replicas", ""),
                            block_cache=settings.get("block_cache", ""),
                            buffer_pool=settings.get("buffer_pool", ""),
                            baseline_rows=rows,
                            sum_cod=cod,
                            n_indexes=ix,
                            threads=th,
                            mode=mode,
                            rep=rep,
                            duration_s=args.seconds,
                            **metrics,
                            final_rows=after_rows,
                            table_bytes=int(data_bytes),
                            index_bytes=int(index_bytes),
                        )
                        save_row(args.output, row)
                        print(
                            run_id,
                            mode,
                            metrics["transactions"],
                            "transactions",
                            flush=True,
                        )
        finally:
            try:
                if args.engine == "tidb":
                    with connect("tidb") as recovery:
                        set_replicas(recovery, 3)
            finally:
                signal.signal(signal.SIGTERM, previous)
                compose("stop", "sysbench")
                client.close()
