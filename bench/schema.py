"""Shared shipments DDL and secondary index definitions."""

import re

INDEXES = {
    "idx_code": "(tracking_code)",
    "idx_code_nonuniq": "(tracking_code)",
    "idx_code_cov": "(tracking_code,status,updated_at)",
    "idx_sender": "(sender_id)",
    "idx_sender_created": "(sender_id,created_at)",
    "idx_sender_cov": "(sender_id,created_at,status,cod_amount)",
    "idx_hub": "(dest_hub_id)",
    "idx_hub_status": "(dest_hub_id,status)",
    "idx_cod": "(cod_amount)",
    "idx_status": "(status)",
}
RQ4_INDEX_SETS = {
    0: [],
    1: ["idx_code"],
    3: ["idx_code", "idx_sender_created", "idx_hub_status"],
}
RQ4_INDEX_SETS[5] = RQ4_INDEX_SETS[3] + ["idx_cod", "idx_status"]
# Same key prefix with and without covering columns. W2 changes only sender_cov.
RQ4_INDEX_SETS["sender_created"] = ["idx_sender_created"]
RQ4_INDEX_SETS["sender_cov"] = ["idx_sender_cov"]


def identifier(name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f"`{name}`"


def shipments_ddl(engine, pk="bigint_clustered", table="shipments"):
    if engine not in {"mysql", "tidb"} or pk not in {
        "bigint_clustered",
        "bigint_nonclustered",
        "code_clustered",
    }:
        raise ValueError((engine, pk))
    if engine == "mysql" and pk == "bigint_nonclustered":
        raise ValueError("InnoDB uses clustered primary keys")
    key = "tracking_code" if pk == "code_clustered" else "id"
    suffix = ""
    if engine == "tidb":
        suffix = " NONCLUSTERED" if pk == "bigint_nonclustered" else " CLUSTERED"
    extra = ", UNIQUE KEY uk_id (id)" if key == "tracking_code" else ""
    return f"""CREATE TABLE {identifier(table)} (
        id BIGINT NOT NULL AUTO_INCREMENT,
        tracking_code VARCHAR(20) NOT NULL,
        sender_id INT NOT NULL,
        origin_hub_id SMALLINT NOT NULL,
        dest_hub_id SMALLINT NOT NULL,
        status TINYINT NOT NULL,
        cod_amount INT NOT NULL DEFAULT 0,
        weight_grams INT NOT NULL,
        shipping_fee INT NOT NULL,
        recipient_phone VARCHAR(15) NOT NULL,
        recipient_address VARCHAR(150) NOT NULL,
        note VARCHAR(100),
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        PRIMARY KEY ({key}){suffix}{extra})"""


def create_index_sql(table, name):
    kind = "UNIQUE " if name == "idx_code" else ""
    return (
        f"CREATE {kind}INDEX {identifier(name)} ON {identifier(table)} {INDEXES[name]}"
    )


def drop_index_sql(table, name):
    return f"DROP INDEX {identifier(name)} ON {identifier(table)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["mysql", "tidb"])
    parser.add_argument("--pk", default="bigint_clustered")
    parser.add_argument("--table", default="shipments")
    args = parser.parse_args()
    print(shipments_ddl(args.engine, args.pk, args.table))
