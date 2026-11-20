---
name: it-system-diagrams
description: Thiết kế, tạo và rà soát sơ đồ kỹ thuật cho báo cáo đồ án IT, gồm architecture, component, deployment, use case, activity, sequence, ERD, data flow và workflow bằng Mermaid hoặc PlantUML. Dùng khi báo cáo cần sơ đồ hoặc cần kiểm tra sơ đồ so với source code.
---

# IT System Diagrams

## Mục tiêu

Sơ đồ phải giúp người đọc hiểu cấu trúc hoặc hành vi hệ thống, không chỉ làm đẹp báo cáo. Mọi thành phần và quan hệ phải phản ánh hệ thống hiện tại hoặc được gắn nhãn rõ là thiết kế đề xuất.

## Chọn loại sơ đồ

| Câu hỏi cần trả lời | Sơ đồ phù hợp |
|---|---|
| Hệ thống gồm những khối nào và kết nối ra sao? | System context, container, component/architecture |
| Mã được triển khai ở đâu? | Deployment |
| Người dùng làm được gì? | Use case hoặc user journey |
| Một nghiệp vụ diễn ra theo trình tự nào? | Sequence |
| Một quy trình có nhánh/điều kiện nào? | Activity/flowchart |
| Dữ liệu gồm thực thể và quan hệ nào? | ERD |
| Dữ liệu đi qua các bước xử lý nào? | Data-flow diagram |
| API/webhook/job tương tác ra sao? | Sequence hoặc integration diagram |

Không dùng sequence diagram để thay thế kiến trúc tổng thể. Không dùng ERD để mô tả luồng xử lý.

## Quy trình

1. Xác định câu hỏi mà sơ đồ cần trả lời và đối tượng đọc.
2. Thu thập các thành phần/actor/luồng từ code, schema, API spec, config và yêu cầu đã xác nhận.
3. Phân biệt sơ đồ hiện trạng (`AS-IS`) với sơ đồ mục tiêu/đề xuất (`TO-BE`).
4. Chốt ranh giới hệ thống, tên thành phần, hướng mũi tên, protocol và quan hệ cần thể hiện.
5. Tạo source Mermaid hoặc PlantUML có thể chỉnh sửa.
6. Render/kiểm tra cú pháp nếu môi trường hỗ trợ. Nếu không render được, ghi rõ mới chỉ kiểm tra bằng đọc cú pháp.
7. So sánh sơ đồ với code và evidence ledger; sửa các thành phần thừa/thiếu.
8. Thêm caption và đoạn giải thích trong báo cáo.

## Quy tắc trung thực

- Không thêm API Gateway, message broker, cache, load balancer, Kubernetes, cloud service hoặc database chỉ vì đó là kiến trúc phổ biến.
- Không vẽ một service ngoài như đã được tích hợp chỉ vì project có SDK dependency.
- Dùng đường nét/nhãn khác nhau để phân biệt request đồng bộ, event, batch job và data store.
- Ghi protocol (HTTP, REST, gRPC, AMQP...) chỉ khi có căn cứ.
- Nếu không rõ quan hệ, để dấu `?`/ghi chú cần xác nhận thay vì vẽ như sự thật.
- Tránh sơ đồ quá dày. Chia theo lớp hoặc luồng nếu vượt quá mức dễ đọc.

## Mermaid conventions

- Dùng `flowchart LR` cho kiến trúc luồng ngang, `flowchart TD` cho quy trình từ trên xuống.
- Dùng `sequenceDiagram` cho tương tác theo thời gian.
- Dùng `erDiagram` cho dữ liệu quan hệ.
- Dùng `stateDiagram-v2` cho vòng đời trạng thái.
- Đặt label ngắn, tiếng Việt có dấu nếu công cụ render tốt; nếu có lỗi font, dùng tiếng Việt không dấu chỉ trong diagram và giải thích đầy đủ ở caption.
- Tránh ký tự đặc biệt không cần thiết trong ID node; ID dùng ASCII và label để trong dấu ngoặc.
- Một sơ đồ cần có chú giải nếu dùng nhiều kiểu đường/màu.

## Lưu và trình bày

Mặc định lưu source sơ đồ tại `docs/report/diagrams/<ten-so-do>.mmd` hoặc `.puml`. Nếu renderer hỗ trợ, xuất SVG/PNG vào cùng thư mục hoặc `docs/report/assets/`.

Trong báo cáo, ghi:

- Số và tên hình.
- Sơ đồ mô tả gì.
- Các thành phần chính.
- Giải thích luồng/quan hệ quan trọng.
- Nguồn: nhóm tự xây dựng dựa trên thiết kế/code, hoặc tài liệu tham khảo nếu lấy từ ngoài.

## Kiểm tra chất lượng

- Sơ đồ có khớp code/DB/API hiện tại không?
- Có nhầm lẫn `AS-IS` và `TO-BE` không?
- Tên component có nhất quán với báo cáo không?
- Mũi tên có đúng chiều và đúng nghĩa không?
- Có thành phần nào không được giải thích trong nội dung không?
- Người không tham gia lập trình có hiểu sơ đồ sau khi đọc caption không?

## Sơ đồ cần có cho đề tài TiDB–MySQL

Với đề tài benchmark DBMS, ưu tiên 3–5 sơ đồ rõ ràng:

1. Topology triển khai phòng lab: một host Docker, PD/TiDB/3 TiKV và MySQL single instance (hai engine được chạy luân phiên, không cùng lúc).
2. TiDB logical architecture: SQL layer → PD metadata/TSO → TiKV Region/Raft/RocksDB; chỉ vẽ quan hệ có nguồn.
3. Data/index mapping: clustered row handle và secondary index entry; tách minh họa conceptual khỏi byte-accurate encoding.
4. Benchmark pipeline: generator → common dataset → engine-specific load → query/write workloads → raw CSV/log → validation → charts.
5. Chaos timeline: baseline, kill TiKV, observe, restart, recovery/checksum.

Mọi sơ đồ đều phải gắn `PLANNED` hay `OBSERVED`; topology một host không được vẽ như hệ nhiều availability zone.
