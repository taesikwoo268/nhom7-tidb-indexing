"""Summarise one machine's RQ1 CSV: latency, covering gain and the model t = a + b*R.

python -m experiments.rq1_summary results/rq1_M3.csv

Writes <input>_summary.csv, <input>_fit.csv and results/fig/<input>_covering.png.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
COLORS = {"mysql": "#2a78d6", "tidb": "#eb6834"}
MARKERS = {"mysql": "o", "tidb": "s"}
NAMES = {"mysql": "MySQL", "tidb": "TiDB C3"}
KV_FIELDS = ("cop_tasks", "rpcs", "process_keys", "rpc_ms", "process_ms", "wait_ms", "rest_ms",
             "block_reads", "handler_reads_per_query", "buffer_pool_reads")


def check_rows(rows):
    if len({r["machine"] for r in rows}) != 1:
        raise ValueError("Summarise one machine at a time")
    for engine, n in {(r["engine"], r["rows"]) for r in rows}:
        ids = {r["config_id"] for r in rows if (r["engine"], r["rows"]) == (engine, n)}
        if len(ids) > 1:
            raise ValueError(f"Mixed config_id for {engine}: {sorted(ids)}")
    results = defaultdict(set)
    for r in rows:
        results[r["rows"], r["query"], r["level"]].add(r["result_sha"])
    if any(len(v) > 1 for v in results.values()):
        raise ValueError("The two engines or designs returned different rows")


def group(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["engine"], int(r["rows"]), r["query"], r["design"], int(r["level"])].append(r)
    return groups


def medians(trials, field):
    values = [float(t[field]) for t in trials if t.get(field) not in (None, "")]
    return round(median(values), 4) if values else ""


def summarise(rows):
    """Median over the runs of each run's p50. Gain compares with design B only."""
    groups = group(rows)
    out = []
    for (engine, n, query, design, level), trials in sorted(groups.items()):
        p50 = [float(t["p50_ms"]) for t in trials]
        base = groups.get((engine, n, "SELECT1", "base", 0))
        floor = median(float(t["p50_ms"]) for t in base) if base else None
        cover = groups.get((engine, n, query, "B", level))
        ratio = net_ratio = ""
        if cover and design != "B":
            b = median(float(t["p50_ms"]) for t in cover)
            ratio = round(median(p50) / b, 3)
            # Without the protocol round trip. Blank near the floor, where the difference
            # is mostly noise and the ratio means nothing.
            if floor is not None and min(median(p50), b) >= 1.5 * floor:
                net_ratio = round((median(p50) - floor) / (b - floor), 3)
        q1, q3 = np.percentile(p50, [25, 75])
        out.append(dict(
            engine=engine, rows=n, query=query, design=design, level=level,
            index=trials[0]["index"], access_op=trials[0]["access_op"],
            runs=len(trials), rows_mean=medians(trials, "rows_mean"),
            p50_ms=round(median(p50), 4), p50_min=round(min(p50), 4),
            p50_max=round(max(p50), 4), iqr_ms=round(q3 - q1, 4),
            p95_ms=medians(trials, "p95_ms"),
            covering_gain=ratio, covering_gain_net=net_ratio,
            **{f: medians(trials, f) for f in KV_FIELDS},
        ))
    return out


def fit(rows):
    """t = a + b*R on Q2R, per engine, size and design. Weighted by 1/t.

    The sizes span three orders of magnitude, so unweighted residuals would come almost
    only from R = 10000 and leave the fixed cost a undetermined.
    """
    points = defaultdict(list)
    for r in rows:
        if r["query"] == "Q2R":
            key = r["engine"], int(r["rows"]), r["design"]
            points[key].append((float(r["rows_mean"]), float(r["p50_ms"])))
    out = []
    for (engine, n, design), values in sorted(points.items()):
        x, t = np.array(values).T
        if len(set(x)) < 3:
            continue
        b, a = np.polyfit(x, t, 1, w=1 / t)
        residual = t - (a + b * x)
        out.append(dict(
            engine=engine, rows=n, design=design, points=len(x),
            a_ms=round(float(a), 4), b_us_per_row=round(float(1000 * b), 4),
            r2=round(float(1 - (residual**2).sum() / ((t - t.mean()) ** 2).sum()), 4),
            max_relative_residual=round(float(np.abs(residual / t).max()), 3),
        ))
    return out


def label(query, level):
    return f"{query}\nR={level:,}".replace(",", ".") if level else query


def plot(rows, summary, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = group(rows)
    sizes = sorted({r["rows"] for r in summary})
    fig, axes = plt.subplots(
        1, len(sizes), figsize=(6.4 * len(sizes), 3.8), sharey=True, squeeze=False
    )
    for ax, n in zip(axes[0], sizes):
        cases = []
        for query, design in (("Q1", "A2"), ("Q2", "A"), ("Q2R", "A"), ("Q3", "A")):
            cases += sorted({
                (query, design, r["level"]) for r in summary
                if (r["rows"], r["query"], r["design"]) == (n, query, design)
            })
        for shift, engine in ((-0.1, "mysql"), (0.1, "tidb")):
            xs, ys, low, high = [], [], [], []
            for i, (query, design, level) in enumerate(cases):
                pair = [groups.get((engine, n, query, d, level)) for d in (design, "B")]
                if not all(pair):
                    continue
                # One ratio per round, so the bar shows how stable the gain is.
                a, b = [{t["rep"]: float(t["p50_ms"]) for t in p} for p in pair]
                ratios = [a[r] / b[r] for r in a if r in b]
                mid = median(a.values()) / median(b.values())
                xs.append(i + shift)
                ys.append(mid)
                low.append(max(0, mid - min(ratios)))
                high.append(max(0, max(ratios) - mid))
            ax.errorbar(
                xs, ys, yerr=[low, high], fmt=MARKERS[engine], color=COLORS[engine],
                label=NAMES[engine], markersize=8, capsize=3, elinewidth=1.2,
            )
        ax.axhline(1, color="#6b6a64", linewidth=1)
        ax.set_xticks(range(len(cases)), [label(q, lv) for q, _, lv in cases], fontsize=9)
        ax.set_title(f"{n:,} dòng".replace(",", "."), fontsize=10)
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.5, 1, 2, 3, 5, 10, 20]))
        ax.yaxis.set_major_formatter("{x:g}×")
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylabel("Độ trễ không covering / covering")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
    fig.suptitle(
        "Lợi ích covering trong từng hệ (trung vị; thanh: min–max qua các vòng)", fontsize=11
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    check_rows(rows)
    summary, fits = summarise(rows), fit(rows)
    write(args.input.with_name(args.input.stem + "_summary.csv"), summary)
    if fits:
        write(args.input.with_name(args.input.stem + "_fit.csv"), fits)
    figure = args.figure or ROOT / f"results/fig/{args.input.stem}_covering.png"
    plot(rows, summary, figure)
    for r in summary:
        print(
            f"{r['engine']:5} {r['rows']:8} {r['query']:7} {r['design']:4} R={r['rows_mean']:<9} "
            f"p50={r['p50_ms']:<9} [{r['p50_min']}-{r['p50_max']}] gain={r['covering_gain']} "
            f"net={r['covering_gain_net']} {r['access_op']}"
        )
    for r in fits:
        print(f"fit {r}")
    print(f"{len(rows)} trials -> {figure}")


if __name__ == "__main__":
    main()
