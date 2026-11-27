"""B.1: size model of the shipments table and its indexes, computed from the TSV.

python -m experiments.b1_model [ROWS ...]  (default 1000000 3000000; adds 10000000)

Every row of the input is encoded the way each engine stores it, so the model has
no fitted constant. 10 million rows are extrapolated from the per-row averages of
the largest input, since the generator draws every row from the same distributions.

MySQL (InnoDB, DYNAMIC rows, one copy): record header 5 B, one length byte per
non-NULL VARCHAR (all values here are shorter than 128 B), 1 B NULL bitmap, the
hidden transaction id (6 B) and roll pointer (7 B) in clustered records; a
secondary record holds its key columns and the primary key. Pages are 16 KiB with
128 B of fixed overhead and 2 B of page directory per 6 records. Clustered pages
filled by ascending inserts keep 1/16 free; secondary pages from a sorted index
build are filled completely (innodb_fill_factor=100). Non-leaf pages are left out.

TiDB (TiKV, one copy, logical bytes before compression): a TiKV key is 'z', the
memcomparable encoding of the TiDB key (9 B per started group of 8 B) and an 8 B
timestamp. Values up to 255 B are stored inside the write column family next to
type (1 B), start_ts (varint, 9 B) and a 2 B prefix; longer values go to the default
column family, which repeats the key. A row value uses row format v2: 6 B header,
1 B column id per column, 2 B offset per non-NULL column, integers in 1, 2, 4 or 8 B,
DATETIME in 8 B and strings as they are. In keys every integer and DATETIME takes
9 B and a string takes 1 flag byte plus its memcomparable encoding. A non-unique
index entry has the handle in its key and a 1 B value; a unique one keeps the 8 B
handle as its value.
"""

import argparse
import csv
from pathlib import Path

SEED = 20261116
PAGE, PAGE_FIXED, DIR_PER_REC = 16384, 128, 2 / 6
CLUSTERED_FILL, SECONDARY_FILL = 15 / 16, 1.0
SHORT_VALUE_MAX = 255
INDEXES = {
    # name: (columns, unique)
    "idx_code": (["tracking_code"], True),
    "idx_sender_created": (["sender_id", "created_at"], False),
    "idx_hub_status": (["dest_hub_id", "status"], False),
    "idx_cod": (["cod_amount"], False),
    "idx_status": (["status"], False),
    "idx_sender_cov": (["sender_id", "created_at", "status", "cod_amount"], False),
}
COLUMNS = [
    "id", "tracking_code", "sender_id", "origin_hub_id", "dest_hub_id", "status",
    "cod_amount", "weight_grams", "shipping_fee", "recipient_phone", "recipient_address",
    "note", "created_at", "updated_at",
]
STRINGS = {"tracking_code", "recipient_phone", "recipient_address", "note"}
DATETIMES = {"created_at", "updated_at"}
MYSQL_FIXED = {"id": 8, "sender_id": 4, "origin_hub_id": 2, "dest_hub_id": 2, "status": 1,
               "cod_amount": 4, "weight_grams": 4, "shipping_fee": 4,
               "created_at": 5, "updated_at": 5}


def mc(n):
    """Length of the memcomparable encoding of n bytes (groups of 8 plus a marker)."""
    return (n // 8 + 1) * 9


def tikv_key(raw_len):
    return 1 + mc(raw_len) + 8


def write_cf(raw_key_len, value_len):
    """Bytes of one MVCC version: write CF entry, plus a default CF entry if long."""
    key = tikv_key(raw_key_len)
    if value_len <= SHORT_VALUE_MAX:
        return key + 1 + 9 + 2 + value_len
    return key + 1 + 9 + key + value_len


def compact_int(v):
    v = int(v)
    for size, bound in ((1, 1 << 7), (2, 1 << 15), (4, 1 << 31)):
        if -bound <= v < bound:
            return size
    return 8


def key_col(name, value):
    if name in STRINGS:
        return 1 + mc(len(value.encode()))
    return 9


def row_sizes(fields):
    """{object: (raw, mysql, tidb)} bytes of one row and of its index entries."""
    row = dict(zip(COLUMNS, fields))
    note_null = row["note"] == r"\N"
    lengths = {c: len(row[c].encode()) for c in STRINGS if not (c == "note" and note_null)}
    raw = sum(MYSQL_FIXED.values()) + sum(lengths.values())
    mysql_row = 5 + len(lengths) + 1 + 6 + 7 + raw
    data = sum(lengths.values())
    for c in COLUMNS[1:]:
        if c in DATETIMES:
            data += 8
        elif c not in STRINGS:
            data += compact_int(row[c])
    not_null = 13 - int(note_null)
    value = 6 + 13 + 2 * not_null + data
    out = {"rows": (raw, mysql_row, write_cf(19, value))}
    for name, (cols, unique) in INDEXES.items():
        key_raw = 19 + sum(key_col(c, row[c]) for c in cols)
        mysql = 5 + sum(1 for c in cols if c in STRINGS) + 8 + sum(
            lengths[c] if c in STRINGS else MYSQL_FIXED[c] for c in cols)
        tidb = write_cf(key_raw, 8) if unique else write_cf(key_raw + 9, 1)
        out[name] = (0, mysql, tidb)
    return out


def pages_bytes(record_bytes, records, fill):
    usable = (PAGE - PAGE_FIXED) * fill
    return -(-(record_bytes + DIR_PER_REC * records) // usable) * PAGE


def model(path):
    sums, count = {}, 0
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            count += 1
            for obj, sizes in row_sizes(line.rstrip("\n").split("\t")).items():
                acc = sums.setdefault(obj, [0, 0, 0])
                for i, v in enumerate(sizes):
                    acc[i] += v
    return count, sums


def to_rows(count, sums, scale=1.0):
    out = []
    for obj, (raw, mysql, tidb) in sums.items():
        fill = CLUSTERED_FILL if obj == "rows" else SECONDARY_FILL
        n = round(count * scale)
        out.append({
            "rows": n,
            "object": obj,
            "raw_bytes": round(raw * scale),
            "mysql_record_bytes": round(mysql * scale),
            "mysql_bytes": round(pages_bytes(mysql * scale, n, fill)),
            "tidb_bytes": round(tidb * scale),
        })
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=int, nargs="*", default=[1_000_000, 3_000_000])
    parser.add_argument("--extrapolate", type=int, default=10_000_000)
    parser.add_argument("--output", type=Path, default=Path("results/b1_model.csv"))
    args = parser.parse_args()
    table = []
    for rows in sorted(args.rows):
        count, sums = model(Path(f"data/shipments_{rows}_{SEED}.tsv"))
        if count != rows:
            raise ValueError(f"TSV has {count} rows, expected {rows}")
        table += to_rows(count, sums)
    table += to_rows(count, sums, args.extrapolate / count)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    for r in table:
        print(r)


if __name__ == "__main__":
    main()
