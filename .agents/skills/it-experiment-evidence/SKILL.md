---
name: it-experiment-evidence
description: Lập kế hoạch kiểm thử, thiết kế test case, thu thập bằng chứng và viết phần thực nghiệm/đánh giá cho đồ án IT. Dùng khi cần báo cáo chức năng, hiệu năng, độ chính xác, độ tin cậy, khả năng mở rộng hoặc kết quả benchmark.
---

# IT Experiment & Evidence

## Nguyên tắc cốt lõi

Không có kết quả nếu chưa có phép đo hoặc bằng chứng. Không được tự tạo số liệu minh họa rồi trình bày như kết quả thật. Nếu chỉ lập kế hoạch, ghi rõ `KẾ HOẠCH — CHƯA THỰC HIỆN`.

## Bước 1 — Chọn câu hỏi đánh giá

Chuyển từng mục tiêu thành câu hỏi có thể kiểm tra. Ví dụ:

- Chức năng: thao tác có trả về kết quả đúng trong các trường hợp hợp lệ/không hợp lệ không?
- Hiệu năng: p50/p95 latency, throughput hoặc thời gian xử lý được đo trong điều kiện nào?
- Mô hình ML: metric nào phù hợp với task/dataset, train/test split và ngưỡng dự đoán là gì?
- Khả năng mở rộng: tải tăng thì throughput, latency, error rate và resource usage thay đổi ra sao?
- Độ tin cậy: hệ thống xử lý lỗi, retry, timeout, mất kết nối như thế nào?

Không chọn metric chỉ vì phổ biến; giải thích tại sao metric đó đo được mục tiêu.

## Bước 2 — Thiết kế phép thử

Với mỗi thử nghiệm ghi:

- ID, mục tiêu, giả thuyết/câu hỏi.
- Phiên bản commit/build, cấu hình phần cứng/phần mềm.
- Dataset/input, nguồn gốc, kích thước, cách chia và tiền xử lý nếu có.
- Công cụ, lệnh chạy, tham số, số lần lặp.
- Baseline/đối chứng và biến được giữ cố định.
- Metric, đơn vị, cách tính.
- Tiêu chí pass/fail hoặc tiêu chí so sánh.
- Rủi ro sai lệch và giới hạn.

## Bước 3 — Thực hiện an toàn

- Chỉ chạy lệnh test/benchmark an toàn, trong phạm vi người dùng cho phép.
- Không chạy tải lớn, stress test, migration, deploy, hoặc bài test gây chi phí/rủi ro nếu chưa được cho phép.
- Không gửi dữ liệu nhạy cảm lên dịch vụ bên ngoài.
- Nếu cần chạy chương trình, đọc README và script trước; kiểm tra script không có hành vi phá hủy.
- Lưu raw output và cấu hình thử nghiệm để tái lập.

## Bước 4 — Ghi kết quả

Tách riêng:

- **Input/thiết lập**: những gì đã cấu hình.
- **Observation**: đầu ra thực tế nhìn thấy.
- **Metric**: con số được tính từ output.
- **Interpretation**: ý nghĩa của kết quả.
- **Limitation**: điều phép thử chưa chứng minh.

Không suy rộng kết quả một máy/ít lượt chạy thành khả năng của toàn hệ thống. Ghi rõ số mẫu, số vòng lặp, môi trường và thời điểm thử.

## Gợi ý metric theo loại dự án

| Loại dự án | Metric/thước đo có thể cân nhắc | Điều phải mô tả |
|---|---|---|
| Web/API | latency p50/p95, throughput, error rate | tải, concurrency, payload, môi trường |
| Database | thời gian query, throughput, transaction success | schema, index, dataset, cache state |
| ML/CV/NLP | precision, recall, F1, mAP, IoU, MAE... | dataset, label, split, threshold, metric phù hợp task |
| Distributed/cloud | availability trong khoảng đo, recovery time, resource usage | topology, failure injection, số lần lặp |
| Image/video processing | thời gian xử lý, memory, output quality, file size | định dạng, độ phân giải, codec, cấu hình |
| Security | test cases, findings, severity, reproduction | phạm vi được phép, công cụ, giới hạn kiểm tra |

Đây là gợi ý, không phải yêu cầu phải có tất cả các metric. Không dùng accuracy cho mọi bài toán phân loại nếu dữ liệu mất cân bằng mà không giải thích.

## Bảng kết quả

Dùng mẫu trong `.agents/skills/vietnamese-it-project-report/references/test-results-template.md` (hoặc `resources/test-results-template.md`). Với kết quả chưa chạy, để `Chưa thực hiện`; không điền số giả để lấp bảng.

## Viết phần đánh giá

1. Nhắc lại tiêu chí đánh giá.
2. Mô tả môi trường và quy trình.
3. Trình bày kết quả bằng bảng/biểu đồ có đơn vị.
4. Phân tích xu hướng và nguyên nhân có bằng chứng.
5. So sánh baseline chỉ khi phép đo tương đương.
6. Nêu giới hạn và đe dọa tính hợp lệ (dataset bias, sample size nhỏ, môi trường không đại diện, cấu hình khác nhau...).
7. Kết luận theo từng mục tiêu, không khái quát vượt quá dữ liệu.

## Đầu ra

Lưu kế hoạch, test case, log/kết quả đã được phép lưu và bảng kết quả dưới `docs/report/experiments/`. Chỉ đưa vào báo cáo kết quả đã xác minh. Nếu kết quả đến từ người dùng, đánh dấu `USER-PROVIDED` cho đến khi có thể kiểm tra lại.

## Protocol bổ sung cho TiDB–MySQL indexing study

Đọc `.agents/skills/tidb-mysql-indexing-study/references/benchmark-protocol.md` và `.agents/skills/tidb-mysql-indexing-study/references/research-questions.md` trước khi tạo test plan. Yêu cầu tối thiểu:

- Không chạy hai DBMS đồng thời trên host 16GB/8 cores theo kế hoạch.
- Cùng dataset source, seed, schema semantics, query và parameters; lưu SHA-256 dataset.
- Ghi exact versions, configs, cache state, index set, ANALYZE, warm-up, repeats và run ID.
- RQ1 dùng 200 parameter samples theo kế hoạch; RQ2 dùng 10 selectivities × 20 ranges × 3 modes; RQ4 ghi đúng index sets, concurrency, mode, RF và duration.
- `docker stats` block I/O là counter tích lũy: tính delta trong cửa sổ run.
- Nếu sysbench insert dùng sender_id uniform thay vì Zipf, ghi đây là sai khác workload.
- Single-host Docker chaos test không chứng minh multi-host/AZ HA.
- Không gọi bytes written là Write Amplification nếu chưa xác định mẫu số bytes logic trong cùng khoảng đo.
