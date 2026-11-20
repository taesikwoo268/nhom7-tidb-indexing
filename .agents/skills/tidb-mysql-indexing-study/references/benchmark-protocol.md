# Benchmark Protocol — Quy trình đo có thể tái lập

## 1. Cấu hình cần đóng băng và ghi trong mỗi run

- Engine, exact version/image digest nếu có.
- OS, kernel, Docker Engine/Compose version.
- CPU model/core count, RAM host, disk type, filesystem và free space.
- Container CPU/memory limits và DB cache settings.
- TiDB PD/TiDB/TiKV topology, TiKV count, RF, Region settings.
- MySQL page size, buffer pool, durability settings, row format, charset/collation.
- Dataset size, TSV/CSV SHA-256, generator version/commit, seed, checksum.
- DDL, PK variant, index set, SQL text, hints, bound parameters.
- Cache state, `ANALYZE TABLE`/statistics state, warm-up count, repeats, run duration.

## 2. Fair comparison

1. Chỉ bật một engine tại một thời điểm như kế hoạch yêu cầu.
2. Dùng cùng file dữ liệu nguồn, cùng seed và xác minh file SHA-256; `COUNT(*)` và `SUM(cod_amount)` là kiểm tra bổ sung chứ không phải checksum tuyệt đối.
3. Cùng câu SQL/ngữ nghĩa truy vấn; nếu cú pháp/hint khác nhau, ghi rõ.
4. Xác minh engine thực sự dùng access path mong muốn; không tin rằng hint đã được thực thi nếu EXPLAIN không chứng minh.
5. Ghi mọi khác biệt về kiến trúc, cache, replication, concurrency và durability. Không gọi hai cơ chế cache là hoàn toàn tương đương chỉ vì tổng dung lượng danh nghĩa tương đương.
6. Sau mỗi lần đổi RF, xác minh cấu hình thực tế và bảo đảm khôi phục RF=3 theo kế hoạch trước các phép đo RF=3.
7. Ghi lại thứ tự chạy và thời gian; nếu có thể, lặp thứ tự engine theo thiết kế hoán đổi để giảm ảnh hưởng nhiệt độ/cache/host load.

## 3. Quy trình một benchmark run

1. Chọn đúng engine; xác nhận engine kia đã dừng.
2. Ghi snapshot cấu hình và trạng thái host/container.
3. Kiểm tra dataset, row count, checksum và index set.
4. Chạy `ANALYZE TABLE` khi protocol yêu cầu.
5. Chạy warm-up 50 lần/đúng số query theo kế hoạch; ghi rõ đây là chế độ warm-cache.
6. Chạy ít nhất 5 lần lặp như kế hoạch, lưu raw latency hoặc output đầy đủ.
7. Tính p50, p95, p99 và IQR; nêu rõ percentile method và population được tính (toàn bộ truy vấn hay median từng run).
8. Lưu `EXPLAIN ANALYZE`, engine settings, Docker stats và log tương ứng.
9. Kiểm tra kết quả hợp lệ trước khi đưa vào summary CSV.

## 4. RQ-specific protocol

### RQ1

- Lấy mẫu 200 parameter sets từ dữ liệu đã nạp (seed cố định).
- Mỗi case: tạo đúng index set, ANALYZE, warm-up, chạy 5 repeats trên cùng bộ tham số.
- Lưu query, parameters/sample identifiers (không có PII), EXPLAIN và TiDB execution info.
- Phân biệt covering vs non-covering bằng danh sách cột thực sự được đọc và index/PK extension, không chỉ dựa vào tên case.

### RQ2

- Dùng selectivity theo danh sách kế hoạch: `0.00001, 0.0001, 0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50`.
- Mỗi mức dùng 20 COD ranges; 3 mode: force_index, force_scan, optimizer; repeats=5.
- Dừng nếu forced index không dùng index hoặc forced scan không tạo table scan theo quy ước parser.
- Tính riêng performance crossover và optimizer crossover.
- Kiểm tra thống kê `cod_amount`, phân phối và số dòng trả về; không suy luận selectivity chỉ từ độ rộng khoảng nếu dữ liệu không uniform.

### RQ3

- Tạo từng variant từ cùng dataset gốc; kiểm tra row count/checksum trước khi đo.
- Lưu DDL thực tế cho từng engine/variant.
- So sánh point lookup, truy vấn theo secondary index, index size; insert TPS là metric bổ sung nếu được triển khai đúng script.
- Không so sánh variant MySQL không tồn tại hoặc không tương thích.

### RQ4

- Kết hợp: 0/1/3/5 indexes × 16/64 threads × insert/update; TiDB thêm RF 3/1.
- Theo kế hoạch, sysbench run 120 giây và báo cáo interval 1 giây; ghi thời lượng thực tế nếu rút ngắn khi smoke test.
- Đo TPS, p95/p99, disk bytes written, resource usage và size cuối cùng.
- Docker block I/O là counter cộng dồn: tính delta giữa đầu/cuối run, không báo tổng counter như lượng ghi của workload.
- Định nghĩa Write Amplification rõ ràng: bytes thực ghi / bytes dữ liệu logic ứng dụng tạo ra trong cùng khoảng đo; nếu không đo được mẫu số chính xác, chỉ báo cáo bytes written thay vì gọi WA.

### Chaos demo A.3

- Kịch bản dự kiến: tải đọc 8 threads/180s; kill một TiKV container tại 60s, start lại tại 150s; ghi QPS/log và checksum trước/sau.
- Chụp hình dashboard nếu có thật; không tạo ảnh giả lập.
- Đo thời gian mất dịch vụ, suy giảm QPS, phục hồi và lỗi truy vấn thực tế.
- Kết luận chỉ trong phạm vi một container/node process trong single-host Docker lab.

## 5. Chất lượng dữ liệu và lưu trữ bằng chứng

- Lưu raw output bất biến; chỉ xử lý trên bản copy.
- Mỗi run có `run_id`, timestamp, engine, version, dataset hash, config snapshot, command, exit code và artifact links.
- Không xoá/ghi đè kết quả gốc khi rerun; tạo run mới.
- Phân biệt raw CSV/log, validated CSV, aggregate summary và chart.
- Chú thích mọi lần chạy fail, aborted, warm-up, smoke test và pilot 1M; không trộn chúng với kết quả 10M chính thức.
