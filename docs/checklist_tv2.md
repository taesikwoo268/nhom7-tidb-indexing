# Checklist công việc TV2 — TiDB và MySQL

**Máy M2 · 1 triệu vận đơn · 18–27/11/2026**  
Bạn phụ trách môi trường dùng chung, thực nghiệm chi phí ghi RQ4, phần cài đặt A.3 và báo cáo B.3. Khi hoàn thành một đầu việc, đổi `- [ ]` thành `- [x]` ở đúng dòng đó.

## 18/11 · Task 1 và Task 4 — Chuẩn bị repo và môi trường

- [x] Chuẩn bị khung repo chung với `pyproject.toml`, `.gitignore` và `bench/__init__.py`.
- [x] Viết `bench/config.py` cho TiDB (cổng 4000) và MySQL (cổng 3306), cùng dùng database `logistics` và cho phép nạp file cục bộ. Đọc `MACHINE_ID` và `PROFILE` từ môi trường.
- [x] Chạy đạt `tests/test_config.py` cho cấu hình kết nối hai hệ.
- [x] Cấu hình Docker Compose cho TiDB v8.5.5 và MySQL 8.4.11 theo hồ sơ M/S ở Phụ lục A. Với hồ sơ M, mỗi hệ được cấp 6 CPU, mỗi TiKV có 800 MiB block cache, MySQL có buffer pool 2.400 MiB và sysbench có 3 CPU. Đặt `innodb_flush_log_at_trx_commit=1` và tắt binlog của MySQL.
- [x] Viết và kiểm tra `scripts/use_engine.sh`. Khi hệ kia đang chạy, script phải báo lỗi. Với `--switch`, script dừng hệ kia, bật hệ được chọn và chờ `SELECT 1` thành công.
- [ ] Đẩy khung repo, Compose và script chuyển hệ lên repo chung để TV1 và TV3 dùng. Mốc kế hoạch là **trước 12h ngày 18/11**.
- [x] Dựng môi trường trên M2, xác nhận đủ 3 TiKV store ở trạng thái `Up` và kết nối được MySQL sau khi chuyển hệ.
- [ ] Điền dòng M2 trong Bảng A.3.1 với CPU, RAM, ổ dữ liệu Docker, hệ điều hành, phiên bản Docker, tài nguyên WSL2 và hồ sơ thực tế.

## 19/11 · Task 4 — Nạp và xác minh dữ liệu

- [x] Viết `connect`, `analyze` và `checksum` trong `bench/db.py`. Checksum trả về cả `COUNT(*)` và `SUM(cod_amount)`.
- [x] Viết `engine_settings` để lấy phiên bản, mã máy, hồ sơ và các giá trị thực tế của từng hệ (block cache và số bản sao của TiDB, buffer pool của MySQL). Chạy đạt `tests/test_db_offline.py`.
- [x] Viết `scripts/load.sh` dùng bộ sinh dữ liệu và schema của TV1 để tạo bảng, nạp file bằng `LOAD DATA LOCAL INFILE`, chạy `ANALYZE TABLE` và in checksum.
- [x] Nạp cùng bộ **1.000.000 dòng**, seed `20261116`, lần lượt vào TiDB và MySQL trên M2. Kiểm tra số dòng và tổng `cod_amount` khớp giữa hai hệ.
- [ ] Đối chiếu checksum của M2 với TV1 và TV3 để xác nhận ba máy dùng cùng dữ liệu.

## 19–20/11 · Task 10 — Viết công cụ và chạy thử RQ4

- [x] Viết `sysbench/shipments_write.lua` cho W1 (chèn vận đơn mới) và W2 (cập nhật `status`, `updated_at` theo một `id` đã tồn tại).
- [x] Viết `bench/resources.py` để lấy mẫu CPU, RAM và byte đọc/ghi của container mỗi 2 giây. Chạy đạt `tests/test_resources.py` cho phần đọc số liệu từ Docker.
- [x] Viết `scripts/rq4_write.sh` để chọn bộ index, số luồng, tải ghi và số bản sao, chạy sysbench rồi ghi từng lượt vào `results/rq4.csv`. Khôi phục TiDB về 3 bản sao khi script thoát hoặc bị ngắt và xác nhận số peer thực tế.
- [x] Chạy thử **10 giây** trên M2. Mở CSV để kiểm tra TPS, p95, p99, byte ghi, dung lượng bảng/index, CPU sysbench và cấu hình thực tế của lượt chạy.
- [x] Kiểm tra CPU sysbench để xác định bộ sinh tải có bị nghẽn. Sau lượt thử với 1 bản sao, xác nhận CSV ghi đúng `max_replicas=1` và `SHOW CONFIG` trả về 3 khi script kết thúc.

## 21–23/11 · Chạy chính thức, kiểm tra CSV và vẽ biểu đồ

Mỗi cấu hình hệ bên dưới có **16 tổ hợp** gồm 4 bộ index (0, 1, 3, 5) × 2 mức luồng (16, 64) × 2 tải (W1, W2). Mỗi tổ hợp chạy **60 giây × 3 lần**, tổng cộng **144 lượt đo** trên M2. Chỉ bật một hệ tại một thời điểm.

- [ ] **21/11 · MySQL** — Hoàn thành 48 lượt và lưu kết quả.
- [ ] **21/11 · TiDB 3 bản sao** — Hoàn thành 48 lượt và lưu kết quả.
- [ ] **21/11 · TiDB 1 bản sao** — Hoàn thành 48 lượt, lưu kết quả và xác nhận cụm trở về 3 bản sao.
- [ ] **22/11** — Rà `results/rq4.csv`, kiểm tra mỗi tổ hợp có đủ 3 lượt hợp lệ và chạy lại các lượt lỗi hoặc thiếu. Nếu còn thời gian, có thể tăng lên 5 lần lặp.
- [ ] **23/11** — Tính byte ghi trên mỗi giao dịch và phần trăm giảm TPS so với mốc 0 index của cùng hệ, số bản sao, tải ghi và số luồng.
- [ ] **23/11** — Xuất `results/fig/rq4_tps_vs_indexes.png` theo style chung của TV3. Mỗi ô biểu đồ ứng với một tải ghi và một mức luồng, mỗi đường ứng với một cấu hình hệ. Đối chiếu hình với CSV.

## 24/11 · Viết A.3 và B.3

- [ ] Hoàn thiện **Bảng A.3.1** bằng thông tin M1, M2, M3 do mỗi thành viên cung cấp.
- [ ] Viết **A.3 phần cài đặt**. Đính kèm kết quả `SELECT tidb_version()`, trạng thái 3 TiKV store, ảnh Dashboard (Topology và Key Visualizer) và `SHOW CREATE TABLE shipments` của hai hệ. TV3 phụ trách phần demo A.3.
- [ ] Viết **B.3** từ số đo M2. Nêu mức giảm TPS khi tăng số index, đối chiếu W1 với W2 và TiDB 1 với 3 bản sao. Dùng p95/p99, byte ghi trên mỗi giao dịch và CPU sysbench để giải thích kết quả. Ghi rõ ba TiKV dùng chung ổ đĩa khi diễn giải chi phí sao chép.
- [ ] Bàn giao phần cài đặt A.3, mục B.3, CSV và biểu đồ RQ4 cho trưởng nhóm ghép báo cáo.

## 25–27/11 · Đọc chéo và thuyết trình

- [ ] **25/11** — Đọc chéo B.2 và gửi góp ý cho TV3.
- [ ] **26/11** — Đối chiếu từng con số trong B.1 với CSV của TV1.
- [ ] **26/11** — Đối chiếu từng con số trong B.2 với CSV của TV3.
- [ ] **27/11** — Tập thuyết trình cùng nhóm.

Phân công, lịch và các điều chỉnh lấy từ [kế hoạch 1,5 tuần, 3 máy](ke_hoach_do_an_tidb_vs_mysql_1.md). Chi tiết triển khai nằm ở Task 1, 4 và 10 của [tài liệu kỹ thuật](2026-11-16-tidb-indexing-van-don.vi.md).
