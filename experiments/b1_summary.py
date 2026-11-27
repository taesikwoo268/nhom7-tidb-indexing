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


def plot(rows, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"mysql": "#2a78d6", "tidb": "#eb6834"}
    names = {"mysql": "MySQL", "tidb": "TiDB C3"}
    scales = sorted({int(r["rows"]) for r in rows})
    fig, axes = plt.subplots(1, len(scales), figsize=(6.4 * len(scales), 4.2), squeeze=False)
    for ax, scale in zip(axes[0], scales):
        cases = [r for r in rows if int(r["rows"]) == scale and r["object"] in ("set0", "set5")]
        xs = list(range(len(cases)))
        width = 0.34
        for offset, engine in ((-0.17, "mysql"), (0.17, "tidb")):
            model_values = []
            measured_values = []
            for case in cases:
                model_field = f"model_{engine}_bytes"
                measured_field = f"measured_{engine}_bytes"
                model_values.append(int(case[model_field]) / 1024**2)
                measured_values.append(int(case[measured_field]) / 1024**2 if case[measured_field] else 0)
            ax.bar(
                [x + offset for x in xs],
                model_values,
                width=width,
                color="#b9bec5",
                label=f"{names[engine]} mo hinh" if cases else None,
            )
            ax.bar(
                [x + offset for x in xs],
                measured_values,
                width=width * 0.55,
                color=colors[engine],
                label=f"{names[engine]} do",
            )
        ax.set_xticks(xs, ["0 chỉ mục", "5 chỉ mục"])
        ax.set_title(f"{scale:,} dòng".replace(",", "."))
        ax.set_ylabel("Dung lượng (MiB)")
        ax.grid(axis="y", color="#e3e5e8", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("Mô hình và số đo dung lượng B.1", fontsize=11)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measured", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/b1_summary.csv"))
    parser.add_argument("--figure", type=Path, default=Path("results/fig/b1_model_vs_measured.png"))
    args = parser.parse_args()
    rows = summarise(read(args.measured), read(args.model))
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{args.output}: {len(rows)} rows")
    plot(rows, args.figure)
    print(f"{args.figure}: plot written")


if __name__ == "__main__":
    main()
