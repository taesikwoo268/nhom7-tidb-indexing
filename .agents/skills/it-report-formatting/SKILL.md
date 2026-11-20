---
name: it-report-formatting
description: Chuẩn hóa và định dạng báo cáo đồ án IT trong Word, LaTeX hoặc Markdown; xử lý tiêu đề, mục lục, caption, đánh số hình bảng, code, phụ lục và xuất bản theo template của trường. Dùng khi cần hoàn thiện layout hoặc chuyển đổi định dạng báo cáo.
---

# IT Report Formatting

## Quy tắc ưu tiên

1. Template và quy định định dạng chính thức do người dùng/giảng viên cung cấp.
2. Mẫu báo cáo hiện có của cùng môn/trường nếu được xác nhận.
3. Cấu hình mặc định đề xuất trong skill này.

Không tự đặt font, lề, giãn dòng, cỡ chữ hay quy tắc bìa như thể đó là yêu cầu chính thức. Nếu thiếu hướng dẫn, hãy hỏi hoặc ghi rõ dùng cấu hình tạm thời.

## Word / DOCX

- Dùng Styles thực sự (`Title`, `Heading 1`, `Heading 2`, `Heading 3`, `Caption`, `Normal`) thay vì định dạng thủ công từng đoạn.
- Mục lục, danh mục hình/bảng nên là field tự động nếu công cụ hỗ trợ.
- Không dùng nhiều dấu cách để canh lề; không dùng Enter lặp để đẩy trang.
- Bảng có header rõ, không bị cắt khó đọc; lặp header row nếu bảng qua trang và công cụ hỗ trợ.
- Ảnh giữ tỷ lệ, đủ độ phân giải; caption gắn với ảnh/bảng.
- Code dùng font monospace, wrap hợp lý, trích đoạn ngắn và có giải thích.
- Header/footer, số trang, section break và trang bìa làm theo mẫu.

## LaTeX

- Ưu tiên template hiện có; không thay class hoặc preamble lớn nếu không cần.
- Quản lý bibliography bằng BibTeX/Biber theo template.
- Dùng `\label`/`\ref`/`\autoref` hoặc cơ chế template để tham chiếu.
- Caption, table placement, code listing và hình phải thống nhất.
- Kiểm tra compile log, reference undefined, citation undefined, overfull/underfull đáng kể.
- Không thêm package hoặc macro không tương thích với template nếu chưa kiểm tra.

## Markdown

- Heading có cấp bậc, không nhảy cấp tùy tiện.
- Dùng relative links cho assets trong repository.
- Sơ đồ nên lưu source Mermaid/PlantUML và render nếu cần.
- Bảng không quá rộng; nội dung dài nên viết thành đoạn hoặc chia bảng.

## Quy trình bàn giao

1. Xác định định dạng nguồn và đích.
2. Đọc template hiện tại.
3. Chỉ áp dụng thay đổi định dạng, không thay đổi nội dung kỹ thuật ngoài yêu cầu.
4. Render/export nếu có công cụ.
5. Kiểm tra trang đầu, mục lục, trang có bảng/hình lớn, phụ lục và trang cuối.
6. Kiểm tra lỗi font tiếng Việt, ngắt dòng, hình mờ, caption và cross-reference.
7. Báo rõ định dạng đã kiểm tra, công cụ đã dùng và phần chưa thể kiểm tra.

Không tuyên bố file DOCX/PDF hiển thị hoàn hảo nếu chưa render hoặc mở kiểm tra.


## Chế độ báo cáo thực nghiệm DBMS — TiDB vs MySQL

Khi định dạng báo cáo môn Hệ quản trị cơ sở dữ liệu này:

- Giữ cấu trúc hai phần A/B theo đề cương đã được nhóm/giảng viên thống nhất; không tự đổi thành mẫu báo cáo xây dựng phần mềm.
- Công thức phải có ký hiệu, định nghĩa biến, đơn vị, giả định và ví dụ thay số; phân biệt B, KiB, MiB, GiB với byte thập phân.
- Bảng benchmark phải ghi engine/version, dataset size, index set, concurrency, RF (nếu có), metric, đơn vị và `run_id` hoặc nguồn CSV.
- Mỗi biểu đồ phải có trục/đơn vị, legend, cỡ mẫu hoặc số lần lặp, chú thích cấu hình; không cắt trục gây hiểu nhầm.
- Phân biệt rõ bảng `theoretical estimate`, `engine-reported size` và `physical disk footprint`; không đặt chung dưới một nhãn “dung lượng” nếu khác định nghĩa.
- Các SQL dài, DDL, lệnh Docker, script và cấu hình đầy đủ ưu tiên đưa vào phụ lục; phần chính chỉ trích đoạn cần giải thích.
- Không tự chỉnh số liệu hoặc làm tròn khiến thứ hạng TiDB/MySQL thay đổi; lưu đủ chữ số trong bảng nguồn và nêu quy tắc làm tròn.
- Trước khi xuất DOCX/PDF, kiểm tra bảng rộng, phương trình dài, dấu tiếng Việt, code monospace, caption và liên kết tới phụ lục.
