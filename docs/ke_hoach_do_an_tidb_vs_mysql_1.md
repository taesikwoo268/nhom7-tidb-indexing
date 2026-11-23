# Kế Hoạch & Đề Cương Báo Cáo Bài Tập Lớn — Nhóm 7 (bản hoàn thiện, phạm vi 1,5 tuần, 3 máy)

* **Tên đề tài (Tiếng Việt):** Chi phí của chỉ mục phụ trên hệ lưu trữ Key-Value phân tán: Nghiên cứu thực nghiệm TiDB so với MySQL InnoDB trên bài toán tra cứu vận đơn
* **Tên đề tài (Tiếng Anh):** The Cost of Secondary Indexes on a Distributed Key-Value Store: An Experimental Study of TiDB vs MySQL InnoDB on a Parcel-Tracking Workload
* **Hệ quản trị chính:** [TiDB](https://docs.pingcap.com/tidb/stable/overview/) **v8.5.5**
* **Hệ quản trị đối chứng:** [MySQL InnoDB](https://dev.mysql.com/doc/refman/8.4/en/using-innodb-tables.html) **8.4.11**

  Đây là hai phiên bản nhóm đã cài và chạy được ở giai đoạn 1.
* **Miền nghiệp vụ:** Hệ thống quản lý vận đơn của một đơn vị giao hàng thương mại điện tử (bảng `shipments`, 1 triệu và 10 triệu dòng).
* **Tài liệu kỹ thuật đi kèm:** `docs/2026-11-16-tidb-indexing-van-don.vi.md`. Các điều chỉnh để vừa 1,5 tuần nằm ở Phụ lục B.
* **Cấu trúc báo cáo theo định hướng của giảng viên:**
  * **PHẦN A (~50%): Tìm hiểu hệ quản trị.** Xuất phát từ đặc trưng dữ liệu, đi đến kiến trúc cốt lõi, rồi cài đặt và demo.
  * **PHẦN B (~50%): Nghiên cứu chi phí chỉ mục phụ.** Gồm mô hình dung lượng lý thuyết đối chiếu với số đo thực tế, chi phí đọc và chi phí ghi khi có index, và so sánh với MySQL. Mọi kết luận đều rút ra từ số đo; mỗi câu hỏi nghiên cứu được trình bày theo dạng **giả thuyết → lý do giả thuyết có thể sai → cách kiểm chứng**.

> **Nguyên tắc viết:** không viết sẵn kết luận "TiDB vượt trội". Ở giai đoạn 1, nhóm đã dự đoán TiDB ổn định hơn ở tải cao, nhưng số đo cho thấy MySQL cao hơn 8–32 lần trên một máy. Kết quả "TiDB thua" vẫn là một kết quả có giá trị nếu giải thích được bằng cơ chế ở Phần A.

---

## Phạm vi trong 1,5 tuần

| Hạng mục | Quyết định | Lý do |
|---|---|---|
| **RQ1** – covering index và lượt quay về bảng | **Làm**, ở 1 triệu và 10 triệu dòng | Câu hỏi cốt lõi; chi phí máy thấp |
| **RQ2** – ngưỡng độ chọn lọc | **Làm**, ở 10 triệu dòng | Trả lời trực tiếp câu hỏi "có index và không có index" của cô |
| **RQ4** – chi phí ghi theo số index | **Làm**, chỉ ở 1 triệu dòng, lặp 3 lần, mỗi lần 60 giây | Ở 10 triệu dòng cần 15–20 giờ máy, vượt khả năng trong 1,5 tuần |
| **B.1** – mô hình dung lượng | **Làm**, đo ở 1 triệu và 10 triệu dòng | Yêu cầu trực tiếp của cô |
| RQ3 – biến thể khóa chính | **Giảm** còn một phép đo dung lượng index phụ khi PK là `tracking_code`, chỉ ở 1 triệu dòng, làm nếu ngày 8 còn trống | Ít ảnh hưởng tới kết luận chính |
| RQ5 – hotspot ghi | **Bỏ**. Chỉ dùng ảnh Key Visualizer giai đoạn 1 làm minh họa | Không đủ thời gian |
| Demo chịu lỗi, scale-out | **Không chạy lại**. Dùng kết quả giai đoạn 1 (bảng `sbtest1`) cho A.3 | Đã có số liệu tốt |
| Tải đồng thời 16→512 luồng | **Không chạy lại**. Dùng làm "Thực nghiệm sơ bộ" B.0 | Là động lực dẫn tới đề tài |
| Quy mô 30 triệu / 100 triệu dòng | **Chỉ tính bằng mô hình** | Không đủ đĩa và thời gian |

---

## PHẦN A: TÌM HIỂU TiDB — TỪ ĐẶC TRƯNG DỮ LIỆU ĐẾN KIẾN TRÚC VÀ CÀI ĐẶT (~50%)

Phần A trả lời yêu cầu thứ nhất của cô: *"Xuất phát từ dữ liệu, tìm ra một hệ quản trị để mô phỏng hóa phần đấy, giới thiệu những đặc trưng lớn nhất của hệ quản trị đấy phù hợp với dạng dữ liệu nào, và cài đặt được nó."*

### Mục A.1. Xuất phát từ dữ liệu: bài toán vận đơn và lý do chọn TiDB

1. **Đặc trưng dữ liệu vận đơn:**
   * Hệ thống phát sinh hàng triệu vận đơn mỗi ngày, mỗi vận đơn có trạng thái được cập nhật nhiều lần.
   * Có ba yêu cầu cùng lúc:
     * **giao dịch ACID** khi cập nhật trạng thái và tiền thu hộ COD;
     * **tra cứu liên tục qua nhiều chỉ mục phụ**: theo mã vận đơn, theo shop, theo kho, theo khoảng tiền COD;
     * **thống kê** theo kho và trạng thái.
   * Vì cần nhiều chỉ mục phụ trên một bảng rất lớn, **chi phí của chỉ mục phụ** trở thành câu hỏi trung tâm. Đây là lý do của Phần B.

2. **Đối chiếu các nhóm hệ quản trị:**

| Nhóm hệ quản trị | Tiêu biểu | Điểm mạnh / hạn chế với bài toán vận đơn |
| :--- | :--- | :--- |
| **RDBMS một máy** | MySQL, PostgreSQL | Có ACID, SQL đầy đủ và nhiều loại index. Toàn bộ dữ liệu và index nằm trên một máy, nên dung lượng, bộ nhớ đệm và khả năng chịu lỗi bị giới hạn bởi máy đó. Muốn chia dữ liệu phải sharding thủ công. |
| **Wide-column NoSQL** | Cassandra, HBase | Ghi rất nhanh, mở rộng ngang tốt. Không có giao dịch ACID đa dòng theo kiểu quan hệ, index phụ hạn chế, không có JOIN, nên khó đáp ứng các truy vấn lọc theo nhiều thuộc tính. |
| **NewSQL phân tán** | **TiDB** | Giữ mô hình quan hệ, giao thức MySQL và giao dịch ACID. Bên dưới, dữ liệu được ánh xạ thành cặp Key-Value và tự chia thành các Region trên nhiều node TiKV. **Câu hỏi đặt ra:** khi bảng và mỗi index đều thành các cặp KV phân tán, thì chi phí đọc và ghi qua index phụ thay đổi thế nào so với B+Tree của MySQL? |

### Mục A.2. Bốn trụ cột kiến trúc của TiDB

Mục này là **nền lý thuyết để giải thích các kết quả ở Phần B**. Mỗi trụ cột cần nói rõ nó ảnh hưởng đến index như thế nào.

#### 1. Tách tầng tính toán và tầng lưu trữ
* **TiDB Server** không lưu trạng thái. Server này phân tích câu lệnh, lập kế hoạch thực thi bằng optimizer dựa trên chi phí (CBO), và đẩy phép lọc, tổng hợp xuống **TiKV Coprocessor**.
* **TiKV** lưu dữ liệu và bảo đảm ACID.
* **Hệ quả cho index:** ba toán tử truy cập cần giải thích kỹ vì Phần B đo chúng trực tiếp:
  * `TableReader`: quét bảng;
  * `IndexReader`: chỉ đọc index, tức covering;
  * `IndexLookUp`: đọc index trước rồi lấy dòng sau.

  `IndexLookUp` gửi cop task tới các Region chứa index, rồi gom các handle thành lô và gửi tiếp cop task tới các Region chứa dòng. Hai phía chạy song song theo kiểu pipeline.

#### 2. Ánh xạ quan hệ sang Key-Value trên RocksDB (LSM-tree)
* **Dòng dữ liệu (clustered PK):** `Key = t{table_id}_r{id}` → `Value = [các cột còn lại]`
* **Index unique** (`idx_code`): `Key = t{table_id}_i{index_id}_{tracking_code}` → `Value = id`
* **Index non-unique** (`idx_sender_created`): `Key = t{table_id}_i{index_id}_{sender_id}_{created_at}_{id}` → `Value` gần như rỗng
* **So sánh với InnoDB:**
  * Trong InnoDB, index phụ là một B+Tree riêng, ở lá chứa giá trị khóa và PK, nên quay về bảng là thêm một lần tra B+Tree trên cùng máy.
  * Trong TiDB, mỗi mục index là một cặp KV, có thể nằm ở Region và TiKV khác với dòng dữ liệu.
* **LSM-tree:** lệnh ghi đi vào WAL và MemTable, sau đó flush thành file SST và được compaction gộp qua các tầng L0→L6.
  * Ưu điểm: **không phải đọc rồi sửa trang và không bị tách trang** như B+Tree.
  * Cái giá: **khuếch đại ghi do compaction** (dữ liệu bị ghi lại nhiều lần khi gộp tầng) và đọc có thể phải tra nhiều tầng.

  Hai điểm này là hai phía của giả thuyết RQ4, nên A.2 **không kết luận** bên nào rẻ hơn.

#### 3. Region và Multi-Raft
* **Region:** dải key được chia thành các Region `[StartKey, EndKey)` và tự tách khi vượt ngưỡng. *Cần ghi kích thước mặc định đúng với v8.5.5, kiểm tra bằng `SHOW CONFIG WHERE name LIKE '%region-split-size%'`, và đối chiếu với số đo giai đoạn 1: bảng `sbtest1` 10 triệu dòng được chia thành 50 Region.*
* **Multi-Raft:**
  * Mỗi Region có 3 bản sao: 1 Leader và 2 Follower.
  * Một lệnh ghi chỉ được commit khi đa số (2/3) bản sao đã ghi Raft log.
  * Khi node chứa Leader chết, Region phải chờ hết thời gian bầu cử `raft-base-tick-interval × raft-election-timeout-ticks = 1 s × 10 = 10 giây` rồi mới bầu Leader mới. Con số này khớp với số đo ở A.3.
* **Hệ quả cho index:**
  * Mỗi mục index được ghi là thêm một lần ghi qua Raft trên 3 bản sao.
  * Index của bảng thường nằm ở Region khác với dữ liệu của bảng.

#### 4. Placement Driver (PD), TSO và giao dịch Percolator
* PD giữ bản đồ Region, cân bằng Leader và Region giữa các node, và cấp **TSO**, tức timestamp tăng đơn điệu toàn cục.
* Giao dịch dùng mô hình **Percolator 2PC** (prewrite rồi commit) cùng MVCC.
  * Mức cô lập mặc định là **Snapshot Isolation**, được TiDB gọi là REPEATABLE READ. TiDB cũng hỗ trợ READ COMMITTED.
  * TiDB **không hỗ trợ SERIALIZABLE**.
* **Hệ quả cho index:** trong cùng một giao dịch, các cặp KV của dòng và của mọi index đều phải đi qua prewrite và commit. Index càng nhiều thì số key mỗi giao dịch phải ghi càng nhiều.

### Mục A.3. Cài đặt, triển khai và demo vận hành

1. **Môi trường thực nghiệm:**
   * **Ba máy, ba phần.** Mỗi thành viên chạy phần của mình trên máy riêng:
     * B.1 trên máy TV1;
     * B.3 trên máy TV2;
     * B.2 trên máy TV3.

     Kết quả giai đoạn 1 (B.0 và A.3) được đo trên laptop 12 luồng CPU, 15,7 GB RAM, Windows với Docker Desktop (WSL2 được cấp 10 CPU, 12 GB).
   * **Mọi máy dùng cùng một cấu hình container** (bên dưới, gọi là hồ sơ **M**), cùng một repo code và cùng seed sinh dữ liệu. Thông số phần cứng của từng máy được ghi trong Bảng A.3.1 và trong mọi dòng kết quả.
   * **Cụm TiDB v8.5.5:**
     * 1 PD (0,5 CPU, 1 GiB);
     * 3 TiKV (mỗi node 1,25 CPU, 2,25 GiB, block cache 800 MiB);
     * 1 TiDB Server (1,75 CPU, 1,5 GiB);
     * mỗi Region có 3 bản sao.

     Tổng cộng 6 CPU và khoảng 9,25 GiB.
   * **MySQL 8.4.11:** 1 node, 6 CPU, giới hạn 4 GiB, `innodb_buffer_pool_size = 2400M`, `innodb_flush_log_at_trx_commit = 1`. **Tắt binlog**, vì TiDB cũng không bật binlog; cả hai vẫn bảo đảm độ bền khi commit.
   * **Tương đương bộ nhớ đệm:** 3 × 800 MiB block cache = 2.400 MiB buffer pool. Ở giai đoạn 1, TiDB chỉ có 1,9 GiB cache so với 4 GiB của MySQL, và nhóm đã ghi nhận điều này là thiên vị MySQL; cấu hình mới sửa chỗ này.
   * **sysbench và script đo** chạy trong container riêng với 3 CPU, nhiều hơn mức 2 CPU từng bị nghẽn ở giai đoạn 1.
   * **Chỉ chạy một hệ tại một thời điểm** trên mỗi máy, được bảo đảm bằng `scripts/use_engine.sh`.
   * **Bảng A.3.1. Ba máy thực nghiệm** (mỗi thành viên điền vào ngày 1):

     | Máy | Người dùng / phần | CPU (model, số luồng) | RAM | Ổ dữ liệu Docker (SSD/HDD) | Hệ điều hành / Docker / bộ nhớ WSL2 | Hồ sơ |
     |---|---|---|---|---|---|---|
     | M1 | TV1 / B.1 | | | | | |
     | M2 | TV2 / B.3 | Intel Core Ultra 5 125H (18 luồng) | 16 GB | NVMe SSD 512 GB | Windows 11 / Docker 29.8.0 / WSL2 7,56 GiB | Hồ sơ S |
     | M3 | TV3 / B.2 | | | | | |
2. **Minh chứng cài đặt:** chạy `SELECT tidb_version();` và `SELECT * FROM information_schema.TIKV_STORE_STATUS;` (3 store `Up`); chụp TiDB Dashboard (Topology, Key Visualizer); chạy `SHOW CREATE TABLE shipments` trên cả hai hệ.
3. **Demo chịu lỗi** (dùng lại kết quả giai đoạn 1, bảng `sbtest1`, tải `oltp_read_write` 64 luồng). Giết `tikv0` bằng `docker kill` ở giây thứ 60:

   | Chỉ số | TiDB (3 bản sao) | MySQL (1 node, không có bản sao) |
   |---|---|---|
   | Số giây QPS bằng 0 | 10 | 46 |
   | Thời gian về lại 90% QPS | 18,4 s, tự phục hồi | 48,3 s, cần khởi động lại |
   | Số lệnh ghi probe bị lỗi | 0 / 2.035 | 140 / 2.050 |
   | Số giao dịch đã commit bị mất (RPO) | 0 | 0 |

   * **Cách diễn giải:** hai hệ khác nhau ở **tính sẵn sàng (RTO)**, không khác nhau ở độ bền. Phép so sánh này **không ngang hàng**, vì MySQL chạy một node, không có replica (MySQL có InnoDB Cluster nhưng nhóm không triển khai). Mục đích của demo là chứng minh cơ chế Raft ở A.2.3 hoạt động đúng trên cụm đã cài.
4. **Demo scale-out** (kết quả giai đoạn 1, khoảng một đoạn):
   * thêm `tikv3` khi đang có tải; Region đầu tiên chuyển sang node mới sau 16 giây;
   * không có lỗi nào phía ứng dụng;
   * TPS giảm 25% vì node mới không mang thêm phần cứng thật.

   Demo này chứng minh khả năng **mở rộng trực tuyến**, không chứng minh việc thêm node làm tăng hiệu năng.

---

## PHẦN B: CHI PHÍ CHỈ MỤC PHỤ TRÊN TiDB SO VỚI MySQL (~50%)

Phần B trả lời câu hỏi của cô: *"Trên máy 16GB RAM, từng đấy CPU, trước khi index available từng này, khi load 1 triệu hay 10 triệu bản ghi nó chiếm bao nhiêu MB? Tính trên lý thuyết nó đi vào tính kiểu gì? Có đối chiếu có index không, chi phí tính toán như thế nào không chỉ về thời gian chạy, và so sánh với database truyền thống (MySQL)."*

### Mục B.0. Thực nghiệm sơ bộ: từ khoảng cách hiệu năng đến câu hỏi nghiên cứu

Ở giai đoạn 1, nhóm chạy sysbench trên bảng `sbtest1` 10 triệu dòng (có một index phụ `k_1`), với số luồng tăng từ 16 đến 512 (khoảng 1 trang, gồm Bảng B.3.1 và Hình B.3.1 cũ). Kết quả:

* MySQL đạt thông lượng cao hơn TiDB **13–32 lần** ở tải `oltp_read_write` và **8–13 lần** ở tải `oltp_update_index`.
* Giả thuyết ban đầu "TiDB ổn định vượt trội ở 256–512 luồng" **không được số liệu xác nhận**.
* Nguyên nhân quan sát được:
  * mỗi giao dịch của TiDB phải lấy TSO, chạy 2PC và chờ fsync Raft;
  * TiKV chạm giới hạn CPU riêng của từng node;
  * dữ liệu vượt bộ nhớ đệm của TiKV.

**Câu hỏi dẫn tới Phần B:** trong khoảng chênh đó, bao nhiêu là do **duy trì và truy cập qua index phụ** trên KV phân tán? Và những quy tắc thiết kế index quen thuộc trên MySQL có còn đúng trên TiDB không?

### Mục B.1. Dữ liệu và mô hình dung lượng lý thuyết

#### 1. Schema chung (hai phiên bản DDL)

```sql
CREATE TABLE shipments (
    id                BIGINT       NOT NULL AUTO_INCREMENT,
    tracking_code     VARCHAR(20)  NOT NULL,   -- 'VN' + 12 chữ số, duy nhất, sinh ngẫu nhiên
    sender_id         INT          NOT NULL,   -- ~100.000 shop, phân phối Zipf
    origin_hub_id     SMALLINT     NOT NULL,   -- ~200 kho
    dest_hub_id       SMALLINT     NOT NULL,
    status            TINYINT      NOT NULL,   -- 6 trạng thái, ~80% là "đã giao"
    cod_amount        INT          NOT NULL DEFAULT 0,  -- phân phối đều 0..10.000.000, không tương quan với id
    weight_grams      INT          NOT NULL,
    shipping_fee      INT          NOT NULL,
    recipient_phone   VARCHAR(15)  NOT NULL,
    recipient_address VARCHAR(150) NOT NULL,
    note              VARCHAR(100) DEFAULT NULL,
    created_at        DATETIME     NOT NULL,   -- 180 ngày, tăng theo id
    updated_at        DATETIME     NOT NULL,
    PRIMARY KEY (id)              -- TiDB: thêm từ khóa CLUSTERED; MySQL: không có từ khóa này (luôn clustered)
);
```

Năm index phụ (dùng ở B.1 và RQ4): `idx_code (tracking_code)` loại UNIQUE, `idx_sender_created (sender_id, created_at)`, `idx_hub_status (dest_hub_id, status)`, `idx_cod (cod_amount)`, `idx_status (status)`.

#### 2. Dữ liệu thô
* **Phần cố định (theo kích thước lưu trữ của InnoDB):** `id` 8 + `sender_id` 4 + hai cột hub 2 + 2 + `status` 1 + `cod_amount` 4 + `weight_grams` 4 + `shipping_fee` 4 + hai cột `DATETIME` **5 + 5** = **39 B**.
  * Lưu ý: từ MySQL 5.6.4, `DATETIME` chỉ chiếm 5 byte. Bản trước tính 8 byte là sai.
* **Phần biến đổi (độ dài trung bình):** `tracking_code` 14 + `recipient_phone` 10 + `recipient_address` 60 + `note` 15 = **99 B**.
* **Một dòng thô:** **138 B**. Với 10⁷ dòng, dữ liệu thô là **1,29 GiB**.
* **Năm mục index thô** (giá trị khóa + `id` 8 B): 22 + 17 + 11 + 12 + 9 = **71 B/dòng**. Bảng cùng 5 index thô là **1,95 GiB**.

#### 3. Trong MySQL InnoDB
* **Một dòng trong clustered B+Tree:** 138 B dữ liệu + 13 B MVCC (`DB_TRX_ID` 6 + `DB_ROLL_PTR` 7) + 5 B header + 4 B độ dài cột biến đổi + 1 B bitmap NULL = **161 B**.
* **Bảng:** khi chèn tuần tự theo `AUTO_INCREMENT`, mỗi trang để trống 1/16, nên một trang chứa `⌊(16.384 × 15/16 − 120) / 161⌋ = 94` dòng.

  `S_bảng = ⌈10⁷ / 94⌉ × 16 KiB × 1,01 ≈ 1.679 MiB ≈ 1,64 GiB`
* **Index phụ:** mỗi mục cộng thêm khoảng 8 B (header và slot thư mục trang). Các mục lần lượt là 31, 25, 19, 20 và 17 B, **tổng 112 B/dòng**.

  Hệ số lấp đầy **phụ thuộc vào cách tạo index**:
  * **Tạo index sau khi nạp** (sắp xếp rồi dựng, cách dùng ở B.1): mọi index có hệ số lấp đầy khoảng 15/16, nên `S_index ≈ 10⁷ × 112 / 0,9375 ≈ 1.139 MiB`.
  * **Index có sẵn rồi chèn dần** (cách dùng ở RQ4):
    * `idx_code`, `idx_sender_created`, `idx_cod` nhận khóa ngẫu nhiên, nên bị tách trang, hệ số lấp đầy khoảng 0,72;
    * `idx_hub_status`, `idx_status` có ít giá trị và id tăng dần, nên chèn gần như tuần tự, hệ số khoảng 15/16.

    Kết quả `S_index ≈ 1.373 MiB`.
* **Tổng cho 10 triệu dòng có 5 index:** **≈ 2,75 GiB** nếu tạo index sau khi nạp, **≈ 2,98 GiB** nếu chèn dần.
* **Kiểm chứng phương pháp:** ở giai đoạn 1, mô hình này dự đoán 2,35 GiB cho `sbtest1` và số đo thực tế là 2,3 GiB.

#### 4. Trong TiDB / TiKV
* **Dòng KV:** key `t{table_id}_r{id}` 19 B + timestamp MVCC 9 B = 28 B; value gồm các cột còn lại (136 B, vì row format của TiDB lưu `DATETIME` 8 B) + 36 B header và metadata MVCC = 172 B. **Tổng 200 B/dòng chưa nén.**
* **Mục index KV:** trung bình khoảng 56 B/mục chưa nén, nên 5 index là khoảng 280 B/dòng.
* **Trên một bản sao:** `S = (dòng + index) × C_nén × α_LSM`. Tổng cụm = `S × 3` + Raft log.
* **Hiệu chỉnh trước khi dùng (ngày 2):** ở giai đoạn 1, mô hình cũ dự đoán 1,88 GiB cho mỗi bản sao của `sbtest1`, nhưng số đo cho thấy khoảng 3,2 GiB dữ liệu logic. Cần tìm nguyên nhân của khoảng chênh này: số đo là kích thước trước hay sau khi nén, có tính các phiên bản MVCC chưa dọn hay không. Sau đó hiệu chỉnh `C_nén` và `α_LSM` (giá trị ban đầu là 0,60 và 1,11) bằng số đo thật, **rồi mới** áp dụng cho `shipments`. Các con số dự đoán cũ (1,24 GiB/node khi không có index, 2,98 GiB/node khi có 5 index) chỉ là ước lượng sơ bộ.

#### 5. Bảng đối chiếu (điền số đo ở ngày 3)

| Quy mô / cấu hình | Thô | MySQL – mô hình | MySQL – đo | TiDB 1 bản sao – mô hình | TiDB toàn cụm – đo |
|---|---|---|---|---|---|
| 1 triệu dòng, 0 index | 0,13 GiB | 0,16 GiB | | | |
| 1 triệu dòng, 5 index | 0,19 GiB | 0,28 GiB | | | |
| 10 triệu dòng, 0 index | 1,29 GiB | 1,64 GiB | | | |
| 10 triệu dòng, 5 index | 1,95 GiB | 2,75 GiB | | | |
| 100 triệu dòng, 5 index (chỉ mô hình) | 19,5 GiB | ~27,5 GiB | — | | — |

Kèm theo là RAM, CPU và lượng ghi đĩa (`docker stats`) **trước, trong và sau** khi chạy `CREATE INDEX` trên 10 triệu dòng, cùng thời gian tạo từng index.

### Mục B.2. Chi phí đọc qua index phụ (RQ1, RQ2)

Quy trình chung cho mọi phép đo đọc:
1. chạy `ANALYZE TABLE` trước;
2. warm-up 50 truy vấn;
3. dùng 200 bộ tham số lấy mẫu với seed cố định;
4. lặp 5 lần, báo cáo trung vị, p95 và IQR;
5. chạy một lần `EXPLAIN ANALYZE` để lấy toán tử truy cập, số key xử lý (`total_process_keys`), số cop task và số RPC (TiDB), hoặc `Handler_read_*` (MySQL).

#### RQ1 — Covering index và lượt quay về bảng (1 triệu và 10 triệu dòng)
* **Truy vấn:**
  * Q1: tra một mã vận đơn, so `SELECT *` với `SELECT status, updated_at`;
  * Q2: lấy 20 đơn mới nhất của một shop trong 7 ngày;
  * Q3: đếm đơn theo trạng thái tại một kho.
* **Các cấu hình index:**
  * Q1: `(tracking_code)` UNIQUE, `(tracking_code)` không UNIQUE (đối chứng) và `(tracking_code, status, updated_at)`. Cặp không UNIQUE tách hiệu ứng covering khỏi hiệu ứng `Point_Get`;
  * Q2: `(sender_id)`, `(sender_id, created_at)` và covering `(sender_id, created_at, status, cod_amount)`;
  * Q3: `(dest_hub_id)` và `(dest_hub_id, status)`.
* **Giả thuyết:** chênh lệch giữa covering và non-covering ở TiDB lớn hơn ở MySQL. Lý do: ở TiDB, `IndexLookUp` cần thêm một đợt cop task tới các Region chứa dòng, còn ở MySQL đó chỉ là các lần tra trang trong buffer pool.
* **Lý do giả thuyết có thể sai:**
  * TiDB gom handle theo lô và chạy hai phía song song, nên chi phí thêm có thể nhỏ khi mỗi truy vấn trả về nhiều dòng;
  * với tra cứu một dòng qua index unique, TiDB dùng `Point_Get` nên có thể không có khác biệt.
* **Kiểm chứng bằng:** tỉ lệ `p50(non-covering) / p50(covering)` trên từng hệ, cùng số cop task, số RPC, `rpc_time`, thời gian xử lý và chờ của cop task. `rpc_time` trên một máy gồm cả xử lý, xếp hàng và gRPC nên không được gọi là độ trễ mạng. Bằng chứng chính cho covering là Q2. Ghi thêm dung lượng của từng index.

#### RQ2 — Ngưỡng độ chọn lọc (10 triệu dòng)
* **Truy vấn:** `SELECT * FROM shipments WHERE cod_amount BETWEEN ? AND ?`. Độ chọn lọc thay đổi từ 0,001% đến 50% qua 10 mức.
* **Mỗi mức chạy 3 chế độ:**
  * ép dùng index (`FORCE INDEX (idx_cod)`);
  * ép quét toàn bảng (`IGNORE INDEX (idx_cod)`);
  * để optimizer tự chọn.

  Script tự dừng nếu hint không được tuân theo, kiểm tra qua toán tử trong kế hoạch thực thi.
* **Kết quả cần ghi:**
  1. **điểm giao nhau**, nơi quét toàn bảng bắt đầu nhanh hơn dùng index;
  2. **điểm optimizer đổi phương án**;
  3. khoảng cách giữa hai điểm này trên mỗi hệ, cho biết optimizer chọn sớm hay muộn so với thực tế.
* **Giả thuyết:** điểm giao nhau của TiDB thấp hơn MySQL, vì mỗi dòng lấy qua index tốn thêm chi phí truy cập KV phân tán, trong khi quét bảng được chia song song cho 3 TiKV.
* **Lý do giả thuyết có thể sai:** TiDB lấy dòng theo lô, nên chi phí tính theo lô chứ không theo dòng; ngoài ra mỗi TiKV chỉ có 1,25 CPU, nên quét toàn bảng cũng không rẻ.
* **Không đặt trước con số** cho hệ nào.

#### (Làm nếu còn thời gian) RQ3 rút gọn — khóa chính là `tracking_code`
Ở quy mô 1 triệu dòng, so sánh dung lượng của `idx_sender_created` khi PK là `id` (BIGINT) và khi PK là `tracking_code` (chuỗi), trên cả hai hệ. Giả thuyết: index phụ phình to trên cả hai hệ, vì mỗi mục phải mang theo PK.

### Mục B.3. Chi phí ghi khi tăng số index phụ (RQ4, 1 triệu dòng)

* **Thiết lập:**
  * tải ghi gồm W1 (insert đơn mới) và W2 (`UPDATE status, updated_at` theo id);
  * số luồng: 16 và 64;
  * bộ index: 0, 1, 3 và 5;
  * mỗi lần chạy 60 giây, lặp 3 lần (5 lần nếu còn thời gian);
  * các cấu hình: **MySQL**, **TiDB 3 bản sao**, **TiDB 1 bản sao** (`SET CONFIG pd \`replication.max-replicas\` = 1`; script tự khôi phục về 3 khi chạy xong).

  Tổng thời gian máy khoảng 4 giờ với 3 lần lặp, chạy trên máy M2.
* **Chỉ số:**
  * TPS, p95, p99;
  * mức TPS giảm theo mỗi index thêm vào, tính theo % so với cấu hình 0 index của chính hệ đó;
  * lượng byte ghi xuống đĩa trên mỗi giao dịch, để tính khuếch đại ghi;
  * dung lượng sau khi chạy;
  * CPU của container sysbench, để loại trừ khả năng bộ sinh tải là nút thắt.
* **Hai giả thuyết đối lập** (thực nghiệm sẽ phân xử):
  * **(a)** LSM-tree ghi tuần tự, không đọc rồi sửa trang, nên mức giảm TPS theo số index trên TiDB **thấp hơn** MySQL.
  * **(b)** Mỗi index là thêm các cặp KV phải prewrite và commit qua Raft trên 3 bản sao, nên mức giảm trên TiDB **cao hơn**.
* **Tách nguyên nhân:** so TiDB 3 bản sao với TiDB 1 bản sao để định lượng tổng chi phí nhân bản (Raft log, fsync, CPU của Follower, tranh chấp đĩa chung), không phải riêng phần mạng. Cả hai cấu hình đều có 3 TiKV; RF=3 có quorum 2/3, RF=1 có quorum 1/1 và không chịu lỗi. Một TiKV không tạo được thiết lập 3 bản sao hợp lệ. So W1 với W2 để thấy chi phí khi cập nhật cột có nằm trong index (`status`). Diễn giải W2 theo số index bị ảnh hưởng, vì `idx_code`, `idx_sender_created` và `idx_cod` không chứa cột được cập nhật.
* **Chi phí ghi của covering (24 lượt, chạy sau 144 lượt chính):** so `idx_sender_created` với `idx_sender_cov`, 16 luồng, W1 và W2, 3 lần, trên MySQL và TiDB RF=3.

### Mục B.4. Tổng hợp, khuyến nghị và hạn chế

1. **Bảng giả thuyết và kết quả:** cho RQ1, RQ2 và RQ4, ghi rõ được xác nhận, bị bác bỏ hay xác nhận một phần, kèm con số chính.
2. **Khuyến nghị thiết kế index cho bài toán vận đơn trên từng hệ:** quy tắc nào giữ nguyên khi chuyển từ MySQL sang TiDB (ví dụ index ghép theo thứ tự lọc rồi sắp xếp), quy tắc nào thay đổi (ví dụ covering index, số index tối đa nên có).
3. **Hạn chế** (theo mẫu B.3.5 của giai đoạn 1):
   * mọi node chạy trên cùng một máy và một ổ đĩa, mạng giữa các node gần như không có độ trễ;
   * CPU được chia cố định cho các container;
   * RQ4 chỉ chạy ở 1 triệu dòng, lặp 3 lần;
   * B.1, B.2 và B.3 được đo trên ba máy khác nhau. So sánh TiDB với MySQL trong cùng một mục là hợp lệ, nhưng không được so độ trễ hay TPS tuyệt đối giữa các mục. Riêng dung lượng ở B.1 gần như không phụ thuộc vào máy;
   * mô hình TiKV phụ thuộc vào các hệ số đã hiệu chỉnh;
   * các kết luận cho biết xu hướng và độ lớn, không phải con số áp dụng được cho hệ thống thật.

---

## PHÂN CÔNG VÀ LỘ TRÌNH 10 NGÀY (3 THÀNH VIÊN, 3 MÁY)

Ngày 1 tính từ **thứ Tư 18/11**, ngày 10 là **thứ Sáu 27/11**. Nếu hạn nộp khác thì dời theo.

Mỗi thành viên **sở hữu trọn một phần trên máy của mình**: viết code, chạy cả TiDB lẫn MySQL, vẽ biểu đồ và viết báo cáo cho phần đó. Ba máy chạy song song, không phải chờ nhau. Điều kiện là code chung phải ổn định sớm, nên xem mục "Quy tắc làm việc trên 3 máy" bên dưới.

### Phân công

| Thành viên | Máy | Phần thực nghiệm | Viết báo cáo | Code (Task trong tài liệu kỹ thuật) |
|---|---|---|---|---|
| **TV1 (trưởng nhóm)** | M1 | **B.1**: dung lượng, tài nguyên khi tạo index (1 triệu và 10 triệu dòng); RQ3 rút gọn nếu còn thời gian | A.1, A.2, B.1, B.4 (bảng giả thuyết và khuyến nghị); ghép báo cáo, làm slide | Task 2 (sinh dữ liệu), Task 3 (DDL), Task 5 (mô hình và đo dung lượng), Task 9 rút gọn |
| **TV2** | M2 | **B.3**: RQ4 chi phí ghi (1 triệu dòng) | A.3 (cài đặt, Bảng A.3.1), B.3 | Task 1 (repo), Task 4 (môi trường, `use_engine.sh`, `load.sh`, `engine_settings`), Task 10 (sysbench, lấy mẫu tài nguyên) |
| **TV3 (tác giả B.3 giai đoạn 1)** | M3 | **B.2**: RQ1 (1 triệu và 10 triệu dòng), RQ2 (10 triệu dòng) | A.3 (demo, lấy từ kết quả cũ), B.0, B.2, B.4 (hạn chế) | Task 6 (công cụ đo, phân tích kế hoạch thực thi), Task 7, Task 8, Task 12 (module style biểu đồ chung) |

**Code chung, do một người viết và cả nhóm dùng:**
- `bench/config.py` và `bench/db.py`: TV2
- `bench/datagen.py` và `bench/schema.py`: TV1
- `bench/runner.py`, phần explain trong `bench/db.py`, và style biểu đồ: TV3

Mọi thay đổi vào code chung sau ngày 2 phải được cả nhóm biết.

### Lộ trình

| Ngày | TV1 (M1, B.1) | TV2 (M2, B.3) | TV3 (M3, B.2) |
|---|---|---|---|
| 1 (18/11) | Task 2, Task 3 có test, đẩy lên repo trước 18h. Điền Bảng A.3.1 | Task 1 (tạo repo), Task 4: compose theo hồ sơ M và `use_engine.sh`, **đẩy lên repo trước 12h**; chiều dựng cụm trên M2. Điền Bảng A.3.1 | Task 6 có test. Chiều: dựng môi trường trên M3 từ repo. Điền Bảng A.3.1 |
| 2 (19/11) | Dựng môi trường trên M1. Task 5: mô hình; hiệu chỉnh hệ số TiKV bằng số đo `sbtest1` cũ | Nạp 1 triệu dòng; `engine_settings`; bắt đầu Task 10 (Lua) | Nạp 1 triệu dòng; Task 7: chạy thử RQ1. **Tối:** sinh CSV và nạp 10 triệu dòng vào TiDB |
| 3 (20/11) | Nạp 1 triệu dòng; đo B.1 ở 1 triệu dòng. **Tối:** nạp 10 triệu dòng vào TiDB | Task 10: chạy thử 10 giây; kiểm tra CPU của sysbench | RQ1 ở 1 triệu dòng (cả hai hệ); nạp 10 triệu dòng vào MySQL |
| 4 (21/11) | Nạp 10 triệu dòng vào MySQL; đo B.1 ở 10 triệu dòng, kèm tài nguyên khi chạy `CREATE INDEX` | **Chạy RQ4 đầy đủ** (~4 giờ, lặp 3 lần) | RQ1 ở 10 triệu dòng; Task 8: chạy thử RQ2 |
| 5 (22/11) | Bảng đối chiếu B.1; RQ3 rút gọn (1 triệu dòng) nếu còn thời gian | Kiểm tra CSV; chạy lại cấu hình lỗi; nếu còn thời gian thì tăng lên 5 lần lặp | RQ2 ở 10 triệu dòng (TiDB rồi MySQL) |
| 6 (23/11) | Viết B.1 và biểu đồ B.1 | Biểu đồ RQ4 | Biểu đồ RQ1, RQ2; dự phòng chạy lại |
| 7 (24/11) | Sửa A.1, A.2 | Viết A.3 (cài đặt), B.3 | Viết B.0, A.3 (demo), B.2 |
| 8 (25/11) | Ghép báo cáo; viết B.4 (bảng giả thuyết, khuyến nghị) | Đọc chéo B.2 | Đọc chéo B.3; viết B.4 phần hạn chế |
| 9 (26/11) | Slide | **Kiểm tra chéo B.1, B.2:** mỗi con số khớp với CSV | **Kiểm tra chéo B.1, B.3:** mỗi kết luận có số đo và cơ chế đi kèm |
| 10 (27/11) | Nộp, tập thuyết trình | Tập thuyết trình | Tập thuyết trình |

**Điểm kiểm tra chung:**
* **Cuối ngày 2:** cả ba máy chạy được cụm TiDB với 3 store `Up` và MySQL. `checksum` của bộ 1 triệu dòng **giống nhau trên cả ba máy**: cùng seed thì phải ra cùng dữ liệu. Nếu một máy không đạt hồ sơ M, chuyển máy đó sang hồ sơ S (Phụ lục A).
* **Cuối ngày 4:** có CSV của B.1 (10 triệu dòng), RQ1 và RQ4. Nếu nạp 10 triệu dòng thất bại trên M1 hoặc M3, máy đó chuyển sang 5 triệu dòng và ghi rõ trong báo cáo.
* **Cuối ngày 6:** đủ toàn bộ CSV và biểu đồ; từ ngày 7 chỉ viết, không chạy thêm thực nghiệm mới.

### Quy tắc làm việc trên 3 máy

1. **Một repo, một nhánh chính.** Dùng chung `docker/`, `bench/`, `experiments/` và `scripts/`. Không ai sửa cấu hình container riêng trên máy mình.
2. **Cùng hồ sơ cấu hình** (Phụ lục A) và cùng phiên bản image trên cả ba máy.
3. **Cùng dữ liệu:** mỗi máy tự sinh CSV với seed `20261116` (không cần copy file lớn), rồi đối chiếu `checksum` với hai máy kia.
4. **Mỗi dòng kết quả ghi thêm `machine`** (M1, M2 hoặc M3), cùng với block cache, buffer pool và `max_replicas`.
5. **Không so sánh độ trễ hay TPS giữa các mục.** Mọi so sánh TiDB với MySQL chỉ thực hiện trên cùng một máy. Dung lượng ở B.1 thì so được với nhau và với mô hình.
6. **Trong lúc đo, máy chỉ chạy Docker:** tắt trình duyệt, IDE nặng và các ứng dụng đồng bộ đám mây; cắm sạc nếu là laptop.

---

## PHỤ LỤC A: CẤU HÌNH TƯƠNG ĐƯƠNG TÀI NGUYÊN

**Hồ sơ M (mặc định).** Máy cần ít nhất 12 luồng CPU, 16 GB RAM và SSD. Docker hoặc WSL2 được cấp ít nhất 10 CPU và 12 GB.
* **CPU** (giữ nguyên như giai đoạn 1 để so sánh được với B.0): PD 0,5 + TiDB 1,75 + 3 × TiKV 1,25 = 6 CPU, tương đương MySQL 6 CPU. sysbench và script đo dùng 3 CPU.
* **Bộ nhớ đệm:** mỗi TiKV đặt `storage.block-cache.capacity = "800MiB"` (3 node là 2.400 MiB), tương đương MySQL `innodb_buffer_pool_size = 2400M`.
  * **Bắt buộc đặt thủ công**, vì mặc định TiKV lấy 45% RAM của máy host.
  * Nên đặt thêm `memory-usage-limit = "2GB"` cho mỗi TiKV.
* **RAM container:** mỗi TiKV 2,25 GiB, TiDB 1,5 GiB, PD 1 GiB (tổng ~9,25 GiB); MySQL 4 GiB.

**Hồ sơ S (máy yếu hơn).** Dùng cho máy có 8 luồng CPU hoặc 16 GB RAM nhưng Docker/WSL2 chỉ được cấp dưới 12 GB.
* **CPU:** PD 0,4 + TiDB 1,2 + 3 × TiKV 0,8 = 4 CPU, tương đương MySQL 4 CPU; sysbench 2 CPU.
* **Bộ nhớ đệm:** block cache 500 MiB × 3, tương đương buffer pool 1.500 MiB.
* **RAM container:** mỗi TiKV 1,75 GiB, TiDB 1,25 GiB, PD 0,75 GiB; MySQL 3 GiB.
* **Quy mô lớn nhất:** 5 triệu dòng thay cho 10 triệu.
* **Báo cáo phải ghi rõ** mục nào chạy theo hồ sơ S.

**Áp dụng cho cả hai hồ sơ:**
* **Độ bền:** MySQL `innodb_flush_log_at_trx_commit = 1`, tắt binlog; TiDB để mặc định (Raft log được fsync).
* **Nguyên tắc vàng:** trên mỗi máy, chỉ một hệ chạy tại một thời điểm (`scripts/use_engine.sh`).

## PHỤ LỤC B: ĐIỀU CHỈNH TÀI LIỆU KỸ THUẬT ĐỂ VỪA 1,5 TUẦN VÀ 3 MÁY

| Task | Điều chỉnh |
|---|---|
| 1 | Repo dùng chung cho cả 3 máy; `bench/config.py` đọc biến môi trường `MACHINE_ID` (M1, M2, M3) và `PROFILE` (M hoặc S). |
| 2, 3 | Đổi schema theo B.1 (thêm `shipping_fee`, bỏ `service_type`, đổi tên cột sang `recipient_*`, `weight_grams`, dùng `VARCHAR(20)` cho mã vận đơn); test `test_columns_match_datagen` dùng danh sách cột mới. Chuyển hai task này sang TV1. |
| 4 | Thông số theo hồ sơ M/S ở Phụ lục A, chọn qua `PROFILE`; tắt binlog thay cho `sync_binlog=1`; image `pingcap/*:v8.5.5`, `mysql:8.4.11`. `engine_settings` trả thêm `machine` và `profile`. `append_result` ghi tự động hai cột này. |
| 5 | Thêm bước hiệu chỉnh hệ số TiKV bằng số đo `sbtest1` cũ; mô hình InnoDB có hai chế độ lấp đầy (tạo index sau khi nạp hoặc chèn dần), `DATETIME` = 5 B. Chạy trên M1. |
| 7, 8 | Chạy trên M3. |
| 9 | Chỉ làm phép đo dung lượng ở 1 triệu dòng trên M1, và chỉ khi còn thời gian. |
| 10 | Chạy trên M2, chỉ ở 1 triệu dòng, 60 giây × 3 lần lặp (5 lần nếu còn thời gian); container sysbench 3 CPU, ghi lại CPU của nó. |
| 11 | Bỏ; dùng kết quả chaos test và scale-out của giai đoạn 1. |
| 12 | TV3 viết module style chung (màu cố định cho TiDB và MySQL, font, kích thước); mỗi người tự vẽ biểu đồ cho phần của mình. |
| 13 | Nạp 10 triệu dòng trên M1 (cho B.1) và M3 (cho RQ1, RQ2); M2 chỉ cần 1 triệu dòng. |

## PHỤ LỤC C: ĐỐI CHIẾU VỚI DANH SÁCH 24 VẤN ĐỀ

| Vấn đề | Đã xử lý tại |
|---|---|
| 1 (viết sẵn kết luận) | Nguyên tắc viết ở đầu tài liệu; dạng giả thuyết trong RQ1, RQ2, RQ4; A.1 |
| 2 (B.3 có "khả năng mở rộng") | B.3 chỉ còn RQ4; scale-out chuyển sang A.3 |
| 3 (kết quả cũ chưa có chỗ) | A.3, B.0 |
| 4 (thiếu B.4) | B.4 |
| 5–12 (sai kỹ thuật) | A.1, A.2, RQ1, RQ2 |
| 13–16 (mô hình B.1) | B.1.2–B.1.4 |
| 17–19 (không khớp kế hoạch kỹ thuật) | B.1.1, đầu tài liệu, Phụ lục A |
| 20–21 (phân công, lộ trình) | Phân công theo phần và theo máy, lộ trình 10 ngày, phạm vi RQ4 |
| 22–24 (kế hoạch kỹ thuật) | Phụ lục A, Phụ lục B |
