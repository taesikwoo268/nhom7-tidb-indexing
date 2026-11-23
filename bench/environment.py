"""Operate only the database containers in this Compose project."""

import os
import subprocess
import time
from pathlib import Path

from filelock import FileLock
import mysql.connector

from .config import get_engine_config, get_profile
from .db import connect

ROOT = Path(__file__).resolve().parents[1]
# One project name for the whole team, so volumes never mix with older profiles.
PROJECT = "nhom7xs"
SERVICES = {"mysql": ["mysql"], "tidb": ["pd", "tikv1", "tikv2", "tikv3", "tidb"]}


def operation_lock():
    lock_path = ROOT / "results/runs/engine.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(lock_path, timeout=0)


def compose(*args, capture=False):
    command = ["docker", "compose"]
    for manifest in ("mysql", "tidb", "sysbench"):
        command += ["-f", str(ROOT / f"docker/{manifest}.compose.yml")]
    return subprocess.run(
        command + list(args),
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        env={
            "COMPOSE_PROJECT_NAME": PROJECT,
            **os.environ,
            "PROFILE": get_profile(),
        },
    ).stdout


def running_services():
    return set(
        compose("ps", "--status", "running", "--services", capture=True).splitlines()
    )


def check_legacy_containers(other):
    # Older project manifests used global container names. Leave their data alone.
    legacy = (
        {"mysql-server"}
        if other == "mysql"
        else {"tidb-server", "tidb-pd", "tidb-tikv1", "tidb-tikv2", "tidb-tikv3"}
    )
    names = subprocess.check_output(
        ["docker", "ps", "--format", "{{.Names}}"], text=True
    )
    conflicts = legacy.intersection(names.splitlines())
    if conflicts:
        raise RuntimeError(
            f"Stop the other project's containers first: {sorted(conflicts)}"
        )


def assert_engine(engine):
    running = running_services()
    other = "tidb" if engine == "mysql" else "mysql"
    check_legacy_containers(other)
    if not set(SERVICES[engine]) <= running or running.intersection(SERVICES[other]):
        raise RuntimeError(
            f"Expected only {engine} running. Active services: {sorted(running)}"
        )


def wait_ready(target):
    deadline = time.monotonic() + 180
    while True:
        try:
            with connect(target, server_only=True) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1, VERSION()")
                value, version = cur.fetchone()
                if value != 1 or (("tidb" in version.lower()) != (target == "tidb")):
                    raise RuntimeError(
                        f"Unexpected server on the configured port: {version}"
                    )
            return value, version
        except mysql.connector.Error as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"{target} readiness query failed: {exc}") from exc
            time.sleep(1)


def restart_engine(target):
    """Restart the containers in place. Container IDs and limits are unchanged."""
    compose("restart", "-t", "90", *SERVICES[target])
    wait_ready(target)
    assert_engine(target)


def trim_docker_disk(image):
    """Let Docker Desktop reuse freed blocks. Harmless where the path does not exist."""
    result = subprocess.run(
        ["docker", "run", "--rm", "--privileged", "--pid=host", "--network", "none",
         "--entrypoint", "nsenter", image, "-t", "1", "-m", "--",
         "fstrim", "/mnt/docker-desktop-disk"],
        capture_output=True, text=True,
    )
    if result.returncode:
        print(f"Trim skipped: {result.stderr.strip()[:120]}", flush=True)


def switch_engine(target, switch):
    active = running_services()
    if target == "status":
        print("Running:", ", ".join(sorted(active)) or "none")
        return
    if target == "stop":
        compose("stop", "-t", "90", "sysbench", *SERVICES["mysql"], *SERVICES["tidb"])
        return
    other = "mysql" if target == "tidb" else "tidb"
    check_legacy_containers(other)
    if active.intersection(SERVICES[other]):
        if not switch:
            raise SystemExit(f"{other} is running. Use --switch.")
        # TiKV needs longer than the default 10 s to close cleanly.
        compose("stop", "-t", "90", "sysbench", *SERVICES[other])
    compose("up", "-d", "--build", "--force-recreate", *SERVICES[target])
    value, version = wait_ready(target)
    assert_engine(target)
    print(
        f"{target} SELECT 1 = {value}; version={version}; port={get_engine_config(target)['port']}"
    )
