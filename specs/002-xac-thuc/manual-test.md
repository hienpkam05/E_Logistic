# Spec 002 — Kịch bản thử trên trình duyệt

Dùng cho bước 7.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**; đánh `[x]` khi đúng, ghi lỗi vào cột cuối bảng tổng kết.

## Chuẩn bị (một lần)

1. Docker Desktop đang chạy, database: `docker compose --env-file backend/.env up -d db`
2. Backend: `cd backend` → `..\venv\Scripts\python manage.py runserver`
3. Frontend (terminal khác): `cd frontend` → `npm.cmd run dev`
4. Dữ liệu demo (đã chạy sẵn 21/11/2026; chạy lại nếu cần làm mới):
   `..\venv\Scripts\python manage.py seed_demo --reset --output .demo-accounts.txt --notifications`
5. Mở `backend/.demo-accounts.txt` để lấy mật khẩu. Mở trình duyệt ở **chế độ ẩn danh** tại `http://127.0.0.1:5173`.

| Tài khoản | Vai trò | Dùng để thử |
|---|---|---|
| `demo_shop` | SHOP | Luồng chính, hồ sơ, 25 thông báo (2 trang) |
| `demo_nhanvien` | ADMIN | Trang chủ Nhân viên, 3 thông báo |
| `demo_shipper` | SHIPPER | Trang chủ Shipper, 3 thông báo |
| `demo_mktam` | SHOP | Mật khẩu tạm — bị buộc đổi mật khẩu |
| `demo_khoa` | SHIPPER | Tài khoản bị khóa |

Sau khi thử xong mục C (đổi mật khẩu `demo_mktam`) hoặc E (đổi mật khẩu `demo_shop`), chạy lại lệnh ở bước 4 để đưa dữ liệu demo về như cũ.

---

## A. Đăng nhập (UC01.1)

- [ ] **A1** Làm: mở `http://127.0.0.1:5173/`. Mong đợi: chuyển sang trang Đăng nhập.
- [ ] **A2** Làm: đăng nhập `demo_shop`. Mong đợi: vào `/shop`, thanh trên có "Shop Demo Hoàn Kiếm", nhãn "Shop", chuông có số **25**.
- [ ] **A3** Làm: gõ thẳng `http://127.0.0.1:5173/login` khi đang đăng nhập. Mong đợi: tự về `/shop` (A1 — đã có phiên).
- [ ] **A4** Làm: gõ `http://127.0.0.1:5173/staff`. Mong đợi: bị đưa về `/shop` (sai vai trò).
- [ ] **A5** Làm: đăng xuất; đăng nhập `demo_shop` với mật khẩu sai. Mong đợi: thông báo đỏ "Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản không thể đăng nhập…", ô mật khẩu bị xóa, vẫn ở trang Đăng nhập.
- [ ] **A6** Làm: đăng nhập `khong_ton_tai` / mật khẩu bất kỳ. Mong đợi: **đúng cùng thông báo** như A5.
- [ ] **A7** Làm: đăng nhập `demo_khoa` với **đúng** mật khẩu trong file. Mong đợi: **đúng cùng thông báo** như A5 (không lộ là bị khóa).
- [ ] **A8** Làm: lần lượt đăng nhập `demo_nhanvien`, `demo_shipper`. Mong đợi: vào `/staff` với nhãn "Nhân viên/Admin", `/shipper` với nhãn "Shipper".
- [ ] **A9** Làm: đăng xuất; gõ `http://127.0.0.1:5173/notifications?page=2`; đăng nhập `demo_shop`. Mong đợi: sau đăng nhập quay đúng về trang 2 thông báo.
- [ ] **A10** Làm: mở `http://127.0.0.1:5173/login?next=//google.com`, đăng nhập. Mong đợi: vào `/shop`, **không** sang trang ngoài.

## B. Đăng xuất và phiên (UC01.2)

- [ ] **B1** Làm: đăng nhập `demo_shop` → bấm Đăng xuất. Mong đợi: về trang Đăng nhập; bấm Back của trình duyệt **không** vào lại được trang trong (bị đưa về Đăng nhập).
- [ ] **B2** Làm: đăng nhập `demo_shop` ở tab 1; mở tab 2 cùng địa chỉ → đăng xuất ở tab 2; quay lại tab 1, bấm "Thông báo". Mong đợi: tab 1 bị đưa về Đăng nhập (phiên đã hủy phía máy chủ).
- [ ] **B3** Làm: đăng nhập `demo_shop`; tắt server Django (Ctrl+C) → bấm Đăng xuất → bật lại Django. Mong đợi: về trang Đăng nhập với thông báo "Đã đăng xuất trên thiết bị này nhưng chưa xác nhận được với máy chủ…".

## C. Mật khẩu tạm (UC01.3 + D5)

- [ ] **C1** Làm: đăng nhập `demo_mktam`. Mong đợi: vào thẳng trang Đổi mật khẩu, có cảnh báo vàng "Bạn đang dùng mật khẩu tạm…", thanh trên **chỉ còn** nút Đăng xuất.
- [ ] **C2** Làm: gõ `http://127.0.0.1:5173/account/profile`. Mong đợi: bị đưa lại trang Đổi mật khẩu.
- [ ] **C3** Làm: đổi mật khẩu (mật khẩu hiện tại = mật khẩu trong file, mật khẩu mới ≥ 8 ký tự). Mong đợi: vào `/shop`, menu đầy đủ trở lại.
- [ ] **C4** Làm: đăng xuất, đăng nhập lại `demo_mktam` bằng mật khẩu **mới**. Mong đợi: vào thẳng `/shop`, không bị buộc đổi nữa.

## D. Quên mật khẩu (UC01.3)

- [ ] **D1** Làm: ở trang Đăng nhập bấm "Quên mật khẩu?". Mong đợi: trang hướng dẫn 4 bước liên hệ Nhân viên; có liên kết quay lại Đăng nhập.

## E. Đổi mật khẩu (UC02.3)

- [ ] **E1** Làm: đăng nhập `demo_shop` → Đổi mật khẩu → nhập sai mật khẩu hiện tại. Mong đợi: lỗi đỏ ngay dưới ô "Mật khẩu hiện tại".
- [ ] **E2** Làm: mật khẩu mới `123`. Mong đợi: lỗi tiếng Việt dưới ô "Mật khẩu mới" ("Mật khẩu quá ngắn…", "…phổ biến", "…là số") — **không có câu tiếng Anh**.
- [ ] **E3** Làm: hai ô mật khẩu mới khác nhau. Mong đợi: lỗi dưới ô "Nhập lại mật khẩu mới".
- [ ] **E4** Làm: đăng nhập `demo_shop` ở thêm một trình duyệt/cửa sổ ẩn danh khác (phiên 2); ở phiên 1 đổi mật khẩu đúng. Mong đợi: phiên 1 báo thành công, vẫn dùng tiếp; phiên 2 bấm bất kỳ mục nào → bị đưa về Đăng nhập.
- [ ] **E5** Làm: ở trang Đổi mật khẩu bấm "Quên mật khẩu hiện tại?". Mong đợi: sang trang Quên mật khẩu, có liên kết "Quay lại đổi mật khẩu".

## F. Thông tin cá nhân (UC02.1, UC02.2)

- [ ] **F1** Làm: `demo_shop` → Thông tin cá nhân. Mong đợi: hiện tên đăng nhập, họ tên, SĐT dạng `0999 000 003`, địa chỉ, vai trò "Shop", ngày tạo; **không** có mật khẩu.
- [ ] **F2** Làm: Chỉnh sửa → xóa địa chỉ → Lưu. Mong đợi: báo đã lưu, Địa chỉ hiện "Chưa cập nhật" (chữ xám).
- [ ] **F3** Làm: Chỉnh sửa → đổi họ tên → **Hủy**. Mong đợi: họ tên cũ giữ nguyên; mở Chỉnh sửa lại thấy họ tên cũ.
- [ ] **F4** Làm: Chỉnh sửa → SĐT `0999000004` (của demo_shipper) → Lưu. Mong đợi: lỗi dưới ô SĐT "Số điện thoại đã được sử dụng.", vẫn ở form.
- [ ] **F5** Làm: SĐT `12345` → Lưu. Mong đợi: lỗi định dạng dưới ô SĐT.
- [ ] **F6** Làm: Chỉnh sửa → nhập lại địa chỉ "1 Tràng Tiền, Hoàn Kiếm, Hà Nội" → Lưu. Mong đợi: lưu thành công (trả dữ liệu về như cũ).

## G. Thông báo

- [ ] **G1** Làm: `demo_shop` → Thông báo. Mong đợi: 20 thông báo, mới nhất ("số 25") trên cùng, có loại (vd "Được phân công nhiệm vụ") và giờ; nút "Trang sau".
- [ ] **G2** Làm: bấm "Trang sau". Mong đợi: 5 thông báo, URL có `?page=2`; Back của trình duyệt về trang 1.
- [ ] **G3** Làm: bấm một thông báo đậm (chưa đọc). Mong đợi: hết nổi bật, số trên chuông giảm 1.
- [ ] **G4** Làm: tab "Chưa đọc". Mong đợi: URL có `?unread=true`, không còn thông báo vừa đọc.
- [ ] **G5** Làm: "Đánh dấu tất cả đã đọc". Mong đợi: chuông hết số; tab Chưa đọc hiện "Không có thông báo chưa đọc."; nút bị khóa.
- [ ] **G6** Làm: `demo_superuser` (không có thông báo) → Thông báo. Mong đợi: "Chưa có thông báo nào.".

## H. Mất kết nối

- [ ] **H1** Làm: đang đăng nhập, tắt Django → mở Thông tin cá nhân. Mong đợi: thông báo lỗi kèm nút "Tải lại", không hiện dữ liệu cũ; bật lại Django → "Tải lại" hiện đúng dữ liệu.

---

## Tổng kết

| Nhóm | Đạt / Tổng | Lỗi phát hiện |
|---|---|---|
| A. Đăng nhập | /10 | |
| B. Đăng xuất | /3 | |
| C. Mật khẩu tạm | /4 | |
| D. Quên mật khẩu | /1 | |
| E. Đổi mật khẩu | /5 | |
| F. Hồ sơ | /6 | |
| G. Thông báo | /6 | |
| H. Mất kết nối | /1 | |

Người thử: …… · Ngày: …… · Trình duyệt: ……
