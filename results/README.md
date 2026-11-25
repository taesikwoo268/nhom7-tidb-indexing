# Kết quả thực nghiệm

| Vị trí | Nội dung |
|---|---|
| `raw/<run_id>/` | Đầu ra gốc của lần chạy: log, cấu hình đã áp dụng, EXPLAIN ANALYZE và mẫu tài nguyên. Git bỏ qua các tệp này. |
| `runs/<run_id>.md` | Máy, hồ sơ M/S, engine và phiên bản, commit mã, dataset và SHA-256, schema/index, lệnh chạy, thời lượng, số lần lặp, trạng thái và vị trí bằng chứng thô. |
| `b1_storage.csv`, `rq1.csv`, `rq2.csv`, `rq3.csv`, `rq4.csv` | Tên tệp tổng hợp theo kế hoạch. Tạo khi có kết quả tương ứng và giữ `run_id`, `machine`, `profile` để truy về lần chạy. RQ3 chỉ phát sinh nếu nhóm thực hiện phần tùy chọn. |
| `rq4_official.csv` | RQ4 lần đo đầu ngày 24/11/2026: MySQL `utf8mb4_unicode_ci`, TiDB C3 và C1. |
| `rq4_official_mysql_bin.csv` | 36 lượt MySQL đo lại ngày 25/11/2026 với `utf8mb4_bin`. |
| `rq4_official_bin.csv` | Bộ dùng cho báo cáo: 36 lượt MySQL `utf8mb4_bin` ghép với 48 lượt TiDB của `rq4_official.csv`. |
| `fig/` | Biểu đồ tạo từ các CSV tổng hợp. Tệp hình chọn để đưa vào bản LaTeX đặt tại `report/figures/`. |

Đặt `run_id` theo dạng `<ngày-giờ-UTC>_<máy>_<phần>_<engine>_<lượt>`, ví dụ `20261118T080000Z_M3_rq1_tidb_01`. Mỗi lần chạy lại dùng ID mới. Khi bàn giao hồ sơ có log thô lưu ngoài Git, ghi vị trí mà thành viên khác có thể truy cập.

Khi tổng hợp, chỉ đối chiếu hai engine trong cùng hồ sơ và trên cùng máy cho một phép đo. Số liệu giai đoạn `sbtest1` dùng cho A.3/B.0 cần ghi rõ nguồn và trạng thái xác minh trước khi đưa vào báo cáo `shipments`.
