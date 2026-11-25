# Checklist công việc TV3 — TiDB và MySQL

**Máy M3 · hồ sơ XS · RQ1 ở 1 triệu dòng, RQ2 ở 3 triệu dòng · 24–27/11/2026**
Bạn phụ trách RQ1 ở 1 triệu dòng, RQ2, các mục B.0, B.2 và phần hạn chế của B.4. Khi hoàn thành một đầu việc, đổi `- [ ]` thành `- [x]` ở đúng dòng đó.

Các mục đã đánh dấu là những gì có trên nhánh `main` ngày 24/11. Việc bạn đã làm nhưng chưa đẩy lên thì tự đánh dấu.

## Quy tắc khi đo

- Cả ba máy chỉ dùng hồ sơ XS. Không sửa `docker/`, `sysbench/`, `bench/datagen.py`, `bench/loader.py`, `bench/schema.py`, vì `team_hash` sẽ đổi.
- Lệnh `check` báo lỗi nếu trong `bench/`, `docker/`, `sysbench/` hoặc `experiments/rq1_covering.py` có file chưa commit. Commit code mới trước khi đo.
- Mỗi lúc chỉ bật một hệ, cắm sạc, đóng ứng dụng nặng. Khi đang đo, không chạy lệnh nào khác trên cụm.
- Đo cả MySQL và TiDB. Chỉ so hai hệ trên cùng máy; giữa các máy chỉ so tỉ lệ.
- Không bịa số, không bỏ lượt đo trái giả thuyết, không quy mọi chênh lệch cho mạng.
- Dùng tên cấu hình **C3** (3 TiKV, 3 bản sao) và **C1** (3 TiKV, 1 bản sao). Phần của bạn chỉ dùng C3.

## 24/11 · Môi trường và đối chiếu dữ liệu

- [ ] Lấy `main` mới nhất và cài môi trường, rồi tạo nhánh riêng:

  ```powershell
  git switch main
  git pull
  git switch -c tv3/rq1-rq2
  python -m venv .venv        # bỏ qua nếu đã có .venv, cần Python 3.10 trở lên
  .venv\Scripts\python -m pip install -e ".[dev]"
  ```

- [ ] Trong file `.env`, đặt `MACHINE_ID=M3` và `PROFILE=XS`. File mẫu ghi sẵn `M2` và `MYSQL_PORT=3307`, nên chép nguyên file mẫu sẽ làm CSV mang nhãn M2. Chỉ giữ `MYSQL_PORT=3307` nếu cổng 3306 đã bị chiếm. Không đẩy `.env` lên Git.
- [ ] Trong `%UserProfile%\.wslconfig`, mục `[wsl2]`, đặt `memory=10GB` và `swap=4GB`, rồi chạy `wsl --shutdown` và mở lại Docker Desktop. Cấu hình 12 GB của giai đoạn 1 không dùng nữa.
- [ ] Chạy lệnh kiểm tra. Kết quả phải là `DAT`, `machine=M3`, `team_hash=fa4c12cdf33a`. Nếu hash khác, dừng lại và báo nhóm.

  ```powershell
  .venv\Scripts\python -m bench.cli check
  ```

- [ ] Gửi TV2 thông tin M3 cho Bảng A.3.1. Chạy lệnh dưới đây, gửi kết quả kèm nội dung `.wslconfig`:

  ```powershell
  Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
  Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
  Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version
  Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,Size
  docker version --format '{{.Server.Version}}'
  docker info --format '{{.NCPU}} CPU, {{.MemTotal}} byte'
  ```

- [ ] Mỗi lần nạp, đối chiếu dòng kết quả với giá trị chuẩn rồi gửi TV2 (seed `20261116`; sinh lại bằng `bench/datagen.py` trên M2 ngày 24/11):

  | Số dòng | `sum_cod` | SHA-256 của file TSV |
  |---|---|---|
  | 1.000.000 | `5000968738439` | `8ee11b63da2217d4b1d00137bd8e4f3ba647b9bed94a594468c990fe981f4827` |
  | 3.000.000 | `15001281300461` | `ca0b2a59cc831050aaf6f4d87bbcfe4367cb676bcd25512dd79a39336df2a560` |

## 24/11 · Task 6, 7 — RQ1 ở 1 triệu dòng

TV2 đã viết code RQ1. Trên M2, phần đo ở 1 triệu dòng mất khoảng 5 phút mỗi hệ, chưa kể nạp dữ liệu. Số chạy thử của M2 không dùng cho báo cáo. Dùng lệnh dưới đây, không chép từ README, vì lệnh RQ1 ở đó bị ngắt dòng sai.

- [x] Công cụ đo, kiểm tra kế hoạch, phân tích `EXPLAIN ANALYZE` và tổng hợp RQ1 đã có trên `main` (`experiments/rq1_covering.py`, `experiments/rq1_summary.py`, `tests/test_rq1.py`).
- [ ] Chạy thử. Script tự chuyển hệ và nạp dữ liệu:

  ```powershell
  .\scripts\rq1_official.ps1 -Reps 1 -Params 20 -Output results/runs/rq1_trial.csv
  .venv\Scripts\python -m experiments.rq1_summary results/runs/rq1_trial.csv --figure results/runs/rq1_trial.png
  ```

- [ ] Mở CSV thử, kiểm tra cả hai hệ, toán tử (`access_op`) và `machine=M3`.
- [ ] Chạy chính thức (5 vòng, 200 tham số). Bị ngắt thì chạy lại đúng lệnh này:

  ```powershell
  .\scripts\rq1_official.ps1
  .venv\Scripts\python -m experiments.rq1_summary results/rq1_M3.csv
  ```

- [ ] Kiểm tra `results/rq1_M3.csv` có 170 dòng, 85 dòng mỗi hệ, TiDB có `replica_config=C3`. Ghi lại mọi lượt bất thường, không xóa lượt nào.
- [ ] Giữ thư mục `results/raw/<run_id>/`, vì Git bỏ qua nó. B.2 cần trích `EXPLAIN ANALYZE` từ đây.
- [ ] Commit và mở PR kết quả:

  ```powershell
  git add results/rq1_M3.csv results/rq1_M3_summary.csv results/rq1_M3_fit.csv results/fig/rq1_M3_covering.png
  git commit -m "data(rq1): RQ1 chinh thuc 1 trieu dong tren M3"
  git push -u origin tv3/rq1-rq2
  ```

## 24–25/11 · Task 8 — RQ2: ngưỡng độ chọn lọc

Trên `main` chưa có code RQ2. Kế hoạch ghi 10 triệu dòng ở hồ sơ M, nhưng nhóm đã chốt XS, nên RQ2 chạy ở **3 triệu dòng** theo phương án dự phòng của kế hoạch.

- [ ] Viết `experiments/rq2_selectivity.py` và `tests/test_rq2.py` (`cod_range`, `find_crossover`). Dùng lại của RQ1: `fast_connect`, `run_queries`, `tidb_plan`, `mysql_plan`, `parse_execution_info`, `percentile`; của RQ4: `settle`, `wait_replicas`, `config_fingerprint`, `save_row`.
- [ ] Câu truy vấn: `SELECT * FROM shipments WHERE cod_amount BETWEEN ? AND ?`, 10 mức chọn lọc từ 0,001% đến 50%, 3 chế độ: `FORCE INDEX (idx_cod)`, `IGNORE INDEX (idx_cod)`, optimizer tự chọn.
- [ ] Kiểm tra kế hoạch trước khi đo, dừng nếu hint không được tuân theo. Hai chế độ ép phải trả cùng số dòng, cùng tham số.
- [ ] Trên TiDB, tắt coprocessor cache bằng `docker/tidb-rq1.yml` như RQ1, gọi `wait_replicas(conn, 3)`, và trả cấu hình chung khi kết thúc.
- [ ] Mỗi lượt ghi `run_id`, `machine`, `profile`, hệ, phiên bản, `replica_config`, `rows`, `sum_cod`, độ chọn lọc, R, chế độ, `rep`, toán tử, p50/p95/p99, số cop task, số RPC, thời gian xử lý và chờ, `Innodb_buffer_pool_reads`, `config_id`, `settled`.
- [ ] Nạp và chạy thử ở 3 triệu dòng, bắt đầu từ mức 50%, vì mức này trả về khoảng 1,5 triệu dòng và dễ làm TiDB (1,25 GiB) hết bộ nhớ. Mở cửa sổ PowerShell mới:

  ```powershell
  $env:PROFILE = "XS"
  $env:DB_NAME = "logistics_3000000"
  .\scripts\use_engine.ps1 -Engine mysql -Switch
  .\scripts\load.ps1 -Engine mysql -Rows 3000000
  .venv\Scripts\python -m experiments.rq2_selectivity mysql 3000000
  .\scripts\use_engine.ps1 -Engine tidb -Switch
  .\scripts\load.ps1 -Engine tidb -Rows 3000000
  .venv\Scripts\python -m experiments.rq2_selectivity tidb 3000000
  ```

- [ ] Ước tính tổng thời gian từ lượt thử. Đề xuất: 20 khoảng giá trị ở mức đến 2%, 3 khoảng ở mức từ 5%, 5 vòng. Ghi đúng số khoảng đã dùng trong báo cáo. Nếu một mức bị OOM thì ghi lại là không đo được.
- [ ] Commit code, chạy `check`, rồi chạy chính thức cho cả hai hệ vào `results/rq2_M3.csv`.
- [ ] Tính điểm giao nhau giữa dùng index và quét bảng, điểm optimizer đổi phương án và khoảng cách giữa hai điểm. Khớp `t = a + b×R` cho từng đường, trong dải gần tuyến tính, kèm R² và phần dư.
- [ ] Vẽ hình RQ2, trục x thang log, màu như `rq1_summary.py`: MySQL `#2a78d6`, TiDB `#eb6834`.
- [ ] Commit CSV bằng `-f`, vì `.gitignore` chỉ cho qua `rq4_official*` và `rq1*`:

  ```powershell
  git add -f results/rq2_M3.csv
  git add experiments/rq2_selectivity.py tests/test_rq2.py results/fig
  git commit -m "data(rq2): nguong do chon loc 3 trieu dong tren M3"
  git push
  ```

Nếu đến tối 25/11 RQ2 chưa xong ở 3 triệu dòng, đo ở 1 triệu dòng và ghi rõ quy mô.

## 24–25/11 · Viết B.0 và B.2

Mỗi người viết mục của mình trong file riêng để tránh xung đột; khung `main.tex` đã nối sẵn, xem `report/README.md`. Bạn dùng `report/sections/b0_so_bo.tex` và `b2_chi_phi_doc.tex`.

- [ ] **B.0** — Kết quả sơ bộ `sbtest1`: MySQL cao hơn TiDB 13–32 lần ở `oltp_read_write`, 8–13 lần ở `oltp_update_index`; giả thuyết TiDB ổn định hơn ở 256–512 luồng không được xác nhận. Không có CSV giai đoạn 1 trong repo, nên gửi log gốc cho nhóm kiểm tra; số không có log thì bỏ.
- [ ] **B.0** — Thay phần `02_phan_b.tex` dòng 308–333. Bản cũ ghi MySQL chỉ hơn 25–35%, P99 180 ms và 42 ms, và "TiDB giữ vững phong độ"; các câu này trái với kết quả trên.
- [x] **A.3 demo** — TV2 nhận làm toàn bộ demo của A.3 (25/11). Bạn không phải làm phần này.
- [ ] **B.2 RQ1** — Ba nguồn chênh lệch tách riêng: độ chọn lọc (R), đường truy cập (toán tử), chi phí gọi KV (cop task, RPC, xử lý, chờ, phần còn lại). Phần còn lại chỉ là xấp xỉ.
- [ ] **B.2 RQ1** — Với Q1, so A2 và B để lấy hiệu ứng covering; so A và B là so với `Point_Get`. Trình bày đường chuẩn `SELECT 1` và tra khóa chính.
- [ ] **B.2 RQ1** — Bảng lợi ích covering `t(A)/t(B)` trong từng hệ ở 1 triệu (M3) và 3 triệu dòng (số chính `results/rq1_M2_summary.csv`; đối chiếu `results/rq1_M1_summary.csv`, nêu cả chỗ hai máy khác nhau). Khớp `a + b×R` riêng cho từng máy, không gộp. Q3 chỉ có một mức R nên không khớp.
- [ ] **B.2 RQ1** — Trích kế hoạch thực thi có và không covering của ít nhất Q2 và Q3 trên hai hệ. Dẫn tới B.3 (chi phí ghi của covering) và B.1 (dung lượng).
- [ ] **B.2 RQ2** — Điểm giao nhau, điểm optimizer đổi phương án và nguồn chênh lệch. Không đặt trước hệ nào thắng.
- [ ] **B.2** — Thay phần so sánh `EXPLAIN ANALYZE` `sbtest1` (dòng 260–302). Không viết "chịu phụ phí mạng gRPC"; mọi node chạy trên một máy.
- [ ] Gửi bản nháp B.2 cho TV2 đọc chéo trong ngày 25/11.

## 25–26/11 · Đọc chéo và B.4

- [ ] **25/11** — Đọc chéo B.3 và gửi góp ý cho TV2.
- [ ] **26/11** — Đối chiếu B.1 với `results/b1_storage_M1.csv` và B.3 với `results/rq4_official_bin_summary.csv`: mỗi kết luận phải có số đo và cơ chế đi kèm.
- [ ] **26/11** — Viết phần hạn chế của B.4: mọi node trên một máy và một ổ đĩa; CPU chia cố định theo container; không có độ trễ mạng vật lý; C1 không chịu lỗi; ba máy khác nhau nên không so số tuyệt đối; RQ4 chỉ ở 1 triệu dòng, 64 luồng, 3 vòng; không có số đo 10 triệu dòng.
- [ ] **26/11** — Sửa B.2 theo góp ý của TV2.

## 27/11 · Nộp và thuyết trình

- [ ] Kiểm tra hình và số của B.0, B.2 trong bản PDF cuối.
- [ ] Tập thuyết trình cùng nhóm.

Phân công theo kế hoạch nhóm bản 2 (bản trong Git là [kế hoạch 1,5 tuần, 3 máy](ke_hoach_do_an_tidb_vs_mysql_1.md)). Chi tiết ở Task 6, 7, 8 và 12 của [tài liệu kỹ thuật](2026-11-16-tidb-indexing-van-don.vi.md).
