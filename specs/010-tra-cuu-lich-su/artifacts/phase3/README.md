# Bằng chứng Phase 3 — 23/11/2026

Chrome headless + Vite 5180 + Django LiveServer 8010, session/CSRF và API thật, PostgreSQL **test DB**.
Fixture được Django dọn sau chạy, không dùng tài khoản/đơn thực. Hai cổng test đã kiểm tra không còn listener.

Kết quả: **1/1 test, 8,987 s; 0 Vue warning / 0 page error**, không tràn ngang.
[Log browser](browser.txt) · [Báo cáo nghiệm thu](../../acceptance.md).

- Shop tra HTT/YC, chuẩn hóa hoa thường/khoảng trắng; mã Shop khác không tìm thấy, không giữ kết quả cũ.
- Link chi tiết/lịch sử theo vai trò; hash cuộn sau tải và không bị topbar che.
- Lần lấy 1, lần giao 2 và đổi Shipper hiện đúng; chọn cũ nhất trước; đơn mới chưa phát sinh vận chuyển.
- URL khôi phục mã/kết quả; lỗi mạng giữ mã, thử lại thành công sau khi kết nối lại.
- Nhân viên tra được Shop khác, hiển thị Shop; Shipper không có menu, bị chặn route.

| Màn | 1440 | 390 |
|---|---|---|
| Shop có kết quả | [Desktop](shop-result-1440.png) | [Mobile](shop-result-390.png) |
| Lịch sử | [Desktop](shop-history-1440.png) | [Mobile](shop-history-390.png) |
| Không tìm thấy | [Desktop](shop-not-found-1440.png) | [Mobile](shop-not-found-390.png) |
| Nhân viên | [Desktop](staff-result-1440.png) | [Mobile](staff-result-390.png) |

Đã xem lại ảnh lịch sử 390 và kết quả Nhân viên 1440; các ảnh còn lại dùng cùng runner/layout đã kiểm ở Phase 2.
Ảnh full-page chụp sau cuộn về đầu trang; assertion cuộn hash chạy trước khi chụp.
Kết quả này không thay thế việc người dùng tự thử.

Chạy lại từ gốc repo sau khi các suite dùng test DB đã dừng (cần Chrome/cache Playwright như Phase 2):

```powershell
$env:SPEC010_BROWSER_PHASE='phase3'
.\venv\Scripts\python.exe specs/010-tra-cuu-lich-su/tools/run_browser_phase2.py
Remove-Item Env:SPEC010_BROWSER_PHASE
```

Biến trên chỉ chọn thư mục artifact `phase2`/`phase3` của công cụ kiểm thử; không cấu hình ứng dụng.
