# Kiểm giao diện Phase 5 — 23/11/2026

Chrome headless, Vue/Vite thật tại 5180, API Django thật tại 8010 và PostgreSQL **test DB**.
Các tài khoản và đơn hàng trong ảnh đều là fixture test; Django tự dọn khi kết thúc.
Hai server test đã dừng và kiểm lại cổng trống; không dừng server người dùng 8000/5173.

- Đổi nhiệm vụ lấy: Nhân viên loại người cũ, nhập lý do, đổi ngay; người cũ chỉ xem, người mới bấm nhận hàng.
- Đổi nhiệm vụ giao: người mới chưa nhận quyền khi đang chờ; người cũ chỉ có báo bàn giao;
  Nhân viên phải tích nhận đủ hàng/người mới đã nhận; sau đó người mới có nhiệm vụ giao lần 2,
  số lần đã giao vẫn 1. Không ghi COD trong quá trình đổi.
- Hộp khóa Shipper: tải và hiện đúng mã vận đơn/nhiệm vụ đang mở; hủy hộp sau khi kiểm tra.
- 0 cảnh báo Vue / 0 lỗi JavaScript; không tràn ngang ở 1440 và 390 px.
- Đã xem ảnh: chụp lại sau khi kết thúc hiệu ứng thanh bên; sửa dải cảnh báo để tên người dự kiến nằm trong câu.

| Màn | Desktop 1440 | Mobile 390 |
|---|---|---|
| Nhân viên chờ bàn giao | [Ảnh](staff-pending-1440.png) | [Ảnh](staff-pending-390.png) |
| Shipper đưa hàng về | [Ảnh](shipper-handover-1440.png) | [Ảnh](shipper-handover-390.png) |
| Xác nhận bàn giao | [Ảnh](staff-confirm-1440.png) | [Ảnh](staff-confirm-390.png) |
| Khóa Shipper có nhiệm vụ | [Ảnh](lock-open-tasks-1440.png) | [Ảnh](lock-open-tasks-390.png) |

Chạy lại từ gốc repo (cần Chrome và hai cổng trống):

```powershell
# Chỉ cần lần đầu; công cụ đặt trong cache bị Git bỏ qua, không sửa package.json của ứng dụng.
npm.cmd install --prefix frontend/node_modules/.cache/spec009-browser --no-audit --no-fund playwright
.\venv\Scripts\python.exe specs/009-doi-shipper/tools/run_browser_phase5.py
```

Kết quả lượt cuối: 1 bài browser tích hợp pass, 36,7 giây khi chạy cùng Vitest/build.
Toàn frontend 326/326 test pass; build đạt tại thư mục kiểm tra riêng (xem tasks.md).
Nghiệm thu tổng thể và kịch bản người dùng tự thử thuộc Phase 6.
