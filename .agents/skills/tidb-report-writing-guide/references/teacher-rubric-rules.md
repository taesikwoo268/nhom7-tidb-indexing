# Hướng Dẫn Vận Dụng Chuẩn Mực Đánh Giá Của Giảng Viên Vào Báo Cáo

Tài liệu này chi tiết hóa cách hành văn, phương pháp luận và lập luận kỹ thuật nhằm thỏa mãn tuyệt đối rubric chấm điểm chính thức của Giảng viên (Cô) gồm 2 phần nội dung và 3 chỉ đạo chuyên sâu.

---

## 0. Quy Chuẩn Hai Phần Báo Cáo Chính Thức Của Giảng Viên

### 📌 Phần 1: Giới thiệu và cài đặt hệ quản trị CSDL
> *"Trình bày tổng quan, kiến trúc, các thành phần chính; quá trình cài đặt, cấu hình, vận hành và demo các chức năng cơ bản của hệ quản trị được lựa chọn (**Trong báo cáo nên trình bày tổng quát, chi tiết có thể dẫn sang tài liệu bổ sung bên ngoài**)."*

* **Cách áp dụng vào bài viết:**
  * **Trình bày tổng quát:** Tập trung vào bản chất kiến trúc 3 tầng (TiDB - PD - TiKV), cơ chế ánh xạ quan hệ sang Key-Value, giải thuật đồng thuận Multi-Raft.
  * **Tránh lỗi paste mã lệnh:** Tuyệt đối không sao chép nguyên văn hàng trăm dòng tệp `docker-compose.yml`, script bash `.sh` hay powershell `.ps1` vào thân bài báo cáo.
  * **Dẫn chứng chuyên nghiệp:** Trong thân bài chỉ đưa bảng tổng hợp tài nguyên tương đương (Bảng A.3.1) và ảnh chụp màn hình minh chứng vận hành (TiDB Dashboard Topology, Key Visualizer). Toàn bộ file cấu hình và lệnh chi tiết được đưa vào **Phụ lục** hoặc dẫn link đến kho mã nguồn GitHub của nhóm.

### 📌 Phần 2: Phân tích vấn đề chuyên sâu
> *"Trình bày vấn đề kỹ thuật đã đăng ký, cơ chế hoạt động, phương pháp triển khai, thiết kế kịch bản thử nghiệm và phân tích kết quả. **Bắt buộc có dữ liệu và demo/thực nghiệm thực tế để minh họa, kiểm chứng nội dung phân tích**."*

* **Cách áp dụng vào bài viết:**
  * **Vấn đề chuyên sâu:** Chi phí của chỉ mục phụ (Secondary Indexing Cost) trên kiến trúc phân tán TiDB so với hệ tập trung MySQL InnoDB.
  * **Tuyệt đối không nói suông:** Mọi nhận định kỹ thuật **bắt buộc phải đi kèm bằng chứng thực nghiệm**:
    1. Bảng số liệu cụ thể đo từ `results/rq4.csv` (TPS, p95, p99).
    2. Biểu đồ đường/cột trực quan (`figures/rq4_tps_vs_indexes.png`).
    3. Minh chứng kế hoạch thực thi `EXPLAIN ANALYZE` và chỉ số giám sát Docker I/O thực tế.

---

## 1. Vận dụng Nhận xét 1: Phân định rạch ròi độ trễ, không quy kết cho mạng

### Lỗi thường gặp (Bị trừ điểm nặng):
> *"TiDB có độ trễ cao hơn MySQL 15 lần chủ yếu là do chi phí mạng phân tán gRPC giữa các máy chủ."*

### Cách viết chuẩn học thuật (Đạt điểm tối đa):
> *"Khoảng chênh lệch độ trễ giữa TiDB và MySQL trên môi trường thực nghiệm không thể quy riêng cho mạng. Nó gồm hiệu ứng index (covering, độ chọn lọc) và chi phí truy cập KV, được tách bằng kế hoạch thực thi và số đo:*
> 1. *Về cơ chế truy vấn (Coprocessor Push-down & Batching): Đối với truy vấn không bao phủ (Non-covering Index), TiDB phải phân rã thành toán tử hai chặng `IndexLookUp`: chặng 1 quét Index Key để thu thập danh sách Handle, chặng 2 gửi các Coprocessor task theo lô (Batch) đến các Region chứa dòng dữ liệu thực tế. Mức tăng độ trễ do chặng thứ hai là [số đo], lấy từ cặp covering và không covering trên cùng câu SQL.*
> 2. *Về cấu trúc vật lý cục bộ (LSM-Tree vs B+Tree): Trong khi MySQL đọc các trang dữ liệu đã sắp xếp sẵn trong bộ đệm hoặc đĩa ngẫu nhiên, TiKV phải thực thi phép đọc qua cấu trúc đa tầng của RocksDB (MemTable $\rightarrow$ Block Cache $\rightarrow$ L0 đến L6 qua Bloom Filters), có thể tốn thêm CPU cho việc đối chiếu phiên bản MVCC. Chỉ nêu mức độ khi có số đo.*

---

## 2. Vận dụng Nhận xét 2: Định nghĩa chuẩn xác Số Node TiKV, Replica và Quorum

### Lỗi thường gặp:
> *"Nhóm chạy thử nghiệm với 1 node TiKV và thiết lập 3 bản sao để kiểm tra khả năng chịu lỗi."* (Sai logic phân tán cơ bản).

### Cách viết chuẩn học thuật:
> *"Để kiểm chứng cơ chế đồng thuận phân tán Multi-Raft và bóc tách chi phí sao chép dữ liệu, nhóm triển khai cụm TiDB chuẩn hóa gồm đúng **3 node TiKV (3 container trên cùng một máy)** (`tikv1`, `tikv2`, `tikv3`) và phân định rõ hai chế độ thực nghiệm:*
> * **Cấu hình TiDB 3 bản sao (`RF=3` — Mặc định sản xuất):** Mỗi Region trên không gian Key-Value được nhân bản thành 3 peer (1 Leader và 2 Follower) phân bổ đều trên 3 node TiKV riêng biệt. Giao dịch tuân thủ nguyên tắc **Quorum $2/3$**: lệnh ghi chỉ được commit sau khi Leader nhận được xác nhận ghi Raft Log từ ít nhất một Follower. Cấu hình này bảo đảm tính sẵn sàng cao và khả năng tự phục hồi khi một node TiKV bất kỳ bị dừng (số đo giai đoạn 1: QPS bằng 0 trong 10 giây, về 90% sau 18,4 giây).*
> * **Cấu hình TiDB 1 bản sao (`RF=1` — Đối chứng phân tích):** Hệ thống vẫn duy trì 3 node TiKV hoạt động, nhưng bộ điều phối PD được cấu hình `replication.max-replicas = 1`. Khi đó, mỗi Region chỉ duy trì duy nhất 1 bản sao (Leader), quy tắc đồng thuận trở thành **Quorum $1/1$** và Region trên một TiKV bị dừng sẽ không truy cập được. 
> * **Mục đích khoa học:** Việc so sánh đối chiếu giữa `RF=3` và `RF=1` trên cùng một tải ghi cho phép nhóm định lượng **tổng chi phí nhân bản** (Raft log, fsync, CPU của Follower, tranh chấp đĩa chung), không phải riêng phần mạng.*

---

## 3. Vận dụng Nhận xét 3: Tập trung nghiệp vụ Logistics & Tối giản Failover

### Nguyên tắc trình bày:
1. **Phần B.2 (Chi phí đọc):** Phân tích sâu 3 câu truy vấn nghiệp vụ vận đơn cụ thể:
   * **Q1 (Point Get):** Tra cứu đơn hàng theo mã `tracking_code` (so `idx_code` unique, `idx_code_nonuniq` và covering `idx_code_cov`, để tách hiệu ứng `Point_Get` khỏi covering).
   * **Q2 (Range Query):** Tra cứu 20 đơn mới nhất của một shop trong 7 ngày (so sánh Index `(sender_id)` vs `(sender_id, created_at)` vs covering `(sender_id, created_at, status, cod_amount)`). Đây là bằng chứng chính cho covering.
   * **Q3 (Aggregate Query):** Đếm số lượng đơn theo từng trạng thái tại kho đích (Index `(dest_hub_id, status)`).
   * Báo cáo đầy đủ: Kế hoạch thực thi (`EXPLAIN ANALYZE`), số lượng cop task, số RPC, `rpc_time`, độ trễ trung vị, p95, p99 và dung lượng index.
2. **Phần A.3 (Demo vận hành):** Phần thử nghiệm đánh sập node (Failover/Chaos Test) chỉ trình bày gọn gàng trong 1 trang như một minh chứng cho cơ chế Multi-Raft của Phần A, không chiếm dung lượng chính của Phần B, tránh làm loãng trọng tâm nghiên cứu về chi phí chỉ mục phụ.
