# Bằng chứng nghiệm thu Phase 6 — 23/11/2026

Chrome headless với API/PostgreSQL test DB: đủ 3 kịch bản đổi lấy, đổi giao qua bàn giao,
và giữ giới hạn ba lần giao khi đổi người. Hộp khóa cũng được kiểm. Kết quả 0 Vue warning / 0 page error;
không tràn ngang. 10 ảnh đã lưu, ảnh mobile ba lần giao đã xem trực tiếp.

| Trạng thái | Desktop | Mobile |
|---|---|---|
| NV chờ bàn giao | [1440](staff-pending-1440.png) | [390](staff-pending-390.png) |
| Shipper đưa về | [1440](shipper-handover-1440.png) | [390](shipper-handover-390.png) |
| Xác nhận nhận hàng | [1440](staff-confirm-1440.png) | [390](staff-confirm-390.png) |
| Hộp khóa có nhiệm vụ | [1440](lock-open-tasks-1440.png) | [390](lock-open-tasks-390.png) |
| Thất bại lần 3 sau đổi người | [1440](staff-three-attempts-1440.png) | [390](staff-three-attempts-390.png) |

Audit lưu nguyên kết quả JSON, không chứa cấu hình npm/secret: [full](npm-audit-full.json), [production](npm-audit-production.json).
Các phát hiện chưa sửa và bước chờ người dùng nằm ở [acceptance.md](../../acceptance.md).

Chạy browser lại từ gốc repo:

```powershell
$env:SPEC009_BROWSER_ARTIFACTS = 'phase6'
.\venv\Scripts\python.exe specs/009-doi-shipper/tools/run_browser_phase5.py
```

Cần Playwright trong cache riêng và Chrome như hướng dẫn Phase 5; hai cổng 8010/5180 phải trống.
