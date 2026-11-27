"""Print compact, screenshot-ready evidence for the report.

python scripts/minh_chung.py cai_dat {tidb,mysql}
python scripts/minh_chung.py ke_hoach {tidb,mysql}

cai_dat   configuration check, running containers, version and (TiDB) store status.
ke_hoach  EXPLAIN ANALYZE of query Q2 with the non-covering index (A) and the covering
          index (B), on table logistics_b1.b1_3000000 left by the B.1 run.
"""

import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench import config
from bench.db import connect

DATABASE = "logistics_b1"
TABLE = "b1_3000000"
SENDER, SINCE = 71, "2026-08-01 00:00:00"
DESIGNS = (("A, khong covering", "idx_sender_created"), ("B, covering", "idx_sender_cov"))
Q2 = ("SELECT id, created_at, status, cod_amount FROM {table} FORCE INDEX ({index}) "
      "WHERE sender_id = {sender} AND created_at >= '{since}' ORDER BY created_at DESC LIMIT 20")


def title(text):
    print("\n" + "=" * 8 + " " + text + " " + "=" * max(4, 78 - len(text)))


def table(rows, header):
    rows = [[str(c) for c in r] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(header)]
    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(c.ljust(w) for c, w in zip(r, widths)))


def cai_dat(engine):
    title("python -m bench.cli check")
    out = subprocess.run([sys.executable, "-W", "ignore", "-m", "bench.cli", "check"],
                         capture_output=True, text=True, cwd=ROOT, check=False)
    print((out.stdout + out.stderr).strip())
    title("docker ps (project nhom7xs)")
    out = subprocess.run(["docker", "ps", "--filter", "name=nhom7xs", "--format",
                          "{{.Names}}\t{{.Image}}\t{{.Status}}"],
                         capture_output=True, text=True, check=False)
    table([line.split("\t") for line in out.stdout.strip().splitlines()], ["NAME", "IMAGE", "STATUS"])
    with connect(engine, server_only=True) as conn, conn.cursor() as cur:
        if engine == "tidb":
            title("SELECT tidb_version()")
            cur.execute("SELECT tidb_version()")
            print("\n".join(cur.fetchone()[0].splitlines()[:3]))
            title("information_schema.tikv_store_status")
            cur.execute("SELECT store_id, address, store_state_name, region_count, leader_count "
                        "FROM information_schema.tikv_store_status ORDER BY store_id")
            table(cur.fetchall(), ["store_id", "address", "state", "regions", "leaders"])
            cur.execute("SHOW CONFIG WHERE type='pd' AND name='replication.max-replicas'")
            print("\nreplication.max-replicas =", cur.fetchone()[3])
        else:
            title("SELECT VERSION(), @@innodb_buffer_pool_size")
            cur.execute("SELECT VERSION(), @@innodb_buffer_pool_size")
            table(cur.fetchall(), ["version", "innodb_buffer_pool_size"])


def counters(info):
    """Main counters of one TiDB operator, in the order a reader looks for them."""
    keep = []
    for pattern in (r"time:[^,}]+", r"loops:\d+", r"cop_task: \{num: \d+", r"num_rpc:\d+",
                    r"total_process_keys: \d+"):
        m = re.search(pattern, info)
        if m:
            keep.append(m.group(0).replace("cop_task: {num: ", "cop_task:").replace("total_process_keys: ", "keys:"))
    text = ", ".join(keep)
    # Operators that run inside TiKV only report the TiKV task time, rounded.
    return text.replace("time:", "tikv_task time:", 1) if info.startswith("tikv_task") else text


def ke_hoach(engine):
    for settings in config.ENGINES.values():
        settings["database"] = DATABASE
    with connect(engine) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
        rows = cur.fetchone()[0]
        cur.execute(f"SHOW INDEX FROM {TABLE}")
        present = {r[2] for r in cur.fetchall()}
        missing = [i for _, i in DESIGNS if i not in present]
        if missing:
            sys.exit(f"Thieu chi muc {missing} tren {DATABASE}.{TABLE}; chay lai B.1 hoac tao chi muc truoc.")
        print(f"{engine}: {DATABASE}.{TABLE}, {rows:,} dong; Q2 = 20 don moi nhat cua shop {SENDER}")
        for name, index in DESIGNS:
            sql = Q2.format(table=TABLE, index=index, sender=SENDER, since=SINCE)
            cur.execute(sql)
            cur.fetchall()  # warm-up, so the plan below reads from memory
            title(f"Thiet ke {name}: {index}")
            print("EXPLAIN ANALYZE " + sql)
            cur.execute("EXPLAIN ANALYZE " + sql)
            result = cur.fetchall()
            print()
            if engine == "tidb":
                cols = [d[0] for d in cur.description]
                pick = [cols.index(c) for c in ("id", "actRows", "task", "access object")]
                info = cols.index("execution info")
                table([[r[i] for i in pick] + [counters(str(r[info]))] for r in result],
                      ["id", "actRows", "task", "access object", "execution info (trich)"])
            else:
                for line in str(result[0][0]).splitlines():
                    pad = " " * (len(line) - len(line.lstrip()) + 4)
                    print(textwrap.fill(line, 140, subsequent_indent=pad))


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("cai_dat", "ke_hoach") or sys.argv[2] not in ("tidb", "mysql"):
        sys.exit(__doc__)
    {"cai_dat": cai_dat, "ke_hoach": ke_hoach}[sys.argv[1]](sys.argv[2])


if __name__ == "__main__":
    main()
