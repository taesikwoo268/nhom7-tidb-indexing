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


def test_failed_rq4_trial_still_restores_rf3_and_stops_load_generator(monkeypatch, tmp_path):
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
    monkeypatch.setattr(rq4, "config_fingerprint", lambda *args: "cfg")
    monkeypatch.setattr(rq4, "restart_engine", MagicMock())
    monkeypatch.setattr(rq4, "trim_docker_disk", MagicMock())
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
        output=tmp_path / "rq4.csv",
    )
    with pytest.raises(RuntimeError, match="trial failed"):
        rq4.benchmark(args)
    assert [call.args[1] for call in replicas.call_args_list] == [1, 3]
    compose.assert_called_with("stop", "sysbench")


def test_resume_refuses_trials_from_another_configuration(tmp_path):
    from bench.rq4 import completed_trials

    path = tmp_path / "rq4.csv"
    path.write_text(
        "engine,replicas,n_indexes,threads,mode,rep,index_set,config_id\n"
        "tidb,3,0,16,insert,1,0,aaa\n"
    )
    assert completed_trials(path, "tidb", "aaa") == {("tidb", 3, "0", 16, "insert", 1)}
    assert completed_trials(path, "mysql", "bbb") == set()
    with pytest.raises(ValueError, match="another configuration"):
        completed_trials(path, "tidb", "bbb")


@pytest.mark.parametrize(
    "peers,stores,ok",
    [
        ([(1, 3), (2, 3)], 3, True),
        ([(1, 3), (2, 2)], 3, False),
        ([], 3, False),
        ([(1, 3)], 1, False),
    ],
)
def test_assert_replicas_requires_three_stores_and_full_peers(monkeypatch, peers, stores, ok):
    from bench import db

    monkeypatch.setattr(
        db, "engine_settings", lambda *a: {"max_replicas": 3, "tikv_stores": stores}
    )
    conn = MagicMock()
    conn.cursor.return_value.fetchall.return_value = peers
    if ok:
        db.assert_replicas(conn, 3)
    else:
        with pytest.raises(RuntimeError):
            db.assert_replicas(conn, 3)


def test_rounds_interleave_indexes_and_limit_c1():
    from argparse import Namespace
    from bench.rq4 import pending_trials

    args = Namespace(
        engine="tidb", reps=2, threads=[16], mode=["update"], indexes=[0, 1, 5]
    )
    rounds = list(pending_trials(args, [3, 1], {("tidb", 3, "0", 16, "update", 1)}))
    assert [(rf, rep, sorted(t[2] for t in trials)) for rf, rep, trials in rounds] == [
        (3, 1, [1, 5]),
        (3, 2, [0, 1, 5]),
        (1, 1, [0, 5]),
        (1, 2, [0, 5]),
    ]


def test_unsettled_disk_is_reported(monkeypatch):
    from bench import rq4

    clock = iter(range(0, 10_000_000, 30))
    monkeypatch.setattr(rq4.time, "sleep", lambda s: None)
    monkeypatch.setattr(rq4.time, "monotonic", lambda: next(clock))
    calls = iter(range(1000))

    def busy(*args):
        n = next(calls)
        return {"time_ns": n * 10**10, "services": {"tikv1": {"write_bytes": n * 10**9}}}

    monkeypatch.setattr(rq4, "resource_snapshot", busy)
    assert rq4.settle(None, {"tikv1": "x"}, ["tikv1"], timeout=120)[1] is False


def test_check_rejects_every_deviation_from_the_team_configuration():
    from bench.check import problems

    gib = 1024**3
    assert problems("XS", 10 * gib, 12, True, "") == []
    assert problems("XS", 10 * gib, 12, None, "") == []
    assert len(problems("S", 5 * gib, 4, False, " M docker/mysql.cnf")) == 5


def test_team_hash_ignores_line_endings_and_sees_changes(tmp_path):
    from bench.check import team_hash

    path = tmp_path / "docker/mysql.cnf"
    path.parent.mkdir()
    path.write_bytes(b"a\nb\n")
    first = team_hash(tmp_path)
    path.write_bytes(b"a\r\nb\r\n")
    assert team_hash(tmp_path) == first
    path.write_bytes(b"a\nc\n")
    assert team_hash(tmp_path) != first


def test_rq4_summary_uses_own_baseline_and_refuses_mixed_configurations():
    from experiments.rq4_summary import summarise

    def row(index_set, tps, config="a"):
        return dict(
            engine="mysql", replica_config="", threads="64", mode="update",
            index_set=index_set, tps=str(tps), config_id=config, machine="M2",
            profile="XS", sysbench_cpu_pct="50",
        )

    rows = [row("0", 100), row("0", 300), row("0", 200), row("5", 150),
            row("sender_created", 180), row("sender_cov", 90)]
    out = {r["index_set"]: r for r in summarise(rows)}
    assert (out["0"]["tps_median"], out["0"]["tps_min"], out["0"]["tps_max"]) == (200, 100, 300)
    assert out["5"]["change_pct"] == -25.0
    assert out["sender_cov"]["change_pct"] == -50.0
    with pytest.raises(ValueError, match="Mixed config_id"):
        summarise(rows + [row("1", 1, "b")])


def test_rq4_summary_groups_tidb_by_checked_replicas():
    from experiments.rq4_summary import system

    # A store that was briefly down when settings were read leaves replica_config blank.
    assert system(dict(engine="tidb", replicas="3", replica_config="")) == "TiDB C3"
    assert system(dict(engine="tidb", replicas="1", replica_config="C1")) == "TiDB C1"


def test_round_order_is_reproducible_and_changes_between_rounds():
    from argparse import Namespace
    from bench.rq4 import pending_trials

    args = Namespace(
        engine="mysql", reps=3, threads=[64], mode=["insert", "update"],
        indexes=[0, 1, 3, 5, "sender_created", "sender_cov"],
    )
    rounds = [trials for _, _, trials in pending_trials(args, [1], set())]
    assert rounds == [trials for _, _, trials in pending_trials(args, [1], set())]
    assert len({r[0] for r in rounds}) == 3
    done = {("mysql", 1, str(ix), th, m, 1) for th, m, ix in rounds[0][:4]}
    assert next(pending_trials(args, [1], done))[2] == rounds[0][4:]


def test_only_stateless_services_may_lack_disk_counters():
    from bench.resources import resource_snapshot

    client = MagicMock()
    client.api.stats.return_value = {
        "blkio_stats": {"io_service_bytes_recursive": None},
        "cpu_stats": {"cpu_usage": {"total_usage": 1}},
        "memory_stats": {"usage": 1},
    }
    assert resource_snapshot(client, {"tidb": "x"})["services"]["tidb"]["write_bytes"] == 0
    with pytest.raises(RuntimeError, match="tikv1"):
        resource_snapshot(client, {"tikv1": "x"})


def test_fingerprint_ignores_image_rebuilds_and_sees_limits():
    from bench.rq4 import config_fingerprint

    def fingerprint(digest, memory):
        client = MagicMock()
        client.info.return_value = {"MemTotal": 10426142720, "NCPU": 18}
        client.containers.get.return_value.attrs = {
            "Image": digest,
            "Config": {"Image": "nhom7xs-mysql", "Cmd": ["mysqld"]},
            "HostConfig": {"NanoCpus": 4, "Memory": memory, "MemorySwap": memory},
        }
        return config_fingerprint(client, {"mysql": "x"})

    assert fingerprint("sha256:a", 1) == fingerprint("sha256:b", 1)
    assert fingerprint("sha256:a", 1) != fingerprint("sha256:a", 2)
