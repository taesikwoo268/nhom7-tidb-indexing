"""Deterministic shipments TSV shared by MySQL and TiDB."""

from bisect import bisect_left
from datetime import datetime, timedelta
from itertools import accumulate
from pathlib import Path
from random import Random

SEED = 20261116
N_SENDERS, N_HUBS, COD_MAX, DAYS = 100_000, 200, 10_000_000, 180
START_TS = datetime(2026, 5, 1)
STATUS_WEIGHTS = {1: 0.03, 2: 0.04, 3: 0.05, 4: 0.05, 5: 0.80, 6: 0.03}
COLUMNS = [
    "id",
    "tracking_code",
    "sender_id",
    "origin_hub_id",
    "dest_hub_id",
    "status",
    "cod_amount",
    "weight_grams",
    "shipping_fee",
    "recipient_phone",
    "recipient_address",
    "note",
    "created_at",
    "updated_at",
]


def generate_rows(n, seed=SEED, start_id=1):
    rng = Random(seed)
    sender_weights = list(accumulate(i**-1.1 for i in range(1, N_SENDERS + 1)))
    status_weights = list(accumulate(STATUS_WEIGHTS.values()))
    used = set()
    for i in range(n):
        # Odd codes are reserved for concurrent W1 writers.
        code = 2 * rng.randrange(5 * 10**11)
        while code in used:
            code = 2 * rng.randrange(5 * 10**11)
        used.add(code)
        sender = 1 + bisect_left(sender_weights, rng.random() * sender_weights[-1])
        ts = START_TS + timedelta(seconds=i * DAYS * 86400 // n)
        addr = f"{rng.randrange(1, 999)} duong Nguyen Trai, phuong Trung Van, quan Nam Tu Liem, Ha Noi"
        yield (
            start_id + i,
            f"VN{code:012}",
            sender,
            rng.randint(1, N_HUBS),
            rng.randint(1, N_HUBS),
            1 + bisect_left(status_weights, rng.random()),
            rng.randrange(COD_MAX),
            rng.randint(100, 10000),
            rng.randint(15000, 150000),
            f"09{rng.randrange(10**8):08}",
            addr,
            "Giao trong gio hanh chinh" if rng.random() < 0.6 else None,
            ts,
            ts,
        )


def write_csv(n, path: Path, seed=SEED):
    with path.open("w", encoding="utf-8", newline="") as stream:
        for row in generate_rows(n, seed):
            stream.write("\t".join(r"\N" if v is None else str(v) for v in row) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=int)
    parser.add_argument("path", type=Path)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    write_csv(args.rows, args.path, args.seed)
