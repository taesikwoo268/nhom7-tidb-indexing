# Ma trận câu hỏi nghiên cứu RQ1–RQ4

> Giữ nguyên trọng tâm của kế hoạch nhóm. Mọi kết quả cuối cùng phải được điền từ `results/*.csv`, log, EXPLAIN hoặc evidence thực tế.

| RQ | Câu hỏi | Biến độc lập | Đầu ra cần báo cáo | Bằng chứng chính |
|---|---|---|---|---|
| RQ1 | Covering index và non-covering index ảnh hưởng thế nào đến chi phí truy vấn đọc trên TiDB và MySQL? | Index set/coverage, truy vấn, engine | p50/p95/p99, IQR, access operator, rows examined; TiDB cop_tasks/rpc_num nếu có | `rq1.csv`, SQL, EXPLAIN ANALYZE, execution info |
| RQ2 | Độ chọn lọc của điều kiện COD làm thay đổi điểm hòa vốn giữa index range scan và table scan ra sao? | Selectivity, mode force_index/force_scan/optimizer | Latency, rows returned, access operator, crossover thực nghiệm và ngưỡng optimizer đổi plan | `rq2.csv`, SQL, EXPLAIN, thống kê dữ liệu |
| RQ3 | Biến thể clustered/nonclustered primary key ảnh hưởng thế nào đến lookup, dung lượng secondary index và hiệu năng liên quan? | `bigint_clustered`, `bigint_nonclustered`, `code_clustered` | Query latency, access operator, dung lượng `idx_sender_created`; `w1_insert_tps` chỉ là phép đo bổ sung theo kế hoạch | `rq3.csv`, DDL, EXPLAIN, size measurements |
| RQ4 | Số lượng secondary index, mức đồng thời và replication factor ảnh hưởng thế nào đến chi phí ghi? | 0/1/3/5 indexes, 16/64 threads, insert/update; TiDB RF=1/3 | TPS, p95/p99, block bytes written/Write Amplification, table/index size | `rq4.csv`, sysbench output, Docker stats, engine settings |

## Hướng dẫn viết kết luận từng RQ

Mỗi RQ cần có: (1) câu hỏi và giả thuyết; (2) truy vấn/workload; (3) biến độc lập và biến kiểm soát; (4) metric; (5) kết quả quan sát; (6) giải thích theo execution plan/kiến trúc; (7) giới hạn.

Không dùng kết luận chung như “TiDB nhanh hơn”. Phải nêu rõ loại workload, cấu hình, dataset, chỉ mục, concurrency và metric mà phát hiện áp dụng.

## RQ1 — các case theo kế hoạch triển khai

- `q1_single_full`, `q1_single_cov`, `q1_covidx_cov`.
- `q2_sender`, `q2_sender_created`, `q2_covering`.
- `q3_hub`, `q3_hub_status`.

Xác minh mỗi case dùng đúng DDL/index và query; ghi access operator thật. Không đảm bảo trước rằng một case bắt buộc phải dùng đúng operator nếu optimizer khác đi.

## RQ2 — cách đọc crossover

Phân biệt hai điểm:

1. **Performance crossover:** vùng selectivity nơi latency đo bằng forced-index và forced-scan giao nhau.
2. **Optimizer crossover:** selectivity đầu tiên mà optimizer tự chọn chuyển access path.

Hai điểm có thể khác nhau; không gộp chúng làm một. Chỉ nội suy nếu dữ liệu thực sự có điểm đổi dấu và phạm vi selectivity đủ bao quanh crossover.

## RQ3 — biến thể primary key

- TiDB: 3 biến thể theo kế hoạch.
- MySQL: 2 biến thể; không tạo cấu hình `bigint_nonclustered` nếu kế hoạch không hỗ trợ.
- Nếu kết quả không giống dự đoán, coi đó là phát hiện; không sửa số liệu để khớp kỳ vọng.
- Cẩn thận khi diễn giải kích thước secondary index: MySQL InnoDB secondary index carries primary key columns; TiDB row handle/storage representation phụ thuộc dạng clustered/nonclustered.

## RQ4 — write penalty

- Bộ index: 0, 1, 3, 5.
- Threads: 16, 64.
- Workload: insert và update.
- TiDB thêm RF=1 và RF=3; RF=1 là ablation/định lượng tác động replica, không phải cấu hình HA tương đương RF=3.
- Script insert có thể đơn giản hóa phân phối sender_id sang uniform; nếu vậy phải ghi rõ lệch so với generator Zipf ở bộ dữ liệu ban đầu.
