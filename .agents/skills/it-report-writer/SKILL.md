---
name: it-report-writer
description: Soạn thảo, viết lại và biên tập từng chương/mục báo cáo đồ án hoặc dự án IT bằng tiếng Việt học thuật-kỹ thuật; giữ nguyên sự thật kỹ thuật, thuật ngữ, số liệu và cấu trúc template. Dùng khi người dùng muốn viết hoặc chỉnh sửa nội dung báo cáo.
---

# IT Report Writer

## Trước khi viết

1. Đọc đề cương/đề bài/template và xác định chính xác chương, mục, mục tiêu của phần cần viết.
2. Đọc hồ sơ dự án và evidence ledger. Nếu chưa có, yêu cầu chạy `it-project-reconnaissance` hoặc khảo sát phần liên quan.
3. Đọc đúng source file/symbol liên quan thay vì dựa vào tên module.
4. Xác định người đọc và mức kỹ thuật cần thiết.
5. Liệt kê thông tin đã xác minh, thông tin do người dùng cung cấp và thông tin còn thiếu.

## Quy trình viết từng mục

1. Viết câu chủ đề nêu rõ nội dung mục.
2. Giải thích vấn đề hoặc lý do cần thành phần đó.
3. Mô tả thiết kế/hiện thực đúng giai đoạn: dự kiến, đã triển khai, hoặc đã kiểm thử.
4. Đưa bằng chứng phù hợp: sơ đồ, bảng, đường dẫn file, test case, ảnh chụp, log hoặc nguồn tham khảo.
5. Phân tích ý nghĩa, đánh đổi, giới hạn hoặc tác động.
6. Kết thúc bằng câu chuyển tiếp tự nhiên nếu cần.

## Quy tắc phân biệt nội dung

- **Yêu cầu**: điều hệ thống cần đáp ứng.
- **Thiết kế**: cách nhóm quyết định giải quyết.
- **Triển khai**: cách code hiện tại thực hiện.
- **Kiểm thử**: cách đã kiểm tra.
- **Kết quả**: điều quan sát/đo được.

Không trộn lẫn năm loại nội dung này. Một chức năng có trong đề cương nhưng chưa có code phải ghi là yêu cầu hoặc kế hoạch, không mô tả như đã hoàn thành.

## Văn phong tiếng Việt

- Trang trọng, chính xác, mạch lạc; tránh dịch word-by-word từ tiếng Anh.
- Dùng thuật ngữ nhất quán; giải thích thuật ngữ ở lần đầu xuất hiện.
- Giữ nguyên code identifier và tên riêng của công nghệ.
- Tránh các cụm rỗng: “trong thời đại công nghệ 4.0”, “vô cùng quan trọng”, “đóng vai trò then chốt” nếu không bổ sung thông tin.
- Tránh tuyên bố tuyệt đối như “đảm bảo an toàn”, “không thể xảy ra lỗi”, “tối ưu nhất”. Dùng phạm vi chính xác như “hỗ trợ”, “giảm nguy cơ”, “đã kiểm thử trong các trường hợp...”.
- Không viết mỗi câu thành một bullet. Dùng đoạn văn để giải thích và dùng danh sách/bảng khi cần so sánh hoặc liệt kê.
- Không lặp lại cùng một định nghĩa ở nhiều chương; dùng tham chiếu chéo.
- Không thêm lời tự khen hoặc quảng cáo sản phẩm.

## Bằng chứng và trích dẫn nội bộ

- Với tuyên bố về code, gắn ghi chú nguồn nội bộ trong bản làm việc (ví dụ `[Code: backend/src/.../OrderService.java — method createOrder]`). Khi xuất bản, chuyển thành mô tả/đánh số hình bảng hoặc phụ lục phù hợp; không để dấu vết biên tập không cần thiết trong bản nộp.
- Với số liệu, ghi đơn vị, số lần chạy, môi trường, phương pháp và nguồn dữ liệu.
- Với kiến thức bên ngoài, dùng `it-reference-research`; không dẫn một trang chung chung cho mọi ý.
- Khi thiếu bằng chứng, dùng `[CẦN BỔ SUNG: ...]` hoặc ghi rõ phạm vi chưa xác minh. Không tự điền.

## Hình, bảng và code

- Mỗi hình/bảng có số thứ tự, tiêu đề, nguồn nếu không phải do nhóm tự tạo và được giới thiệu trong đoạn văn trước hoặc sau.
- Bảng nên có mục đích rõ; không chuyển đoạn văn dài thành bảng chỉ để tạo cảm giác học thuật.
- Code snippet chỉ trích phần cần giải thích, không chèn cả file dài. Giữ code nguyên bản; nếu lược bớt, ghi `...` và nói rõ đó là đoạn trích.
- Ảnh giao diện phải là ảnh từ ứng dụng thật. Không tạo mockup rồi gọi là kết quả chạy thật.

## Chỉnh sửa tài liệu có sẵn

- Giữ lại ý đúng và giọng văn/tên gọi đã được người dùng thống nhất.
- Không thay đổi ý nghĩa kỹ thuật, con số, kết quả, tên bảng hoặc thuật ngữ khi chỉ được yêu cầu sửa văn phong.
- Khi chỉnh sửa, ưu tiên sửa đúng đoạn; không viết lại toàn bộ chương khi không cần.
- Nếu phát hiện mâu thuẫn quan trọng, báo trước hoặc chú thích thay vì tự ý hợp thức hóa.

## Kiểm tra trước khi bàn giao

- Mục có trả lời đúng câu hỏi mà đề cương đặt ra không?
- Có khẳng định nào không có bằng chứng không?
- Đã phân biệt yêu cầu, thiết kế, triển khai, kiểm thử chưa?
- Có trùng lặp với chương khác không?
- Thuật ngữ, tên module, số liệu, hình/bảng có nhất quán không?
- Có đoạn nào nghe như marketing hoặc câu chữ chung chung không?
- Có placeholder nào cần người dùng hoàn thiện không?

## Định dạng đầu ra

Tuân theo format gốc của báo cáo. Nếu chưa có, viết Markdown với heading phân cấp rõ, bảng Markdown và code fence có ngôn ngữ. Không tự chuyển định dạng hoặc tạo file nhị phân nếu người dùng chưa yêu cầu.

## Chế độ viết báo cáo benchmark DBMS

Với nghiên cứu TiDB vs MySQL, đọc `tidb-mysql-indexing-study` trước khi viết các mục A.2, A.3, B.1–B.3.

- Mỗi đoạn phân tích kết quả cần truy về run ID/CSV/log/EXPLAIN hoặc source chính thức đúng phiên bản.
- Viết trung tính: “kết quả trong cấu hình thử nghiệm cho thấy…”, không viết “TiDB luôn tốt hơn MySQL”.
- Phân biệt mô hình lý thuyết, engine-reported size và physical disk footprint.
- Khi mô tả B+Tree/LSM-Tree, trình bày cả chi phí tương ứng: page split/fragmentation và flush/compaction/write amplification.
- Không ghi “một RPC”/“hai RPC” như quy luật tuyệt đối; ghi kết quả `rpc_num`/`cop_tasks` đã đo.
- Với TiDB isolation, clustered/nonclustered PK và Region defaults, dùng nguồn version-specific; kiểm tra `.agents/skills/tidb-mysql-indexing-study/references/risk-register.md`.
- Mọi bảng kết quả phải có đơn vị, engine/version, data scale, index set và điều kiện chạy.
