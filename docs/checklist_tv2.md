# Checklist công việc TV2 — TiDB và MySQL

**Máy M2 · hồ sơ XS · 1 triệu vận đơn · 18–27/11/2026**  
Bạn phụ trách môi trường dùng chung, thực nghiệm chi phí ghi RQ4, phần cài đặt A.3 và báo cáo B.3. Khi hoàn thành một đầu việc, đổi `- [ ]` thành `- [x]` ở đúng dòng đó.

## 18/11 · Task 1 và Task 4 — Chuẩn bị repo và môi trường

- [x] Chuẩn bị khung repo chung với `pyproject.toml`, `.gitignore` và `bench/__init__.py`.
- [x] Viết `bench/config.py` cho TiDB (cổng 4000) và MySQL (cổng 3306), cùng dùng database `logistics` và cho phép nạp file cục bộ. Đọc `MACHINE_ID` và `PROFILE` từ môi trường.
- [x] Chạy đạt `tests/test_config.py` cho cấu hình kết nối hai hệ.
- [x] Cấu hình Docker Compose cho TiDB v8.5.5 và MySQL 8.4.11 theo hồ sơ M/S ở Phụ lục A. Với hồ sơ M, mỗi hệ được cấp 6 CPU, mỗi TiKV có 800 MiB block cache, MySQL có buffer pool 2.400 MiB và sysbench có 3 CPU. Đặt `innodb_flush_log_at_trx_commit=1` và tắt binlog của MySQL.
- [x] Viết và kiểm tra `scripts/use_engine.sh`. Khi hệ kia đang chạy, script phải báo lỗi. Với `--switch`, script dừng hệ kia, bật hệ được chọn và chờ `SELECT 1` thành công.
- [x] Đẩy khung repo, Compose và script chuyển hệ lên repo chung để TV1 và TV3 dùng. Mốc kế hoạch là **trước 12h ngày 18/11**.
- [x] Dựng môi trường trên M2, xác nhận đủ 3 TiKV store ở trạng thái `Up` và kết nối được MySQL sau khi chuyển hệ.
- [x] Thêm hồ sơ XS cho cả ba máy (TiDB 4 CPU / 5,5 GiB, MySQL 4 CPU / 2 GiB) và lệnh `python -m bench.cli check`, `team_hash=fa4c12cdf33a`.
- [ ] Điền dòng M2 trong Bảng A.3.1 với CPU, RAM, ổ dữ liệu Docker, hệ điều hành, phiên bản Docker, tài nguyên WSL2 và hồ sơ thực tế.

## 19/11 · Task 4 — Nạp và xác minh dữ liệu

- [x] Viết `connect`, `analyze` và `checksum` trong `bench/db.py`. Checksum trả về cả `COUNT(*)` và `SUM(cod_amount)`.
- [x] Viết `engine_settings` để lấy phiên bản, mã máy, hồ sơ và các giá trị thực tế của từng hệ (block cache và số bản sao của TiDB, buffer pool của MySQL). Chạy đạt `tests/test_db_offline.py`.
- [x] Viết `scripts/load.sh` dùng bộ sinh dữ liệu và schema của TV1 để tạo bảng, nạp file bằng `LOAD DATA LOCAL INFILE`, chạy `ANALYZE TABLE` và in checksum.
- [x] Nạp cùng bộ **1.000.000 dòng**, seed `20261116`, lần lượt vào TiDB và MySQL trên M2. Kiểm tra số dòng và tổng `cod_amount` khớp giữa hai hệ.
- [ ] Đối chiếu checksum và `team_hash` của M2 với TV1 và TV3. Giá trị chuẩn: 1 triệu dòng `sum_cod=5000968738439`, 3 triệu dòng `sum_cod=15001281300461`.

## 19–20/11 · Task 10 — Viết công cụ và chạy thử RQ4

- [x] Viết `sysbench/shipments_write.lua` cho W1 (chèn vận đơn mới) và W2 (cập nhật `status`, `updated_at` theo một `id` đã tồn tại).
- [x] Viết `bench/resources.py` để lấy mẫu CPU, RAM và byte đọc/ghi của container mỗi 2 giây. Chạy đạt `tests/test_resources.py` cho phần đọc số liệu từ Docker.
- [x] Viết `scripts/rq4_write.sh` để chọn bộ index, số luồng, tải ghi và số bản sao, chạy sysbench rồi ghi từng lượt vào `results/rq4.csv`. Khôi phục TiDB về 3 bản sao khi script thoát hoặc bị ngắt và xác nhận số peer thực tế.
- [x] Chạy thử **10 giây** trên M2. Mở CSV để kiểm tra TPS, p95, p99, byte ghi, dung lượng bảng/index, CPU sysbench và cấu hình thực tế của lượt chạy.
- [x] Kiểm tra CPU sysbench để xác định bộ sinh tải có bị nghẽn. Sau lượt thử với 1 bản sao, xác nhận CSV ghi đúng `max_replicas=1` và `SHOW CONFIG` trả về 3 khi script kết thúc.

## 21–24/11 · Chạy chính thức, kiểm tra CSV và vẽ biểu đồ

Thiết kế cuối cùng là **84 lượt**, 64 luồng, hồ sơ XS, 1 triệu dòng, **60 giây × 3 vòng**, hai tải W1 và W2, mỗi lúc chỉ bật một hệ. Bỏ mức 16 luồng vì MySQL nhảy giữa các trạng thái group commit; nguyên nhân chưa được chứng minh.

| Cấu hình | Bộ index | Số lượt |
|---|---|---|
| MySQL | 0, 1, 3, 5, `sender_created`, `sender_cov` | 36 |
| TiDB C3 (3 TiKV, 3 bản sao) | 0, 1, 3, 5, `sender_created`, `sender_cov` | 36 |
| TiDB C1 (3 TiKV, 1 bản sao) | 0, 5 | 12 |

- [x] **24/11 · MySQL** — 36 lượt.
- [x] **24/11 · TiDB C3** — 36 lượt.
- [x] **24/11 · TiDB C1** — 12 lượt.
- [x] Rà `results/rq4_official.csv`: 84 dòng, mỗi tổ hợp đủ 3 lượt, mọi lượt có `settled=1`. Không bỏ lượt nào.
- [x] Tính byte ghi trên mỗi giao dịch và phần trăm thay đổi TPS so với mốc của cùng hệ trong `results/rq4_official_summary.csv`.
- [x] Xuất `results/fig/rq4_tps_vs_indexes.png`.
- [x] Thử bỏ 6 lượt bị nhiễu (5 C3, 1 C1): hướng kết luận không đổi.

Code RQ1 cho TV1 và TV3:

- [x] Viết `experiments/rq1_covering.py`, `experiments/rq1_summary.py`, `scripts/rq1_official.ps1` và hướng dẫn trong README. Chạy thử 170/170 lượt ở 1 triệu dòng trên M2 (không dùng cho báo cáo).
- [ ] Hỗ trợ TV1 chạy thử ở 3 triệu dòng và TV3 chạy ở 1 triệu dòng. Chưa có kết quả RQ1 chính thức.

## 24/11 · Viết A.3 và B.3

- [ ] Hoàn thiện **Bảng A.3.1** bằng thông tin M1, M2, M3 do mỗi thành viên cung cấp.
- [ ] Viết **A.3 phần cài đặt**. Đính kèm kết quả `SELECT tidb_version()`, trạng thái 3 TiKV store, ảnh Dashboard (Topology và Key Visualizer) và `SHOW CREATE TABLE shipments` của hai hệ. TV3 phụ trách phần demo A.3.
- [ ] Chạy demo chức năng cơ bản trên hai hệ bằng `scripts/demo_co_ban.py` và viết `a3_demo_co_ban.tex`.
- [ ] Viết **vận hành cụm** (`a3_van_hanh.tex`), **phương pháp và kịch bản** của Chương 4 (`p2_phuong_phap.tex`) và **Phụ lục C**.
- [ ] Viết **B.3** trong `report/sections/b3_chi_phi_ghi.tex` từ số đo M2, thay phần `sbtest1` cũ; TV1 nối bằng `\input{}`. Nêu mức giảm TPS khi tăng số index, đối chiếu W1 với W2, TiDB C1 với C3, và covering (`sender_cov`) với `sender_created`. Dùng p95/p99, byte ghi trên mỗi giao dịch và CPU sysbench để giải thích kết quả. Ghi rõ ba TiKV dùng chung ổ đĩa khi diễn giải chi phí sao chép.
- [ ] Trong B.3, nêu đủ các điểm bất thường: 5 lượt C3 vòng 2 chạy khi `tikv1` giữ 0 leader; 1 lượt C1 trùng lệnh chẩn đoán; 3 lượt C1 đo lại; 1 dòng C3 ghi `tikv_stores=2`; leader C1 lệch; MySQL `sender_cov` dao động 7.597–12.647 TPS; C3 cập nhật 1 index +6% nằm trong mức nhiễu; dung lượng index TiDB là ước tính; bỏ mức 16 luồng; TiDB dùng tới 1.156/1.280 MiB; TiKV bận nhất ở C3 thường dùng 0,7–0,8 trên 0,8 CPU, MySQL khoảng 3,9 trên 4 CPU.
- [ ] Viết A.3 theo hồ sơ XS. Từ nhánh `tv2/teacher-feedback` chỉ lấy `report/` (ảnh Dashboard, định nghĩa bản sao và quorum), không merge cả nhánh; sửa RF=3/RF=1 thành C3/C1.
- [ ] Thay hoặc bỏ 4 hình còn thiếu trong `report/figures/` và biên dịch XeLaTeX (M2 chưa cài, dùng Overleaf hoặc máy TV1).
- [ ] Bàn giao phần cài đặt A.3, mục B.3, CSV và biểu đồ RQ4 cho trưởng nhóm ghép báo cáo.

## 25–27/11 · Đọc chéo và thuyết trình

- [ ] **25/11** — Đọc chéo B.2 và gửi góp ý cho TV3.
- [ ] **26/11** — Đối chiếu từng con số trong B.1 với CSV của TV1.
- [ ] **26/11** — Đối chiếu từng con số trong B.2 với CSV của TV3.
- [ ] **27/11** — Tập thuyết trình cùng nhóm.

Phân công, lịch và các điều chỉnh lấy từ [kế hoạch 1,5 tuần, 3 máy](ke_hoach_do_an_tidb_vs_mysql_1.md). Chi tiết triển khai nằm ở Task 1, 4 và 10 của [tài liệu kỹ thuật](2026-11-16-tidb-indexing-van-don.vi.md).
