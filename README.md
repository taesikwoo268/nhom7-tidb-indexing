# Nhóm 7 — Chi phí chỉ mục phụ trên TiDB và MySQL InnoDB

Nghiên cứu kết hợp phân tích kiến trúc TiDB và thực nghiệm đối chứng trên dữ liệu vận đơn `shipments`. Phạm vi thực nghiệm lấy từ [đề cương nhóm, Phụ lục A/B](docs/ke_hoach_do_an_tidb_vs_mysql_1.md). Tên module, interface và các bước triển khai nằm trong [kế hoạch kỹ thuật](docs/2026-11-16-tidb-indexing-van-don.vi.md).

## Cấu trúc workspace

```text
project/
├── bench/              # Sinh dữ liệu, DDL, kết nối, đo đạc và thống kê dùng chung
├── docker/             # Compose và cấu hình TiDB/MySQL (cả nhóm dùng hồ sơ XS)
├── experiments/        # Điểm chạy B.1, RQ1, RQ2, RQ3 và sinh biểu đồ
├── scripts/            # Chuyển hệ, nạp dữ liệu và điều phối RQ4
├── sysbench/           # Workload insert/update bằng Lua cho RQ4
├── tests/              # Kiểm thử generator, DDL, mô hình, parser và cấu hình
├── data/               # TSV/CSV sinh cục bộ
├── results/
│   ├── raw/            # Log, EXPLAIN ANALYZE và snapshot theo từng run_id
│   ├── runs/           # Hồ sơ môi trường, dữ liệu và lệnh của từng lần chạy
│   └── fig/            # Biểu đồ sinh từ CSV tổng hợp
├── docs/               # Đề cương, kế hoạch kỹ thuật và tài liệu nền
├── report/             # Nguồn LaTeX, hình đưa vào báo cáo và lệnh biên dịch
├── code/               # Compose TiDB v7.5.0 hiện có
└── dataset_report/     # Thư mục sẵn có, hiện chưa có dữ liệu
```

## Chạy phần TV2

Dùng Python 3.10 trở lên, Docker Desktop và Compose v2. Trong môi trường Python của dự án, chạy `python -m pip install -e ".[dev]"`. Các script Bash và PowerShell tự tìm Python trong `.venv`. Cụm TiDB 8.5.5 và MySQL 8.4.11 dùng các manifest ở `docker/`.

**Cấu hình chung.** Cả ba máy dùng hồ sơ XS lấy từ Git, không sửa tay. File `.env` chỉ đặt `MACHINE_ID` (M1, M2 hoặc M3), `PROFILE=XS` và cổng MySQL nếu 3306 đã bị chiếm (ví dụ `MYSQL_PORT=3307`). File `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=10GB
swap=4GB
```

Trước khi đo, cắm sạc và chạy lệnh kiểm tra. `team_hash` phải giống nhau trên cả ba máy.

```powershell
.venv/Scripts/python -m bench.cli check
```

Mỗi phép đo chạy cả TiDB và MySQL trên cùng máy, mỗi lúc một hệ. Không so TPS hay độ trễ tuyệt đối giữa các máy. Compose dùng tên dự án `nhom7xs`, nên dữ liệu không lẫn với hồ sơ cũ. Khi chuyển hệ, các volume được giữ lại.

```powershell
.\scripts\use_engine.ps1 -Engine mysql
.\scripts\load.ps1 -Engine mysql -Rows 1000000
.\scripts\use_engine.ps1 -Engine tidb -Switch
.\scripts\load.ps1 -Engine tidb -Rows 1000000
```

Chạy thử đúng một tổ hợp bằng lệnh dưới đây sau khi nạp TiDB. CSV thử nằm trong `results/runs/`. Để chạy RQ4 chính thức cho cả hai hệ (84 lượt), dùng `.\scripts\rq4_official.ps1`; nếu bị ngắt, chạy lại đúng lệnh đó.

```powershell
.venv/Scripts/python -m bench.cli rq4 tidb 1000000 --seconds 10 --reps 1 --indexes 1 --replicas 1 --mode update --output results/runs/rq4_trial.csv
```

Mỗi lượt ghi trên bản sao mới của `shipments`. Dữ liệu gốc dùng tracking code chẵn, W1 sinh mã lẻ và dùng phân bố đều cho `sender_id`. p95/p99 lấy từ histogram độ trễ của cùng lượt sysbench. Byte ghi là chênh lệch bộ đếm block I/O của các container database trong cửa sổ chạy. Dung lượng bảng và index lấy từ `information_schema.tables` sau `ANALYZE TABLE`. Hồ sơ S và XS dùng 2.048 mẫu khi TiDB phân tích thống kê để vừa giới hạn RAM.

## Chạy RQ1 (covering index)

Sau khi pull, cài thêm client C dùng để đo: `python -m pip install -e ".[dev]"`. Rồi chạy thử khoảng 5 phút, xem CSV, và chạy chính thức. Nếu bị ngắt, chạy lại đúng lệnh đó.

```powershell
# Chạy thử
.\scripts
q1_official.ps1 -Reps 1 -Params 20 -Output results/runs/rq1_trial.csv
# Chính thức: 1 triệu dòng (M3), 3 triệu dòng (M1)
.\scripts
q1_official.ps1
.\scripts
q1_official.ps1 -Rows 3000000
# Bảng, mô hình t = a + b×R và hình
.venv/Scripts/python -m experiments.rq1_summary results/rq1_M3.csv
```

Kết quả của mỗi máy nằm trong `results/rq1_<máy>.csv`, kế hoạch thô và bộ tham số trong `results/raw/<run_id>/`. Mã nguồn: `experiments/rq1_covering.py` (đo) và `experiments/rq1_summary.py` (tổng hợp).

- **Thiết kế:** A là index không covering, B là covering. Riêng Q1, A là UNIQUE, A2 (A′ trong kế hoạch) là index thường cùng khóa với B; hiệu ứng covering lấy từ A2 và B. Index được ép bằng hint và mọi kế hoạch được kiểm tra trước khi đo.
- **Bộ nhớ đệm kết quả của TiDB bị tắt** trong lúc đo (`docker/tidb-rq1.yml`), vì lệnh lặp lại sẽ trúng bộ nhớ đệm này, còn MySQL 8 không có cơ chế tương đương. Script trả TiDB về cấu hình chung khi kết thúc.
- **Độ trễ** đo từ lúc gửi lệnh đến khi client C nhận đủ dòng, một kết nối, không TLS, gồm cả đường mạng từ Windows vào container. Chỉ so tỉ số trong từng hệ.
- **R** là số dòng khớp. Q2R chọn mốc thời gian để có đúng khoảng 10, 100, 1.000 và 10.000 dòng. Q3 chỉ có một mức R (số dòng chia 200 kho) nên không khớp `a + b×R`.
- **Thời gian RPC, xử lý và chờ của TiDB** là trung vị của 10 lệnh `EXPLAIN ANALYZE` mỗi lượt, cộng dồn qua các tác vụ song song nên có thể lớn hơn thời gian chạy. `rest_ms` chỉ là xấp xỉ.

## Vị trí bàn giao theo phần việc

| Máy | Công việc | Tệp dự kiến |
|---|---|---|
| M1 / TV1 | Generator, DDL, B.1 và RQ3 rút gọn nếu còn thời gian | `bench/datagen.py`, `bench/schema.py`, `bench/storage_model.py`, `experiments/b1_storage.py`, `experiments/rq3_pk.py` |
| M2 / TV2 | Cấu hình hai DBMS, kết nối, nạp dữ liệu và RQ4 | `docker/`, `bench/config.py`, phần kết nối của `bench/db.py`, `scripts/use_engine.sh`, `scripts/load.sh`, `scripts/rq4_write.sh`, `sysbench/shipments_write.lua` |
| M3 / TV3 | Đo và phân tích RQ1/RQ2, sinh biểu đồ | `experiments/rq1_covering.py`, `experiments/rq1_summary.py`, `experiments/rq2_selectivity.py`, `experiments/plots.py` |

## Từ chuẩn bị đến báo cáo

1. Hoàn thiện cấu hình và mã dùng chung theo bảng phân công. Mỗi máy ghi `MACHINE_ID` và hồ sơ `PROFILE` theo đề cương.
2. Sinh dữ liệu trong `data/` với seed thống nhất, ghi SHA-256 và kiểm dữ liệu sau nạp. Mỗi máy chạy TiDB và MySQL luân phiên cho cùng một phép đối chứng.
3. Lưu bằng chứng và kết quả theo [quy ước trong `results/`](results/README.md). Chạy lại dùng ID riêng để truy vết được kết quả ban đầu.
4. Lấy số liệu đã kiểm tra từ CSV tổng hợp, chọn hình đưa vào `report/figures/` và soạn nội dung trong `report/sections/`. Điểm biên dịch là [`report/main.tex`](report/main.tex). Xem [hướng dẫn XeLaTeX](report/README.md#3-hướng-dẫn-biên-dịch-compile).
