# Spec 010 — Nghiệm thu Phase 3 (23/11/2026)

**Kiểm tra kỹ thuật đạt; chưa chốt nghiệm thu toàn bộ.** Người dùng chưa xác nhận thử tay;
audit phụ thuộc phát triển còn 7 mục. Hướng dẫn: [manual-test.md](manual-test.md).

## Kết quả trên code hiện tại

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Django check | Không có lỗi | [Log](artifacts/phase3/django-check.txt) |
| Migration drift | No changes detected | [Log](artifacts/phase3/migrations.txt) |
| Backend PostgreSQL xuôi | 550/550, 56,421 s | [Log](artifacts/phase3/backend-forward.txt) |
| Backend PostgreSQL đảo thứ tự | 550/550, 77,548 s | [Log](artifacts/phase3/backend-reverse.txt) |
| Vitest | 337/337, 44 file, 28,90 s | [Log](artifacts/phase3/vitest.txt) |
| Build production | Đạt, 1.833 module, 4,67 s | [Log](artifacts/phase3/build.txt) |
| Chrome + API thật | Shop/NV/Shipper, lịch sử, URL, retry; 8 ảnh 1440/390 | [Bằng chứng](artifacts/phase3/README.md) |
| Audit production | 0 phát hiện | [JSON](artifacts/phase3/audit-production.json) |
| Audit đầy đủ | 5 moderate, 2 critical, đều trong graph dev | [JSON](artifacts/phase3/audit-all.json) |

Build xuất vào `frontend/node_modules/.cache/spec010-phase3-build`, theo cách tránh lỗi khóa/quyền
`dist` đã ghi ở spec 009. Không suy ra rằng xuất vào `dist` mặc định đã được kiểm tra thành công.
Vitest vẫn có warning fixture AccountCreateView/navActive đã biết; kết quả Chrome thực tế ghi riêng.

## Rà soát UC03.1–03.2

- Lookup và lịch sử dùng `CanViewShipments` cùng `shipments_visible_to`; Shop chỉ thấy đơn mình,
  Nhân viên thấy toàn hệ thống. Không công khai, Shipper bị chặn. Đơn ngoài quyền/mã không tồn tại cùng 404.
- Chuẩn hóa trim đầu/cuối + uppercase, tìm đúng trên cột mã; không tìm gần đúng. Lookup/lịch sử chỉ đọc.
- Actor của Shop chỉ có id/tên, không username/SĐT nội bộ; lịch sử lấy actor/task bằng `select_related`.
- Số lần lấy và cờ vận chuyển tính toàn đơn, không suy từ trang; giao thay người giữ nguyên attempt_no.
  Thứ tự có khóa phụ id; phân trang giữ lựa chọn ordering.
- Frontend dùng API client/service, enum role/task/action và giới hạn metadata sẵn có.
  Không thấy host, ID tài khoản, mã vai trò/trạng thái hoặc màu hex hardcode mới trong logic spec 010.
  Chưa phát hiện lỗi chức năng cần sửa trong lượt nghiệm thu; không thêm model/migration/API mới ở Phase 3.
- Bằng chứng Phase 1 vẫn áp dụng vì query/backend không đổi: [EXPLAIN 20.000 đơn](artifacts/phase1/explain-lookup.txt),
  9/9 đột biến bị bắt và kiểm tra không N+1. Không chạy lại các phép đo này để thay thế kết quả hồi quy hiện tại.

## Khoản còn mở

1. Người dùng thử [manual-test.md](manual-test.md), ghi người thử/ngày/kết quả; mục 3.2 còn mở.
2. Audit dev: `vitest`, `tinypool` critical; `@vitest/mocker`, `js-beautify`, `editorconfig`, `glob`,
   `minimatch` moderate. Đây là phân loại của npm audit, không kết luận khả năng khai thác.
   Máy quét đề xuất Vitest major 5.1.1; không thực hiện nâng major trong lượt nghiệm thu.

[Skill dự án](../../.agents/skills/htt-express-code/SKILL.md) yêu cầu “Giữ phiên bản và package manager hiện có.”
Giữ các major hiện tại, ghi rõ audit chưa sạch; việc xử lý dependency cần kiểm chứng tương thích riêng.
Spec 009 đã thử `npm audit fix` không force và không đổi package; Phase 3 không lặp lại thay đổi đó.

Các log PowerShell có thể chứa nhãn `NativeCommandError` khi chương trình ghi stderr;
kết luận test dựa trên tổng số test, `OK`/passed và exit code, không dựa vào nhãn shell.
