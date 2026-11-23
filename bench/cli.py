"""Shared entry points for the Bash and PowerShell TV2 tools."""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    switch = commands.add_parser("engine")
    switch.add_argument("engine", choices=["tidb", "mysql", "status", "stop"])
    switch.add_argument("--switch", action="store_true")
    load = commands.add_parser("load")
    load.add_argument("engine", choices=["tidb", "mysql"])
    load.add_argument("rows", type=int, nargs="?", default=1_000_000)
    load.add_argument("seed", type=int, nargs="?", default=20261116)
    rq4 = commands.add_parser("rq4")
    rq4.add_argument("engine", choices=["tidb", "mysql"], nargs="?", default="tidb")
    rq4.add_argument("rows", type=int, nargs="?", default=1_000_000)
    rq4.add_argument("--seconds", type=int, default=int(os.getenv("RUN_SECONDS", "60")))
    rq4.add_argument("--reps", type=int, default=int(os.getenv("REPS", "3")))
    rq4.add_argument("--threads", type=int, nargs="+", default=[64])
    rq4.add_argument(
        "--indexes",
        type=lambda v: int(v) if v.isdigit() else v,
        choices=[0, 1, 3, 5, "sender_created", "sender_cov"],
        nargs="+",
        default=[0, 1, 3, 5],
    )
    rq4.add_argument("--replicas", type=int, choices=[1, 3], nargs="+", default=[3, 1])
    rq4.add_argument(
        "--mode", choices=["insert", "update"], nargs="+", default=["insert", "update"]
    )
    rq4.add_argument("--output", type=Path, default=ROOT / "results/rq4.csv")
    args = parser.parse_args()
    if args.command == "check":
        from .check import check

        check()
        return
    from .environment import operation_lock

    with operation_lock():
        if args.command == "engine":
            from .environment import switch_engine

            switch_engine(args.engine, args.switch)
        elif args.command == "load":
            from .loader import load_dataset

            load_dataset(args.engine, args.rows, args.seed)
        else:
            from .rq4 import benchmark

            benchmark(args)


if __name__ == "__main__":
    main()
