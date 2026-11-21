# Danh sách spec HTT EXPRESS

Mỗi spec là một thư mục `specs/NNN-ten/` gồm:

| File | Bắt buộc | Nội dung |
|---|---|---|
| `spec.md` | Luôn có | Phạm vi UC, quyết định, thiết kế, tiêu chí nghiệm thu |
| `tasks.md` | Luôn có | Công việc chia theo phase, mỗi phase có điều kiện "Xong khi" và lệnh kiểm tra |
| `models.md` | Khi thêm/sửa bảng, trường, ràng buộc, enum hoặc migration | Bảng trường (kiểu, null, mặc định, ràng buộc, UC nguồn), enum, hằng số, migration, nhật ký thay đổi |
| `api.md` | Khi thêm/sửa endpoint hoặc quy ước API | Method, URL, quyền, request/response mẫu, mã lỗi, nhật ký thay đổi; đánh dấu rõ **Mới** / **Sửa** / **Bỏ** |
| `manual-test.md` | Khi có giao diện cần thử bằng tay | Kịch bản thử trên trình duyệt: tài khoản dùng, từng bước **Làm / Mong đợi**, bảng tổng kết |

Không có thay đổi model/API thì ghi "Không phát sinh" trong `spec.md` thay vì tạo file rỗng. Code lệch khỏi `models.md`/`api.md` thì sửa file đó trong cùng thay đổi.

Quy ước API chung (định dạng lỗi, phân trang, CSRF, gửi lại yêu cầu) đặt tại [001-nen-tang/api.md](001-nen-tang/api.md); spec sau chỉ tham chiếu, không chép lại. Phủ đủ 42 UC của [đặc tả](../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md), mỗi UC thuộc đúng một spec. Làm theo thứ tự phụ thuộc; cột mốc demo "giao thành công" đạt sau spec 007.

| Spec | Tên | UC | App chính | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|
| [001](001-nen-tang/spec.md) | Nền tảng và mô hình dữ liệu | — (xử lý dùng chung) | `core`, `accounts`, `notifications` | — | Đã triển khai — chờ 2 việc phía người dùng (superuser, xóa `dist/`) |
| [002](002-xac-thuc/spec.md) | Xác thực, hồ sơ cá nhân, thông báo | 01.1–01.3, 02.1–02.3 | `accounts`, `notifications` | 001 | Đã triển khai — chờ thử trình duyệt ([manual-test.md](002-xac-thuc/manual-test.md)) |
| [003](003-quan-ly-tai-khoan/spec.md) | Quản lý tài khoản và Shipper | 02.4, 06.1–06.4 | `accounts` | 002 | Đã triển khai — chờ thử trình duyệt ([manual-test.md](003-quan-ly-tai-khoan/manual-test.md)) |
| 004 | Yêu cầu gửi hàng của Shop | 05.1–05.5 | `shipments` | 002 | Chưa viết |
| 005 | Duyệt và quản lý vận đơn | 05.6–05.9 | `shipments` | 004 | Chưa viết |
| 006 | Lấy hàng và nhập điểm tập kết | 06.5, 04.1–04.3, 04.13, 04.10 | `dispatch` | 003, 005 | Chưa viết |
| 007 | Giao hàng, COD, giao lại | 06.6, 04.4–04.7, 04.12 | `dispatch` | 006 | Chưa viết |
| 008 | Hoàn hàng | 06.7, 04.8, 04.9, 04.11 | `dispatch` | 007 | Chưa viết |
| 009 | Đổi Shipper / phân công lại | 06.8 | `dispatch` | 006–008 | Chưa viết |
| 010 | Tra cứu và lịch sử vận chuyển | 03.1–03.2 | `tracking` | 005 | Chưa viết |
| 011 | GPS và bản đồ ("Nên có") | 03.3–03.5 | `tracking` | 006–009 | Chưa viết |
