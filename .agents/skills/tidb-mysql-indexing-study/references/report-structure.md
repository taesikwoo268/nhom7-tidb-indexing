# Cấu trúc báo cáo đề xuất — giữ định hướng A/B của giảng viên

> Đây là cách tổ chức lại nội dung từ kế hoạch nhóm, không phải template chính thức của trường. Nếu giảng viên đã có mẫu hoặc yêu cầu số chương khác, ưu tiên mẫu đó nhưng giữ logic nghiên cứu A/B.

## Phần mở đầu

- Bìa, nhận xét/lời cảm ơn nếu mẫu yêu cầu.
- Tóm tắt và từ khóa.
- Mục lục, danh mục hình/bảng, danh mục từ viết tắt.
- Giới thiệu đề tài ngắn: vấn đề, mục tiêu, phương pháp và bố cục.

## PHẦN A — Tìm hiểu DBMS từ đặc trưng dữ liệu đến kiến trúc và triển khai (~50%)

### A.1. Bài toán dữ liệu vận đơn và lý do chọn TiDB

- Bối cảnh logistics thương mại điện tử.
- Transactional/read/query/statistical workload.
- Đặc trưng quan hệ của `shipments`.
- So sánh lớp giải pháp RDBMS truyền thống, NoSQL/wide-column và NewSQL ở mức có nguồn; tránh khẳng định quá rộng hoặc dựng strawman.
- Lý do chọn TiDB và vai trò MySQL làm baseline.

### A.2. Kiến trúc TiDB và các cơ chế liên quan

1. SQL/compute layer TiDB và storage layer TiKV.
2. Relational-to-KV mapping, row handle, clustered/nonclustered primary key.
3. RocksDB/LSM-Tree, WAL, MemTable, SST, compaction và trade-offs.
4. Region, Raft replication, PD/TSO và transaction protocol/isolation semantics.

Chỉ giữ những khái niệm phục vụ giải thích RQ1–RQ4. Phân biệt cơ chế chính thức với cấu hình thực nghiệm.

### A.3. Cài đặt, vận hành và demo chịu lỗi

- Docker Compose topology và giới hạn tài nguyên.
- Cấu hình TiDB / MySQL.
- Nạp dữ liệu và xác minh tính nhất quán.
- Demo TiDB Dashboard và thao tác SQL cơ bản.
- Chaos demo: phương pháp, timeline, log, QPS, lỗi và checksum; kết luận giới hạn ở single-host container-level fault.

## PHẦN B — Mô hình và thực nghiệm chi phí secondary index (~50%)

### B.1. Mô hình lý thuyết và đo dung lượng

- DDL 14 cột, giả định payload và cách đo byte trung bình từ generator.
- Công thức raw table và index entry.
- Mô hình InnoDB B+Tree.
- Mô hình TiKV/RocksDB KV/LSM.
- Vai trò PK/row handle, nén, compaction, page utilization và replication.
- Đối chiếu estimate, engine statistics và physical disk measurement; sai số và sensitivity analysis.

### B.2. Read workload — RQ1, RQ2, RQ3

- Môi trường, query set, index sets, warm-up/sample/repeats.
- RQ1: covering vs non-covering và execution plan.
- RQ2: selectivity crossover và optimizer path.
- RQ3: clustered/nonclustered PK variants, lookup và secondary-index footprint.
- So sánh theo từng case; không gom thành một kết luận tốc độ chung.

### B.3. Write workload — RQ4 và đánh đổi

- Sysbench workloads insert/update.
- 0/1/3/5 indexes, 16/64 threads, TiDB RF=3/1.
- TPS, p95/p99, disk writes, CPU/RAM, final storage.
- Phân tích write penalty và replication overhead.
- Đánh đổi giữa read benefit, write cost, storage, replication và operational complexity.

## Kết luận và hướng phát triển

- Trả lời riêng từng RQ bằng kết quả đã kiểm chứng.
- Tóm tắt những nội dung đạt/chưa đạt so với mục tiêu.
- Hạn chế: single host, quy mô, cache, data distribution, số lượt chạy, topology và các assumption storage model.
- Hướng phát triển dựa trên giới hạn đã phát hiện.

## Phụ lục

- DDL đầy đủ, câu SQL benchmark, lệnh chạy.
- Cấu hình Docker không chứa secret.
- Test cases và schema output CSV.
- Bảng số liệu bổ sung, log trích đoạn, ảnh Dashboard.
