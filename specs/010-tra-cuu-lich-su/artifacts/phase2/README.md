# Bằng chứng giao diện spec 010 Phase 2 — 23/11/2026

Chrome headless, Vite 5180 + LiveServer Django 8010, API thật và PostgreSQL **test DB**.
Đăng nhập qua UI (session/CSRF thật); không dùng tài khoản/đơn thực của người dùng.
Server test được dừng và kiểm cổng trống; Django dọn fixture test DB khi kết thúc.

- Shop tìm mã HTT thường/hoa có khoảng trắng đầu/cuối; URL giữ mã; kết quả có trạng thái/thời điểm/link chi tiết.
- Shop tra YC chưa duyệt; lịch sử có dòng Chưa phát sinh vận chuyển.
- Mã của Shop khác hiển thị không tìm thấy, không còn kết quả đơn trước.
- Link Lịch sử vận chuyển tới đúng trang chi tiết theo vai trò và cuộn tới lịch sử sau khi tải, không bị thanh trên che.
- Lịch sử hiện Lần lấy 1, Lần giao 2 và Đổi Shipper; đổi sang Cũ nhất trước hiển thị mốc tạo đầu tiên.
- Mất mạng khi lookup: giữ mã, nút Thử lại thành công sau khi mạng khôi phục.
- NV xem đơn của Shop khác, có tên Shop/link chi tiết NV; Shipper không có menu và bị guard chặn `/tracking`.
- **0 Vue warning / 0 page error**, không tràn ngang; lượt cuối 8,068 giây.

| Màn | 1440 | 390 |
|---|---|---|
| Shop có kết quả | [Desktop](shop-result-1440.png) | [Mobile](shop-result-390.png) |
| Lịch sử cũ nhất trước | [Desktop](shop-history-1440.png) | [Mobile](shop-history-390.png) |
| Shop không có quyền/không tìm thấy | [Desktop](shop-not-found-1440.png) | [Mobile](shop-not-found-390.png) |
| NV tra đơn Shop khác | [Desktop](staff-result-1440.png) | [Mobile](staff-result-390.png) |

Đã xem ảnh, chụp lại sau khi cuộn về đầu trang và ổn định hai animation frames để thanh sticky không lệch vị trí.
Test không thay thế bước người dùng thử ở Phase 3.

Chạy từ gốc repo (cần Chrome, cổng 8010/5180 trống):

```powershell
# Chỉ cần lần đầu, dùng cache công cụ như spec 009, không sửa package.json ứng dụng.
npm.cmd install --prefix frontend/node_modules/.cache/spec009-browser --no-audit --no-fund playwright
.\venv\Scripts\python.exe specs/010-tra-cuu-lich-su/tools/run_browser_phase2.py
```
