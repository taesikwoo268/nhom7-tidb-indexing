# Khung Báo Cáo LaTeX Bài Tập Lớn: TiDB vs MySQL (Chuẩn UET)

Khung tài liệu LaTeX được xây dựng dựa trên mẫu chuẩn `report2.tex` của Trường Đại học Công nghệ (ĐHQGHN) và hiện thực hóa đầy đủ kế hoạch đề tài trong file `project/docs/ke_hoach_do_an_tidb_vs_mysql.md`.

---

## 1. Cấu Trúc Báo Cáo Theo Đúng Định Hướng Giảng Viên (Tỷ lệ 50% – 50%)

Báo cáo được chia thành **2 Phần lớn (Phần A và Phần B)** rõ ràng, tích hợp banner phân tách chuyên nghiệp và mục lục 3 cấp:

### **PHẦN A: TÌM HIỂU HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU PHÂN TÁN TiDB (50% đầu)**
* **Mục 1 (Mục A.1):** Xuất phát từ Đặc trưng Dữ liệu: Phân loại dữ liệu và Lý do chọn TiDB (NewSQL) thay vì RDBMS truyền thống hay NoSQL.
  * Bảng đối chiếu 4 dạng dữ liệu (Quan hệ vừa/nhỏ, Cột rộng, Tìm kiếm/Đồ thị, Giao dịch lớn HTAP).
  * Hạn chế của MySQL khi bảng vượt 50–100 triệu dòng (dẫn chứng case study Pipedrive bảng `activities` 1,47 tỷ dòng).
* **Mục 2 (Mục A.2):** Các Đặc trưng Kiến trúc Cốt lõi làm nên Sức mạnh của TiDB:
  * **Đặc trưng 1:** Tách biệt hoàn toàn Tầng Tính toán (*Compute - Stateless*) và Tầng Lưu trữ (*Storage - Stateful*).
  * **Đặc trưng 2:** Tầng Ánh xạ Dữ liệu (*Table-to-KV*) và Cấu trúc Lưu trữ Vật lý Cục bộ RocksDB LSM-Tree (`MemTable`, `WAL`, các tầng `SST` và 4 Column Families).
  * **Đặc trưng 3:** Chia mảnh tự động theo Vùng (*Region Auto-Splitting*) và Cơ chế Đồng thuận Multi-Raft (3 Replicas, Quorum $2/3$, Leader Election).
  * **Đặc trưng 4:** Bộ điều phối trung tâm Placement Driver (PD), Timestamp Oracle (TSO) và Giao dịch phân tán Percolator 2 pha (MVCC Snapshot Isolation).
* **Mục 3 (Mục A.3):** Cài đặt, Triển khai Cụm TiDB Đa Node và Demo Vận hành Cơ bản:
  * Kiến trúc thực nghiệm trên máy 16GB RAM / 8 CPU Cores (5 containers: 1 PD, 3 TiKV, 1 TiDB + MySQL đối chứng).
  * Minh chứng cài đặt thành công (`SELECT tidb_version()`, `INFORMATION_SCHEMA.TIKV_STORE_STATUS`, TiDB Dashboard và Key Visualizer).

---

### **PHẦN B: ĐI SÂU PHÂN TÍCH BÀI TOÁN LƯU TRỮ VẬT LÝ, CHI PHÍ CHỈ MỤC VÀ THỰC NGHIỆM ĐỐI CHỨNG (50% sau)**
* **Mục 4 (Mục B.1):** Bài toán Tính toán Lý thuyết Dung lượng Lưu trữ Vật lý (*Theoretical Storage Model*):
  * Lược đồ bảng thực nghiệm chuẩn `sbtest1`.
  * Công thức tính Dữ liệu Thô lý thuyết ($S_{\text{raw}}$) cho 10 triệu và 100 triệu dòng (Chưa Index: $1,75\text{ GiB}$; Có Index: $1,83\text{ GiB}$).
  * Mô hình lưu trữ vật lý trên MySQL InnoDB: Cây B+Tree trang 16KB, 13B MVCC, Record Header 5B, hệ số lấp đầy $93,75\%$, phân mảnh trang Index $72\% \rightarrow 2,35\text{ GiB}$ (10M dòng) và $\sim 23,5\text{ GiB}$ (100M dòng).
  * Mô hình lưu trữ vật lý trên TiDB / TiKV: Mã hóa cặp Key-Value, tỷ lệ nén LSM-Tree $C_{\text{ratio}} \approx 0,60$, khuếch đại không gian $\alpha_{\text{LSM}} \approx 1,11$.
    * Trên 1 bản sao: $1,54\text{ GiB}$ (chưa index) và $1,88\text{ GiB}$ (có index).
    * Toàn cụm 3 node (Multi-Raft RF=3): $4,87\text{ GiB}$ (chưa index) và $6,00\text{ GiB}$ (có index, $\sim 22$ Regions).
  * Bảng tổng hợp đối chiếu toàn diện Lý thuyết vs. Thực tế.
* **Mục 5 (Mục B.2):** Phân tích Chi phí Tính toán (RAM, CPU, IOPS) Trước và Sau khi có Index trên Máy 16GB RAM:
  * Trạng thái 0: Baseline hệ thống.
  * Trạng thái 1: Nạp 10 triệu bản ghi chưa có Index (Buffer Pool vs MemTable/BlockCache, Auto-split 18 Regions).
  * Trạng thái 2: Tạo Index `k_1` (`ALTER TABLE ADD INDEX`) và chèn dữ liệu (MySQL Sort Buffer / Merge Sort đĩa tạm / bão I/O vs TiDB Distributed Reorg Workers / LSM-Tree ghi tuần tự không Read-Modify-Write).
  * So sánh kế hoạch thực thi câu lệnh (`EXPLAIN ANALYZE`) trước và sau Index (TableFullScan đẩy xuống Coprocessor 3 node song song vs IndexLookUp 2 chặng).
* **Mục 6 (Mục B.3):** Thực nghiệm Đối chứng Nâng tầm TiDB so với MySQL trên Dữ liệu Lớn:
  * Thực nghiệm 2: Scalability & Chịu tải đồng thời cao (Sysbench 16 $\rightarrow$ 512 threads). Phân tích khách quan tại sao tải thấp MySQL nhanh hơn (IPC nội bộ), nhưng tải cao TiDB ổn định vượt trội nhờ LSM và đa Region Leader.
  * Mở rộng ngang không gián đoạn (Online Scale-out thêm node `tikv3`).
  * Thực nghiệm 3: Chaos Testing (đánh sập node lưu trữ ở giây thứ 60). MySQL sập $100\%$, TiDB Raft Quorum $2/3$ tự bầu Leader mới sau 3--8 giây, $RPO = 0$.

---

### **KẾT LUẬN & PHỤ LỤC**
* **Mục 7:** Kết luận, Bảng khuyến nghị lựa chọn kiến trúc (Khi nào nên giữ MySQL, khi nào bắt buộc chuyển sang TiDB NewSQL) và hướng mở rộng (TiFlash HTAP, Multi-DC).
* **Tài liệu tham khảo:** Chuẩn trích dẫn IEEE / học thuật (PingCAP, MySQL 8.4 Manual, Google Spanner, F1, Percolator, Raft, LSM-Tree, Pipedrive report).
* **Phụ lục Kỹ thuật:** Toàn bộ câu lệnh SQL kiểm tra dung lượng bảng, script Bash giám sát tài nguyên `docker stats`, file `docker-compose.yml` hoàn chỉnh, script Sysbench và Bảng phân chia công việc cho 3 thành viên.

---

## 2. Cấu Trúc Thư Mục Tệp Tin

```
project/report/
├── main.tex                    # Tệp chính điều phối văn bản (Preamble, Fonts, Layout, TOC)
├── logo.png                    # Logo Trường Đại học Công nghệ (ĐHQGHN)
├── compile.bat                 # Script chạy biên dịch 1-click bằng XeLaTeX trên Windows
├── README.md                   # Tài liệu hướng dẫn sử dụng khung báo cáo
├── figures/                    # Thư mục chứa hình ảnh và đồ thị thực nghiệm
│   └── README.md
└── sections/                   # Thư mục chứa các module nội dung theo phân công 3 thành viên
    ├── 00_cover.tex            # Trang bìa chuẩn UET (khung đôi, logo, thông tin sinh viên)
    ├── 01_phan_a.tex           # PHẦN A: Tìm hiểu TiDB (Mục 1, 2, 3) -> TV1 & TV2
    ├── 02_phan_b.tex           # PHẦN B: Phân tích lưu trữ & Thực nghiệm (Mục 4, 5, 6) -> TV1, TV2, TV3
    ├── 03_ket_luan.tex         # Kết luận & Khuyến nghị đánh đổi kiến trúc (Mục 7) -> TV3
    ├── 04_phu_luc.tex          # Phụ lục kỹ thuật: SQL, Bash, Docker Compose, Lộ trình 4 tuần
    └── tai_lieu_tham_khao.tex  # Danh mục tài liệu tham khảo khoa học chuẩn
```

---

## 3. Hướng Dẫn Biên Dịch (Compile)

### Cách 1: Biên dịch bằng XeLaTeX trên máy tính cá nhân
Dự án sử dụng bộ font chuẩn XeLaTeX (`fontspec`, hỗ trợ Unicode tiếng Việt đầy đủ).
1. Mở Command Prompt hoặc PowerShell tại thư mục `project/report`.
2. Chạy lệnh:
   ```bash
   xelatex -synctex=1 -interaction=nonstopmode main.tex
   xelatex -synctex=1 -interaction=nonstopmode main.tex
   ```
   *(Chạy 2 lần để cập nhật số trang, mục lục tự động và danh mục bảng/hình).*
3. Hoặc chỉ cần **nhấp đúp chuột vào file `compile.bat`** trên Windows!

### Cách 2: Tải lên Overleaf
1. Nén toàn bộ thư mục `report/` thành file `.zip`.
2. Truy cập [Overleaf.com](https://www.overleaf.com), tạo dự án mới (*New Project* $\rightarrow$ *Upload Project*).
3. Trong phần **Menu** (góc trên bên trái), tại mục **Compiler**, chọn **XeLaTeX**.
4. Nhấn **Recompile** để xem kết quả PDF chuẩn xác 100%.

---

## 4. Phân Công Thành Viên Theo Lộ Trình 4 Tuần
* **Thành viên 1 (Trưởng nhóm):** Chịu trách nhiệm viết `01_phan_a.tex` (Mục 1, 2) và `02_phan_b.tex` (Mục 4 - Mô hình toán học).
* **Thành viên 2 (Kỹ sư Hạ tầng):** Chịu trách nhiệm hoàn thiện `01_phan_a.tex` (Mục 3 - Triển khai thực nghiệm) và `02_phan_b.tex` (Mục 5 - Chi phí RAM/CPU/Index).
* **Thành viên 3 (Kỹ sư Chịu tải & Chaos Test):** Chịu trách nhiệm hoàn thiện `02_phan_b.tex` (Mục 6 - Scalability, Chaos Test) và `03_ket_luan.tex` (Mục 7).
