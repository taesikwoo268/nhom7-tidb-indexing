---
name: it-report-auditor
description: Kiểm định báo cáo đồ án/dự án IT trước khi nộp, rà tính đúng với source code, logic chương mục, mục tiêu, số liệu, hình bảng, sơ đồ, trích dẫn, thuật ngữ, văn phong và định dạng. Dùng khi cần review, audit hoặc hoàn thiện báo cáo.
---

# IT Report Auditor

## Mục tiêu

Đánh giá báo cáo dựa trên tiêu chí và bằng chứng, không chỉ sửa câu chữ. Không tự động sửa các lỗi làm thay đổi ý nghĩa kỹ thuật.

## Quy trình audit

### 1. Kiểm tra yêu cầu và cấu trúc

- Đối chiếu từng yêu cầu trong rubric/template.
- Kiểm tra các phần bắt buộc, thứ tự chương, đánh số, giới hạn trang và phụ lục.
- Xác định mục tiêu, phạm vi, phương pháp, kết quả và kết luận có khớp nhau không.

### 2. Kiểm tra tính đúng kỹ thuật

- Đối chiếu stack, module, API, database, công nghệ, luồng xử lý với source code.
- Kiểm tra sơ đồ với kiến trúc hiện tại.
- Phân biệt thiết kế tương lai và tính năng đã triển khai.
- Kiểm tra tên class/function/table/endpoint, version và lệnh chạy.
- Tìm các claim không có bằng chứng hoặc được suy rộng quá mức.

### 3. Kiểm tra kết quả và số liệu

- Mỗi số liệu có nguồn, đơn vị, môi trường, cách đo và số lần lặp phù hợp.
- Không có số liệu minh họa bị trình bày như kết quả thực nghiệm.
- Bảng/biểu đồ có cùng số liệu với phần phân tích.
- Kết luận không vượt quá những gì dữ liệu chứng minh.

### 4. Kiểm tra logic và tính học thuật

- Chương 2 phục vụ chương 3–4, không chỉ là danh sách định nghĩa.
- Chương 3 trình bày thiết kế, chương 4 trình bày hiện thực; tránh sao chép lặp.
- Chương 5 trả lời mục tiêu và tiêu chí đã đặt ra.
- Kết luận tóm tắt kết quả, không đưa tính năng mới chưa trình bày.
- Lập luận theo mạch vấn đề → mục tiêu → phương pháp → thiết kế → triển khai → đánh giá.

### 5. Kiểm tra hình thức

- Đánh số chương/mục/hình/bảng nhất quán.
- Mỗi hình/bảng được nhắc trong văn bản và có caption.
- Sơ đồ có thể đọc được, nhãn rõ, không bị vỡ/cắt.
- Thuật ngữ và chữ viết tắt được định nghĩa và sử dụng nhất quán.
- Tài liệu tham khảo thống nhất theo một style.
- Kiểm tra link, cross-reference, mục lục và placeholder.
- Không để lại `[CẦN BỔ SUNG]`, `TODO`, `TBD`, nội dung nháp hoặc lời nhắc nội bộ trong bản nộp cuối (trừ khi người dùng yêu cầu để lại).

## Phân loại phát hiện

- `BLOCKER`: sai sự thật kỹ thuật, số liệu bịa/không thể xác minh, vi phạm yêu cầu bắt buộc, thiếu phần cốt lõi.
- `MAJOR`: thiếu lập luận/bằng chứng quan trọng, mâu thuẫn giữa chương, sơ đồ sai, trích dẫn sai.
- `MINOR`: lỗi diễn đạt, thuật ngữ, định dạng hoặc tham chiếu nhỏ.
- `SUGGESTION`: cải thiện thêm nhưng không bắt buộc.

Mỗi phát hiện phải nêu: vị trí, vấn đề, vì sao quan trọng, bằng chứng đối chiếu và cách sửa cụ thể. Không chỉ đưa nhận xét chung chung.

## Đầu ra

Tạo `docs/report/review-report.md` với:

1. Tóm tắt trạng thái (không dùng điểm số giả).
2. Các blocker/major/minor/suggestion.
3. Ma trận yêu cầu rubric và trạng thái.
4. Claim cần xác minh và bằng chứng còn thiếu.
5. Danh sách hành động ưu tiên trước khi nộp.
6. Những phần chưa thể audit do thiếu quyền truy cập hoặc dữ liệu.

Nếu người dùng yêu cầu sửa trực tiếp, sửa lỗi an toàn và giữ nguyên ý nghĩa. Với lỗi kỹ thuật hoặc mâu thuẫn chưa rõ, đưa đề xuất và chờ xác nhận trước khi đổi nội dung.

## Checklist chuyên biệt cho TiDB–MySQL benchmark

Trước khi duyệt báo cáo này, kiểm tra tối thiểu:

- [ ] TiDB version exact và MySQL version exact nhất quán ở mọi chương/bảng/hình.
- [ ] TiDB Region defaults/config phù hợp phiên bản; không mặc định 96 MiB với v8.5 khi chưa cấu hình.
- [ ] Transaction isolation không nhầm Snapshot Isolation với Serializable.
- [ ] MySQL 8.4 DATETIME byte size khớp FSP và DDL; VARCHAR đo theo byte/charset, có length prefix.
- [ ] Mô hình index size tính đúng primary-key handle; tách clustered/nonclustered PK và code_clustered.
- [ ] Compression ratio, fill factor, LSM amplification, per-entry bytes và replica overhead có nhãn assumption/nguồn/độ nhạy.
- [ ] Không nhân RF hai lần; phân biệt per-replica với whole-cluster.
- [ ] `information_schema`, TiDB approximate size và `du` không bị coi là cùng loại metric.
- [ ] Dataset file hash/seed/row count/checksum được lưu; hai hệ nạp cùng dữ liệu.
- [ ] EXPLAIN chứng minh index hint/access path được áp dụng.
- [ ] Performance crossover và optimizer crossover RQ2 tách riêng.
- [ ] RQ1 RPC/coprocessor counts là giá trị đo, không phải giả định cố định.
- [ ] RQ4 bytes written là delta; WA có numerator/denominator cùng cửa sổ.
- [ ] RF=1 được diễn giải là ablation, không so sánh như cấu hình HA bình đẳng.
- [ ] Chaos demo single-host chỉ kết luận lỗi container/process.
- [ ] 1M pilot không trộn với 10M official.
- [ ] Biểu đồ khớp CSV và có đơn vị, sample size, conditions.
- [ ] Kết luận có thể nói TiDB tốt hơn, tương đương hoặc kém hơn tùy theo dữ liệu; không ép kết luận theo mục tiêu ban đầu.
