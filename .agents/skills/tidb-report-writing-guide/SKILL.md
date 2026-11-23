---
name: tidb-report-writing-guide
description: Hướng dẫn chuyên sâu và chuẩn mực viết báo cáo bài tập lớn Hệ Quản Trị CSDL về đề tài TiDB vs MySQL (chuẩn UET LaTeX); tích hợp 3 chỉ đạo sống còn của giảng viên, chuẩn hóa phân tích độ trễ/LSM-tree vs B+Tree, định nghĩa chính xác Quorum Multi-Raft 1 vs 3 bản sao, và chi tiết biên soạn Mục A.3 và B.3 cho TV2.
---

# Kỹ năng Biên Soạn Báo Cáo: TiDB vs MySQL Indexing Study (Chuẩn UET)

Skill này cung cấp toàn bộ hướng dẫn, nguyên tắc học thuật, quy chuẩn phân tích kỹ thuật và mẫu văn bản phục vụ riêng cho việc **viết báo cáo bài tập lớn môn Hệ Quản Trị Cơ Sở Dữ Liệu** (Trường ĐH Công Nghệ - ĐHQGHN).

---

## 1. Mục Tiêu Đề Tài & Định Hướng Báo Cáo

* **Đề tài:** *Chi phí của chỉ mục phụ trên hệ lưu trữ Key-Value phân tán: Nghiên cứu thực nghiệm TiDB so với MySQL InnoDB trên bài toán tra cứu vận đơn* (Bảng `shipments`, 1M và 10M dòng).
* **Cấu trúc chuẩn theo 2 phần quy định của Giảng viên (Tỷ lệ 50% – 50%):**
  * **PHẦN 1 - Giới thiệu và cài đặt hệ quản trị CSDL (~50% đầu):**
    * *Định hướng viết theo chỉ đạo:* **Trình bày tổng quát, súc tích**, chắt lọc 4 trụ cột kiến trúc cốt lõi (TiDB vô trạng thái, PD điều phối, TiKV phân tán với RocksDB LSM-tree, Multi-Raft 3 bản sao). Quá trình cài đặt, cấu hình, vận hành và demo tập trung vào sơ đồ topology, bảng tham số tài nguyên tương đương (Bảng A.3.1), ảnh minh chứng Dashboard và status node.
    * *Lưu ý quan trọng:* **Tránh liệt kê mã lệnh dài dòng.** Các cấu hình chi tiết (docker-compose, script bash/powershell, file config toml/cnf) chỉ tóm lược nguyên lý trong thân bài và dẫn link sang Phụ lục hoặc kho mã nguồn GitHub/thư mục dự án.
  * **PHẦN 2 - Phân tích vấn đề chuyên sâu (~50% sau):**
    * *Vấn đề kỹ thuật chuyên sâu:* Đánh giá chi phí chỉ mục phụ (Secondary Indexing Cost) trên không gian Key-Value phân tán so sánh với cấu trúc B+Tree tập trung.
    * *Yêu cầu bắt buộc:* **Bắt buộc có dữ liệu và demo/thực nghiệm thực tế để minh họa, kiểm chứng nội dung phân tích.** Không nói lý thuyết suông; mọi phân tích về độ trễ, thông lượng và dung lượng phải gắn chặt với số liệu thực tế đo đạc từ CSV (`results/rq4.csv`), kế hoạch thực thi (`EXPLAIN ANALYZE`) và biểu đồ trực quan.
* **Nguyên tắc viết cốt lõi:** Luôn giữ quan điểm khoa học khách quan, **không viết sẵn kết luận "TiDB vượt trội hơn MySQL"**. Mọi chênh lệch hiệu năng phải được giải thích bằng cơ chế kiến trúc bên dưới (LSM-Tree vs B+Tree, Multi-Raft vs Single Node, Coprocessor Push-down vs Local Memory).

---

## 2. Ba Chỉ Đạo Sống Còn Của Giảng Viên (Rubric Chấm Điểm)

Khi biên soạn bất kỳ mục nào trong báo cáo, **BẮT BUỘC tuân thủ tuyệt đối 3 chỉ đạo của Giảng viên**:

### 🎯 Quy tắc 1: Phân định rạch ròi bản chất độ trễ — Không đổ lỗi cho mạng
* **Lỗi cần tránh:** Tuyệt đối không quy chụp *"TiDB có độ trễ cao hơn MySQL là do mạng phân tán gRPC"*. Không nêu con số độ trễ mạng nếu nhóm chưa đo.
* **Cách phân tích chuẩn mực:**
  1. **Hiệu ứng Index Covering & Toán tử Coprocessor 2 chặng (`IndexLookUp`):**
     * Trong non-covering index, TiDB phải tách thành 2 chặng: quét Index lấy danh sách Row Handle, sau đó gửi các Coprocessor task theo lô (batch) tới các Region chứa dòng dữ liệu để lấy các cột còn lại.
     * So sánh với MySQL: MySQL chỉ cần quay về trang dữ liệu trong Buffer Pool (tra B+Tree cục bộ).
  2. **Cấu trúc lưu trữ LSM-Tree của RocksDB:**
     * Đọc trên TiKV phải tra cứu qua MemTable, Block Cache và các tầng SST (L0 $\rightarrow$ L6) qua Bloom Filter.
     * Ghi trên TiDB đi vào WAL/MemTable rồi Compaction (khuếch đại ghi), trong khi MySQL ghi vào trang B+Tree (nguy cơ Page Split). Không kết luận bên nào rẻ hơn trước khi có số đo.

### 🎯 Quy tắc 2: Định nghĩa chính xác số TiKV node, số Replica và Quorum Multi-Raft
* **Lỗi cần tránh:** Không bao giờ viết mập mờ kiểu *"chạy 1 node và coi là thiết lập 3 replica hợp lệ"*.
* **Cách định nghĩa chuẩn mực trong Mục A.3 và B.3:**
  1. **Cụm TiDB luôn có 3 node TiKV (3 container trên cùng một máy và một ổ đĩa)** (`tikv1`, `tikv2`, `tikv3`).
  2. **Cấu hình 3 bản sao (`RF=3` — Chuẩn sản xuất):**
     * Mỗi Region có 3 bản sao (1 Leader, 2 Follower) phân bổ trên 3 TiKV node.
     * **Quorum = 2/3:** Giao dịch chỉ commit khi quá bán bản sao ghi nhận Raft Log. Bảo đảm tính sẵn sàng cao (High Availability, chịu lỗi 1 node chết mà không mất dữ liệu $RPO=0$).
  3. **Cấu hình 1 bản sao (`RF=1` — Cấu hình đối chứng):**
     * Vẫn trên 3 TiKV node đó, nhưng cấu hình PD: `replication.max-replicas = 1`.
     * Mỗi Region chỉ duy trì đúng 1 bản sao (1 Leader), **Quorum = 1/1**, không còn khả năng chịu lỗi.
     * **Mục đích:** Định lượng tổng chi phí nhân bản (Raft log, fsync, CPU của Follower, tranh chấp đĩa chung). Phép so sánh này không tách riêng phần mạng.

### 🎯 Quy tắc 3: Tập trung vào nghiệp vụ Logistics & Tối giản phần Failover
* **Trọng tâm nghiên cứu:** Tập trung vào các truy vấn thực tế trên bảng vận đơn `shipments` (Q1: tra cứu mã vận đơn, Q2: xem đơn theo shop trong 7 ngày, Q3: lọc đơn theo kho và trạng thái), phân tích Execution Plan (`EXPLAIN ANALYZE`), độ trễ p95/p99, chi phí ghi RQ4 và dung lượng B.1. So sánh **có và không có covering index** phải đủ bốn mặt: kế hoạch, độ trễ, chi phí ghi, dung lượng vật lý.
* **Xử lý phần Failover (Chaos Test):** Chỉ đóng vai trò demo vận hành phụ ở Mục A.3 (tái sử dụng kết quả giai đoạn 1), **không chạy lại tốn thời gian** và không để lấn át nội dung đánh giá chỉ mục phụ ở Phần B.

---

## 3. Hướng Dẫn Chi Tiết Cho Thành Viên 2 (TV2)

TV2 phụ trách viết 2 mục nòng cốt trong báo cáo, tương ứng với 2 phần của đề cương:

### 📝 Mục A.3: Cài Đặt, Triển Khai Thực Nghiệm và Bảng A.3.1 (Thuộc Phần 1)
* **Vị trí file:** `project/report/sections/01_phan_a.tex`.
* **Tiêu chí viết theo yêu cầu của Cô:** **Trình bày tổng quát, không paste mã lệnh/script dài dòng**. Các script nạp liệu (`load.sh`), script đo (`rq4_write.sh`), cấu hình compose chi tiết chỉ tóm lược ý đồ thiết kế trong thân bài và dẫn chiếu sang Phụ lục hoặc repository.
* **Nội dung cần có trong thân bài:**
  1. **Bảng A.3.1 (Thông số 3 máy thực nghiệm):** Điền đầy đủ thông số máy M2:
     * *CPU:* Intel(R) Core(TM) Ultra 5 125H (18 luồng logic).
     * *RAM:* 16 GB vật lý, ổ cứng NVMe SSD 512 GB.
     * *Hệ điều hành / Docker:* Windows 11 / Docker Engine 29.8.0 / RAM của WSL2 lấy từ `docker info` **tại thời điểm đo chính thức** (giá trị đã đổi trong quá trình thử).
     * *Hồ sơ áp dụng:* **Hồ sơ S** (WSL2 cấp < 12 GiB). Nếu giới hạn RAM container khác Phụ lục A thì ghi rõ giá trị thực và lý do.
  2. **Minh chứng cài đặt cụm TiDB v8.5.5:**
     * Trích xuất kết quả `SELECT tidb_version();`.
     * Trích xuất bảng `INFORMATION_SCHEMA.TIKV_STORE_STATUS` chứng minh cả 3 store TiKV đều ở trạng thái `Up`.
     * Chèn ảnh chụp TiDB Dashboard: `report/figures/tidb_dashboard_topology.png`.
     * Chèn ảnh nhiệt Region: `report/figures/tidb_key_visualizer.png`.
  3. **Cấu hình đối chứng tương đương tài nguyên (Resource Parity):**
     * Đối chiếu rõ: MySQL được cấp 4 CPU, 1.500 MiB Buffer Pool, tắt binlog $\Leftrightarrow$ TiDB được cấp 4 CPU (0.4 PD + 1.2 TiDB + 3 $\times$ 0.8 TiKV), 3 $\times$ 500 MiB Block Cache.
  4. **Demo vận hành cơ bản & Failover:** Tóm tắt ngắn gọn quy trình kiểm tra trạng thái và demo chịu lỗi khi 1 node TiKV dừng (Leader tự bầu lại theo Raft khi hết thời gian bầu cử), không kéo dài nội dung.

### 📝 Mục B.3: Đánh Giá Thực Nghiệm Chi Phí Ghi (RQ4 trên 1M dòng - Thuộc Phần 2)
* **Vị trí file:** `project/report/sections/02_phan_b.tex`.
* **Tiêu chí viết theo yêu cầu của Cô:** **Bắt buộc có dữ liệu và demo/thực nghiệm thực tế để minh họa, kiểm chứng nội dung phân tích.** Mọi kết luận về hiệu năng ghi phải được bảo chứng bằng số liệu từ bảng thực nghiệm, biểu đồ và trích xuất chỉ số giám sát.
* **Nội dung cần có trong thân bài:**
  1. **Bảng số liệu tổng hợp từ `results/rq4.csv`:** Trình bày bảng so sánh TPS, độ trễ phân vị p95 và p99 giữa 4 mốc index (0, 1, 3, 5), 2 mức luồng (16, 64) trên 3 cấu hình: MySQL, TiDB (RF=3), TiDB (RF=1).
  2. **Biểu đồ trực quan:** Nhúng hình `report/figures/rq4_tps_vs_indexes.png`.
  3. **Kiểm chứng cơ chế bằng dữ liệu thực nghiệm:**
     * *Mức suy giảm TPS (%):* Khi tăng từ 0 lên 5 index, TPS giảm bao nhiêu % ở từng hệ. Giả thuyết cần kiểm chứng: mỗi mục index là thêm một cặp Key-Value phải qua 2PC, nên chi phí ghi tăng theo số index bị ảnh hưởng. Không giả định tăng tuyến tính, dạng quan hệ phải lấy từ số đo.
     * *So sánh Tải W1 (Insert) và W2 (Update):* Cơ chế: W1 ghi vào mọi index đang có; W2 chỉ chạm index chứa `status` (`idx_hub_status`, `idx_status`). Mức giảm TPS của từng tải lấy từ số đo, và diễn giải theo số index bị ảnh hưởng.
     * *Định lượng chi phí Raft (RF=3 vs RF=1):* Dùng số liệu đo đạc thực tế giữa 3 bản sao (Quorum 2/3) và 1 bản sao (Quorum 1/1) để định lượng tổng chi phí nhân bản, không gọi là chi phí mạng. Kèm số Leader trên mỗi store.
     * *Khuếch đại ghi (Write Amplification):* Dùng bộ đếm block I/O để so byte ghi trên mỗi giao dịch. Cửa sổ 60 giây có thể lẫn compaction của lượt trước, nên báo cáo kèm `settled` và độ phân tán giữa các lần lặp.
     * *Covering:* so `idx_sender_created` với `idx_sender_cov` (24 lượt bổ sung) trên W1 và W2.
  4. **Điều kiện dùng số liệu:** chỉ dùng CSV chính thức có một `config_id` cho mỗi hệ. Không dùng `results/rq4.csv` thử nghiệm ngày 22--23/11 để kết luận. Không dùng `index_bytes` của TiDB làm dung lượng vật lý.

---

## 4. Quy Chuẩn Trình Bày LaTeX (UET Template)

* **Font chữ & Bảng biểu:** Dùng gói `tabularx`, định dạng `\bangfont` chuẩn UET.
* **Nhúng hình ảnh:**
  ```latex
  \begin{figure}[H]
  \centering
  \includegraphics[width=0.88\textwidth]{figures/ten_file.png}
  \caption{Mô tả ngắn gọn, súc tích nội dung hình ảnh}
  \label{fig:nhan_dan}
  \end{figure}
  ```
* **Ký hiệu toán học:** Dùng KaTeX/LaTeX chuẩn: $RPO = 0$, Quorum $2/3$, phân vị $p95, p99$, độ trễ $\text{ms}$.
