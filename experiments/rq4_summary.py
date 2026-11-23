"""Summarise the RQ4 CSV: median, min-max and change against the own baseline.

python -m experiments.rq4_summary [results/rq4_official.csv]
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ("0", "1", "3", "5")
SYSTEMS = ("MySQL", "TiDB C3", "TiDB C1")
COLORS = {"MySQL": "#2a78d6", "TiDB C3": "#eb6834", "TiDB C1": "#1baf7a"}
MARKERS = {"MySQL": "o", "TiDB C3": "s", "TiDB C1": "^"}
MODE_NAMES = {"insert": "W1: thêm đơn mới", "update": "W2: cập nhật trạng thái"}


def system(row):
    return "MySQL" if row["engine"] == "mysql" else f"TiDB {row['replica_config']}"


def summarise(rows):
    """One output row per (system, threads, mode, index set). No trial is dropped."""
    for key in ("config_id", "machine", "profile"):
        for engine in ("mysql", "tidb"):
            values = {r[key] for r in rows if r["engine"] == engine}
            if len(values) > 1:
                raise ValueError(f"Mixed {key} for {engine}: {sorted(values)}")
    groups = defaultdict(list)
    for row in rows:
        groups[system(row), int(row["threads"]), row["mode"], row["index_set"]].append(row)
    out = []
    for (name, threads, mode, index_set), trials in sorted(groups.items()):
        tps = [float(t["tps"]) for t in trials]
        # Covering is compared with the same key prefix without covering columns.
        base_set = "sender_created" if index_set == "sender_cov" else "0"
        base = groups.get((name, threads, mode, base_set))
        base_tps = median(float(t["tps"]) for t in base) if base else None

        def mid(field):
            values = [float(t[field]) for t in trials if t.get(field) not in (None, "")]
            return round(median(values), 4) if values else ""

        out.append(
            dict(
                system=name,
                threads=threads,
                mode=mode,
                index_set=index_set,
                trials=len(trials),
                tps_median=round(median(tps), 1),
                tps_min=round(min(tps), 1),
                tps_max=round(max(tps), 1),
                baseline_set=base_set,
                change_pct=(
                    round(100 * (median(tps) / base_tps - 1), 1) if base_tps else ""
                ),
                p95_ms=mid("p95_ms"),
                p99_ms=mid("p99_ms"),
                bytes_per_transaction=mid("bytes_per_transaction"),
                table_bytes=mid("table_bytes"),
                index_bytes=mid("index_bytes"),
                sysbench_cpu_pct_max=round(
                    max(float(t["sysbench_cpu_pct"]) for t in trials), 1
                ),
                redo_fsyncs_per_transaction=mid("redo_fsyncs_per_transaction"),
            )
        )
    return out


def plot(summary, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    threads = max(r["threads"] for r in summary)
    modes = [m for m in MODE_NAMES if any(r["mode"] == m for r in summary)]
    fig, axes = plt.subplots(
        1, len(modes), figsize=(4.6 * len(modes), 3.6), sharey=True, squeeze=False
    )
    for ax, mode in zip(axes[0], modes):
        for name in SYSTEMS:
            points = {
                r["index_set"]: r
                for r in summary
                if (r["system"], r["mode"], r["threads"]) == (name, mode, threads)
            }
            if "0" not in points:
                continue
            base = points["0"]["tps_median"]
            xs = [c for c in COUNTS if c in points]
            ys = [100 * points[c]["tps_median"] / base for c in xs]
            low = [y - 100 * points[c]["tps_min"] / base for c, y in zip(xs, ys)]
            high = [100 * points[c]["tps_max"] / base - y for c, y in zip(xs, ys)]
            ax.errorbar(
                [int(c) for c in xs], ys, yerr=[low, high], label=name, linewidth=2,
                marker=MARKERS[name], markersize=7, capsize=3, color=COLORS[name],
                elinewidth=1,
            )
        ax.set_title(MODE_NAMES[mode], fontsize=10)
        ax.set_xlabel("Số chỉ mục phụ")
        ax.set_xticks([int(c) for c in COUNTS])
        ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylim(bottom=0)
    axes[0][0].set_ylabel("TPS so với 0 chỉ mục của chính hệ (%)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle(
        f"Chi phí ghi theo số chỉ mục phụ ({threads} luồng; trung vị, thanh: min–max)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, nargs="?", default=ROOT / "results/rq4_official.csv"
    )
    parser.add_argument(
        "--figure", type=Path, default=ROOT / "results/fig/rq4_tps_vs_indexes.png"
    )
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    summary = summarise(rows)
    output = args.input.with_name(args.input.stem + "_summary.csv")
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=summary[0])
        writer.writeheader()
        writer.writerows(summary)
    for r in summary:
        print(
            f"{r['system']:8} {r['threads']:3} {r['mode']:6} {r['index_set']:14} "
            f"n={r['trials']} TPS {r['tps_median']} [{r['tps_min']}-{r['tps_max']}] "
            f"{r['change_pct']}% so voi {r['baseline_set']}"
        )
    plot(summary, args.figure)
    print(f"{len(rows)} trials -> {output}, {args.figure}")


if __name__ == "__main__":
    main()
