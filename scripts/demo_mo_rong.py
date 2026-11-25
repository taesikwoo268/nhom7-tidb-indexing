"""Extra demos for the report: fault tolerance and adding a TiKV node.

python scripts/demo_mo_rong.py chiu_loi {tidb,mysql}
python scripts/demo_mo_rong.py them_node

Only runs in the Compose project nhom7demo (see scripts/demo.ps1), so the volumes used
for measurements are never touched. These demos show a mechanism. They are not
performance results and are not used for any conclusion about indexes.
"""

import argparse
import csv
import json
import os
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import MySQLdb  # noqa: E402

from bench.config import get_engine_config, get_machine_id, get_profile  # noqa: E402
from bench.datagen import COLUMNS, generate_rows  # noqa: E402
from bench.db import connect  # noqa: E402
from bench.environment import (  # noqa: E402
    ROOT as _ROOT,
    assert_engine,
    compose,
    operation_lock,
)
from bench.rq4 import wait_replicas, wait_settings  # noqa: E402
from bench.schema import shipments_ddl  # noqa: E402

PROJECT = "nhom7demo"
DATABASE = "demo_nhom7"
WORKERS = 8
PD = "http://127.0.0.1:2379/pd/api/v1"


class Tee:
    """Keep a copy of everything printed, to quote it in the report."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


class Load:
    """Writers that insert one probe row per transaction and remember every commit."""

    def __init__(self, engine):
        self.engine, self.stop = engine, threading.Event()
        self.ok, self.failed, self.lock = Counter(), Counter(), threading.Lock()
        self.acked = [set() for _ in range(WORKERS)]
        self.errors = Counter()

    def connect(self):
        cfg = get_engine_config(self.engine)
        return MySQLdb.connect(
            host=cfg["host"], port=cfg["port"], user=cfg["user"], passwd=cfg["password"],
            db=DATABASE, autocommit=True, ssl_mode="DISABLED",
            connect_timeout=3, read_timeout=60, write_timeout=60,
        )

    def work(self, worker):
        conn, seq = None, 0
        while not self.stop.is_set():
            seq += 1
            try:
                conn = conn or self.connect()
                conn.query(f"INSERT INTO probe (worker, seq) VALUES ({worker}, {seq})")
                self.acked[worker].add(seq)
                done, error = True, None
            except MySQLdb.Error as exc:
                done, error = False, exc
            second = int(time.monotonic() - self.start)
            with self.lock:
                (self.ok if done else self.failed)[second] += 1
                if error is not None:
                    self.errors[str(error.args[0]) + " " + str(error.args[-1])[:60]] += 1
            if error is not None:
                try:
                    conn and conn.close()
                except MySQLdb.Error:
                    pass
                conn = None
                time.sleep(0.2)

    def __enter__(self):
        self.start = time.monotonic()
        self.threads = [
            threading.Thread(target=self.work, args=(i,), daemon=True) for i in range(WORKERS)
        ]
        for t in self.threads:
            t.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        for t in self.threads:
            t.join(90)


def stores():
    """State, leader and Region counts of every store, straight from PD."""
    with urlopen(PD + "/stores", timeout=3) as response:
        data = json.load(response)["stores"]
    return {
        s["store"]["address"].split(":")[0]: (
            s["store"]["state_name"],
            s["status"].get("leader_count", 0),
            s["status"].get("region_count", 0),
        )
        for s in data
    }


def text(snapshot):
    return " ".join(f"{k}={v[0]}/{v[1]}L/{v[2]}R" for k, v in sorted(snapshot.items()))


def prepare(engine, rows):
    with connect(engine, server_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {DATABASE}")
        cur.execute(f"CREATE DATABASE {DATABASE}")
        cur.execute(f"USE {DATABASE}")
        cur.execute(
            "CREATE TABLE probe (worker INT NOT NULL, seq BIGINT NOT NULL, "
            "PRIMARY KEY (worker, seq))"
        )
        cur.execute(shipments_ddl(engine))
        if engine == "tidb" and rows >= 24_000:
            # Enough Regions for PD to have something to balance.
            cur.execute("SPLIT TABLE shipments BETWEEN (0) AND (%s) REGIONS 24" % rows)
            cur.fetchall()
        insert = (
            f"INSERT INTO shipments ({','.join(COLUMNS)}) "
            f"VALUES ({','.join(['%s'] * len(COLUMNS))})"
        )
        batch = []
        for row in generate_rows(rows):
            batch.append(row)
            if len(batch) == 1000:
                cur.executemany(insert, batch)
                batch = []
        if batch:
            cur.executemany(insert, batch)


def leader_service(engine):
    """Service that leads the Region of the probe table, so the kill is sure to be felt."""
    with connect(engine, server_only=True) as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(f"SHOW TABLE {DATABASE}.probe REGIONS")
        store = cur.fetchall()[0]["LEADER_STORE_ID"]
        cur.execute(
            "SELECT address FROM information_schema.tikv_store_status WHERE store_id=%s", (store,)
        )
        return cur.fetchall()[0]["address"].split(":")[0]


def verify(load):
    """Every acknowledged commit must still be there."""
    with connect(load.engine, server_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT worker, seq FROM {DATABASE}.probe")
        present = set(cur.fetchall())
    acked = {(w, s) for w, seqs in enumerate(load.acked) for s in seqs}
    return len(acked), len(acked - present), len(present - acked)


def timeline(load, duration, events, engine, sample=True):
    """Run the events at their second. Return one record per second."""
    records, pending = [], sorted(events.items())
    for second in range(duration):
        note = ""
        while pending and pending[0][0] <= second:
            _, (label, action) = pending.pop(0)
            print(f"t={second:3} s  >>> {label}", flush=True)
            action()
            note = label
        state = ""
        if sample and engine == "tidb":
            try:
                state = text(stores())
            except OSError as exc:
                state = f"PD: {exc}"
        time.sleep(max(0, load.start + second + 1 - time.monotonic()))
        with load.lock:
            ok, failed = load.ok[second], load.failed[second]
        records.append(dict(second=second, ok=ok, failed=failed, event=note, stores=state))
        if note or second % 5 == 0:
            print(f"t={second:3} s  ok={ok:5}  loi={failed:3}  {state}", flush=True)
    return records


def save(name, records, load, title, marks):
    path = ROOT / f"results/{name}_{get_machine_id()}.csv"
    for r in records:
        # Commits that finished after the second was printed.
        r["ok"], r["failed"] = load.ok[r["second"]], load.failed[r["second"]]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0])
        writer.writeheader()
        writer.writerows(records)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 3.4))
    color = "#2a78d6" if load.engine == "mysql" else "#eb6834"
    ax.plot([r["second"] for r in records], [r["ok"] for r in records], color=color, linewidth=1.6)
    for x, label in marks:
        ax.axvline(x, color="#6b6a64", linewidth=1, linestyle="--")
        ax.annotate(label, (x, 1), xycoords=("data", "axes fraction"), xytext=(3, -4),
                    textcoords="offset points", fontsize=8, va="top")
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Thời gian (giây)")
    ax.set_ylabel("Giao dịch thành công mỗi giây")
    ax.set_title(title, fontsize=10)
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    figure = ROOT / f"results/fig/{name}_{get_machine_id()}.png"
    fig.savefig(figure, dpi=200)
    plt.close(fig)
    print(f"CSV: {path}\nHinh: {figure}")


def report(load, records, kill, base_from=10):
    ok = [r["ok"] for r in records]
    base = sum(ok[base_from:kill]) / (kill - base_from)
    zero = sum(x == 0 for x in ok[kill:])
    recovered = None
    for t in range(kill, len(ok) - 4):
        # First second after the dip from which five seconds average 90% of the base.
        dipped = any(x < base / 2 for x in ok[kill:t])
        if dipped and sum(ok[t:t + 5]) / 5 >= 0.9 * base:
            recovered = t - kill
            break
    acked, lost, extra = verify(load)
    attempts = sum(load.ok.values()) + sum(load.failed.values())
    print("\n--- KET QUA ---")
    print(f"Muc nen (giay {base_from}-{kill}): {base:.1f} giao dich/giay")
    print(f"So giay khong co giao dich nao thanh cong sau su co: {zero}")
    print(f"Thoi gian ve 90% muc nen: {recovered if recovered is not None else 'chua ve'} giay")
    print(f"Lenh ghi bi loi: {sum(load.failed.values())} / {attempts}")
    print(f"Giao dich da commit: {acked}; bi mat: {lost}; co trong bang nhung client khong nhan duoc xac nhan: {extra}")
    print(f"Loi theo loai: {dict(load.errors)}")


def chiu_loi(engine, args):
    if engine == "tidb":
        require_three_stores()
    prepare(engine, 2000)
    if engine == "tidb":
        with connect(engine, server_only=True) as conn:
            wait_replicas(conn, 3)
        service = leader_service(engine)
        print(f"C3: 3 TiKV, 3 ban sao. Store bi tat: {service} (giu leader cua bang probe)")
        print("Truoc su co:", text(stores()))
    else:
        service = "mysql"
        print("MySQL mot node, khong co ban sao.")
    kill, start, duration = args.kill, args.restart, args.duration
    events = {
        kill: (f"kill {service}", lambda: compose("kill", service)),
        start: (f"start {service}", lambda: compose("start", service)),
    }
    with Load(engine) as load:
        records = timeline(load, duration, events, engine)
    name = "TiDB C3" if engine == "tidb" else "MySQL một node"
    save(f"demo_chiu_loi_{engine}", records, load, f"{name}: tắt {service} rồi bật lại",
         [(kill, f"tắt {service}"), (start, "bật lại")])
    report(load, records, kill)
    if engine == "tidb":
        print("Sau khi bat lai:", text(stores()))


def require_three_stores():
    """A store left over from an earlier run would still hold peers of some Regions."""
    found = stores()
    if len(found) != 3:
        raise SystemExit(f"Can dung 3 store, dang co {text(found)}. Chay: demo.ps1 don")


def them_node(args):
    require_three_stores()
    prepare("tidb", 100_000)
    with connect("tidb", server_only=True) as conn:
        wait_replicas(conn, 3)
    print("Truoc khi them:", text(stores()))
    extra = str(_ROOT / "docker/tikv4-demo.yml")
    add = args.kill
    events = {add: ("them tikv4", lambda: compose("-f", extra, "up", "-d", "--no-deps", "tikv4"))}
    with Load("tidb") as load:
        records = timeline(load, args.duration, events, "tidb")
    save("demo_them_node", records, load, "TiDB C3: thêm TiKV thứ tư khi đang có tải",
         [(add, "thêm tikv4")])
    first = next((r["second"] for r in records if "tikv4=Up" in r["stores"]
                  and "/0R" not in r["stores"].split("tikv4=")[1].split()[0]), None)
    joined = next((r["second"] for r in records if "tikv4=Up" in r["stores"]), None)
    ok = [load.ok[r["second"]] for r in records]
    acked, lost, unknown = verify(load)
    print("\n--- KET QUA ---")
    print(f"tikv4 o trang thai Up sau {None if joined is None else joined - add} giay")
    print(f"Region dau tien tren tikv4 sau {None if first is None else first - add} giay")
    print(f"Giao dich/giay truoc khi them (giay 10-{add}): {sum(ok[10:add]) / (add - 10):.1f}")
    tail = ok[-30:]
    print(f"Giao dich/giay o 30 giay cuoi: {sum(tail) / len(tail):.1f}")
    print(f"Lenh ghi bi loi: {sum(load.failed.values())} {dict(load.errors)}")
    print(f"Giao dich da commit: {acked}; bi mat: {lost}; khong nhan duoc xac nhan: {unknown}")
    print("Sau khi them:", text(stores()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="demo", required=True)
    fault = sub.add_parser("chiu_loi")
    fault.add_argument("engine", choices=["tidb", "mysql"])
    fault.add_argument("--kill", type=int, default=30)
    fault.add_argument("--restart", type=int, default=90)
    fault.add_argument("--duration", type=int, default=150)
    scale = sub.add_parser("them_node")
    scale.add_argument("--kill", type=int, default=30, help="second at which tikv4 is added")
    scale.add_argument("--duration", type=int, default=150)
    args = parser.parse_args()
    if os.environ.get("COMPOSE_PROJECT_NAME") != PROJECT:
        raise SystemExit("Chay qua .\\scripts\\demo.ps1, de khong dung vao du lieu do.")
    engine = getattr(args, "engine", "tidb")
    log = ROOT / f"results/runs/demo_{args.demo}_{engine}_{get_machine_id()}.txt"
    with operation_lock(), log.open("w", encoding="utf-8") as copy:
        sys.stdout = Tee(sys.__stdout__, copy)
        print(f"Project {PROJECT}, ho so {get_profile()}, may {get_machine_id()}")
        assert_engine(engine)
        if engine == "tidb":
            with connect("tidb", server_only=True) as conn:
                wait_settings(conn)
        if args.demo == "chiu_loi":
            chiu_loi(engine, args)
        else:
            them_node(args)
        sys.stdout = sys.__stdout__
    print(f"Log: {log}")


if __name__ == "__main__":
    main()
