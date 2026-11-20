# Kiểm định & Chuẩn hóa Mô hình Dung lượng Lưu trữ Vật lý (Mục B.1)

## 1. Bốn lớp đại lượng lưu trữ cần phân biệt rõ trong Mục B.1

Để trả lời trọn vẹn câu hỏi của giảng viên (*"Trước khi index available từng này, khi load 1 triệu hay 10 triệu bản ghi nó chiếm bao nhiêu MB? Tính trên lý thuyết nó đi vào tính kiểu gì?"*), báo cáo cần tách bạch 4 lớp dung lượng:

1. **Dung lượng dữ liệu thô lý thuyết ($S_{\text{raw}}$ - Raw Logical Payload):** Tổng số byte của 14 cột dữ liệu thuần túy và khóa chỉ mục do `bench/datagen.py` sinh ra.
2. **Ước lượng vật lý theo mô hình cấu trúc dữ liệu ($S_{\text{model}}$ - Theoretical Engine Estimate):** Dung lượng tính theo công thức toán học khi cộng thêm chi phí Header, MVCC, hệ số lấp đầy trang B+Tree (InnoDB) hoặc nén LZ4/Zstd, hệ số khuếch đại không gian LSM-Tree và hệ số nhân bản Raft (TiKV).
3. **Dung lượng thống kê bởi Hệ quản trị ($S_{\text{engine\_stat}}$ - Engine-Reported Size):**
   - Trên MySQL: `DATA_LENGTH` và `INDEX_LENGTH` từ `information_schema.TABLES`.
   - Trên TiDB: `SUM(APPROXIMATE_SIZE)` từ `information_schema.TIKV_REGION_STATUS`.
4. **Dung lượng chiếm đĩa vật lý thực tế ($S_{\text{disk}}$ - Physical Disk Footprint):** Đo bằng `du -sb` trên thư mục volume dữ liệu của MySQL và 3 node TiKV (bao gồm cả SST files, WAL/Redo log, Raft log, không gian phân mảnh).

## 2. Đồng bộ hóa số liệu giữa 2 file kế hoạch (`ke_hoach_do_an_tidb_vs_mysql.md` vs `2026-11-16-tidb-indexing-van-don.vi.md`)

Giữa 2 file kế hoạch gốc của nhóm có một điểm khác biệt nhỏ về hằng số giả định cần được đồng bộ khi viết Mục B.1 và cài đặt `bench/storage_model.py`:

| Tham số mô hình | Trong `ke_hoach_do_an_tidb_vs_mysql.md` (Mục B.1) | Trong `2026-11-16-tidb-indexing-van-don.vi.md` (Task 5) | Cách xử lý chuẩn trong Báo cáo & Code |
|---|---|---|---|
| **Kích thước dòng thô (`shipments`)** | 45B cố định + 99B biến đổi = **144 B/row** | `SHIPMENT_ROW = RowSpec(45, 99)` = **144 B/row** | Thống nhất **144 B/row** (và trình bày thêm ghi chú `DATETIME(0)` 5B vs 8B). |
| **Chi phí phụ mỗi dòng InnoDB** | **+24 B/row** (13B MVCC + 5B Header + 6B offset/slot) $\to$ **168 B/row** | Ghi ngắn gọn `+20 B` (từ mô hình bảng `sbtest1` cũ không có cột `VARCHAR` biến đổi) | Với bảng `shipments` (có 4 cột `VARCHAR`), dùng **+24 B/row** (gồm 13B MVCC + 5B record header + 4B length prefix cho 4 cột VARCHAR + 2B page directory slot = 24B) để khớp chính xác con số **168 B/row** và **1,73 GiB** ở Mục B.1. Với bảng `sbtest1` (cố định hoàn toàn), dùng `+20 B/row` để pass unit test hồi quy `test_storage_model.py`. |
| **Chi phí phụ mỗi mục Index InnoDB** | **+8 B/entry** (6B header + 2B directory slot), $F_{\text{rand}} = 0,72$ $\to$ **1,47 GiB** (5 index) | Ghi `+16 B` (trong đó đã gộp cả 8B khóa chính `id` + 8B header/slot) | Làm rõ trong báo cáo: **+16 B/entry so với cột được đánh index** chính là **8 B khóa chính `id` (PK pointer) + 8 B (6B index header + 2B page slot)**. Như vậy hai file hoàn toàn khớp nhau về bản chất toán học! |
| **Chi phí 1 bản sao & 3 bản sao TiKV** | 1 bản sao: **1,24 GiB** (0 idx) / **2,98 GiB** (5 idx); Toàn cụm 3 node (+Raft log): **3,97 GiB** / **9,39 GiB** | Hàm `tikv_estimate` trả về `per_replica` và `cluster` | Trình bày cả 2 cột **TiDB (1 Bản sao RocksDB LSM)** và **TiDB Toàn cụm (3 Node TiKV - RF=3)** trong bảng B.1 để so sánh công bằng với MySQL 1 bản sao. |

## 3. Ba ghi chú "Ăn điểm Tuyệt đối" khi giải thích Mô hình B.1 trước Giảng viên

Khi trình bày công thức ở Mục B.1, hãy thêm mục nhỏ **"Thảo luận độ nhạy của mô hình và đặc thù mã hóa vật lý theo phiên bản"** gồm 3 ý:

1. **Mã hóa nhị phân của `DATETIME` trên MySQL 8.4 vs. Biểu diễn 64-bit:**
   - Trong mô hình lý thuyết cơ sở, `created_at` và `updated_at` được tính 8 bytes/cột (tổng phần cố định 45 bytes).
   - Trên thực tế, MySQL 8.4 InnoDB sử dụng định dạng nén nhị phân `TIME2` cho `DATETIME(0)` (không có fractional seconds) chỉ tốn **5 bytes/cột** (giảm 6 bytes/dòng trên 2 cột thời gian), nhưng lại cần thêm **4 bytes** danh sách độ dài (`Variable-length field lengths`) cho 4 cột `VARCHAR` và **1 byte** `NULL bitmap` (do cột `note` cho phép `NULL`). Nhờ phân tích chi tiết đến từng byte ở cấp độ `COMPACT/DYNAMIC Row Format` này, báo cáo giải thích được chính xác sai số vài phần trăm giữa công thức lý thuyết và số đo `DATA_LENGTH` thực tế.
2. **Ảnh hưởng của Biến thể Khóa chính (RQ3) lên kích thước Secondary Index:**
   - Trên cả InnoDB và TiKV (khi dùng Clustered PK), mọi chỉ mục phụ đều phải lưu giá trị của Khóa chính làm con trỏ dòng (`Row Locator` / `Primary Key Handle`).
   - Khi đổi khóa chính từ `id BIGINT` (8 bytes) sang `tracking_code VARCHAR(20)` (trung bình 14 bytes + length byte), mỗi mục trong cả 5 chỉ mục phụ đều bị phình thêm $\approx 6-7\text{ bytes}$, nhân với $5 \times 10^7$ mục sẽ làm tăng hàng trăm MiB dung lượng chỉ mục phụ.
3. **Sự khác biệt giữa Nén Khối (Block Compression) của RocksDB và B+Tree Page Fragmenation của InnoDB:**
   - InnoDB chèn ngẫu nhiên vào 5 chỉ mục phụ gây tách trang (`Page Split`), làm hệ số lấp đầy giảm xuống $F_{\text{rand}} \approx 65\% - 75\%$ (lãng phí không gian trống trong trang 16KiB).
   - TiKV RocksDB gom các khóa chỉ mục đã sắp xếp vào các SSTable blocks và nén bằng LZ4/Zstd (đạt tỷ lệ nén $C_{\text{ratio}} \approx 0,55 - 0,65$ nhờ tiền tố khóa `t{table_id}_i{index_id}_` lặp lại giống hệt nhau giữa các dòng liền kề - *Prefix Compression*), giúp dung lượng 1 bản sao trên TiKV rất gọn dù đi kèm chi phí nhân bản 3x của Raft.
