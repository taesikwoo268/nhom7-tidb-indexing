"""Regression cases found during TV2 acceptance."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bench.datagen import write_csv
from bench.db import engine_settings
from bench.rq4 import parse_sysbench


def test_settings_requires_live_values_from_three_stores_and_pd():
    rows = [
        ("tikv", f"tikv{i}", "storage.block-cache.capacity", "500MiB") for i in range(3)
    ]
    for stores, pd in [
        (rows[:2], []),
        (rows, []),
        (rows, [("pd", "pd:2379", "max-replicas", "?")]),
    ]:
        conn = MagicMock()
        conn.cursor.return_value.fetchall.side_effect = [stores, pd]
        with pytest.raises(ValueError):
            engine_settings(conn, "tidb")


def test_histogram_requires_all_committed_events():
    log = "transactions: 100 (10.00 per sec.)\n1.0 | **** 95\n2.0 | ** 4\n4.0 | * 1\n"
    assert parse_sysbench(log) == dict(
        transactions=100, tps=10.0, p95_ms=1.0, p99_ms=2.0
    )
    with pytest.raises(ValueError):
        parse_sysbench(log.replace("transactions: 100", "transactions: 102"))


def test_shared_tsv_is_deterministic_and_w1_codes_do_not_collide(tmp_path: Path):
    first, second = tmp_path / "first.tsv", tmp_path / "second.tsv"
    write_csv(250, first, seed=20261116)
    write_csv(250, second, seed=20261116)
    assert first.read_bytes() == second.read_bytes()
    rows = [line.split("\t") for line in first.read_text().splitlines()]
    assert len({r[1] for r in rows}) == 250
    assert all(len(r) == 14 and int(r[1][2:]) % 2 == 0 for r in rows)


def test_failed_rq4_trial_still_restores_rf3_and_stops_load_generator(monkeypatch):
    from argparse import Namespace
    from bench import rq4

    connection = MagicMock()
    conn = connection.__enter__.return_value
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1, 10)
    monkeypatch.setattr(rq4, "connect", lambda *args, **kwargs: connection)
    monkeypatch.setattr(rq4, "assert_engine", lambda engine: None)
    monkeypatch.setattr(rq4, "checksum", lambda *args: (10, 100))
    compose = MagicMock(return_value="container-id")
    monkeypatch.setattr(rq4, "compose", compose)
    monkeypatch.setattr(rq4.docker, "from_env", MagicMock())
    replicas = MagicMock()
    monkeypatch.setattr(rq4, "set_replicas", replicas)
    monkeypatch.setattr(
        rq4, "measured_table", MagicMock(side_effect=RuntimeError("trial failed"))
    )
    args = Namespace(
        engine="tidb",
        rows=10,
        seconds=1,
        reps=1,
        threads=[1],
        indexes=[0],
        mode=["update"],
        replicas=[1],
    )
    with pytest.raises(RuntimeError, match="trial failed"):
        rq4.benchmark(args)
    assert [call.args[1] for call in replicas.call_args_list] == [1, 3]
    compose.assert_called_with("stop", "sysbench")
