# Checklist công việc TV2 — TiDB và MySQL

**Máy M2 · hồ sơ XS · 1 triệu vận đơn · 18–27/11/2026**  
Bạn phụ trách môi trường dùng chung, thực nghiệm chi phí ghi RQ4, toàn bộ A.3 (cài đặt, vận hành, demo), phương pháp của Chương 4 và báo cáo B.3. Cập nhật lần cuối: 25/11/2026. Khi hoàn thành một đầu việc, đổi `- [ ]` thành `- [x]` ở đúng dòng đó.

## 18/11 · Task 1 và Task 4 — Chuẩn bị repo và môi trường

- [x] Chuẩn bị khung repo chung với `pyproject.toml`, `.gitignore` và `bench/__init__.py`.
- [x] Viết `bench/config.py` cho TiDB (cổng 4000) và MySQL (cổng 3306), cùng dùng database `logistics` và cho phép nạp file cục bộ. Đọc `MACHINE_ID` và `PROFILE` từ môi trường.
- [x] Chạy đạt `tests/test_config.py` cho cấu hình kết nối hai hệ.
- [x] Cấu hình Docker Compose cho TiDB v8.5.5 và MySQL 8.4.11 theo hồ sơ M/S ở Phụ lục A. Với hồ sơ M, mỗi hệ được cấp 6 CPU, mỗi TiKV có 800 MiB block cache, MySQL có buffer pool 2.400 MiB và sysbench có 3 CPU. Đặt `innodb_flush_log_at_trx_commit=1` và tắt binlog của MySQL.
- [x] Viết và kiểm tra `scripts/use_engine.sh`. Khi hệ kia đang chạy, script phải báo lỗi. Với `--switch`, script dừng hệ kia, bật hệ được chọn và chờ `SELECT 1` thành công.
- [x] Đẩy khung repo, Compose và script chuyển hệ lên repo chung để TV1 và TV3 dùng. Mốc kế hoạch là **trước 12h ngày 18/11**.
- [x] Dựng môi trường trên M2, xác nhận đủ 3 TiKV store ở trạng thái `Up` và kết nối được MySQL sau khi chuyển hệ.
- [x] Thêm hồ sơ XS cho cả ba máy (TiDB 4 CPU / 5,5 GiB, MySQL 4 CPU / 2 GiB) và lệnh `python -m bench.cli check`, `team_hash=fa4c12cdf33a`.
- [x] Điền dòng M2 trong Bảng A.3.1 với CPU, RAM, ổ dữ liệu Docker, hệ điều hành, phiên bản Docker, tài nguyên WSL2 và hồ sơ thực tế.

## 19/11 · Task 4 — Nạp và xác minh dữ liệu

- [x] Viết `connect`, `analyze` và `checksum` trong `bench/db.py`. Checksum trả về cả `COUNT(*)` và `SUM(cod_amount)`.
- [x] Viết `engine_settings` để lấy phiên bản, mã máy, hồ sơ và các giá trị thực tế của từng hệ (block cache và số bản sao của TiDB, buffer pool của MySQL). Chạy đạt `tests/test_db_offline.py`.
- [x] Viết `scripts/load.sh` dùng bộ sinh dữ liệu và schema của TV1 để tạo bảng, nạp file bằng `LOAD DATA LOCAL INFILE`, chạy `ANALYZE TABLE` và in checksum.
- [x] Nạp cùng bộ **1.000.000 dòng**, seed `20261116`, lần lượt vào TiDB và MySQL trên M2. Kiểm tra số dòng và tổng `cod_amount` khớp giữa hai hệ.
- [x] M2: `team_hash=fa4c12cdf33a`, 1 triệu dòng `sum_cod=5000968738439` khớp giá trị chuẩn.
- [x] M1: 3 triệu dòng `sum_cod=15001281300461` khớp giá trị chuẩn (lấy từ `results/rq1_M1.csv`).
- [ ] Nhận `team_hash` của M1, và `team_hash` cùng checksum của M3; điền vào bảng trong `p2_phuong_phap.tex`.

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
- [x] **25/11** — Đo lại 36 lượt MySQL với `utf8mb4_bin` (cùng collation với TiDB), ghép thành `results/rq4_official_bin.csv`. Cả 12 cấu hình có khoảng giao với lần đo `unicode_ci`.
- [x] Thử bỏ 6 lượt bị nhiễu (5 C3, 1 C1): hướng kết luận không đổi.

Code RQ1 cho TV1 và TV3:

- [x] Viết `experiments/rq1_covering.py`, `experiments/rq1_summary.py`, `scripts/rq1_official.ps1` và hướng dẫn trong README. Chạy thử 170/170 lượt ở 1 triệu dòng trên M2 (không dùng cho báo cáo).
- [x] Kiểm tra RQ1 chính thức của TV1 ở 3 triệu dòng: 170/170 lượt, đúng cấu hình và dữ liệu, tổng hợp lại ra kết quả giống hệt. Dữ liệu còn nhiễu (p50 của MySQL chênh trung vị 1,77 lần giữa các vòng).
- [ ] Nhắn TV1: đo lại RQ1 khi máy yên, nếu không làm chậm B.1. Hai hệ khác collation ở Q1 nên chỉ so tỉ số trong từng hệ.
- [ ] Kiểm tra RQ1 chính thức của TV3 ở 1 triệu dòng khi có trên GitHub.

## 24–25/11 · Viết A.3, Chương 4 và B.3

- [ ] Hoàn thiện **Bảng A.3.1**: dòng M2 đã có, còn chờ thông tin M1 (TV1) và M3 (TV3).
- [x] Viết **A.3 phần cài đặt** theo hồ sơ XS, dùng tên C3/C1: cấu hình, định nghĩa bản sao và quorum, `SELECT tidb_version()`, trạng thái 3 store, `SHOW CREATE TABLE` và khác biệt collation của hai hệ.
- [x] Chạy mọi demo của A.3 bằng `scripts/demo.ps1` (cơ bản, chịu lỗi, thêm node; phần demo bổ sung nhận từ TV3) và viết `a3_demo_co_ban.tex`, `a3_demo.tex`.
- [x] Viết **vận hành cụm** kèm ảnh Dashboard và Key Visualizer (`a3_van_hanh.tex`), **phương pháp và kịch bản** của Chương 4 (`p2_phuong_phap.tex`) và **Phụ lục C**.
- [x] Viết **B.3** trong `report/sections/b3_chi_phi_ghi.tex`, thay phần `sbtest1` cũ. Số MySQL lấy từ lần đo `utf8mb4_bin` ngày 25/11 (`results/rq4_official_bin.csv`); có mục kiểm tra collation và so với lần đo `unicode_ci`.
- [x] Trong B.3, nêu đủ các điểm bất thường: 5 lượt C3 vòng 2 chạy khi `tikv1` giữ 0 leader; 1 lượt C1 trùng lệnh chẩn đoán; 3 lượt C1 đo lại; 1 dòng C3 ghi `tikv_stores=2`; leader C1 lệch; MySQL `sender_cov` ở lần đo cũ dao động 7.597–12.647 TPS; hai hệ đo khác ngày; C3 cập nhật 1 index +6% nằm trong mức nhiễu; dung lượng index TiDB là ước tính; bỏ mức 16 luồng; TiDB dùng tới 1.156/1.280 MiB; một TiKV của C3 chạy sát 0,8 CPU; byte ghi của TiDB dao động tới hơn 5 lần.
- [x] Thay khung báo cáo theo mẫu và yêu cầu của giảng viên (Phần 1, Phần 2, 8 chương), mỗi thành viên một nhóm file riêng trong `report/sections/`.
- [x] Bỏ các hình cũ không có file; mọi hình trong phần TV2 đã có trong `report/figures/`.
- [ ] Biên dịch bản hiện tại trên Overleaf bằng XeLaTeX (khung ban đầu đã biên dịch được; bản có nội dung mới chưa thử).
- [ ] Đọc lại Chương 3, phần phương pháp của Chương 4, Chương 7 và Phụ lục; mở các tài liệu tham khảo mới để đối chiếu.
- [x] Đưa code, CSV, hình và phần viết lên `main` (PR #7, #8).
- [ ] Báo TV1 phần TV2 đã sẵn sàng để ghép; nhắc lấy số RQ4 từ `results/rq4_official_bin_summary.csv`.

## 25–27/11 · Đọc chéo và thuyết trình

- [ ] **25/11** — Hỏi tiến độ TV1 (B.1, RQ3 có làm không) và TV3 (RQ1 1 triệu dòng, RQ2, B.2).
- [ ] **25/11** — Đọc chéo B.2 và gửi góp ý cho TV3. Đang chờ TV3 viết.
- [ ] **26/11** — Đối chiếu từng con số trong B.1 với CSV của TV1.
- [ ] **26/11** — Đối chiếu từng con số trong B.2 với CSV của TV3.
- [ ] **26/11** — Soạn phần thuyết trình RQ4 và A.3, chuẩn bị câu hỏi bảo vệ.
- [ ] **26/11** — Sửa B.3 theo góp ý đọc chéo của TV3.
- [ ] **26/11** — Viết dòng của TV2 trong "Phân chia công việc" và một ý trong "Kiến thức và kỹ năng đạt được"; gửi TV1 họ tên, MSSV để điền bìa.
- [ ] **26/11** — Nếu demo trực tiếp: chạy `.\scripts\demo.ps1 don` (cụm demo đang còn `tikv4`), rồi `bat_tidb` khi còn Internet. Không chạy `use_engine.ps1` khi chưa đặt `PROFILE=XS`, vì M2 đang mặc định hồ sơ S.
- [ ] **27/11** — Tập thuyết trình cùng nhóm.

Phân công, lịch và các điều chỉnh lấy từ [kế hoạch 1,5 tuần, 3 máy](ke_hoach_do_an_tidb_vs_mysql_1.md). Chi tiết triển khai nằm ở Task 1, 4 và 10 của [tài liệu kỹ thuật](2026-11-16-tidb-indexing-van-don.vi.md). RQ3 thuộc TV1: giữ nguyên cho tới khi TV1 trả lời.
