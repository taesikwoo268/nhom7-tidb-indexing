from bench.schema import create_index_sql, shipments_ddl
from experiments.rq3_pk import (
    EXPECTED_ROWS,
    QUERIES,
    VARIANTS,
    extra_unique,
    inside_index,
    parse_ctl_size,
    render,
    table_name,
)


def test_variants_match_the_plan():
    assert VARIANTS["tidb"] == ["bigint_clustered", "bigint_nonclustered", "code_clustered"]
    # InnoDB always clusters on the primary key.
    assert "bigint_nonclustered" not in VARIANTS["mysql"]


def test_every_variant_has_unique_keys_on_id_and_tracking_code():
    for engine, variants in VARIANTS.items():
        for variant in variants:
            ddl = shipments_ddl(engine, variant, table_name(variant))
            keys = ddl[ddl.index("PRIMARY KEY"):]
            extra = extra_unique(variant)
            sql = create_index_sql(table_name(variant), extra) if extra else ""
            has_id = "PRIMARY KEY (id)" in keys or "uk_id (id)" in keys
            has_code = "PRIMARY KEY (tracking_code)" in keys or "(tracking_code)" in sql
            assert has_id and has_code, (engine, variant)
            assert not extra or sql.startswith("CREATE UNIQUE INDEX")


def test_tidb_ddl_states_the_clustering():
    assert "CLUSTERED" in shipments_ddl("tidb", "bigint_clustered")
    assert "NONCLUSTERED" in shipments_ddl("tidb", "bigint_nonclustered")
    assert "CLUSTERED" not in shipments_ddl("mysql", "code_clustered")


def test_render_quotes_strings_and_forces_the_index():
    assert render("by_id", "code_clustered", (7,)).endswith("WHERE id=7")
    assert "tracking_code='VN00000002'" in render("by_code", "bigint_clustered", ("VN00000002",))
    sql = render("secondary", "bigint_nonclustered", (5, "2026-08-01 00:00:00"))
    assert "FROM rq3_bigint_nonclustered FORCE INDEX (idx_sender_created)" in sql
    assert "created_at>='2026-08-01 00:00:00'" in sql
    assert set(QUERIES) == set(EXPECTED_ROWS)


def test_parse_ctl_size_sums_every_column_family():
    text = (
        "region id: 100049\ncf default region size: 0B\n"
        "cf write region size: 10.109MiB\ncf lock region size: 512KiB\n"
    )
    assert parse_ctl_size(text) == round(10.109 * 1024**2 + 512 * 1024)


def test_parse_ctl_size_rejects_unknown_output():
    import pytest

    with pytest.raises(ValueError):
        parse_ctl_size("error: region not found")


def test_inside_index_accepts_only_regions_of_that_index():
    tid, iid = 493, 2
    assert inside_index("t_493_i_2_03800", "t_493_i_2_03900", tid, iid)
    # The last Region may end where the next index or the rows begin.
    assert inside_index("t_493_i_2_03900", "t_493_i_3_", tid, iid)
    assert inside_index("t_493_i_2_03900", "t_493_r", tid, iid)
    # Starting before the index, or running into the rows, mixes in other keys.
    assert not inside_index("t_493_i_1_", "t_493_i_2_03900", tid, iid)
    assert not inside_index("t_493_i_2_03900", "t_493_r_0380", tid, iid)
    assert not inside_index("t_493_i_2_03900", "", tid, iid)
