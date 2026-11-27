import pytest

from experiments.b1_model import compact_int, mc, pages_bytes, row_sizes, write_cf
from experiments.b1_storage import FLOOR, ORDER, SET5, parse_ctl_size, region_inside

ROW = ["1", "VN696703683626", "16", "87", "130", "5", "9641779", "315", "147626", "0925344764", "953 duong Nguyen Trai, phuong Trung Van, quan Nam Tu Liem, Ha Noi", "\\N", "2026-05-01 00:00:00", "2026-05-01 00:00:00"]


def test_index_order_builds_set5_then_the_covering_index():
    assert SET5 == ["idx_code", "idx_sender_created", "idx_hub_status", "idx_cod", "idx_status"]
    assert ORDER[-1] == "idx_sender_cov"
    assert set(FLOOR) == set(ORDER)


def test_memcomparable_length_counts_started_groups():
    assert mc(0) == 9
    assert mc(7) == 9
    assert mc(8) == 18
    assert mc(46) == 54


def test_sender_created_entry_matches_the_rq3_measurement():
    # 76.0 B per entry was read with tikv-ctl in RQ3 for a BIGINT clustered table.
    assert row_sizes(ROW)["idx_sender_created"][2] == 76


def test_long_values_go_to_the_default_column_family():
    # A row key: 19 raw bytes, 27 after encoding, 36 with 'z' and the timestamp.
    assert write_cf(19, 255) == 36 + 1 + 9 + 2 + 255
    assert write_cf(19, 256) == 36 + 1 + 9 + 36 + 256


def test_compact_int_widths():
    assert [compact_int(v) for v in (5, 127, 128, 40000, 1 << 31)] == [1, 1, 2, 4, 8]


def test_mysql_record_of_a_row_with_null_note():
    raw, mysql, _ = row_sizes(ROW)["rows"]
    # 3 non-NULL VARCHARs, so 3 length bytes, 1 NULL bitmap byte, 5+6+7 B overhead.
    assert mysql - raw == 5 + 3 + 1 + 6 + 7


def test_pages_round_up_and_respect_the_fill_factor():
    assert pages_bytes(1, 1, 1.0) == 16384
    assert pages_bytes(16256, 0, 1.0) == 16384
    assert pages_bytes(16256, 0, 15 / 16) == 2 * 16384


def test_parse_ctl_size_and_region_checks():
    assert parse_ctl_size("cf default region size: 1.5KiB\ncf write region size: 2MiB") == round(
        1.5 * 1024 + 2 * 1024**2)
    with pytest.raises(ValueError):
        parse_ctl_size("error")
    assert region_inside("t_9_r_0380", "", 9)
    assert region_inside("t_9_r_0380", "t_10_", 9)
    assert not region_inside("t_9_i_1_", "t_9_r_0380", 9)
    assert region_inside("t_9_i_2_0380", "t_9_i_3_", 9, 2)
    assert region_inside("t_9_i_2_0380", "t_9_r", 9, 2)
    assert not region_inside("t_9_i_2_0380", "t_9_i_4_", 9, 2)
    assert not region_inside("t_9_i_1_", "t_9_i_3_", 9, 2)
