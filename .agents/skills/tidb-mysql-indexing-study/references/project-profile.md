# Hồ sơ dự án — DBMS NewSQL TiDB và chi phí chỉ mục phụ

> Toàn bộ thông tin dưới đây được trích từ hai file kế hoạch nhóm cung cấp. Mặc định mang trạng thái `USER-PROVIDED` hoặc `PLANNED`, không phải bằng chứng hệ thống đã chạy.

## Thông tin đề tài

| Trường | Nội dung | Trạng thái |
|---|---|---|
| Môn học | Hệ quản trị cơ sở dữ liệu | USER-PROVIDED |
| Tên tiếng Việt | Nghiên cứu kiến trúc NewSQL phân tán và đánh giá thực nghiệm chi phí chỉ mục phụ trên TiDB so với MySQL | USER-PROVIDED |
| Tên tiếng Anh | Analyzing Distributed NewSQL Architecture: An Empirical Evaluation of Secondary Indexing Cost in TiDB Compared to MySQL | USER-PROVIDED |
| Nhóm | Nhóm 7 | USER-PROVIDED |
| Số thành viên | 3 | USER-PROVIDED |
| DBMS nghiên cứu | TiDB | PLANNED |
| DBMS đối chứng | MySQL InnoDB | PLANNED |
| Phiên bản TiDB | Kế hoạch triển khai pin `pingcap/*:v8.5.0`; đề cương còn ghi v8.5 / v7.5 LTS | CONFLICT / NEEDS CONFIRMATION |
| Phiên bản MySQL | MySQL 8.4 | PLANNED |
| Dataset | Logistics thương mại điện tử, bảng `shipments` | PLANNED |
| Quy mô dữ liệu | 1M dòng phát triển; 10M dòng đo chính thức; 30M tùy chọn | PLANNED |
| Phần báo cáo | Phần A khoảng 50%, Phần B khoảng 50% | USER-PROVIDED |

## Bài toán và dữ liệu

Bảng `shipments` dự kiến có 14 cột:

`id`, `tracking_code`, `sender_id`, `origin_hub_id`, `dest_hub_id`, `status`, `cod_amount`, `weight_grams`, `shipping_fee`, `recipient_phone`, `recipient_address`, `note`, `created_at`, `updated_at`.

Các workload nghiệp vụ được nêu trong kế hoạch:

- Tra cứu vận đơn theo `tracking_code`.
- Tra cứu/lọc vận đơn theo người gửi và thời gian tạo.
- Lọc theo bưu cục đích và trạng thái.
- Lọc theo khoảng tiền COD.
- Lọc theo trạng thái.
- Chèn vận đơn và cập nhật trạng thái giao hàng.

Các giá trị phân phối trong generator plan: `N_SENDERS=100_000`, `N_HUBS=200`, `COD_MAX=10_000_000`, `DAYS=180`, seed `20261116`; sender có phân phối Zipf (s=1.1), status 5 có tỷ lệ dự kiến 80%, `created_at` không giảm theo id. Đây là đặc tả generator dự kiến; chỉ ghi thành tính chất dataset thực nghiệm sau khi xác minh code và CSV đã sinh.

## Hệ thống và cấu hình dự kiến

### TiDB

- 1 PD node.
- 1 TiDB Server.
- 3 TiKV nodes.
- Replication mặc định dự kiến RF=3.
- TiKV block cache dự kiến 1 GB/node.
- Container memory limit dự kiến: TiKV 2.5 GB/node, TiDB 2 GB, PD 1 GB.
- CPU quota dự kiến tổng 7 cores: PD 1, TiDB 1.5, mỗi TiKV 1.5.

### MySQL

- MySQL 8.4 InnoDB, single instance.
- CPU quota dự kiến 7 cores.
- `innodb_buffer_pool_size=3G`.
- Container memory limit dự kiến 4 GB.
- Độ bền ghi dự kiến: `innodb_flush_log_at_trx_commit=1`, `sync_binlog=1`.

### Máy thực nghiệm

- 1 host, 16 GB RAM, 8 CPU cores.
- Không chạy TiDB và MySQL đồng thời khi đo.
- Hai hệ dùng cùng dữ liệu nguồn TSV/CSV sinh với seed cố định và cùng câu SQL ở từng case.
- Sau khi nạp, kế hoạch yêu cầu đối chiếu `COUNT(*)` và `SUM(cod_amount)`.

**Lưu ý diễn giải:** một host có nhiều container TiKV không tương đương cụm nhiều máy/zone. Chaos demo ở mức container chỉ có phạm vi lỗi container/tiến trình.

## Bộ chỉ mục chính cho RQ4

| Bộ | Index |
|---|---|
| 0 | Không có secondary index |
| 1 | `idx_code` trên `tracking_code` (unique) |
| 3 | `idx_code`, `idx_sender_created` trên `(sender_id, created_at)`, `idx_hub_status` trên `(dest_hub_id, status)` |
| 5 | Bộ 3 + `idx_cod` trên `cod_amount` + `idx_status` trên `status` |

Kế hoạch cũng có các biến thể phụ phục vụ RQ1 như `idx_code_cov`, `idx_sender`, `idx_sender_cov`, `idx_hub`; không nhập nhằng chúng với bộ 0/1/3/5 của RQ4.

## Kết quả dự kiến và kết quả thực tế

Tất cả các claim hiệu năng, dung lượng, độ trễ, số RPC, TPS, write amplification, thời gian failover và RPO trong đề cương hiện tại phải được đánh dấu là `HYPOTHESIS` hoặc `PLANNED` cho đến khi có CSV/log/screenshot thực tế. Không sao chép con số dự báo vào phần kết quả.
