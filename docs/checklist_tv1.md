# Checklist công việc TV1 — TiDB và MySQL

**Máy M1 · hồ sơ XS · 1 triệu và 3 triệu vận đơn · 24–27/11/2026**
Bạn phụ trách dung lượng B.1, RQ1 ở 3 triệu dòng, các mục A.1, A.2, B.1, phần bảng giả thuyết và khuyến nghị của B.4, ghép báo cáo và slide. Khi hoàn thành một đầu việc, đổi `- [ ]` thành `- [x]` ở đúng dòng đó.

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
  git switch -c tv1/b1-rq1
  python -m venv .venv        # bỏ qua nếu đã có .venv, cần Python 3.10 trở lên
  .venv\Scripts\python -m pip install -e ".[dev]"
  ```

- [ ] Trong file `.env`, đặt `MACHINE_ID=M1` và `PROFILE=XS`. File mẫu ghi sẵn `M2` và `MYSQL_PORT=3307`, nên chép nguyên file mẫu sẽ làm CSV mang nhãn M2. Chỉ giữ `MYSQL_PORT=3307` nếu cổng 3306 đã bị chiếm. Không đẩy `.env` lên Git.
- [ ] Trong `%UserProfile%\.wslconfig`, mục `[wsl2]`, đặt `memory=10GB` và `swap=4GB`, rồi chạy `wsl --shutdown` và mở lại Docker Desktop.
- [ ] Chạy lệnh kiểm tra. Kết quả phải là `DAT`, `machine=M1`, `team_hash=fa4c12cdf33a`. Nếu hash khác, dừng lại và báo nhóm.

  ```powershell
  .venv\Scripts\python -m bench.cli check
  ```

- [ ] Nạp 1 triệu dòng vào hai hệ và gửi TV2 dòng kết quả mà lệnh nạp in ra:

  ```powershell
  .\scripts\use_engine.ps1 -Engine mysql -Switch
  .\scripts\load.ps1 -Engine mysql -Rows 1000000
  .\scripts\use_engine.ps1 -Engine tidb -Switch
  .\scripts\load.ps1 -Engine tidb -Rows 1000000
  ```

- [ ] Đối chiếu với giá trị chuẩn (seed `20261116`; sinh lại bằng `bench/datagen.py` trên M2 ngày 24/11):

  | Số dòng | `sum_cod` | SHA-256 của file TSV |
  |---|---|---|
  | 1.000.000 | `5000968738439` | `8ee11b63da2217d4b1d00137bd8e4f3ba647b9bed94a594468c990fe981f4827` |
  | 3.000.000 | `15001281300461` | `ca0b2a59cc831050aaf6f4d87bbcfe4367cb676bcd25512dd79a39336df2a560` |

- [ ] Gửi TV2 thông tin M1 cho Bảng A.3.1. Chạy lệnh dưới đây, gửi kết quả kèm nội dung `.wslconfig`:

  ```powershell
  Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
  Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
  Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version
  Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,Size
  docker version --format '{{.Server.Version}}'
  docker info --format '{{.NCPU}} CPU, {{.MemTotal}} byte'
  ```

## 24/11 · Task 7 — RQ1 ở 3 triệu dòng

Code do TV2 viết (`experiments/rq1_covering.py`, `experiments/rq1_summary.py`), mới chạy thử ở 1 triệu dòng trên M2. Quy mô 3 triệu dòng chưa ai chạy, nên phải chạy thử trước. Dùng lệnh dưới đây, không chép từ README, vì lệnh RQ1 ở đó bị ngắt dòng sai.

- [x] Code đo, kiểm tra kế hoạch và tổng hợp RQ1 đã có trên `main`.
- [ ] Mở **cửa sổ PowerShell mới** và chạy thử ở 3 triệu dòng:

  ```powershell
  .\scripts\rq1_official.ps1 -Rows 3000000 -Reps 1 -Params 20 -Output results/runs/rq1_trial.csv
  ```

- [ ] Sau khi chạy thử, kiểm tra không có container nào bị `OOMKilled` và CSV có cả hai hệ. Lệnh thứ hai in bảng; hình thử nằm trong `results/runs/`, không dùng cho báo cáo.

  ```powershell
  docker ps -a --filter "name=nhom7xs" --format '{{.Names}}' | ForEach-Object { docker inspect --format '{{.Name}} OOM={{.State.OOMKilled}}' $_ }
  .venv\Scripts\python -m experiments.rq1_summary results/runs/rq1_trial.csv --figure results/runs/rq1_trial.png
  ```

  Lệnh đầu xem được MySQL, PD và ba TiKV. Container TiDB server được tạo lại khi kết thúc nên mất cờ OOM; nếu nó bị OOM thì script đã dừng với lỗi mất kết nối. Khi có OOM, gửi TV2 log, không tự sửa cấu hình.
- [ ] Chạy chính thức (5 vòng, 200 tham số). Bị ngắt thì chạy lại đúng lệnh này:

  ```powershell
  .\scripts\rq1_official.ps1 -Rows 3000000
  ```

- [ ] Kiểm tra `results/rq1_M1.csv` có 170 dòng, 85 dòng mỗi hệ. Nếu script bỏ qua một mức R thì ghi lại lý do. TiDB phải có `replica_config=C3`.
- [ ] Tạo bảng tổng hợp, mô hình `t = a + b×R` và hình:

  ```powershell
  .venv\Scripts\python -m experiments.rq1_summary results/rq1_M1.csv
  ```

- [ ] Ghi lại mọi lượt bất thường (máy chạy việc khác, container khởi động lại, đĩa chưa lắng). Không xóa lượt nào.
- [ ] Commit và mở PR kết quả, rồi báo TV3 để viết B.2 và báo TV2 kiểm tra số:

  ```powershell
  git add results/rq1_M1.csv results/rq1_M1_summary.csv results/rq1_M1_fit.csv results/fig/rq1_M1_covering.png
  git commit -m "data(rq1): RQ1 chinh thuc 3 trieu dong tren M1"
  git push -u origin tv1/b1-rq1
  ```

`rq1_official.ps1` đặt `DB_NAME=logistics_3000000` trong cửa sổ PowerShell đang dùng. Đóng cửa sổ đó trước khi làm việc với bảng 1 triệu dòng.

## 24–25/11 · Task 2, 3, 5 — Mô hình và số đo dung lượng B.1

- [x] `bench/datagen.py` và `bench/schema.py` đã có trên `main`, dùng chung cho ba máy.
- [ ] Viết `bench/storage_model.py` và `tests/test_storage_model.py`. Mô hình InnoDB có hai chế độ lấp đầy (tạo index sau khi nạp; chèn dần), `DATETIME` tính 5 B. Giữ phép kiểm tra hồi quy với `sbtest1` theo Task 5.
- [ ] Hiệu chỉnh `C_nén` và `α_LSM` trước khi áp dụng cho `shipments`. Ở giai đoạn 1, mô hình cho 1,88 GiB mỗi bản sao còn số đo khoảng 3,2 GiB dữ liệu logic. Nếu không tìm được nguyên nhân, ghi rõ phần chênh, không chỉnh hệ số cho khớp.
- [ ] Viết `experiments/b1_storage.py` với tham số hệ và số dòng, ghi `results/b1_storage_M1.csv`. Mỗi dòng có `run_id`, `machine`, `profile`, hệ, phiên bản, `rows`, bộ index, `replica_config`, dung lượng đo, dung lượng mô hình, thời gian tạo từng index.
- [ ] MySQL: chạy `ANALYZE TABLE`, đặt `information_schema_stats_expiry=0`, rồi lấy dung lượng bảng và từng index.
- [ ] TiDB: đo ở C3. Gọi `assert_replicas(conn, 3)` trước khi đo, lấy `APPROXIMATE_SIZE` từ `information_schema.TIKV_REGION_STATUS` và đối chiếu với dung lượng thư mục dữ liệu TiKV. Không dùng `index_length` của `information_schema.tables` làm dung lượng vật lý, vì đó là ước tính từ thống kê.
- [ ] Ghi rõ với mỗi số TiDB: trước hay sau nén, một bản sao hay toàn cụm (cụm chia 3 chỉ là xấp xỉ), có gồm phiên bản MVCC chưa dọn không. Một Region có thể chứa cả bảng và index, nên kiểm tra trước khi tách dung lượng từng index.
- [ ] Chạy thử ở 1.000 dòng, commit code, chạy lại `check`, rồi mới đo.
- [ ] Đo ở **1 triệu dòng**: hai hệ, 0 và 5 index (`RQ4_INDEX_SETS[0]` và `[5]`).
- [ ] Đo ở **3 triệu dòng**: hai hệ, 0 và 5 index. Đặt database trước khi nạp:

  ```powershell
  $env:PROFILE = "XS"
  $env:DB_NAME = "logistics_3000000"
  .\scripts\use_engine.ps1 -Engine mysql -Switch
  .\scripts\load.ps1 -Engine mysql -Rows 3000000
  ```

- [ ] Ghi CPU, RAM và byte ghi đĩa **trước, trong và sau** `CREATE INDEX` ở 3 triệu dòng, dùng `bench/resources.py`.
- [ ] Đo thêm dung lượng `idx_sender_created` và `idx_sender_cov` trên cả hai hệ. Đây là phần dung lượng trong nhận xét 3 của thầy.
- [ ] Vẽ `results/fig/b1_model_vs_measured.png`, dùng màu của `rq1_summary.py`: MySQL `#2a78d6`, TiDB `#eb6834`.
- [ ] Commit CSV bằng `-f`, vì `.gitignore` chỉ cho qua `rq4_official*` và `rq1*`:

  ```powershell
  git add -f results/b1_storage_M1.csv
  git add results/fig/b1_model_vs_measured.png bench/storage_model.py experiments/b1_storage.py tests/test_storage_model.py
  git commit -m "data(b1): mo hinh va so do dung luong 1 va 3 trieu dong tren M1"
  git push
  ```

- [ ] Quy mô 10 triệu và 100 triệu dòng chỉ ghi số mô hình, vì nhóm dùng hồ sơ XS. RQ3 đã do TV2 đo và viết (`report/sections/b1_rq3.tex`), TV1 không phải làm.

## 25/11 · Viết A.1, A.2, B.1

Mỗi người viết mục của mình trong file riêng để tránh xung đột; bạn nối bằng `\input{}` khi ghép. B.1 đặt ở `report/sections/b1_dung_luong.tex`. Khung và phân công file nằm trong `report/README.md`.

- [ ] **A.1** — Viết theo bài toán vận đơn. Bỏ các câu khẳng định chưa đo trong `01_phan_a.tex`, ví dụ "mở rộng ngang vô hạn" (dòng 37), "giải quyết triệt để" (dòng 30), `RTO ≤ 10s` (dòng 42). Dòng 39 ghi 4 phẩm chất nhưng chỉ liệt kê 3.
- [ ] **Chương 2, tổng quan** (`a0_tong_quan.tex`) — Tổng quan TiDB khoảng nửa trang và bảng thành phần chính. Viết tổng quát, chi tiết dẫn sang kho mã (đầu Chương 3).
- [ ] **Chương 4, vấn đề và cơ chế** (`p2_van_de_co_che.tex`) — Vấn đề đã đăng ký; cơ chế đọc và ghi qua chỉ mục phụ trên hai hệ; covering index.
- [ ] **A.2** — Mỗi trụ cột nêu ảnh hưởng tới index. Sửa kích thước Region theo `SHOW CONFIG WHERE name LIKE '%region-split-size%'` trên v8.5.5. Bỏ "3–8 giây": giai đoạn 1 ghi nhận 10 giây QPS bằng 0.
- [ ] **A.2** — Quorum là đa số peer của một Region: C3 cần 2/3, chịu mất 1 store; C1 cần 1/1, không chịu mất store nào. Sửa câu "3 node TiKV độc lập vật lý" (dòng 156): ba TiKV là ba container trên một máy và một ổ đĩa. TiDB không hỗ trợ SERIALIZABLE.
- [ ] **B.1** — Thay toàn bộ phần `sbtest1` (`02_phan_b.tex` dòng 9–258) bằng mô hình và số đo `shipments`. Các số giai đoạn 1 ở phần này không được giữ nếu không có log.
- [ ] **B.1** — Bảng đối chiếu thô, MySQL mô hình và đo, TiDB mô hình và đo, kèm tỉ lệ đo trên mô hình. Nêu cả chỗ mô hình sai.

## 25–26/11 · B.4, ghép báo cáo và slide

- [ ] **B.4** — Bảng giả thuyết RQ1, RQ2, RQ4: xác nhận, bác bỏ hoặc một phần, kèm số chính và tên CSV. Chỉ điền khi CSV chính thức đã ở trên `main`.
- [ ] **B.4** — Khuyến nghị index cho bài toán vận đơn trên từng hệ, ghép lợi ích đọc (RQ1), chi phí ghi (RQ4) và dung lượng (B.1) của covering. TV3 viết phần hạn chế.
- [ ] Viết lại `03_ket_luan.tex`. Bỏ các kết luận trái số đo, ví dụ "TiDB áp đảo hoàn toàn" và "3–8 giây" (dòng 24), "LSM-Tree giải quyết triệt để" (dòng 23).
- [ ] Sửa `04_phu_luc.tex`: thay compose v8.1.0 / MySQL 8.0 bằng cấu hình XS (TiDB v8.5.5, MySQL 8.4.11), câu lệnh `sbtest1` bằng `shipments`, và bảng phân công cũ.
- [ ] Nối các file mục vào `main.tex`, thêm hình còn thiếu, biên dịch XeLaTeX hai lần, không còn `??` và khung hình trống. M2 chưa cài XeLaTeX, nên dùng máy của bạn hoặc Overleaf.
- [ ] Kiểm tra ba nhận xét của thầy đã được trả lời: tách covering và độ chọn lọc khỏi chi phí gọi KV; số TiKV, bản sao, quorum, chịu lỗi; truy vấn có và không covering với kế hoạch, độ trễ, chi phí ghi, dung lượng.
- [ ] **26/11** — Làm slide. Failover chỉ là demo phụ.

## 27/11 · Nộp và thuyết trình

- [ ] Sửa các góp ý của TV2 và TV3 về số liệu B.1.
- [ ] Nộp báo cáo, CSV, hình và mã nguồn.
- [ ] Tập thuyết trình cùng nhóm.

Phân công theo kế hoạch nhóm bản 2 (bản trong Git là [kế hoạch 1,5 tuần, 3 máy](ke_hoach_do_an_tidb_vs_mysql_1.md)). Chi tiết ở Task 2, 3, 5, 7 và 9 của [tài liệu kỹ thuật](2026-11-16-tidb-indexing-van-don.vi.md).
