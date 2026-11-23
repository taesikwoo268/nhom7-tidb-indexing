"""Unit tests for bench.config configuration module.

Verifies connection parameters, engine definitions, machine identification,
and resource profile specifications.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from bench.config import (
    DEFAULT_MACHINE_ID,
    DEFAULT_PROFILE,
    ENGINES,
    PROFILES,
    VALID_MACHINE_IDS,
    VALID_PROFILES,
    get_engine_config,
    get_machine_id,
    get_profile,
)


class TestConfig(unittest.TestCase):
    def test_engines_defined(self):
        """Verify both tidb and mysql are defined with correct ports and logistics database."""
        self.assertEqual(set(ENGINES.keys()), {"tidb", "mysql"})

        tidb = ENGINES["tidb"]
        self.assertEqual(tidb["port"], 4000)
        self.assertEqual(tidb["database"], "logistics")
        self.assertIs(tidb["allow_local_infile"], True)
        self.assertEqual(tidb["user"], "root")

        mysql = ENGINES["mysql"]
        self.assertEqual(mysql["port"], int(os.getenv("MYSQL_PORT", 3306)))
        self.assertEqual(mysql["database"], "logistics")
        self.assertIs(mysql["allow_local_infile"], True)
        self.assertEqual(mysql["user"], "root")

    def test_get_engine_config(self):
        """Verify get_engine_config returns independent deep copy and validates input."""
        tidb_cfg = get_engine_config("tidb")
        self.assertEqual(tidb_cfg["port"], 4000)
        tidb_cfg["port"] = 9999
        self.assertEqual(ENGINES["tidb"]["port"], 4000, "Original dict should not be mutated")

        mysql_cfg = get_engine_config("mysql")
        self.assertEqual(mysql_cfg["port"], int(os.getenv("MYSQL_PORT", 3306)))

        with self.assertRaises(ValueError):
            get_engine_config("postgres")

    def test_machine_id_detection(self):
        """Verify default machine ID is M2 and respects MACHINE_ID env var."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_machine_id(), DEFAULT_MACHINE_ID)

        for mid in VALID_MACHINE_IDS:
            with patch.dict(os.environ, {"MACHINE_ID": mid}):
                self.assertEqual(get_machine_id(), mid)

        # Invalid machine ID should fall back to default M2
        with patch.dict(os.environ, {"MACHINE_ID": "INVALID_MACHINE"}):
            self.assertEqual(get_machine_id(), DEFAULT_MACHINE_ID)

    def test_profile_detection(self):
        """Verify default profile is XS and respects PROFILE env var."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_profile(), DEFAULT_PROFILE)

        for prof in VALID_PROFILES:
            with patch.dict(os.environ, {"PROFILE": prof}):
                self.assertEqual(get_profile(), prof)

        # Invalid profile falls back to XS
        with patch.dict(os.environ, {"PROFILE": "UNKNOWN"}):
            self.assertEqual(get_profile(), DEFAULT_PROFILE)

    def test_profile_resource_alignments(self):
        """Verify resource equivalence between TiDB and MySQL in Profiles M and S."""
        prof_m = PROFILES["M"]
        self.assertEqual(prof_m["total_db_cpus"], 6.0)
        self.assertEqual(prof_m["sysbench_cpus"], 3.0)
        self.assertEqual(prof_m["tidb"]["tikv_nodes"] * 800, 2400)
        self.assertEqual(prof_m["mysql"]["buffer_pool_size"], "2400M")
        self.assertFalse(prof_m["mysql"]["binlog_enabled"])

        prof_s = PROFILES["S"]
        self.assertEqual(prof_s["total_db_cpus"], 4.0)
        self.assertEqual(prof_s["sysbench_cpus"], 2.0)
        self.assertEqual(prof_s["tidb"]["tikv_nodes"] * 500, 1500)
        self.assertEqual(prof_s["mysql"]["buffer_pool_size"], "1500M")
        self.assertFalse(prof_s["mysql"]["binlog_enabled"])

        prof_xs = PROFILES["XS"]
        self.assertEqual(prof_xs["tidb"]["tikv_nodes"], 3)
        self.assertEqual(prof_xs["tidb"]["tikv_nodes"] * 250, 750)
        self.assertEqual(prof_xs["mysql"]["buffer_pool_size"], "750M")
        self.assertFalse(prof_xs["mysql"]["binlog_enabled"])


if __name__ == "__main__":
    unittest.main()
