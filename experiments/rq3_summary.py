"""Summarise RQ3: index size per primary key variant and lookup latency.

python -m experiments.rq3_summary results/rq3_M2.csv results/rq3_size_M2.csv

Writes <latency csv>_summary.csv with one row per engine, variant and query: the
median over rounds of the per-round p50 and p95, the range of p50, the access path
and the median number of TiKV RPCs. Index size gets one row per engine and variant,
with the ratio to the bigint_clustered table of the same engine.
"""

import argparse
import csv
from pathlib import Path
from statistics import median


def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def latency_summary(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r["engine"], r["pk_variant"], r["query"]), []).append(r)
    out = []
    for (engine, variant, query), rs in sorted(groups.items()):
        p50 = [float(r["p50_ms"]) for r in rs]
        rpcs = [float(r["rpcs"]) for r in rs if r["rpcs"] != ""]
        out.append(
            {
                "engine": engine,
                "pk_variant": variant,
                "query": query,
                "rounds": len(rs),
                "access_op": "/".join(sorted({r["access_op"] for r in rs})),
                "p50_ms": round(median(p50), 3),
                "p50_min_ms": round(min(p50), 3),
                "p50_max_ms": round(max(p50), 3),
                "p95_ms": round(median(float(r["p95_ms"]) for r in rs), 3),
                "rpcs": median(rpcs) if rpcs else "",
            }
        )
    return out


def size_summary(rows):
    base = {r["engine"]: int(r["index_bytes"]) for r in rows if r["pk_variant"] == "bigint_clustered"}
    return [
        {
            "engine": r["engine"],
            "pk_variant": r["pk_variant"],
            "rows": r["rows"],
            "index_mib": round(int(r["index_bytes"]) / 1024**2, 1),
            "bytes_per_entry": r["bytes_per_entry"],
            "vs_bigint_clustered": round(int(r["index_bytes"]) / base[r["engine"]], 3),
            "primary_mib": round(int(r["primary_bytes"]) / 1024**2, 1) if r["primary_bytes"] else "",
            "isolated": r["isolated"],
        }
        for r in rows
    ]


def write(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path}: {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("latency", type=Path)
    parser.add_argument("size", type=Path)
    args = parser.parse_args()
    write(args.latency.with_name(args.latency.stem + "_summary.csv"), latency_summary(read(args.latency)))
    write(args.size.with_name(args.size.stem + "_summary.csv"), size_summary(read(args.size)))


if __name__ == "__main__":
    main()
