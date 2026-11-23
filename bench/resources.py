"""Resource monitoring and docker stats parsing module for benchmark runs.

Provides utilities to parse docker stats output and sample container resource
utilization (CPU percentage, memory usage, block read/write I/O) at fixed intervals.
"""

from __future__ import annotations

import csv
import re
import subprocess
import time
from pathlib import Path
from typing import Any

# Multipliers for storage units (decimal and binary)
UNIT_MULTIPLIERS = {
    "b": 1,
    "bytes": 1,
    "k": 1000,
    "kb": 1000,
    "kib": 1024,
    "m": 1000**2,
    "mb": 1000**2,
    "mib": 1024**2,
    "g": 1000**3,
    "gb": 1000**3,
    "gib": 1024**3,
    "t": 1000**4,
    "tb": 1000**4,
    "tib": 1024**4,
}


def parse_bytes(size_str: str) -> float:
    """Parse human-readable storage string into bytes.

    Examples: '1.8GiB' -> 1,932,735,283.2, '3.4GB' -> 3,400,000,000.0, '512kB' -> 512,000.0
    """
    clean = size_str.strip()
    match = re.match(r"^([\d.]+)\s*([a-zA-Z]+)?$", clean)
    if not match:
        return 0.0
    val = float(match.group(1))
    unit = (match.group(2) or "b").lower()
    return val * UNIT_MULTIPLIERS.get(unit, 1)


def parse_docker_stats(line: str) -> dict[str, Any]:
    """Parse a tab-delimited docker stats line into a structured dictionary.

    Expected format:
      name \t cpu_pct \t mem_usage / mem_limit \t block_read / block_write
    Example:
      'tidb-tikv0\t35.20%\t1.8GiB / 2.5GiB\t1.2GB / 3.4GB'
    """
    parts = [p.strip() for p in line.split("\t")]
    if len(parts) < 4:
        # Fallback if split by multiple spaces
        parts = [p.strip() for p in re.split(r"\s{2,}", line) if p.strip()]

    name = parts[0] if len(parts) > 0 else "unknown"

    # CPU parsing: "35.20%" -> 35.20
    cpu_str = parts[1].replace("%", "").strip() if len(parts) > 1 else "0"
    try:
        cpu_pct = float(cpu_str)
    except ValueError:
        cpu_pct = 0.0

    # Memory parsing: "1.8GiB / 2.5GiB" -> 1.8 GiB in bytes
    mem_bytes = 0.0
    if len(parts) > 2:
        mem_part = parts[2].split("/")[0].strip()
        mem_bytes = parse_bytes(mem_part)

    # Block I/O parsing: "1.2GB / 3.4GB" -> (read bytes, write bytes)
    block_read_bytes = 0.0
    block_write_bytes = 0.0
    if len(parts) > 3:
        io_parts = parts[3].split("/")
        if len(io_parts) >= 1:
            block_read_bytes = parse_bytes(io_parts[0].strip())
        if len(io_parts) >= 2:
            block_write_bytes = parse_bytes(io_parts[1].strip())

    return {
        "name": name,
        "cpu_pct": cpu_pct,
        "mem_bytes": mem_bytes,
        "block_read_bytes": block_read_bytes,
        "block_write_bytes": block_write_bytes,
    }


def sample_once(container_names: list[str] | None = None) -> list[dict[str, Any]]:
    """Query docker stats once and return a list of parsed container metrics."""
    cmd = [
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.BlockIO}}",
    ]
    if container_names:
        cmd.extend(container_names)

    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    results = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            results.append(parse_docker_stats(line))
    return results


def sample(
    containers: list[str],
    interval_s: float = 2.0,
    out: Path | str = "results/resources.csv",
    stop_event: Any = None,
) -> None:
    """Sample container resources periodically and record snapshots to a CSV file."""
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "timestamp",
        "name",
        "cpu_pct",
        "mem_bytes",
        "block_read_bytes",
        "block_write_bytes",
    ]

    write_header = not out_path.exists() or out_path.stat().st_size == 0
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        while stop_event is None or not stop_event.is_set():
            ts = time.time()
            try:
                samples = sample_once(containers)
                for s in samples:
                    s["timestamp"] = ts
                    writer.writerow(s)
                f.flush()
            except Exception:
                pass
            time.sleep(interval_s)


def resource_snapshot(client, containers):
    snapshot = {}
    for name, cid in containers.items():
        stats = client.api.stats(cid, stream=False, one_shot=True)
        io = stats["blkio_stats"]["io_service_bytes_recursive"]
        # These two keep no data, so they may not have touched the disk since a restart.
        if io is None and name not in {"sysbench", "tidb"}:
            raise RuntimeError(f"Missing device I/O counters for {name}")
        snapshot[name] = {
            "cpu_ns": stats["cpu_stats"]["cpu_usage"]["total_usage"],
            "memory_bytes": stats["memory_stats"]["usage"],
            "write_bytes": sum(r["value"] for r in io or [] if r["op"].lower() == "write"),
            "read_bytes": sum(r["value"] for r in io or [] if r["op"].lower() == "read"),
        }
    return {"time_ns": time.monotonic_ns(), "services": snapshot}
