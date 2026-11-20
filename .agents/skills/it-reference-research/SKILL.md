---
name: it-reference-research
description: Tìm kiếm, đánh giá, xác minh và chuẩn hóa tài liệu tham khảo cho báo cáo đồ án IT bằng APA hoặc IEEE; ưu tiên tài liệu chính thức, bài báo và tiêu chuẩn có thể truy cập. Dùng khi cần nguồn cho cơ sở lý thuyết, công nghệ, thuật toán, tiêu chuẩn hoặc trích dẫn.
---

# IT Reference Research

## Mục tiêu

Tạo danh mục nguồn có thật, liên quan trực tiếp và có thể kiểm tra. Không tạo citation để trang trí, không bịa tác giả, tiêu đề, năm, DOI, số trang hoặc URL.

## Chiến lược tìm nguồn

Ưu tiên theo thứ tự, tùy chủ đề:

1. Tài liệu chính thức của nhà cung cấp/framework/tiêu chuẩn (ví dụ documentation, RFC, specification).
2. Bài báo khoa học gốc, proceedings, sách học thuật hoặc nhà xuất bản uy tín.
3. Tài liệu kỹ thuật của tổ chức có uy tín.
4. Bài viết chuyên sâu có tác giả và ngày xuất bản rõ ràng.
5. Blog/cộng đồng chỉ dùng cho kinh nghiệm hoặc vấn đề thực hành, không làm căn cứ duy nhất cho định nghĩa/khẳng định trọng yếu.

Không dùng kết quả tìm kiếm hoặc snippet làm bằng chứng cuối cùng. Mở trang/đọc tài liệu để kiểm tra ngữ cảnh và ngày.

## Quy trình xác minh

Mỗi nguồn phải có:

- Tác giả/tổ chức.
- Tiêu đề chính xác.
- Năm/ngày xuất bản hoặc cập nhật nếu có.
- Tên tạp chí/hội nghị/nhà xuất bản/trang web.
- DOI hoặc URL ổn định.
- Ngày truy cập với trang web nếu style/giảng viên yêu cầu.
- Luận điểm cụ thể mà nguồn hỗ trợ.
- Phần/trang/section liên quan nếu xác định được.

Kiểm tra nguồn có thực sự nói điều mà đoạn báo cáo trích dẫn không. Không dẫn một trang tổng quan để hỗ trợ claim rất cụ thể nếu tài liệu không chứa claim đó.

## APA và IEEE

- Dùng duy nhất một style xuyên suốt, trừ khi template yêu cầu khác.
- **IEEE**: đánh số theo thứ tự xuất hiện `[1]`, `[2]`; danh mục sắp theo số trích dẫn. Không tự suy đoán thông tin xuất bản.
- **APA 7**: trích dẫn tác giả–năm trong nội dung; danh mục theo alphabet. Với tổ chức là tác giả, dùng tên tổ chức thống nhất.
- Nếu người dùng chưa chỉ định, hỏi một câu hoặc chọn IEEE tạm thời cho báo cáo kỹ thuật và ghi rõ để người dùng đổi theo yêu cầu trường.
- Dùng DOI dạng URL `https://doi.org/...` khi xác minh được.
- Không tạo citation giả để lấp mục chưa có nguồn.

## Quản lý nguồn

Lưu `docs/report/references.md` với các cột:

| ID | Tài liệu | Loại nguồn | Năm | URL/DOI | Luận điểm được hỗ trợ | Trạng thái |
|---|---|---|---|---|---|---|

Trạng thái: `VERIFIED`, `NEEDS_CHECK`, `REJECTED`.

Giữ một bảng mapping claim → reference để tránh trích dẫn không đúng vị trí. Nếu nguồn đã thay đổi sau thời điểm nghiên cứu, ghi ngày truy cập và phiên bản tài liệu nếu có.

## Khi không thể tra cứu web

- Không giả vờ đã xác minh nguồn.
- Có thể dùng tài liệu người dùng cung cấp và ghi `USER-PROVIDED — NOT INDEPENDENTLY VERIFIED`.
- Đề xuất truy vấn tìm kiếm hoặc placeholder `[CẦN NGUỒN: ...]`.
- Không tự tạo danh mục từ trí nhớ nếu thông tin thư mục không chắc chắn.

## Kiểm tra trước khi bàn giao

- Mỗi citation trong nội dung có entry trong danh mục và ngược lại (trừ nguồn chỉ tham khảo không trích dẫn nếu style cho phép).
- Không có ID trùng hoặc citation bị nhảy số sai.
- URL/DOI có thể mở và trỏ đúng tài liệu.
- Ngày/tác giả/tiêu đề/phiên bản đúng.
- Claim được hỗ trợ đúng phạm vi và không bị phóng đại.

## Nguồn tham khảo chuyên biệt cho DBMS study

Với TiDB vs MySQL:

- Dùng tài liệu PingCAP theo exact version chạy (ví dụ nhánh v8.5), tránh dùng tài liệu `stable` nếu phiên bản đã khác.
- Dùng MySQL 8.4 Reference Manual cho InnoDB row/storage/index semantics.
- Dùng tài liệu RocksDB gốc và bài báo/sách học thuật để giải thích LSM/compaction/write amplification.
- Mỗi claim version-sensitive (Region size, isolation, system variable, operator, clustered index) phải lưu version + URL + section + ngày truy cập.
- Đặc biệt kiểm tra `.agents/skills/tidb-mysql-indexing-study/references/risk-register.md` trước khi trích dẫn. Không dùng Whitepaper như bằng chứng cho cấu hình thực nghiệm nếu không đối chiếu với exact release docs.
