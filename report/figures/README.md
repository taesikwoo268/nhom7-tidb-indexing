Thư mục chứa các hình ảnh minh chứng và đồ thị thực nghiệm được chèn vào báo cáo LaTeX:

1. `tidb_architecture.png`: Sơ đồ kiến trúc phân tầng TiDB (Đã tích hợp sẵn TikZ vector dự phòng trong file `01_phan_a.tex` nếu chưa có file ảnh).
2. `tidb_dashboard.png`: Ảnh chụp màn hình giao diện TiDB Dashboard (Topology cụm 3 node TiKV và phân bổ Region).
3. `benchmark_scalability.png`: Đồ thị biểu diễn thông lượng TPS và độ trễ P99 giữa MySQL và TiDB từ 16 đến 512 luồng.
4. `chaos_test_recovery.png`: Đồ thị diễn biến QPS theo từng giây trước và sau sự cố sập node tại thời điểm t = 60s (đối chứng MySQL sập 100% vs TiDB tự phục hồi sau 3-8 giây).

*Lưu ý:* Mẫu LaTeX đã được lập trình sẵn cơ chế `\IfFileExists` an toàn tuyệt đối: nếu file ảnh chưa được đặt vào thư mục này, trình biên dịch XeLaTeX sẽ tự động hiển thị khung placeholder mô tả mà không bao giờ báo lỗi dừng biên dịch!
