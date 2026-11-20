"""Offline unit tests for bench.db functions using mock cursors."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from bench.db import analyze, checksum, engine_settings


class TestDbOffline(unittest.TestCase):
    def test_analyze(self):
        """Verify analyze executes ANALYZE TABLE and closes cursor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        analyze(mock_conn, "shipments")

        mock_cursor.execute.assert_called_once_with("ANALYZE TABLE shipments;")
        mock_cursor.close.assert_called_once()

    def test_checksum(self):
        """Verify checksum returns tuple (count, sum_cod)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1000000, 5000000000000)
        mock_conn.cursor.return_value = mock_cursor

        cnt, sum_cod = checksum(mock_conn, "shipments")

        self.assertEqual(cnt, 1000000)
        self.assertEqual(sum_cod, 5000000000000)
        mock_cursor.execute.assert_called_once_with(
            "SELECT COUNT(*), COALESCE(SUM(cod_amount), 0) FROM shipments;"
        )
        mock_cursor.close.assert_called_once()

    def test_engine_settings_tidb(self):
        """Verify engine_settings extracts block_cache and max_replicas for TiDB."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Responses for SHOW CONFIG (tikv), SHOW CONFIG (pd), and SELECT tidb_version()
        mock_cursor.fetchall.side_effect = [
            [("tikv", f"tikv{i}:20160", "storage.block-cache.capacity", "800MiB") for i in range(3)],
            [("pd", "127.0.0.1:2379", "replication.max-replicas", "3")],
        ]
        mock_cursor.fetchone.return_value = ("Release Version: v8.5.5",)
        mock_conn.cursor.return_value = mock_cursor

        settings = engine_settings(mock_conn, "tidb")

        self.assertEqual(settings["engine"], "tidb")
        self.assertEqual(settings["block_cache"], "800MiB")
        self.assertEqual(settings["max_replicas"], 3)
        self.assertIn("v8.5.5", settings["version"])
        self.assertIn("machine", settings)
        self.assertIn("profile", settings)
        mock_cursor.close.assert_called_once()

    def test_engine_settings_mysql(self):
        """Verify engine_settings extracts buffer_pool and version for MySQL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor.fetchone.side_effect = [
            ("innodb_buffer_pool_size", "2516582400"),  # 2400 MiB in bytes
            ("8.4.11",),
        ]
        mock_conn.cursor.return_value = mock_cursor

        settings = engine_settings(mock_conn, "mysql")

        self.assertEqual(settings["engine"], "mysql")
        self.assertEqual(settings["buffer_pool"], "2516582400")
        self.assertEqual(settings["version"], "8.4.11")
        self.assertIn("machine", settings)
        self.assertIn("profile", settings)
        mock_cursor.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
