"""Unit tests for bench.resources module."""

from __future__ import annotations

import unittest

from bench.resources import parse_bytes, parse_docker_stats


class TestResources(unittest.TestCase):
    def test_parse_docker_stats(self):
        """Verify parsing of standard tab-delimited docker stats line."""
        line = "tidb-tikv0\t35.20%\t1.8GiB / 2.5GiB\t1.2GB / 3.4GB"
        parsed = parse_docker_stats(line)

        self.assertEqual(parsed["name"], "tidb-tikv0")
        self.assertAlmostEqual(parsed["cpu_pct"], 35.20, places=2)
        # 1.8 GiB = 1.8 * 1024^3 = 1,932,735,283.2 bytes
        self.assertAlmostEqual(parsed["mem_bytes"], 1.8 * (1024**3), delta=100)
        # 1.2 GB = 1.2 * 10^9
        self.assertAlmostEqual(parsed["block_read_bytes"], 1.2 * (1000**3), delta=100)
        # 3.4 GB = 3.4 * 10^9
        self.assertAlmostEqual(parsed["block_write_bytes"], 3.4 * (1000**3), delta=100)

    def test_parse_handles_kB_MB(self):
        """Verify correct parsing of kB, MB, KiB, MiB units."""
        line = "mysql-server\t10.5%\t500MB / 4GB\t250kB / 15MiB"
        parsed = parse_docker_stats(line)

        self.assertEqual(parsed["name"], "mysql-server")
        self.assertAlmostEqual(parsed["cpu_pct"], 10.5, places=2)
        self.assertEqual(parsed["mem_bytes"], 500 * (1000**2))
        self.assertEqual(parsed["block_read_bytes"], 250 * 1000)
        self.assertEqual(parsed["block_write_bytes"], 15 * (1024**2))

    def test_parse_bytes_helpers(self):
        """Verify parse_bytes helper directly."""
        self.assertEqual(parse_bytes("100B"), 100.0)
        self.assertEqual(parse_bytes("2KiB"), 2048.0)
        self.assertEqual(parse_bytes("10MB"), 10000000.0)
        self.assertEqual(parse_bytes("1GiB"), 1024.0**3)


if __name__ == "__main__":
    unittest.main()
