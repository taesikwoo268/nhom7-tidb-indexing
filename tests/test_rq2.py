import math

import pytest

from bench.datagen import COD_MAX
from experiments.rq2_selectivity import (
    LEVELS_PCT,
    cod_range,
    find_crossover,
    level_params,
    params_for,
    plan_ok,
    render,
)
from experiments.rq2_summary import crossover, fit, optimizer_switch


def test_cod_range_width_matches_selectivity():
    lo, hi = cod_range(1, 0.5)
    assert hi - lo + 1 == COD_MAX // 100
    assert 0 <= lo and hi < COD_MAX


def test_cod_range_stays_inside_the_domain_at_the_edges():
    for pct in LEVELS_PCT:
        for u in (0.0, 0.999999):
            lo, hi = cod_range(pct, u)
            assert 0 <= lo <= hi < COD_MAX


def test_cod_range_rejects_bad_input():
    with pytest.raises(ValueError):
        cod_range(0, 0.1)
    with pytest.raises(ValueError):
        cod_range(1, 1.0)


def test_level_params_are_deterministic_and_distinct_per_level():
    assert level_params(0.1, 5) == level_params(0.1, 5)
    assert level_params(0.1, 5) != level_params(1, 5)


def test_params_for_uses_fewer_ranges_above_two_percent():
    assert len(params_for(2, 20, 3)) == 20
    assert len(params_for(5, 20, 3)) == 3


def test_render_adds_the_hint_for_each_mode():
    assert "FORCE INDEX (idx_cod)" in render("index", 1, 9)
    assert "IGNORE INDEX (idx_cod)" in render("scan", 1, 9)
    sql = render("auto", 1, 9)
    assert "INDEX" not in sql and "BETWEEN 1 AND 9" in sql


@pytest.mark.parametrize(
    "mode,op,index,expected",
    [
        ("index", "IndexLookUp", "idx_cod", True),
        ("index", "IndexAndRow(range)", "idx_cod", True),
        ("index", "TableReader", None, False),
        ("index", "IndexReader", "idx_cod", False),
        ("scan", "TableReader", None, True),
        ("scan", "TableScan", None, True),
        ("scan", "IndexLookUp", "idx_cod", False),
        ("auto", "TableScan", None, True),
        ("auto", "Point_Get", None, False),
    ],
)
def test_plan_ok(mode, op, index, expected):
    assert plan_ok(mode, op, index) is expected


def test_find_crossover_interpolates_in_log_space():
    got = find_crossover([1, 10, 100], [1, 2, 8], [4, 4, 4])
    assert got == pytest.approx(10 ** 1.5)


def test_find_crossover_returns_none_without_a_sign_change():
    assert find_crossover([1, 10], [1, 2], [4, 4]) is None
    assert find_crossover([1, 10], [5, 8], [4, 4]) is None


def test_find_crossover_needs_two_matching_points():
    with pytest.raises(ValueError):
        find_crossover([1], [1], [1])
    with pytest.raises(ValueError):
        find_crossover([1, 2], [1], [1, 1])


def rows(engine, mode, points, ops=None):
    return [
        dict(engine=engine, rows=1000, pct=p, mode=mode, runs=3, rows_mean=r, p50_ms=t,
             access_op=(ops or {}).get(p, "x"))
        for p, r, t in points
    ]


def test_crossover_and_optimizer_switch_from_a_summary():
    summary = (
        rows("mysql", "index", [(1, 10, 1.0), (10, 100, 2.0), (100, 1000, 8.0)])
        + rows("mysql", "scan", [(1, 10, 4.0), (10, 100, 4.0), (100, 1000, 4.0)])
        + rows("mysql", "auto", [(1, 10, 1.0), (10, 100, 2.0), (100, 1000, 4.0)],
               ops={1: "IndexAndRow(range)", 10: "IndexAndRow(range)", 100: "TableScan"})
    )
    assert crossover(summary, "mysql", 1000) == pytest.approx(10 ** 1.5)
    assert optimizer_switch(summary, "mysql", 1000) == 100
    assert crossover(summary, "tidb", 1000) is None


def test_fit_recovers_fixed_and_per_row_cost():
    points = [(p, r, 2.0 + 0.01 * r) for p, r in [(1, 10), (2, 100), (3, 1000), (4, 5000)]]
    result = fit(rows("tidb", "index", points))[0]
    assert result["a_ms"] == pytest.approx(2.0, abs=1e-3)
    assert result["b_us_per_row"] == pytest.approx(10.0, abs=1e-2)
    assert result["r2"] == pytest.approx(1.0)
    assert not math.isnan(result["max_relative_residual"])
