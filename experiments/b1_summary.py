"""B.1: compare measured sizes with the model.

python -m experiments.b1_summary results/b1_storage_M2.csv results/b1_model.csv

Writes results/b1_summary.csv: one row per scale and object (rows, each index, set 0,
set 5) with the raw bytes, the model and the measurement of each engine, one copy.
MySQL is given twice: allocated pages and leaf pages only.
"""

import argparse
import csv
from pathlib import Path

SET5 = ["idx_code", "idx_sender_created", "idx_hub_status", "idx_cod", "idx_status"]


def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def num(value):
    return int(value) if value not in ("", None) else 0


def summarise(measured, model):
    meas = {}
    for r in measured:
        key = (int(r["rows"]), r["object"])
        meas.setdefault(key, {})[r["engine"]] = (num(r["bytes"]), num(r["leaf_bytes"]))
    mod = {(int(r["rows"]), r["object"]): r for r in model}
    out = []
    for rows in sorted({k[0] for k in mod}):
        groups = {obj: [obj] for rows_, obj in mod if rows_ == rows}
        groups["set0"] = ["rows"]
        groups["set5"] = ["rows", *SET5]
        for name, parts in groups.items():
            row = {"rows": rows, "object": name}
            for field in ("raw_bytes", "mysql_bytes", "tidb_bytes"):
                row["model_" + field] = sum(int(mod[rows, p][field]) for p in parts)
            have = all((rows, p) in meas for p in parts)
            for i, label in ((0, "mysql_bytes"), (1, "mysql_leaf_bytes")):
                row["measured_" + label] = (
                    sum(meas[rows, p]["mysql"][i] for p in parts) if have else "")
            row["measured_tidb_bytes"] = (
                sum(meas[rows, p]["tidb"][0] for p in parts) if have else "")
            for engine, model_field in (("mysql", "model_mysql_bytes"), ("tidb", "model_tidb_bytes")):
                m = row[f"measured_{engine}_bytes"]
                row[f"{engine}_measured_over_model"] = round(m / row[model_field], 3) if m else ""
            m = row["measured_mysql_leaf_bytes"]
            row["mysql_leaf_over_model"] = round(m / row["model_mysql_bytes"], 3) if m else ""
            out.append(row)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measured", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/b1_summary.csv"))
    args = parser.parse_args()
    rows = summarise(read(args.measured), read(args.model))
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{args.output}: {len(rows)} rows")


if __name__ == "__main__":
    main()
