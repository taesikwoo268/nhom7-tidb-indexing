import re
from datetime import datetime

import pytest

pytest.importorskip("MySQLdb")

from bench.schema import INDEXES
from experiments.rq1_covering import (
    CASES,
    QUERIES,
    completed,
    milliseconds,
    mysql_plan,
    parse_execution_info,
    render,
    tidb_plan,
)
from experiments.rq1_summary import check_rows, fit, summarise

LOOKUP = (
    "IndexLookUp_16 root IndexRangeScan_14(Build) table:shipments, "
    "index:idx_sender_created(sender_id, created_at) cop_task: {num: 2, proc_keys: 10}, "
    "rpc_info:{Cop:{num_rpc:2, total_time:1.5ms}}, scan_detail: {total_process_keys: 10, "
    "rocksdb: {block: {cache_hit_count: 2, read_count: 1}}}, "
    "time_detail: {total_process_time: 76.8µs, total_wait_time: 50µs} "
    "TableRowIDScan_15(Probe) cop_task: {num: 1}, rpc_info:{Cop:{num_rpc:1, "
    "total_time:500µs}}, scan_detail: {total_process_keys: 10}, "
    "time_detail: {total_process_time: 123.2µs, total_wait_time: 50µs}"
)


def test_execution_info_adds_both_readers():
    info = parse_execution_info(LOOKUP)
    assert (info["cop_tasks"], info["rpcs"], info["process_keys"]) == (3, 3, 20)
    assert info["block_reads"] == 1
    assert info["rpc_ms"] == pytest.approx(2.0)
    assert info["process_ms"] == pytest.approx(0.2)
    assert info["rest_ms"] == pytest.approx(1.7)


def test_point_get_counts_rpcs_without_cop_tasks():
    info = parse_execution_info("Get:{num_rpc:2, total_time:593.2µs}, time_detail: {")
    assert (info["cop_tasks"], info["rpcs"]) == (0, 2)


def test_durations():
    assert milliseconds("1m2.5s") == pytest.approx(62500)
    assert milliseconds("510ns") == pytest.approx(0.00051)
    assert milliseconds("0s") == 0


def test_plans_name_the_access_path_and_index():
    assert tidb_plan([(LOOKUP,)]) == ("IndexLookUp", "idx_sender_created")
    point = [("Point_Get_1", "1.00", "root", "table:shipments, index:idx_code(tracking_code)")]
    assert tidb_plan(point) == ("Point_Get", "idx_code")
    row = dict(type="ref", key="idx_hub_status", Extra="Using where; Using index")
    assert mysql_plan([row]) == ("CoveringIndex", "idx_hub_status")
    # An index condition is checked in the index but still reads the row.
    row = dict(type="range", key="idx_sender_created", Extra="Using index condition")
    assert mysql_plan([row]) == ("IndexAndRow(range)", "idx_sender_created")


def test_covering_indexes_hold_every_column_of_their_query():
    for case in CASES:
        if case.index is None:
            continue
        sql = QUERIES[case.query]
        used = set(re.findall(r"[a-z_]+", sql.split(" FROM ")[0].lower())) - {"select", "count"}
        used |= set(re.findall(r"(\w+)(?:>?=)\{", sql))
        # The primary key is part of every secondary index.
        held = set(re.findall(r"\w+", INDEXES[case.index])) | {"id"}
        assert (used <= held) == case.covering, case


def test_render_uses_the_hint_and_quotes_values():
    case = next(c for c in CASES if (c.query, c.design) == ("Q2", "B"))
    sql = render(case, (4, datetime(2026, 8, 1)))
    assert "FORCE INDEX (idx_sender_cov)" in sql
    assert "sender_id=4 AND created_at>='2026-08-01 00:00:00'" in sql


def row(design, p50, rep="1", **extra):
    return dict(
        dict(engine="tidb", rows="1000", query="Q2", design=design, level="0", rep=rep,
             machine="M3", config_id="a", result_sha="x", index="i", access_op="o",
             rows_mean="20", p50_ms=str(p50), p95_ms=str(p50)),
        **extra,
    )


def test_summary_compares_with_covering_and_removes_the_protocol_floor():
    rows = [row("A", 9), row("B", 3), row("base", 1, query="SELECT1", result_sha="y")]
    out = {(r["query"], r["design"]): r for r in summarise(rows)}
    assert out["Q2", "A"]["covering_gain"] == 3
    assert out["Q2", "A"]["covering_gain_net"] == 4
    assert out["Q2", "B"]["covering_gain"] == ""


def test_summary_refuses_mixed_configurations_and_different_results():
    with pytest.raises(ValueError, match="Mixed config_id"):
        check_rows([row("A", 1), row("B", 1, config_id="b")])
    with pytest.raises(ValueError, match="different rows"):
        check_rows([row("A", 1), row("B", 1, result_sha="z")])


def test_fit_recovers_fixed_and_per_row_cost():
    rows = [
        row("A", 2 + 0.005 * r, query="Q2R", level=str(r), rows_mean=str(r))
        for r in (10, 100, 1000, 10000)
    ]
    (out,) = fit(rows)
    assert out["a_ms"] == pytest.approx(2, abs=1e-3)
    assert out["b_us_per_row"] == pytest.approx(5, abs=1e-3)


def test_resume_skips_recorded_trials_and_refuses_another_setup(tmp_path):
    path = tmp_path / "rq1.csv"
    path.write_text(
        "engine,rows,query,design,level,rep,config_id,params_sha\n"
        "tidb,1000,Q2,A,0,1,c,p\n",
        encoding="utf-8",
    )
    assert completed(path, "tidb", 1000, "c", "p") == {("Q2", "A", 0, 1)}
    assert completed(path, "mysql", 1000, "other", "p") == set()
    with pytest.raises(ValueError, match="another setup"):
        completed(path, "tidb", 1000, "other", "p")
