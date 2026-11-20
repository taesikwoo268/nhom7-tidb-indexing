"""Load a shared TSV and publish shipments only after verifying its checksum."""

import hashlib
from itertools import islice
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from .config import get_engine_config
from .datagen import COLUMNS, write_csv
from .db import analyze, checksum, connect
from .environment import ROOT, assert_engine
from .schema import identifier, shipments_ddl


def load_tsv(cursor, path, table):
    sql = (
        f"LOAD DATA LOCAL INFILE %s INTO TABLE {identifier(table)} CHARACTER SET utf8mb4 "
        r"FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n' "
        + "("
        + ",".join(COLUMNS)
        + ")"
    )
    # Bound transaction memory on the 1.75 GiB TiKV nodes of profile S.
    with TemporaryDirectory(dir=path.parent) as folder, path.open("rb") as source:
        batch_path = Path(folder) / "batch.tsv"
        while batch := list(islice(source, 10000)):
            with batch_path.open("wb") as dest:
                dest.writelines(batch)
            cursor.execute(sql, (batch_path.resolve().as_posix(),))
            cursor.execute("SHOW WARNINGS")
            warnings = cursor.fetchall()
            if warnings:
                raise RuntimeError(f"LOAD DATA warnings: {warnings[:3]}")


def load_dataset(engine, rows, seed):
    if rows <= 0:
        raise ValueError("rows must be positive")
    assert_engine(engine)
    path = ROOT / f"data/shipments_{rows}_{seed}.tsv"
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        temp = path.with_suffix(".tmp")
        write_csv(rows, temp, seed)
        temp.replace(path)
    digest = hashlib.sha256()
    count = total = 0
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            count += 1
            total += int(line.split(b"\t", 7)[6])
    if count != rows:
        raise ValueError(f"TSV has {count} rows, expected {rows}")
    database = identifier(get_engine_config(engine)["database"])
    with connect(engine, server_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        cur.execute(f"USE {database}")
        cur.execute("SHOW TABLES LIKE 'shipments'")
        if cur.fetchall():
            if checksum(conn, "shipments") != (rows, total):
                raise ValueError(
                    "Existing shipments differs from input TSV; select another DB_NAME for this dataset."
                )
        else:
            staging = "shipments_load_" + uuid4().hex
            cur.execute(shipments_ddl(engine, table=staging))
            try:
                load_tsv(cur, path, staging)
                if checksum(conn, staging) != (rows, total):
                    raise ValueError(
                        "Database row count or SUM(cod_amount) differs from TSV"
                    )
                cur.execute(f"RENAME TABLE {staging} TO shipments")
            finally:
                cur.execute(f"DROP TABLE IF EXISTS {staging}")
        analyze(conn, "shipments", engine=engine)
    print(
        f"{engine}: rows={rows} sum_cod={total} seed={seed} sha256={digest.hexdigest()}"
    )
