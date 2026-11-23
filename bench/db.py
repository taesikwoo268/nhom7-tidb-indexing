"""Database connection, table inspection, checksum, and engine settings module.

Supports both TiDB (port 4000) and MySQL InnoDB (port 3306).
Provides consistent interfaces for:
- Database connectivity with local infile support.
- Statistical analysis (`ANALYZE TABLE`).
- Verification checksum (`COUNT(*)`, `SUM(cod_amount)`).
- Runtime engine settings extraction (block cache, buffer pool, max replicas).
"""

from __future__ import annotations

from typing import Any

from bench.config import get_engine_config, get_machine_id, get_profile


def connect(engine: str, *, server_only: bool = False) -> Any:
    """Establish and return a connection to the requested database engine.

    Requires mysql-connector-python installed.
    """
    import mysql.connector

    cfg = get_engine_config(engine)
    conn = mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=None if server_only else cfg["database"],
        connection_timeout=5,
        allow_local_infile=cfg.get("allow_local_infile", True),
        autocommit=True,
    )
    return conn


def analyze(conn: Any, table: str = "shipments", *, engine: str | None = None) -> None:
    """Execute ANALYZE TABLE to update optimizer statistics."""
    cursor = conn.cursor()
    try:
        options = ""
        if engine == "tidb" and get_profile() in {"S", "XS"}:
            cursor.execute("SET SESSION tidb_build_stats_concurrency=1")
            options = " WITH 2048 SAMPLES"
        cursor.execute(f"ANALYZE TABLE {table}{options};")
        cursor.fetchall()
    finally:
        cursor.close()


def checksum(conn: Any, table: str = "shipments") -> tuple[int, int]:
    """Calculate and return (COUNT(*), SUM(cod_amount)) for the given table.

    Used across M1, M2, M3 to verify dataset identity (seed 20261116).
    """
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(cod_amount), 0) FROM {table};")
        row = cursor.fetchone()
        if not row:
            return (0, 0)
        cnt = int(row[0]) if row[0] is not None else 0
        total_cod = int(row[1]) if row[1] is not None else 0
        return (cnt, total_cod)
    finally:
        cursor.close()


def engine_settings(conn: Any, engine: str) -> dict[str, Any]:
    """Retrieve runtime engine parameters and environment metadata.

    For TiDB: extracts TiKV storage.block-cache.capacity, PD replication.max-replicas, and version.
    For MySQL: extracts innodb_buffer_pool_size and version.
    Always includes machine ID (M1/M2/M3) and active profile (M/S).
    """
    eng = engine.strip().lower()
    machine = get_machine_id()
    profile = get_profile()
    result: dict[str, Any] = {
        "engine": eng,
        "machine": machine,
        "profile": profile,
    }

    cursor = conn.cursor()
    try:
        if eng == "tidb":
            # Extract block cache capacity from TiKV
            cursor.execute(
                "SHOW CONFIG WHERE type='tikv' AND name='storage.block-cache.capacity';"
            )
            rows = cursor.fetchall()
            # Row schema: Type, Instance, Name, Value
            if len({r[1] for r in rows}) != 3 or len({r[3] for r in rows}) != 1:
                raise ValueError(f"Expected matching cache settings on three TiKV stores: {rows!r}")
            result["block_cache"] = rows[0][3]

            # Extract max-replicas from PD
            cursor.execute(
                "SHOW CONFIG WHERE type='pd' AND name='replication.max-replicas';"
            )
            rows = cursor.fetchall()
            if len(rows) != 1:
                raise ValueError(f"Missing or ambiguous PD max-replicas setting: {rows!r}")
            result["max_replicas"] = int(rows[0][3])

            cursor.execute(
                "SELECT store_state_name FROM information_schema.tikv_store_status;"
            )
            result["tikv_stores"] = sum(r[0] == "Up" for r in cursor.fetchall())
            # C3 and C1 are only defined on three stores (Table A.3.2).
            result["replica_config"] = (
                {3: "C3", 1: "C1"}.get(result["max_replicas"], "")
                if result["tikv_stores"] == 3
                else ""
            )

            # Extract TiDB version
            cursor.execute("SELECT tidb_version();")
            ver_row = cursor.fetchone()
            result["version"] = ver_row[0] if ver_row else "unknown"

        elif eng == "mysql":
            # Extract InnoDB buffer pool size
            cursor.execute("SHOW VARIABLES LIKE 'innodb_buffer_pool_size';")
            row = cursor.fetchone()
            if not row:
                raise ValueError("Missing MySQL buffer pool setting")
            result["buffer_pool"] = row[1]

            # Extract MySQL version
            cursor.execute("SELECT VERSION();")
            ver_row = cursor.fetchone()
            result["version"] = ver_row[0] if ver_row else "unknown"

        else:
            raise ValueError(f"Unsupported engine '{engine}'. Expected 'tidb' or 'mysql'.")

        return result
    finally:
        cursor.close()


def assert_replicas(conn: Any, expected: int) -> None:
    """Require three Up stores and exactly `expected` peers in every Region."""
    settings = engine_settings(conn, "tidb")
    if settings["max_replicas"] != expected or settings["tikv_stores"] != 3:
        raise RuntimeError(
            f"Expected max-replicas={expected} on 3 Up stores, got "
            f"{settings['max_replicas']} on {settings['tikv_stores']}"
        )
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT region_id, COUNT(*) AS peers FROM information_schema.tikv_region_peers "
            "GROUP BY region_id"
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
    wrong = [r for r in rows if int(r[1]) != expected]
    if not rows or wrong:
        raise RuntimeError(
            f"{len(wrong)} of {len(rows)} Regions do not have {expected} peers: {wrong[:5]}"
        )
