# Nhóm 7 — Chi phí chỉ mục phụ trên TiDB và MySQL: Kế hoạch triển khai

> **Dành cho agent thực thi:** BẮT BUỘC dùng skill superpowers:subagent-driven-development (khuyến nghị) hoặc superpowers:executing-plans để thực hiện kế hoạch theo từng task. Các bước dùng checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Xây dựng bộ công cụ thực nghiệm có thể chạy lại được, gồm môi trường, script sinh dữ liệu, script đo và biểu đồ, để trả lời RQ1–RQ4 trong tài liệu thiết kế và tạo demo chịu lỗi cho mục A.3.

**Kiến trúc:**
- Package Python `bench/` chứa mọi phần thuần logic và kiểm thử được: sinh dữ liệu, tạo câu lệnh DDL, mô hình dung lượng, thống kê, phân tích kế hoạch thực thi.
- Thư mục `experiments/` chứa các script mỏng, mỗi script chạy một câu hỏi nghiên cứu trên một trong hai hệ. Cả hai hệ được kết nối qua cùng giao thức MySQL và chạy cùng một câu SQL. Kết quả được ghi nối tiếp vào các file CSV trong `results/`.
- Các file Docker Compose trong `docker/` chỉ khởi động một hệ tại một thời điểm, với cấu hình tài nguyên tương đương theo mục 7 của tài liệu thiết kế.

**Công nghệ:** Python 3.11, `mysql-connector-python`, `pytest`, `pandas`, `matplotlib`; Docker Compose; TiDB v8.5 LTS (image `pingcap/*:v8.5.0`); MySQL 8.4; sysbench 1.0 với script Lua tùy biến.

**Tài liệu thiết kế:** `docs/superpowers/specs/2026-11-16-nhom7-tidb-indexing-van-don-design.md`

## Ràng buộc chung

- Một máy, 16 GB RAM, 8 nhân. **Tuyệt đối không chạy container TiDB và MySQL cùng lúc khi đang đo.**
- Tương đương CPU: cụm TiDB gồm PD 1 + TiDB 1,5 + 3 × TiKV 1,5 = 7 nhân; MySQL = 7 nhân.
- Tương đương bộ nhớ đệm: `storage.block-cache.capacity = "1GB"` trên mỗi TiKV (3 node) tương ứng với `innodb_buffer_pool_size = 3G`.
- Giới hạn RAM container: mỗi TiKV 2,5G, TiDB 2G, PD 1G, MySQL 4G.
- Mức độ bền: TiDB để mặc định; MySQL đặt `innodb_flush_log_at_trx_commit=1`, `sync_binlog=1`.
- Số bản sao: TiDB mặc định 3. Riêng RQ4 đo thêm với `replication.max-replicas = 1`.
- Dữ liệu: cả hai hệ nạp cùng một file CSV bằng `LOAD DATA LOCAL INFILE`, seed cố định `20261116`.
- Quy mô: 1.000.000 dòng (phát triển) và 10.000.000 dòng (đo chính thức); 30.000.000 dòng là tùy chọn.
- Quy trình mỗi phép đo: chạy `ANALYZE TABLE` trước, warm-up, lặp ít nhất 5 lần, báo cáo trung vị và IQR.
- Hai hệ chạy cùng một câu SQL. Hint chỉ mục dùng `FORCE INDEX` / `IGNORE INDEX` vì cả hai hệ đều hỗ trợ.
- RQ5 (hotspot) nằm ngoài kế hoạch này, sẽ bổ sung nếu tuần 4 còn thời gian.

## Các điểm cần kiểm soát khi review

1. **TiKV bỏ qua giới hạn RAM của container.** Nếu `block-cache.capacity` không được áp dụng, TiKV tính bộ nhớ đệm theo RAM của máy host và bị OOM. Task 4 kiểm tra giá trị này bằng `SHOW CONFIG`, và mọi dòng kết quả đều ghi lại giá trị đó.
2. **Hai hệ chạy cùng lúc.** Khi đó tài nguyên âm thầm bị chia đôi và mọi số đo đều sai. `scripts/use_engine.sh` từ chối khởi động một hệ khi container của hệ kia đang chạy (Task 4).
3. **Hint chỉ mục bị bỏ qua mà không báo.** Nếu lần chạy "ép dùng index" thực chất lại quét toàn bảng, kết quả RQ2 sẽ bị đảo ngược. Mỗi lần chạy có ép buộc đều ghi lại toán tử truy cập dữ liệu ở trên cùng, và script dừng ngay nếu toán tử không khớp (bộ phân tích ở Task 6, kiểm tra ở Task 8).
4. **Hai hệ chứa dữ liệu khác nhau.** Sau khi nạp, số dòng và checksum `SUM(cod_amount)` của hai hệ phải bằng nhau, nếu không thì dừng nạp (Task 4).
5. **Cấu hình số bản sao của TiDB bị sót lại giữa các lần chạy.** Sau một lần chạy RQ4 với 1 bản sao, các lần đo sau có thể vô tình vẫn chạy ở 1 bản sao. Mọi dòng kết quả đều ghi `max_replicas`, và `rq4_write.sh` dùng `trap` để khôi phục về 3 khi kết thúc (Task 10).

---

## Cấu trúc thư mục

```
nhom7-tidb-indexing/
  docker/
    tidb.compose.yml        # PD, 3×TiKV, TiDB với giới hạn theo mục 7
    tikv.toml               # block cache 1GB
    mysql.compose.yml
    mysql.cnf
  bench/
    __init__.py
    config.py               # thông tin kết nối từng hệ
    datagen.py              # sinh CSV vận đơn
    schema.py               # tạo DDL, biến thể PK, các bộ index
    storage_model.py        # mô hình dung lượng lý thuyết (B.1)
    db.py                   # kết nối, analyze, phân tích EXPLAIN ANALYZE
    runner.py               # đo thời gian, Stats, ghi CSV
  experiments/
    b1_storage.py
    rq1_covering.py
    rq2_selectivity.py
    rq3_pk.py
    plots.py
  sysbench/
    shipments_write.lua     # W1 insert / W2 update
  scripts/
    use_engine.sh           # bật một hệ, tắt hoặc từ chối nếu hệ kia đang chạy
    load.sh                 # sinh dữ liệu + nạp + kiểm tra
    rq4_write.sh
    chaos_demo.sh
  tests/
  results/                  # CSV kết quả (bản thô bị gitignore, bản tổng hợp được commit)
```

---

### Task 1: Khung dự án

**Files:**
- Tạo: `pyproject.toml`, `bench/__init__.py`, `bench/config.py`, `tests/test_config.py`, `.gitignore`

**Interfaces:**
- Cung cấp: `bench.config.ENGINES: dict[str, dict]` với hai khóa:
  - `"tidb"`: `host=127.0.0.1, port=4000, user=root, password=""`;
  - `"mysql"`: `port=3306`, cùng user.

  Cả hai đều có `database="logistics"` và `allow_local_infile=True`.

- [ ] **Bước 1: Viết test (sẽ fail)** `test_engines_defined`. Kiểm tra:
  - `set(ENGINES) == {"tidb", "mysql"}`;
  - `ENGINES["tidb"]["port"] == 4000` và `ENGINES["mysql"]["port"] == 3306`;
  - cả hai có `database == "logistics"` và `allow_local_infile is True`.
- [ ] **Bước 2: Chạy** `pytest tests/test_config.py -v` → FAIL (lỗi import).
- [ ] **Bước 3: Cài đặt:**
  - `bench/config.py`;
  - `pyproject.toml` với các thư viện ở mục Công nghệ;
  - `.gitignore` gồm `results/raw/`, `data/`, `*.csv`.
- [ ] **Bước 4: Chạy** `pytest -v` → PASS.
- [ ] **Bước 5: Commit.** Chạy `git init`, add tài liệu thiết kế, kế hoạch và khung dự án, rồi `git commit -m "chore: project skeleton"`.

---

### Task 2: Script sinh dữ liệu vận đơn

**Files:**
- Tạo: `bench/datagen.py`, `tests/test_datagen.py`

**Interfaces:**
- Cung cấp:
  - Hằng số: `N_SENDERS = 100_000`, `N_HUBS = 200`, `COD_MAX = 10_000_000`, `DAYS = 180`, `SEED = 20261116`, `STATUS_WEIGHTS = {1: .03, 2: .04, 3: .05, 4: .05, 5: .80, 6: .03}` (5 = đã giao), `START_TS = datetime(2026, 5, 1)`.
  - `COLUMNS: list[str]`: 14 cột của `shipments` theo đúng thứ tự trong DDL.
  - `generate_rows(n: int, seed: int = SEED, start_id: int = 1) -> Iterator[tuple]`
  - `write_csv(n: int, path: Path, seed: int = SEED) -> None`: phân tách bằng tab, không có header, giá trị NULL ghi là `\N`.

- [ ] **Bước 1: Viết các test (sẽ fail)**, dùng `n = 50_000`:
  - `test_deterministic`: hai lần gọi với cùng seed cho ra 1000 dòng đầu giống hệt nhau.
  - `test_tracking_code_unique_and_format`: mọi mã vận đơn là duy nhất và khớp `^VN\d{12}$`.
  - `test_id_sequential`: id chạy liên tục từ `start_id` đến `start_id+n-1`.
  - `test_status_skew`: tỉ lệ status 5 nằm trong `0,80 ± 0,01`.
  - `test_cod_uniform_and_uncorrelated`:
    - `0 <= cod < COD_MAX`;
    - tỉ lệ dòng có cod trong `[0, COD_MAX/10)` nằm trong `0,10 ± 0,01`;
    - `abs(pearson(id, cod)) < 0,02`.
  - `test_created_at_monotonic_with_id`: `created_at` không giảm khi id tăng, và toàn bộ nằm trong `DAYS` ngày kể từ `START_TS`.
  - `test_sender_zipf`: shop có nhiều đơn nhất có số đơn lớn hơn 10 lần shop ở mức trung vị; mọi `sender_id` nằm trong `1..N_SENDERS`.
  - `test_hubs_in_range`: `origin_hub_id` và `dest_hub_id` nằm trong `1..N_HUBS`.
- [ ] **Bước 2: Chạy** `pytest tests/test_datagen.py -v` → FAIL.
- [ ] **Bước 3: Cài đặt:**
  - Dùng `random.Random(seed)`.
  - Mã vận đơn sinh bằng `rng.getrandbits`, dùng một `set` để kiểm tra trùng.
  - `sender_id` lấy theo phân phối Zipf (s = 1,1): tính sẵn trọng số cộng dồn rồi dùng `rng.choices`.
  - `created_at = START_TS + (i / n) * DAYS ngày`, cộng thêm một chút nhiễu nhỏ nhưng vẫn giữ tính không giảm.
- [ ] **Bước 4: Chạy** → PASS. Ngoài ra chạy `python -m bench.datagen 1000000 data/shipments_1m.tsv` phải hoàn thành; ghi lại thời gian chạy.
- [ ] **Bước 5: Commit** `feat: shipments data generator`.

---

### Task 3: Hàm tạo DDL và các bộ index

**Files:**
- Tạo: `bench/schema.py`, `tests/test_schema.py`

**Interfaces:**
- Cung cấp:
  - `PkVariant = Literal["bigint_clustered", "bigint_nonclustered", "code_clustered"]`
  - `shipments_ddl(engine: str, pk: PkVariant = "bigint_clustered", table: str = "shipments") -> str`
  - `INDEXES: dict[str, str]`, ánh xạ tên index sang danh sách cột:
    - `idx_code: "(tracking_code)"`, `idx_code_cov: "(tracking_code, status, updated_at)"`;
    - `idx_sender: "(sender_id)"`, `idx_sender_created: "(sender_id, created_at)"`, `idx_sender_cov: "(sender_id, created_at, status, cod_amount)"`;
    - `idx_hub: "(dest_hub_id)"`, `idx_hub_status: "(dest_hub_id, status)"`;
    - `idx_cod: "(cod_amount)"`, `idx_status: "(status)"`.
  - `RQ4_INDEX_SETS: dict[int, list[str]]`:
    - `0: []`
    - `1: ["idx_code"]`
    - `3: ["idx_code", "idx_sender_created", "idx_hub_status"]`
    - `5`: 3 index của bộ 3, thêm `"idx_cod"` và `"idx_status"`.
  - `create_index_sql(table: str, name: str) -> str` và `drop_index_sql(table: str, name: str) -> str`. Riêng `idx_code` là `UNIQUE`.

- [ ] **Bước 1: Viết các test (sẽ fail):**
  - `test_tidb_clustered_keyword`: DDL tidb/bigint_clustered chứa `PRIMARY KEY (id) CLUSTERED`; biến thể bigint_nonclustered chứa `NONCLUSTERED`.
  - `test_mysql_has_no_cluster_keyword`: DDL của mysql không bao giờ chứa `CLUSTERED`.
  - `test_mysql_rejects_nonclustered`: `shipments_ddl("mysql", "bigint_nonclustered")` ném `ValueError`.
  - `test_code_clustered`: DDL của cả hai hệ có `PRIMARY KEY (tracking_code)` và `UNIQUE KEY uk_id (id)` (vì cột AUTO_INCREMENT bắt buộc phải là key).
  - `test_columns_match_datagen`: danh sách cột đọc ra từ DDL trùng với `datagen.COLUMNS`.
  - `test_rq4_sets_nested`: mỗi bộ index lớn hơn chứa trọn bộ nhỏ hơn.
- [ ] **Bước 2: Chạy** → FAIL.
- [ ] **Bước 3: Cài đặt.**
- [ ] **Bước 4: Chạy** → PASS.
- [ ] **Bước 5: Commit** `feat: DDL builders and index sets`.

---

### Task 4: Môi trường, chuyển hệ, nạp và kiểm tra dữ liệu

**Files:**
- Tạo: `docker/tidb.compose.yml`, `docker/tikv.toml`, `docker/mysql.compose.yml`, `docker/mysql.cnf`, `scripts/use_engine.sh`, `scripts/load.sh`, `bench/db.py` (ở task này chỉ có `connect`, `analyze`, `checksum`), `tests/test_db_offline.py`

**Interfaces:**
- Cung cấp:
  - `scripts/use_engine.sh tidb|mysql`: thoát với mã 1 và in thông báo nếu container của hệ *kia* đang chạy. Với cờ `--switch`, script tắt hệ kia trước. Sau khi bật, script chờ đến khi cổng trả lời `SELECT 1`.
  - `scripts/load.sh <engine> <rows>`: lần lượt
    1. sinh `data/shipments_<rows>.tsv` nếu chưa có;
    2. tạo database `logistics`;
    3. tạo bảng bằng `python -m bench.schema`;
    4. nạp bằng `LOAD DATA LOCAL INFILE`;
    5. chạy `ANALYZE TABLE`;
    6. in checksum.
  - `bench.db.connect(engine: str) -> mysql.connector.MySQLConnection`
  - `bench.db.analyze(conn, table: str) -> None`
  - `bench.db.checksum(conn, table: str) -> tuple[int, int]`: trả về `(COUNT(*), SUM(cod_amount))`.
  - `bench.db.engine_settings(conn, engine) -> dict`:
    - tidb trả về `block_cache`, `max_replicas`, `version`;
    - mysql trả về `buffer_pool`, `version`.

    Mọi dòng kết quả đều ghi kèm giá trị này.

- [ ] **Bước 1: Viết các file compose** theo giới hạn và cấu hình ở mục Ràng buộc chung:
  - TiKV mount `tikv.toml` (`[storage.block-cache] capacity = "1GB"`) qua tham số `--config`.
  - MySQL dùng `mysql.cnf`, đặt buffer pool, flush, sync_binlog và `local_infile=1`.
- [ ] **Bước 2: Viết test offline (sẽ fail)** `test_settings_keys`: với một cursor giả trả về các dòng `SHOW CONFIG` mẫu, `engine_settings(conn, "tidb")` trả về `block_cache == "1GiB"` và `max_replicas == 3`.
- [ ] **Bước 3: Cài đặt** các hàm trong `bench/db.py`. Thông số của tidb đọc bằng:
  - `SHOW CONFIG WHERE type='tikv' AND name='storage.block-cache.capacity'`
  - `SHOW CONFIG WHERE type='pd' AND name='replication.max-replicas'`
- [ ] **Bước 4: Chạy** `pytest tests/test_db_offline.py -v` → PASS.
- [ ] **Bước 5: Kiểm tra trên máy thực nghiệm:**
  - Chạy `scripts/use_engine.sh tidb` rồi `scripts/use_engine.sh mysql`. Lệnh thứ hai phải thoát với mã 1 và báo "tidb is running".
  - Khi TiDB đang chạy:
    - `SHOW CONFIG WHERE type='tikv' AND name='storage.block-cache.capacity'` trả về 3 dòng, mỗi dòng `1GiB`;
    - `SELECT * FROM information_schema.TIKV_STORE_STATUS` cho thấy 3 store ở trạng thái `Up`.
  - Chạy `scripts/load.sh tidb 1000000`, chuyển hệ bằng `--switch`, rồi chạy `scripts/load.sh mysql 1000000`. Hai lệnh phải in ra checksum giống nhau.
- [ ] **Bước 6: Commit** `feat: docker environment, engine switch, load + verify`.

---

### Task 5: Mô hình dung lượng và đo đạc cho B.1

**Files:**
- Tạo: `bench/storage_model.py`, `experiments/__init__.py`, `experiments/b1_storage.py`, `tests/test_storage_model.py`

**Interfaces:**
- Cung cấp:
  - `RowSpec(fixed_bytes: int, var_bytes_avg: float)`. `SHIPMENT_ROW = RowSpec(...)` được tính từ kiểu dữ liệu trong DDL và độ dài trung bình của các chuỗi do generator sinh ra.
  - `mysql_estimate(n: int, row: RowSpec, index_entry_bytes: list[int], fill_seq=15/16, fill_rand=0.72) -> dict[str, int]`, trả về các khóa `table`, `indexes`, `total` (đơn vị byte).
  - `tikv_estimate(n: int, row: RowSpec, index_entry_bytes: list[int], compression=0.60, lsm_amp=1.11, replicas=3) -> dict[str, int]`, trả về các khóa `per_replica`, `cluster`.
  - `experiments/b1_storage.measure_size(conn, engine: str, table: str) -> dict[str, int]`, trả về các khóa `table_bytes`, `index_bytes` (theo tên từng index), `total_bytes`. Task 9 dùng lại hàm này.
  - `experiments/b1_storage.py --engine E --rows N` ghi thêm vào `results/b1_storage.csv` các cột:
    - engine, rows, index_set;
    - dung lượng đo được: MySQL lấy từ `information_schema.TABLES`; TiDB lấy `SUM(APPROXIMATE_SIZE)` từ `TIKV_REGION_STATUS` nhân với số bản sao, kèm `du -sb` trên thư mục dữ liệu;
    - dung lượng theo mô hình;
    - snapshot docker stats trước và sau `CREATE INDEX`;
    - số giây để tạo index.

- [ ] **Bước 1: Viết các test (sẽ fail).** Dùng lại số liệu `sbtest1` của kế hoạch cũ làm phép kiểm tra hồi quy:
  - `mysql_estimate(10**7, RowSpec(188, 0), [8])["table"]` lệch không quá 2% so với `2192 MiB`;
  - `tikv_estimate(10**7, RowSpec(188,0), [8])["per_replica"]` lệch không quá 3% so với `1930 MiB`;
  - `test_linear_in_n`: ước lượng cho 2n xấp xỉ 2 lần ước lượng cho n, sai số không quá 1%.
- [ ] **Bước 2: Chạy** → FAIL.
- [ ] **Bước 3: Cài đặt** theo các chi phí phụ trên mỗi dòng ghi trong kế hoạch cũ:
  - InnoDB: +20 B header/MVCC mỗi dòng, 16 B cho mỗi mục index phụ;
  - TiKV: key 28 B, phần phụ của value 36 B, mỗi KV index 56 B.
- [ ] **Bước 4: Chạy** → PASS.
- [ ] **Bước 5: Kiểm tra:** chạy `b1_storage.py` cho cả hai hệ ở quy mô 1 triệu dòng, với `RQ4_INDEX_SETS[0]` và `RQ4_INDEX_SETS[5]`. File CSV phải có 4 dòng, và script in ra tỉ lệ giữa số đo thực tế và mô hình.
- [ ] **Bước 6: Commit** `feat: storage model and B.1 measurement`.

---

### Task 6: Công cụ đo và phân tích kế hoạch thực thi

**Files:**
- Sửa: `bench/db.py` (thêm các hàm explain)
- Tạo: `bench/runner.py`, `tests/test_runner.py`, `tests/test_explain_parse.py`

**Interfaces:**
- Cung cấp:
  - Dataclass `Stats`: `p50_ms, p95_ms, p99_ms, run_medians_ms: list[float], iqr_ms: float`.
  - `time_query(conn, sql: str, params: list[tuple], repeats: int = 5, warmup: int = 50) -> Stats`. Mỗi lần lặp chạy toàn bộ `params` một lượt và đọc hết các dòng trả về. Độ trễ đo bằng `time.perf_counter_ns`.
  - `summarize(latencies_ns: list[list[int]]) -> Stats` (hàm thuần).
  - `append_result(path: Path, row: dict) -> None`: ghi header ở lần ghi đầu tiên và tự thêm cột `timestamp`.
  - `parse_tidb_execution_info(text: str) -> dict`, trả về `cop_tasks`, `rpc_num`, `total_process_keys` (số nguyên, cộng dồn qua mọi lần xuất hiện).
  - `explain_analyze(conn, engine, sql, params) -> dict`, trả về:
    - `access_op`:
      - với tidb: toán tử đầu tiên tìm được từ trên xuống trong số `IndexLookUp|IndexReader|TableReader|Point_Get|Batch_Point_Get|IndexMerge`;
      - với mysql: một trong `Index lookup|Index range scan|Covering index|Table scan`;
    - `rows_examined`;
    - các trường phân tích được của tidb, hoặc với mysql là phần chênh lệch của `Handler_read_*` và `Innodb_buffer_pool_reads`.

- [ ] **Bước 1: Viết các test (sẽ fail):**
  - `test_summarize`: với 5 lần chạy dạng `[[1e6]*100, [2e6]*100, …]`, `p50_ms` bằng trung vị của toàn bộ, `run_medians_ms` có 5 phần tử, `iqr_ms` tính đúng.
  - `test_parse_tidb`: đầu vào `"cop_task: {num: 3, max: 1.1ms, proc_keys: 10, tot_proc: 2ms, rpc_num: 3, rpc_time: 2.4ms}, scan_detail: {total_process_keys: 30, total_keys: 31}"` cho ra `{"cop_tasks": 3, "rpc_num": 3, "total_process_keys": 30}`.
  - `test_parse_tidb_sums_two_readers`: khi có hai khối `cop_task` (IndexLookUp có một phía index và một phía bảng), các giá trị được cộng dồn.
  - `test_access_op_tidb`: với các dòng EXPLAIN ANALYZE mẫu có `IndexLookUp_7` ở trên cùng, kết quả là `"IndexLookUp"`.
  - `test_append_result_header_once`: sau hai lần ghi, file có 1 dòng header và 2 dòng dữ liệu.
- [ ] **Bước 2: Chạy** → FAIL.
- [ ] **Bước 3: Cài đặt.**
- [ ] **Bước 4: Chạy** → PASS.
- [ ] **Bước 5: Commit** `feat: timing harness and explain parsing`.

---

### Task 7: RQ1 — covering index và non-covering index

**Files:**
- Tạo: `experiments/rq1_covering.py`, `experiments/queries.py`, `tests/test_queries.py`

**Interfaces:**
- Sử dụng: `connect`, `analyze`, `engine_settings`, `explain_analyze`, `time_query`, `append_result`, `INDEXES`, `create_index_sql`, `drop_index_sql`.
- Cung cấp:
  - Trong `experiments/queries.py`:
    - các câu SQL `Q1_FULL`, `Q1_COV`, `Q2_FULL`, `Q2_COV`, `Q3`, dùng tham số `%s`;
    - `sample_params(conn, query_name: str, k: int, seed: int) -> list[tuple]`: lấy mẫu mã vận đơn, id shop, id kho từ dữ liệu có thật.
  - `RQ1_CASES: list[tuple[str, str, list[str]]]`, mỗi phần tử là (tên case, tên SQL, các index có mặt):
    - `("q1_single_full", "Q1_FULL", ["idx_code"])`
    - `("q1_single_cov", "Q1_COV", ["idx_code"])`
    - `("q1_covidx_cov", "Q1_COV", ["idx_code_cov"])`
    - `("q2_sender", "Q2_COV", ["idx_sender"])`
    - `("q2_sender_created", "Q2_COV", ["idx_sender_created"])`
    - `("q2_covering", "Q2_COV", ["idx_sender_cov"])`
    - `("q3_hub", "Q3", ["idx_hub"])`
    - `("q3_hub_status", "Q3", ["idx_hub_status"])`
  - Lệnh `--engine E --rows N` ghi ra `results/rq1.csv` các cột: engine, rows, case, các trường của Stats, các trường explain, thông số của hệ.

- [ ] **Bước 1: Viết test (sẽ fail)** `test_rq1_cases_reference_known`:
  - mọi tên SQL đều có trong `queries`;
  - mọi index đều có trong `INDEXES`;
  - `Q2_COV` chỉ SELECT các cột nằm trong `idx_sender_cov` cộng với PK.
- [ ] **Bước 2: Chạy** → FAIL.
- [ ] **Bước 3: Cài đặt.** Với mỗi case:
  1. xóa mọi index không phải PK;
  2. tạo các index của case;
  3. chạy `analyze`;
  4. warm-up;
  5. chạy `time_query` với 200 bộ tham số lấy mẫu;
  6. chạy một lần `explain_analyze` với bộ tham số đầu tiên.
- [ ] **Bước 4: Chạy** test → PASS. Sau đó chạy trên máy `python experiments/rq1_covering.py --engine tidb --rows 1000000`:
  - CSV có 8 dòng;
  - trên TiDB, case `q1_covidx_cov` có `access_op` là `IndexReader` (hoặc `Point_Get` vì là index unique);
  - case `q1_single_full` có `access_op` là `IndexLookUp` hoặc `Point_Get`.
- [ ] **Bước 5: Commit** `feat: RQ1 covering-index experiment`.

---

### Task 8: RQ2 — ngưỡng độ chọn lọc

**Files:**
- Tạo: `experiments/rq2_selectivity.py`, `bench/selectivity.py`, `tests/test_selectivity.py`

**Interfaces:**
- Cung cấp:
  - `SELECTIVITIES = [0.00001, 0.0001, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50]`
  - `cod_range(sel: float, cod_max: int, seed_offset: int) -> tuple[int, int]`: khoảng rộng `round(sel * cod_max)`, điểm bắt đầu thay đổi theo offset, luôn nằm trong `[0, cod_max)`.
  - `find_crossover(sels: list[float], t_index: list[float], t_scan: list[float]) -> float | None`: nội suy tuyến tính trên thang log tại lần đổi dấu đầu tiên của `t_index - t_scan`.
  - Lệnh chạy ghi ra `results/rq2.csv` các cột: engine, rows, sel, mode (`force_index|force_scan|optimizer`), Stats, `access_op`, `rows_returned`.

- [ ] **Bước 1: Viết các test (sẽ fail):**
  - `test_cod_range_width`.
  - `test_cod_range_in_bounds`, kiểm tra với mọi sel và mọi offset.
  - `test_crossover_simple`: với `t_index=[1,2,4,8]`, `t_scan=[5,5,5,5]`, sels `[.01,.02,.04,.08]`, kết quả nằm giữa .02 và .04.
  - `test_crossover_none`: trả về None khi index luôn nhanh hơn.
- [ ] **Bước 2: Chạy** → FAIL.
- [ ] **Bước 3: Cài đặt.** Ba câu SQL:
  - `SELECT * FROM shipments FORCE INDEX (idx_cod) WHERE cod_amount BETWEEN %s AND %s`;
  - câu tương tự với `IGNORE INDEX (idx_cod)`;
  - câu không có hint.

  Mỗi mức sel dùng 20 khoảng giá trị, `repeats=5`. **Dừng và báo lỗi** nếu lần chạy `force_index` có `access_op` là quét toàn bảng, hoặc lần chạy `force_scan` lại không phải quét toàn bảng.
- [ ] **Bước 4: Chạy** test → PASS. Chạy trên máy ở quy mô 1 triệu dòng:
  - mỗi hệ có 30 dòng kết quả;
  - script in ra điểm giao nhau và "điểm optimizer đổi phương án", tức mức sel đầu tiên mà `access_op` do optimizer chọn chuyển sang quét toàn bảng.
- [ ] **Bước 5: Commit** `feat: RQ2 selectivity crossover`.

---

### Task 9: RQ3 — các biến thể khóa chính

**Files:**
- Tạo: `experiments/rq3_pk.py`

**Interfaces:**
- Sử dụng: `shipments_ddl(engine, pk, table)`, các truy vấn của Task 7, `time_query`, `measure_size` của Task 5.
- Cung cấp: `results/rq3.csv` với các cột:
  - engine, pk_variant;
  - case (`q1_by_code`, `q1_by_id`, `q2_secondary`);
  - Stats, `access_op`;
  - dung lượng index phụ `idx_sender_created`.

  Ngoài ra có một dòng `w1_insert_tps`, đo bằng vòng lặp insert 60 giây:
  - 16 luồng qua `concurrent.futures`, mỗi luồng một kết nối riêng;
  - lô 100 dòng;
  - dữ liệu mới do generator sinh với `start_id = rows + 1`.

- [ ] **Bước 1: Cài đặt.** Với mỗi biến thể (tidb có 3: `bigint_clustered`, `bigint_nonclustered`, `code_clustered`; mysql có 2: `bigint_clustered`, `code_clustered`):
  1. tạo bảng `shipments_<variant>` bằng DDL;
  2. chạy `INSERT INTO ... SELECT * FROM shipments`;
  3. thêm `idx_sender_created`;
  4. chạy `analyze`;
  5. chạy các case.
- [ ] **Bước 2: Kiểm tra** ở quy mô 1 triệu dòng:
  - trên TiDB, `q1_by_id` của `bigint_nonclustered` có kế hoạch 2 bước (`IndexLookUp`, hoặc `Point_Get` trên `PRIMARY` rồi lấy dòng), trong khi `bigint_clustered` chỉ có một `Point_Get`;
  - dung lượng index phụ của `code_clustered` lớn hơn của `bigint_clustered` trên cả hai hệ.

  Nếu kết quả không như vậy thì ghi lại: đó là một phát hiện, không phải lỗi.
- [ ] **Bước 3: Commit** `feat: RQ3 primary-key variants`.

---

### Task 10: RQ4 — chi phí ghi bằng sysbench, cấu hình số bản sao, lấy mẫu tài nguyên

**Files:**
- Tạo: `sysbench/shipments_write.lua`, `scripts/rq4_write.sh`, `bench/resources.py`, `tests/test_resources.py`

**Interfaces:**
- Cung cấp:
  - Tham số của script Lua: `--mode=insert|update`, `--batch=1|100`, `--start-id`.
    - Chế độ insert sinh dòng theo các phân phối của `datagen`. Được phép đơn giản hóa trong Lua: `sender_id` phân bố đều, và báo cáo cần ghi chú điểm này.
    - Chế độ update chạy `UPDATE shipments SET status=?, updated_at=NOW() WHERE id=?` với id ngẫu nhiên đã tồn tại.
  - `bench.resources.parse_docker_stats(line: str) -> dict`, trả về name, cpu_pct, mem_bytes, block_read_bytes, block_write_bytes.
  - `sample(containers, interval_s=2, out=Path)`: lấy mẫu chạy nền.
  - `rq4_write.sh <engine> <rows>`:
    - lặp qua các bộ index `0 1 3 5` × số luồng `16 64` × chế độ `insert update`, riêng tidb thêm số bản sao `3 1`;
    - mỗi lần chạy: tạo lại index, chạy sysbench 120 giây với `--report-interval=1`, bật bộ lấy mẫu;
    - ghi thêm vào `results/rq4.csv` các cột: engine, n_indexes, threads, mode, replicas, tps, p95, p99, lượng byte ghi xuống đĩa tăng thêm, dung lượng bảng và index cuối cùng;
    - dùng `trap` để khi kết thúc khôi phục `SET CONFIG pd \`replication.max-replicas\` = 3` và chờ đến khi `SHOW CONFIG` xác nhận.

- [ ] **Bước 1: Viết các test (sẽ fail):**
  - `test_parse_docker_stats`: với dòng `"tidb-tikv0\t35.20%\t1.8GiB / 2.5GiB\t1.2GB / 3.4GB"`, kết quả có cpu 35,2, mem xấp xỉ 1,8 GiB tính bằng byte, write 3,4e9.
  - `test_parse_handles_kB_MB`: xử lý đúng các đơn vị kB, MB.
- [ ] **Bước 2: Chạy** → FAIL.
- [ ] **Bước 3: Cài đặt.**
- [ ] **Bước 4: Chạy** → PASS. Chạy thử trên máy với `RUN_SECONDS=10` ở quy mô 1 triệu dòng:
  - CSV có dữ liệu;
  - cột `max_replicas` chỉ bằng 1 ở các dòng replicas=1;
  - sau khi script kết thúc, giá trị trở về 3 (kiểm tra bằng `SHOW CONFIG`).
- [ ] **Bước 5: Commit** `feat: RQ4 write-cost experiment`.

---

### Task 11: Demo chịu lỗi cho A.3

**Files:**
- Tạo: `scripts/chaos_demo.sh`

**Interfaces:**
- Cung cấp: script chạy tải đọc nhẹ kiểu `sysbench oltp_read_only` (8 luồng, `--report-interval=1`, 180 giây) vào TiDB.
  - Tại giây thứ 60, chạy `docker kill tidb-tikv0`.
  - Tại giây thứ 150, chạy `docker start tidb-tikv0`.
  - Ghi log ra `results/chaos_qps.log`, kèm checksum `SELECT COUNT(*), SUM(cod_amount)` trước và sau.

- [ ] **Bước 1: Cài đặt.**
- [ ] **Bước 2: Kiểm tra:**
  - log cho thấy QPS tụt sau giây thứ 60 và hồi phục trong khoảng 20 giây;
  - checksum trước và sau bằng nhau;
  - chụp màn hình TiDB Dashboard trong lúc chạy để đưa vào báo cáo.
- [ ] **Bước 3: Commit** `feat: fault-tolerance demo for A.3`.

---

### Task 12: Biểu đồ

**Files:**
- Tạo: `experiments/plots.py`

**Interfaces:**
- Sử dụng: `results/{b1_storage,rq1,rq2,rq3,rq4}.csv`.
- Cung cấp các file trong `results/fig/`:
  - `b1_model_vs_measured.png`: cột nhóm theo hệ × bộ index.
  - `rq1_covering.png`: p50 kèm thanh IQR cho từng case, hai hệ đặt cạnh nhau.
  - `rq2_crossover_<engine>.png`: độ trễ theo độ chọn lọc, trục x thang log, 3 chế độ, có đường dọc tại điểm giao nhau và điểm optimizer đổi phương án.
  - `rq3_pk.png`.
  - `rq4_tps_vs_indexes.png`: mỗi đường ứng với một tổ hợp hệ/số bản sao, mỗi panel ứng với một tổ hợp chế độ × số luồng.

- [ ] **Bước 1: Cài đặt** bằng matplotlib:
  - dùng bảng màu thân thiện với người mù màu;
  - mỗi hệ luôn giữ một màu cố định (TiDB và MySQL);
  - nhãn trục có ghi đơn vị.
- [ ] **Bước 2: Kiểm tra:** `python experiments/plots.py` chạy trên kết quả 1 triệu dòng tạo đủ ít nhất 5 file mà không lỗi. Mở từng file để kiểm tra trục và chú thích đọc rõ.
- [ ] **Bước 3: Commit** `feat: result charts`.

---

### Task 13: Chạy toàn bộ ở quy mô 10 triệu dòng

**Files:** không tạo file mới.

- [ ] **Bước 1:** chạy `scripts/load.sh` cho cả hai hệ với 10.000.000 dòng. Checksum phải khớp.
- [ ] **Bước 2:** chạy các script của Task 5, 7, 8, 9, 10 ở quy mô 10 triệu dòng cho từng hệ (chuyển hệ bằng `use_engine.sh --switch`).
- [ ] **Bước 3:** chạy `python experiments/plots.py`, commit các CSV tổng hợp và biểu đồ: `git commit -m "data: 10M results"`.

---

## Đối chiếu với tài liệu thiết kế và phân công

| Mục trong tài liệu thiết kế | Task | Phụ trách (mục 9) |
|---|---|---|
| Mục 7: môi trường, cấu hình tương đương | 4 | TV2 |
| Mục 6: dữ liệu, quy mô | 2, 4, 13 | TV2 |
| B.1: mô hình, số đo thực tế, tài nguyên | 5 | TV1 (mô hình), TV2 (đo đạc) |
| RQ1 / RQ2 / RQ3 (phần đọc) | 6, 7, 8, 9 | TV3 |
| RQ3 (phần ghi) / RQ4 | 9, 10 | TV2 |
| Demo A.3 | 11 | TV2 |
| Biểu đồ | 12 | TV3 |

**Lộ trình:**
- Tuần 1: task 1–4
- Tuần 2: task 5–8, nạp dữ liệu 10 triệu dòng (task 13)
- Tuần 3: task 9–11
- Tuần 4: task 12, 13, viết báo cáo
