# Mẫu Soạn Thảo LaTeX Cho Thành Viên 2 (TV2: Mục A.3 & B.3)

Tài liệu này cung cấp sẵn các khung đoạn văn và mẫu bảng biểu chuẩn LaTeX (tương thích mẫu `report2.tex` của UET) dành riêng cho phần việc của TV2.

---

## 1. Mẫu Bảng Số Liệu RQ4 Cho Mục B.3 (LaTeX)

```latex
\begin{table}[H]
\centering
\caption{Bảng B.3.1: Đối sánh Thông lượng ghi (TPS) và Độ trễ phân vị P95/P99 theo Số lượng Index phụ trên bảng 1 triệu dòng}
\label{tab:ket_qua_rq4}
\bangfont
\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}p{2.2cm}>{\centering\arraybackslash}p{1.2cm}>{\centering\arraybackslash}p{1.2cm}>{\raggedright\arraybackslash}p{1.4cm}>{\centering\arraybackslash}p{2.0cm}>{\centering\arraybackslash}p{1.8cm}>{\centering\arraybackslash}p{1.8cm}>{\centering\arraybackslash}p{1.8cm}@{}}
\toprule
\textbf{Cấu hình Hệ} & \textbf{Replicas} & \textbf{Luồng} & \textbf{Tải ghi} & \textbf{0 Index (Gốc)} & \textbf{1 Index} & \textbf{3 Index} & \textbf{5 Index}\\
\midrule
\multirow{4}{*}{\textbf{MySQL 8.4}} 
 & -- & 16 & W1 (Insert) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & -- & 16 & W2 (Update) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & -- & 64 & W1 (Insert) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & -- & 64 & W2 (Update) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
\midrule
\multirow{4}{*}{\textbf{TiDB v8.5.5 (RF=3)}} 
 & 3 & 16 & W1 (Insert) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & 3 & 16 & W2 (Update) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & 3 & 64 & W1 (Insert) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & 3 & 64 & W2 (Update) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
\midrule
\multirow{4}{*}{\textbf{TiDB v8.5.5 (RF=1)}} 
 & 1 & 16 & W1 (Insert) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & 1 & 16 & W2 (Update) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & 1 & 64 & W1 (Insert) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
 & 1 & 64 & W2 (Update) & [TPS / p95] & [TPS / p95] & [TPS / p95] & [TPS / p95]\\
\bottomrule
\end{tabularx}
\end{table}
```

---

## 2. Khung Lập Luận Cho Mục B.3

Các khung dưới đây **không chứa kết luận**. Điền số đo vào `[...]` rồi mới chọn hướng diễn giải. Nếu số đo trái giả thuyết thì viết đúng như số đo. Cột Replicas của MySQL là "--" (không áp dụng).

### W1 và W2
> *"Khi tăng từ 0 lên 5 index ở [16/64] luồng, TPS của W1 đổi [..]% trên MySQL và [..]% trên TiDB RF=3 (trung vị 3 lần, khoảng dao động [..]). Với W2, mức đổi là [..]% và [..]%. W1 ghi vào mọi index, còn W2 chỉ chạm `idx_hub_status` và `idx_status`. Số đo [ủng hộ / bác bỏ / chưa đủ để kết luận] giả thuyết chi phí tăng theo số index bị ảnh hưởng."*

Lưu ý: khóa clustered và mỗi index là các cặp KV riêng, nên một INSERT với 5 index ghi 6 key thay vì 1. Đây là cơ chế, không phải bằng chứng cho mức giảm TPS.

### RF=3 và RF=1
> *"Cả hai cấu hình chạy trên 3 TiKV. So với RF=1 (quorum 1/1), RF=3 (quorum 2/3) có TPS [cao/thấp] hơn [..]% và p99 chênh [..] ms. Chênh lệch này là tổng chi phí nhân bản, gồm Raft log, fsync, CPU của Follower và tranh chấp ổ đĩa chung, không tách được riêng phần mạng. Phân bố Leader trên ba store là [..]."*

RF=3 chỉ chịu được lỗi ở mức container trong thực nghiệm này, vì cả ba TiKV nằm trên một máy.

### Khuếch đại ghi
> *"Byte ghi trên mỗi giao dịch là [..] trên MySQL và [..] trên TiDB RF=3 ở [..] index (dao động [..])."*

Hai cơ chế cần cân nhắc: tách trang của B+Tree khi chèn khóa ngẫu nhiên, và compaction của LSM-Tree. Byte ghi của TiDB cộng cả ba bản sao, nên so thêm với RF=1.

### Covering index
> *"So với `idx_sender_created`, `idx_sender_cov` đổi TPS [..]% ở W1 và [..]% ở W2, dung lượng index tăng [..]. Đổi lại, độ trễ Q2 đổi [..] (xem RQ1)."*
