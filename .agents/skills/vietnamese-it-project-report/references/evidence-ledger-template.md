# Evidence Ledger — Sổ bằng chứng

| ID | Claim/Thông tin | Nhãn | Nguồn (file + symbol/section) | Ngày/commit | Giới hạn |
|---|---|---|---|---|---|
| EV-001 | Ví dụ: Backend có endpoint đăng nhập | CHƯA XÁC MINH | Chưa đọc controller/router | — | Không được đưa vào báo cáo trước khi xác minh |

## Nhãn

- `VERIFIED`: trực tiếp quan sát trong nguồn đáng tin.
- `USER-PROVIDED`: nhóm cung cấp.
- `INFERRED`: suy luận; ghi rõ căn cứ.
- `UNKNOWN`: chưa biết.
- `CONFLICT`: nguồn mâu thuẫn.

## Nguyên tắc

- Mỗi claim quan trọng nên có ID để dùng lại xuyên suốt báo cáo.
- Đường dẫn phải là đường dẫn thực tế; không bịa line number.
- Test chỉ được ghi pass khi có kết quả chạy/CI tương ứng.
- Không lưu secret hoặc dữ liệu cá nhân trong ledger.
