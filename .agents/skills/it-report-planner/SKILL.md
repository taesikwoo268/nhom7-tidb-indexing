---
name: it-report-planner
description: Lập đề cương báo cáo đồ án/dự án IT bằng tiếng Việt, chuyển đề bài và source code thành cấu trúc chương, mục, ma trận truy vết yêu cầu–chức năng–mã nguồn–kiểm thử và kế hoạch viết. Dùng trước khi soạn báo cáo hoặc khi cần tổ chức lại nội dung.
---

# IT Report Planner

## Đầu vào cần xem

- Đề bài, rubric, template Word/LaTeX, hướng dẫn trình bày và giới hạn trang.
- `docs/report/00-project-profile.md` và `01-evidence-ledger.md` nếu đã có.
- Báo cáo/đề cương cũ (nếu người dùng cung cấp).

Không yêu cầu người dùng lặp lại thông tin đã có trong workspace. Nếu thiếu, đánh dấu chưa cung cấp và thiết kế phần có thể làm.

## Quy trình lập đề cương

1. Viết lại vấn đề cần giải quyết trong 1–3 câu, phân biệt bối cảnh và vấn đề thực tế.
2. Chuyển mục tiêu thành mục tiêu cụ thể, có thể kiểm chứng.
3. Xác định đối tượng, phạm vi, giả định, giới hạn và nội dung ngoài phạm vi.
4. Xác định phương pháp: khảo sát, phân tích yêu cầu, thiết kế, xây dựng, kiểm thử, đánh giá. Chỉ ghi phương pháp nhóm thực sự dùng hoặc dự kiến dùng.
5. Chọn cấu trúc chương phù hợp template.
6. Với từng mục, ghi: mục đích, câu hỏi cần trả lời, dữ liệu/bằng chứng cần có, độ dài dự kiến và trạng thái.
7. Lập ma trận truy vết: mục tiêu → yêu cầu → chức năng → module/API/database → test case → bằng chứng/kết quả.
8. Chỉ ra mục nào cần hình, bảng, sơ đồ hoặc phụ lục.
9. Đánh dấu nội dung bị trùng, không liên quan hoặc vượt phạm vi.

## Cấu trúc tham khảo khi không có template

### Chương 1. Giới thiệu
- Bối cảnh và lý do chọn đề tài.
- Phát biểu vấn đề.
- Mục tiêu tổng quát và mục tiêu cụ thể.
- Đối tượng, phạm vi và giới hạn.
- Phương pháp thực hiện.
- Bố cục báo cáo.

### Chương 2. Cơ sở lý thuyết và công nghệ
- Khái niệm nền tảng trực tiếp liên quan.
- Công nghệ/giải pháp được cân nhắc.
- Tiêu chí lựa chọn và lý do chọn.
- Chỉ trình bày kiến thức cần để hiểu thiết kế/triển khai ở chương sau.

### Chương 3. Phân tích yêu cầu và thiết kế hệ thống
- Đối tượng sử dụng và bối cảnh vận hành.
- Yêu cầu chức năng/phi chức năng.
- Use case hoặc user flow.
- Kiến trúc tổng thể và các thành phần.
- Thiết kế dữ liệu, API, giao diện và bảo mật.
- Quyết định thiết kế quan trọng và đánh đổi.

### Chương 4. Xây dựng và triển khai
- Môi trường, công cụ và phiên bản có bằng chứng.
- Cấu trúc source code và trách nhiệm module.
- Các luồng chức năng quan trọng.
- Cơ chế xử lý lỗi, xác thực, phân quyền, logging nếu có.
- Giao diện và triển khai thực tế.

### Chương 5. Kiểm thử và đánh giá
- Môi trường và phương pháp kiểm thử.
- Test case và kết quả.
- Đánh giá theo mục tiêu/tiêu chí.
- Phân tích lỗi, giới hạn và threat to validity.

### Chương 6. Kết luận và hướng phát triển
- Kết quả đối chiếu với từng mục tiêu.
- Những nội dung đã hoàn thành/chưa hoàn thành.
- Hạn chế.
- Hướng phát triển cụ thể và có cơ sở.

## Ma trận truy vết

Dùng mẫu trong `.agents/skills/vietnamese-it-project-report/references/traceability-matrix-template.md` (hoặc `resources/traceability-matrix-template.md`). Mỗi mục tiêu phải được nối với chức năng và cách chứng minh. Không chấp nhận mục tiêu quan trọng không có phương pháp đánh giá; cũng không nên trình bày chức năng ngoài phạm vi như kết quả chính.

## Nguyên tắc chọn nội dung

- Chương công nghệ không phải danh sách định nghĩa. Chỉ giữ khái niệm giải thích quyết định kỹ thuật thực sự.
- Chương phân tích và thiết kế trình bày điều hệ thống cần làm và cách dự kiến tổ chức.
- Chương triển khai trình bày điều đã thực hiện trong code.
- Chương kiểm thử trình bày điều đã kiểm tra và kết quả quan sát được.
- Không lặp toàn bộ mô tả chức năng ở cả chương 3 và chương 4: chương 3 giải thích thiết kế, chương 4 giải thích hiện thực.
- Tránh mục quá nhỏ, chỉ có một câu; gom các mục liên quan.
- Đề cương phải vừa với dung lượng, trình độ và phạm vi đồ án.

## Đầu ra

Tạo `docs/report/02-report-outline.md` và `docs/report/03-traceability-matrix.md`. Kèm danh sách bằng chứng còn thiếu (ví dụ ảnh giao diện, sơ đồ, log test, quyết định của nhóm) và thứ tự viết tối ưu.

## Chế độ môn Hệ quản trị cơ sở dữ liệu — TiDB vs MySQL

Nếu đề tài nghiên cứu TiDB vs MySQL trong workspace, đọc skill `tidb-mysql-indexing-study` và tuân thủ:

- Giữ bố cục Phần A/Phần B khoảng 50/50 như kế hoạch của giảng viên; không áp outline phần mềm thông thường.
- A: A.1 dữ liệu logistics và chọn TiDB; A.2 kiến trúc; A.3 cài đặt và chaos demo.
- B: B.1 mô hình lưu trữ và số đo; B.2 read workload RQ1–RQ3; B.3 write workload RQ4 và trade-offs.
- Tạo ma trận RQ → giả thuyết → biến → metric → query/script → CSV/log → mục báo cáo.
- Đánh dấu tất cả số dự báo trong kế hoạch là `HYPOTHESIS/PLANNED`, không phải kết quả.
- Không thay cấu trúc RQ hoặc phạm vi 1M/10M nếu chưa có quyết định nhóm/giảng viên.
- Ghi riêng sự khác biệt giữa benchmark ở 1M (pilot) và 10M (official run).
