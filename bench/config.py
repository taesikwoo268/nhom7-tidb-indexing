"""Configuration module for TiDB and MySQL experiments.

Defines connection parameters, machine environment detection (M1, M2, M3),
and resource profile specifications (Profiles M, S and XS) according to
Appendix A of the project plan.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

# Valid identifiers
VALID_MACHINE_IDS = {"M1", "M2", "M3"}
VALID_PROFILES = {"M", "S", "XS"}

# Default machine and profile if not specified in environment
# Machine M2 is assigned to TV2 (write cost RQ4)
DEFAULT_MACHINE_ID = "M2"
DEFAULT_PROFILE = "XS"


def get_machine_id() -> str:
    """Return the current MACHINE_ID from environment, defaulting to M2."""
    mid = os.environ.get("MACHINE_ID", DEFAULT_MACHINE_ID).strip().upper()
    return mid if mid in VALID_MACHINE_IDS else DEFAULT_MACHINE_ID


def get_profile() -> str:
    """Return the current resource PROFILE from environment, defaulting to XS."""
    prof = os.environ.get("PROFILE", DEFAULT_PROFILE).strip().upper()
    return prof if prof in VALID_PROFILES else DEFAULT_PROFILE


MACHINE_ID: str = get_machine_id()
PROFILE: str = get_profile()

# Connection dictionaries for the two database engines
ENGINES: dict[str, dict[str, Any]] = {
    "tidb": {
        "host": os.environ.get("TIDB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("TIDB_PORT", 4000)),
        "user": os.environ.get("TIDB_USER", "root"),
        "password": os.environ.get("TIDB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "logistics"),
        "allow_local_infile": True,
    },
    "mysql": {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", 3306)),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "logistics"),
        "allow_local_infile": True,
    },
}

# Resource profiles defined in Appendix A
PROFILES: dict[str, dict[str, Any]] = {
    "M": {
        "description": "Standard Profile M (>=12 CPU threads, >=16GB RAM)",
        "total_db_cpus": 6.0,
        "sysbench_cpus": 3.0,
        "tidb": {
            "version": "v8.5.5",
            "pd_cpus": 0.5,
            "pd_memory": "1GiB",
            "tidb_cpus": 1.75,
            "tidb_memory": "1.5GiB",
            "tikv_nodes": 3,
            "tikv_cpus_per_node": 1.25,
            "tikv_memory_per_node": "2.25GiB",
            "tikv_block_cache": "800MiB",
            "total_block_cache": "2400MiB",
            "replicas": 3,
        },
        "mysql": {
            "version": "8.4.11",
            "cpus": 6.0,
            "memory": "4GiB",
            "buffer_pool_size": "2400M",
            "flush_log_at_trx_commit": 1,
            "binlog_enabled": False,
        },
    },
    "S": {
        "description": "Small Profile S (8 CPU threads or lower RAM allocation)",
        "total_db_cpus": 4.0,
        "sysbench_cpus": 2.0,
        "tidb": {
            "version": "v8.5.5",
            "pd_cpus": 0.4,
            "pd_memory": "0.75GiB",
            "tidb_cpus": 1.2,
            "tidb_memory": "1.25GiB",
            "tikv_nodes": 3,
            "tikv_cpus_per_node": 0.8,
            "tikv_memory_per_node": "1.75GiB",
            "tikv_block_cache": "500MiB",
            "total_block_cache": "1500MiB",
            "replicas": 3,
        },
        "mysql": {
            "version": "8.4.11",
            "cpus": 4.0,
            "memory": "3GiB",
            "buffer_pool_size": "1500M",
            "flush_log_at_trx_commit": 1,
            "binlog_enabled": False,
        },
    },
    "XS": {
        "description": "Default for the 16 GB machines M1 and M2 (largest dataset 3M rows)",
        "total_db_cpus": 4.0,
        "sysbench_cpus": 2.0,
        "max_rows": 3_000_000,
        "tidb": {
            "version": "v8.5.5",
            "pd_cpus": 0.4,
            "pd_memory": "0.5GiB",
            "tidb_cpus": 1.2,
            "tidb_memory": "1.25GiB",
            "tikv_nodes": 3,
            "tikv_cpus_per_node": 0.8,
            "tikv_memory_per_node": "1.25GiB",
            "tikv_block_cache": "250MiB",
            "total_block_cache": "750MiB",
            "replicas": 3,
        },
        "mysql": {
            "version": "8.4.11",
            "cpus": 4.0,
            "memory": "2GiB",
            "buffer_pool_size": "750M",
            "flush_log_at_trx_commit": 1,
            "binlog_enabled": False,
        },
    },
}


def get_engine_config(engine: str) -> dict[str, Any]:
    """Return a deep copy of the configuration dictionary for the specified engine."""
    eng = engine.strip().lower()
    if eng not in ENGINES:
        raise ValueError(f"Unknown engine '{engine}'. Expected one of {list(ENGINES.keys())}")
    return copy.deepcopy(ENGINES[eng])
