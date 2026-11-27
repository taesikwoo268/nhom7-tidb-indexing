# Khung báo cáo nhóm 7

Định dạng lấy theo báo cáo mẫu của nhóm (bìa UET, tóm tắt, phân công, mục lục, danh sách hình và bảng, từ viết tắt). Nội dung chia theo Phần 1 và Phần 2 mà giảng viên yêu cầu. Mã A.x, B.x là mã trong kế hoạch của nhóm.

## Ai viết file nào

Mỗi người chỉ sửa file của mình trong `sections/`. Không sửa `main.tex`, trừ thông tin bìa ở mục 6.

| File | Nội dung | Người viết |
|---|---|---|
| `00_mo_dau.tex` | Cam đoan, tóm tắt, phân công | TV1, cả nhóm sửa dòng của mình |
| `00_viet_tat.tex` | Từ viết tắt | Cả nhóm |
| `a1_du_lieu.tex`, `a0_tong_quan.tex`, `a2_kien_truc.tex` | Chương 1, dữ liệu, tổng quan, kiến trúc (A.1, A.2) | TV1 |
| `a3_cai_dat.tex`, `a3_van_hanh.tex`, `a3_demo_co_ban.tex` | Chương 2, cài đặt, vận hành, demo cơ bản (A.3) | TV2 |
| `a3_demo.tex` | Chương 2, demo bổ sung (A.3) | TV2 |
| `p2_van_de_co_che.tex` | Chương 3, vấn đề, câu hỏi, mục tiêu, phạm vi, cơ chế | TV1 |
| `p2_phuong_phap.tex` | Chương 3, phương pháp và kịch bản | TV2 |
| `b0_so_bo.tex` | Chương 4, thực nghiệm sơ bộ (B.0) | TV3 |
| `b1_dung_luong.tex` | Chương 4, dung lượng (B.1) | TV1 |
| `b1_rq3.tex` | Chương 4, RQ3: kiểu khóa chính | TV2 |
| `b2_chi_phi_doc.tex` | Chương 5 (B.2) | TV3 |
| `b3_chi_phi_ghi.tex` | Chương 6 (B.3) | TV2 |
| `b4_tong_hop.tex` | Chương 7, giả thuyết và khuyến nghị (B.4) | TV1 |
| `b4_han_che.tex` | Chương 7, hạn chế (B.4) | TV3 |
| `ket_luan.tex` | Kết luận | TV1 |
| `tai_lieu_tham_khao.tex` | Tài liệu tham khảo | Cả nhóm thêm, TV1 rà |

`01_phan_a.tex`, `02_phan_b.tex`, `03_ket_luan.tex` và `04_phu_luc.tex` là bản cũ, không còn được biên dịch. Chỉ dùng để tham khảo, vì có nhiều số và nhận định chưa được kiểm chứng.

## Yêu cầu của giảng viên nằm ở đâu

| Yêu cầu | Vị trí trong khung |
|---|---|
| Phần 1: tổng quan, kiến trúc, thành phần chính | Chương 1 |
| Phần 1: cài đặt, cấu hình, vận hành, demo chức năng cơ bản | Chương 2 |
| Phần 1: trình bày tổng quát, chi tiết dẫn ra ngoài | Kho mã (dẫn ở đầu Chương 2) |
| Phần 2: vấn đề đã đăng ký, cơ chế, phương pháp, kịch bản | Chương 3 và đầu Chương 4, 5, 6 |
| Phần 2: phân tích kết quả | Chương 4, 5, 6, 7 |
| Phần 2: dữ liệu và thực nghiệm thực tế (bắt buộc) | Chương 4, 5, 6; mỗi bảng ghi file nguồn trong `results/` |

Phần 1 viết tổng quát. Phần nào cần nhiều lệnh thì dẫn sang kho mã. Báo cáo không có Phụ lục và không có mục trả lời nhận xét riêng (nhóm quyết định 26/11/2026); ba nhận xét của giảng viên được trả lời ngay trong Chương 2, 5, 6. Báo cáo không có chương Đặt vấn đề riêng: câu hỏi, mục tiêu và phạm vi nằm ở đầu Phần 2 (Chương 3).

## Lệnh có sẵn

| Lệnh | Dùng để |
|---|---|
| `\ghichu{...}` | Ghi chú biên soạn. Viết xong mục nào thì xóa ghi chú của mục đó |
| `\phutrach{TV2}` | Ghi người viết mục |
| `\chuaco` | Ô bảng chưa có số. Thay bằng số thật, không để ước lượng |
| `\hinhcho{mô tả}{chú thích}{fig:nhan}` | Khung giữ chỗ cho hình chưa có |
| `\hinh{ten.png}{0.9}{chú thích}{fig:nhan}` | Chèn hình trong `figures/` |
| `\code{...}` | Tên lệnh, cột, bảng. Viết `\_` thay cho `_` |
| `\path{...}` | Đường dẫn file, viết `_` bình thường |
| `\bangfont`, `\bangnho`, `\dongdau` | Cỡ chữ bảng và nền dòng đầu |

Bảng và hình luôn có `\caption` và `\label`, và được nhắc trong bài bằng `Bảng~\ref{tab:...}` hoặc `Hình~\ref{fig:...}`. Trong đoạn mã `lstlisting` chỉ viết chữ không dấu.

## Quy tắc viết

- Mỗi con số có nguồn là một CSV trong `results/`. Số thập phân dùng dấu phẩy, hàng nghìn dùng dấu chấm.
- Chỉ so TiDB với MySQL trên cùng máy. Giữa các máy chỉ so tỉ lệ.
- Dùng C3 và C1 đúng như Bảng "Định nghĩa cấu hình bản sao", không viết RF=3, RF=1.
- Không giấu kết quả trái giả thuyết, không bỏ lượt đo, không quy mọi chênh lệch cho mạng.
- Không viết "vượt trội", "tuyệt đối", "triệt để".

## Biên dịch

- **Overleaf:** nén thư mục `report/` (bỏ `ReportExample/`), tải lên bằng New Project → Upload Project, rồi chọn Menu → Compiler → XeLaTeX.
- **Máy cá nhân:** chạy `compile.bat`, hoặc chạy `xelatex main.tex` ít nhất hai lần.

Trước khi nộp, đổi `\biensoantrue` thành `\biensoanfalse` trong `main.tex` để ẩn mọi ghi chú, rồi tìm và thay hết `\chuaco` và `\hinhcho`.
