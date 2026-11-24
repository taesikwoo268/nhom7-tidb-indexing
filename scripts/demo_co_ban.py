"""Basic feature demo for the report (section A.3). Not a performance measurement.

python scripts/demo_co_ban.py {tidb,mysql}

Works only in its own database, demo_nhom7, which is recreated at every run.
The transcript is written to results/runs/demo_<engine>_<machine>.txt.
"""

import argparse
import sys
from itertools import islice
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import mysql.connector  # noqa: E402

from bench.config import get_machine_id  # noqa: E402
from bench.datagen import COLUMNS, generate_rows  # noqa: E402
from bench.db import analyze, connect  # noqa: E402
from bench.environment import assert_engine, operation_lock  # noqa: E402
from bench.schema import create_index_sql, shipments_ddl  # noqa: E402

DATABASE = "demo_nhom7"
ROWS = 20_000
QUERY = (
    "SELECT id, created_at, status, cod_amount FROM shipments{hint} "
    "WHERE sender_id = 500 AND created_at >= '2026-05-01' "
    "ORDER BY created_at DESC LIMIT 20"
)


def demo(engine, out):
    def say(text=""):
        print(text, flush=True)
        out.write(text + "\n")

    with connect(engine, server_only=True) as conn, conn.cursor() as cur:

        def run(sql, show=True):
            if show:
                say(f"sql> {' '.join(sql.split())}")
            cur.execute(sql)
            if cur.with_rows:
                names, rows = cur.column_names, cur.fetchall()
                if show:
                    say("  " + " | ".join(names))
                    for row in rows:
                        say("  " + " | ".join("NULL" if v is None else str(v) for v in row))
                    say(f"  ({len(rows)} rows)")
                return rows
            if show:
                say(f"  OK, {cur.rowcount} rows affected")
            return []

        def title(text):
            say()
            say(f"=== {text} ===")

        title("1. Version and cluster status")
        run("SELECT VERSION()")
        if engine == "tidb":
            run("SELECT tidb_version()")
            run("SELECT store_id, address, store_state_name FROM information_schema.tikv_store_status")

        title("2. Create the table")
        run(f"DROP DATABASE IF EXISTS {DATABASE}", show=False)
        run(f"CREATE DATABASE {DATABASE}")
        run(f"USE {DATABASE}")
        run(shipments_ddl(engine))
        run("SHOW CREATE TABLE shipments")

        title("3. Load sample orders")
        marks = ",".join(["%s"] * len(COLUMNS))
        insert = f"INSERT INTO shipments ({','.join(COLUMNS)}) VALUES ({marks})"
        rows = generate_rows(ROWS)
        while batch := list(islice(rows, 1000)):
            cur.executemany(insert, batch)
        run("SELECT COUNT(*) FROM shipments")

        title("4. Insert, read, update, delete")
        new = ROWS + 1
        run(
            "INSERT INTO shipments (id, tracking_code, sender_id, origin_hub_id, dest_hub_id, status, "
            "cod_amount, weight_grams, shipping_fee, recipient_phone, recipient_address, created_at, updated_at) "
            f"VALUES ({new}, 'VN000000000001', 500, 1, 2, 1, 250000, 1200, 30000, '0900000000', "
            "'Ha Noi', '2026-11-01 08:00:00', '2026-11-01 08:00:00')"
        )
        one = f"SELECT id, tracking_code, status, cod_amount FROM shipments WHERE id = {new}"
        run(one)
        run(f"UPDATE shipments SET status = 2 WHERE id = {new}")
        run(one)
        run(f"DELETE FROM shipments WHERE id = {new}")
        run(one)

        title("5. Transaction with ROLLBACK")
        two = "SELECT id, status, cod_amount FROM shipments WHERE id IN (1, 2) ORDER BY id"
        before = run(two)
        run("START TRANSACTION")
        run("UPDATE shipments SET cod_amount = cod_amount + 1000 WHERE id IN (1, 2)")
        run(two)
        run("ROLLBACK")
        if run(two) != before:
            raise RuntimeError("ROLLBACK did not restore the old values")

        title("6. Transaction with COMMIT")
        run("START TRANSACTION")
        run("UPDATE shipments SET cod_amount = cod_amount + 1000 WHERE id IN (1, 2)")
        run("COMMIT")
        if [r[2] for r in run(two)] != [r[2] + 1000 for r in before]:
            raise RuntimeError("COMMIT did not keep the new values")

        title("7. Unique constraint")
        run(create_index_sql("shipments", "idx_code"))
        code = run("SELECT tracking_code FROM shipments WHERE id = 1")[0][0]
        try:
            run(f"UPDATE shipments SET tracking_code = '{code}' WHERE id = 2")
        except mysql.connector.IntegrityError as error:
            say(f"  Rejected as expected: {error}")
        else:
            raise RuntimeError("The duplicate tracking code was accepted")

        title("8. Plan without a secondary index on sender_id")
        analyze(conn, "shipments", engine=engine)
        run("EXPLAIN " + QUERY.format(hint=""))

        title("9. Plan with an index that does not cover the query")
        run(create_index_sql("shipments", "idx_sender_created"))
        analyze(conn, "shipments", engine=engine)
        run("EXPLAIN " + QUERY.format(hint=" FORCE INDEX (idx_sender_created)"))

        title("10. Plan with a covering index")
        run(create_index_sql("shipments", "idx_sender_cov"))
        analyze(conn, "shipments", engine=engine)
        run("EXPLAIN " + QUERY.format(hint=" FORCE INDEX (idx_sender_cov)"))
        if engine == "tidb":
            title("11. Regions of the table")
            run("SHOW TABLE shipments REGIONS")

        run(f"DROP DATABASE {DATABASE}", show=False)
        say()
        say("Demo finished. Every check passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["tidb", "mysql"])
    engine = parser.parse_args().engine
    path = ROOT / f"results/runs/demo_{engine}_{get_machine_id()}.txt"
    # The lock refuses to run while a measurement is in progress.
    with operation_lock():
        assert_engine(engine)
        with path.open("w", encoding="utf-8") as out:
            demo(engine, out)
    print(f"Transcript: {path}")


if __name__ == "__main__":
    main()
