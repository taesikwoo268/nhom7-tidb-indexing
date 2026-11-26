"""Summarise one machine's RQ2 CSV: crossover, optimizer switch point and t = a + b*R.

python -m experiments.rq2_summary results/rq2_M3.csv

Writes <input>_summary.csv, <input>_fit.csv and results/fig/<input>.png.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np

from experiments.rq2_selectivity import INDEX_OPS, SCAN_OPS, find_crossover

ROOT = Path(__file__).resolve().parents[1]
COLORS = {"mysql": "#2a78d6", "tidb": "#eb6834"}
NAMES = {"mysql": "MySQL", "tidb": "TiDB C3"}
STYLES = {"index": "-", "scan": "--", "auto": ":"}
MODE_NAMES = {"index": "ép dùng index", "scan": "quét bảng", "auto": "optimizer chọn"}


def summarise(rows):
    """Median over the reps of each rep's p50, per engine, selectivity and mode."""
    groups = defaultdict(list)
    for r in rows:
        groups[r["engine"], int(r["rows"]), float(r["pct"]), r["mode"]].append(r)
    out = []
    for (engine, n, pct, mode), trials in sorted(groups.items()):
        p50 = [float(t["p50_ms"]) for t in trials]
        out.append(dict(
            engine=engine, rows=n, pct=pct, mode=mode, runs=len(trials),
            rows_mean=median(float(t["rows_mean"]) for t in trials),
            access_op=trials[0]["access_op"],
            p50_ms=round(median(p50), 4), p50_min=round(min(p50), 4),
            p50_max=round(max(p50), 4), p95_ms=round(median(float(t["p95_ms"]) for t in trials), 4),
        ))
    return out


def curve(summary, engine, n, mode):
    pts = sorted(
        (r["pct"], r["rows_mean"], r["p50_ms"])
        for r in summary if (r["engine"], r["rows"], r["mode"]) == (engine, n, mode)
    )
    return [p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts]


def crossover(summary, engine, n):
    """Selectivity (percent) where the forced index becomes slower than the scan."""
    px, _, index = curve(summary, engine, n, "index")
    sx, _, scan = curve(summary, engine, n, "scan")
    common = sorted(set(px) & set(sx))
    if len(common) < 2:
        return None
    pick = lambda xs, ys: [y for x, y in zip(xs, ys) if x in common]  # noqa: E731
    return find_crossover(common, pick(px, index), pick(sx, scan))


def optimizer_switch(summary, engine, n):
    """Smallest selectivity at which the optimizer's own plan is a table scan."""
    for r in sorted(summary, key=lambda r: r["pct"]):
        if (r["engine"], r["rows"], r["mode"]) == (engine, n, "auto"):
            ops = set(r["access_op"].split("/"))
            if ops <= SCAN_OPS:
                return r["pct"]
    return None


def fit(summary):
    """t = a + b*R per engine, size and forced mode. Weighted by 1/t, as in RQ1."""
    out = []
    keys = {(r["engine"], r["rows"], r["mode"]) for r in summary if r["mode"] != "auto"}
    for engine, n, mode in sorted(keys):
        _, x, t = (np.array(v) for v in curve(summary, engine, n, mode))
        if len(x) < 3:
            continue
        b, a = np.polyfit(x, t, 1, w=1 / t)
        res = t - (a + b * x)
        total = ((t - t.mean()) ** 2).sum()
        out.append(dict(
            engine=engine, rows=n, mode=mode, points=len(x),
            a_ms=round(float(a), 4), b_us_per_row=round(float(1000 * b), 4),
            r2=round(float(1 - (res**2).sum() / total), 4) if total else "",
            max_relative_residual=round(float(np.abs(res / t).max()), 3),
        ))
    return out


def plot(summary, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    sizes = sorted({r["rows"] for r in summary})
    for engine in COLORS:
        for n in sizes:
            for mode in ("index", "scan", "auto"):
                x, _, t = curve(summary, engine, n, mode)
                if x:
                    ax.plot(
                        x, t, STYLES[mode], color=COLORS[engine], marker="o", markersize=4,
                        linewidth=1.6 if mode != "auto" else 1.2,
                        label=f"{NAMES[engine]}, {MODE_NAMES[mode]}",
                    )
            c = crossover(summary, engine, n)
            if c:
                ax.axvline(c, color=COLORS[engine], linewidth=0.8, alpha=0.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Độ chọn lọc (% số dòng khớp)")
    ax.set_ylabel("Độ trễ p50 (ms)")
    ax.grid(color="#e1e0d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, frameon=False, ncol=2)
    ax.set_title("RQ2: index (tra lại bảng) so với quét bảng", fontsize=11)
    fig.tight_layout()
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
    if len({r["machine"] for r in rows}) != 1:
        raise SystemExit("Summarise one machine at a time")
    summary = summarise(rows)
    fits = fit(summary)
    write(args.input.with_name(args.input.stem + "_summary.csv"), summary)
    if fits:
        write(args.input.with_name(args.input.stem + "_fit.csv"), fits)
    figure = args.figure or ROOT / f"results/fig/{args.input.stem}.png"
    plot(summary, figure)
    for engine in COLORS:
        for n in sorted({r["rows"] for r in summary}):
            c, s = crossover(summary, engine, n), optimizer_switch(summary, engine, n)
            print(f"{engine:5} {n:8} crossover={c and round(c, 3)}% optimizer_switch={s}%")
            if c and s:
                print(f"      gap = {s / c:.2f}x (optimizer / crossover)")
    for r in fits:
        print(f"fit {r}")
    print(f"{len(rows)} trials -> {figure}")


if __name__ == "__main__":
    main()
