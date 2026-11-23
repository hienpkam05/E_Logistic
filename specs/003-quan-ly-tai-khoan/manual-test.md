# Spec 003 — Kịch bản thử trên trình duyệt

Dùng cho bước 6.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**; đánh `[x]` khi đúng, ghi lỗi vào bảng tổng kết. Phần quy tắc khó tạo bằng tay (hai Admin khóa nhau cùng lúc, Admin cuối cùng) đã có test tự động — xem tasks.md Phase 3.


> **Giao diện mới (21/11/2026):**
> - Menu chức năng nằm ở **thanh bên trái**; điện thoại bấm ☰ để mở.
> - Chuông thông báo ở góc phải thanh trên.
> - "Thông tin cá nhân", "Đổi mật khẩu", "Đăng xuất" nằm trong **menu avatar**: bấm vào tên/ảnh đại diện ở góc phải.
>
> Các bước ghi "bấm Đăng xuất" nghĩa là mở menu avatar rồi bấm.

## Chuẩn bị (một lần)

1. Docker Desktop + database: `docker compose --env-file backend/.env up -d db`
2. Backend: `cd backend` → `..\venv\Scripts\python manage.py runserver`
3. Frontend (terminal khác): `cd frontend` → `npm.cmd run dev`
4. Mở `backend/.demo-accounts.txt` để lấy mật khẩu.
5. Cần **2 cửa sổ trình duyệt** tách phiên: cửa sổ thường (Nhân viên) và cửa sổ **ẩn danh** (tài khoản bị quản lý). Mở `http://127.0.0.1:5173`.

| Tài khoản | Vai trò | Trạng thái lúc bắt đầu (21/11/2026) |
|---|---|---|
| `demo_nhanvien` | Nhân viên/Admin | Hoạt động — **người thử đăng nhập bằng tài khoản này** |
| `demo_superuser` | Nhân viên/Admin | Hoạt động |
| `demo_shop` | Shop | Hoạt động |
| `demo_shipper` | Shipper | Hoạt động |
| `demo_mktam` | Shop | Chờ đổi mật khẩu |
| `demo_khoa` | Shipper | Bị khóa |

**Sau khi thử xong**, đưa tài khoản demo về như cũ (mật khẩu mới ghi vào file):
`..\venv\Scripts\python manage.py seed_demo --reset --output .demo-accounts.txt`
Tài khoản tạo thêm trong lúc thử (`thu_shipper`…) **không xóa được trong app** (đúng BR1) — để lại hoặc khóa đi.

---

## A. Vào màn hình và phân quyền

- [ ] **A1** Làm: cửa sổ thường đăng nhập `demo_nhanvien`. Mong đợi: thanh bên có "Quản lý tài khoản", "Quản lý Shipper"; trang chủ có mục "Chức năng" với hai ô đó.
- [ ] **A2** Làm: bấm "Quản lý tài khoản". Mong đợi: bảng 6 tài khoản; cột Trạng thái: `demo_khoa` "Bị khóa" (đỏ), `demo_mktam` "Chờ đổi mật khẩu" (vàng), còn lại "Hoạt động".
- [ ] **A3** Làm: bấm "Quản lý Shipper". Mong đợi: tiêu đề "Quản lý Shipper", chỉ `demo_khoa`, `demo_shipper`; nút "Thêm Shipper".
- [ ] **A4** Làm: mở **tab mới** dán thẳng `http://127.0.0.1:5173/staff/accounts?role=SHIPPER`. Mong đợi: vẫn chỉ 2 Shipper (lỗi đã sửa ở Phase 5).
- [ ] **A5** Làm: cửa sổ ẩn danh đăng nhập `demo_shop`, gõ `http://127.0.0.1:5173/staff/accounts`. Mong đợi: bị đưa về `/shop`; thanh bên không có "Quản lý tài khoản". Đăng xuất cửa sổ ẩn danh.

## B. Danh sách — lọc, tìm (UC02.4, UC06.1)

- [ ] **B1** Làm: tab "Shop". Mong đợi: `demo_mktam`, `demo_shop`; URL có `?role=SHOP`.
- [ ] **B2** Làm: tab "Tất cả" → chọn "Bị khóa". Mong đợi: chỉ `demo_khoa`.
- [ ] **B3** Làm: "Mọi trạng thái" → tìm `0999000004` → Tìm. Mong đợi: chỉ `demo_shipper`.
- [ ] **B4** Làm: tìm `DEMO_S` (chữ hoa). Mong đợi: ra `demo_shipper`, `demo_shop`, `demo_superuser` (không phân biệt hoa thường).
- [ ] **B5** Làm: tìm `hoan`. Mong đợi: **không** ra `demo_shop` ("Shop Demo Hoàn Kiếm") — đúng quyết định D7 (tìm có phân biệt dấu); hiện "Không có tài khoản phù hợp với bộ lọc." và nút "Bỏ lọc".
- [ ] **B6** Làm: bấm "Bỏ lọc". Mong đợi: về đủ 6 tài khoản, URL không còn tham số.
- [ ] **B7** Làm: lọc "Shipper" + "Bị khóa", vào chi tiết `demo_khoa`, bấm Back của trình duyệt. Mong đợi: quay lại đúng bộ lọc cũ.

## C. Tạo tài khoản (UC02.4 A1, UC06.2)

- [ ] **C1** Làm: "Quản lý Shipper" → "Thêm Shipper". Mong đợi: tiêu đề "Thêm Shipper", ô Vai trò là chữ cố định "Shipper" (không chọn được).
- [ ] **C2** Làm: Tên đăng nhập `DEMO_SHOP`, họ tên bất kỳ, SĐT `0999000003` → Tạo. Mong đợi: lỗi dưới ô Tên đăng nhập "Tên đăng nhập đã được sử dụng." **và** dưới ô SĐT "Số điện thoại đã được sử dụng."; dữ liệu đã gõ vẫn còn.
- [ ] **C3** Làm: Tên đăng nhập `tên có dấu`. Mong đợi: lỗi định dạng tên đăng nhập.
- [ ] **C4** Làm: Tên đăng nhập `thu_shipper`, họ tên `Shipper Thử`, SĐT `0999000099` → Tạo. Mong đợi: form biến mất; báo "Đã tạo tài khoản thu_shipper"; hộp vàng "Chỉ hiển thị một lần" với mật khẩu tạm 12 ký tự. **Ghi lại mật khẩu này.**
- [ ] **C5** Làm: bấm "Sao chép", dán vào Notepad. Mong đợi: đúng mật khẩu đang hiện.
- [ ] **C6** Làm: bấm "Quản lý tài khoản" trên thanh bên. Mong đợi: hộp hỏi "Mật khẩu tạm sẽ không xem lại được…"; chọn **Hủy** → vẫn ở trang, mật khẩu vẫn hiện.
- [ ] **C7** Làm: bấm "Tôi đã ghi lại". Mong đợi: sang trang chi tiết `thu_shipper`, trạng thái "Chờ đổi mật khẩu", lịch sử có "Tạo tài khoản — bởi Nhân viên điều phối (demo) — Vai trò: Shipper".
- [ ] **C8** Làm: cửa sổ ẩn danh đăng nhập `thu_shipper` bằng mật khẩu tạm. Mong đợi: bị buộc sang Đổi mật khẩu; đổi xong vào `/shipper`.
- [ ] **C9** Làm: "Thêm tài khoản" từ "Quản lý tài khoản" (không qua Shipper). Mong đợi: có ô chọn Vai trò (Shop / Nhân viên/Admin / Shipper); bấm Hủy → về danh sách, không tạo gì.

## D. Sửa hồ sơ (UC02.4, UC06.3)

- [ ] **D1** Làm: chi tiết `thu_shipper` → Chỉnh sửa → địa chỉ "Cầu Giấy" → Lưu. Mong đợi: báo đã lưu; lịch sử thêm "Cập nhật hồ sơ — Địa chỉ liên hệ: (trống) → Cầu Giấy".
- [ ] **D2** Làm: Chỉnh sửa → đổi họ tên → **Hủy**. Mong đợi: họ tên cũ; lịch sử không thêm dòng.
- [ ] **D3** Làm: Chỉnh sửa → SĐT `0999000004` → Lưu. Mong đợi: lỗi dưới ô SĐT, vẫn ở form.
- [ ] **D4 (chống ghi đè — UC06.3 E1)** Làm: mở chi tiết `thu_shipper` ở **hai tab** cùng cửa sổ thường, cả hai bấm Chỉnh sửa. Tab 1: địa chỉ "Ba Đình" → Lưu. Tab 2: địa chỉ "Đống Đa" → Lưu. Mong đợi: tab 2 hiện cảnh báo vàng "Tài khoản vừa được người khác thay đổi…" và nút "Tải bản mới nhất"; bấm nút → ô địa chỉ thành "Ba Đình". Dữ liệu đã lưu là "Ba Đình", không bị ghi đè.

## E. Khóa / mở khóa (UC02.4 A2, UC06.4)

- [ ] **E1** Làm: cửa sổ ẩn danh đang đăng nhập `thu_shipper` (từ C8). Cửa sổ thường: chi tiết `thu_shipper` → "Khóa tài khoản". Mong đợi: hộp đỏ nêu "đăng xuất ngay trên mọi thiết bị" và "Nhiệm vụ đang mở của Shipper vẫn được giữ…"; có ô Lý do.
- [ ] **E2** Làm: nhập lý do "Thử khóa" → Khóa. Mong đợi: trạng thái "Bị khóa", nút đổi thành "Mở khóa"; lịch sử "Khóa tài khoản — Lý do: Thử khóa".
- [ ] **E3** Làm: cửa sổ ẩn danh bấm "Thông báo". Mong đợi: bị đưa về trang Đăng nhập.
- [ ] **E4** Làm: cửa sổ ẩn danh đăng nhập `thu_shipper` (mật khẩu đã đổi ở C8). Mong đợi: thông báo chung "Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản không thể đăng nhập…" (không lộ là bị khóa).
- [ ] **E5** Làm: cửa sổ ẩn danh **không đăng nhập lại**, chỉ để nguyên. Cửa sổ thường: "Mở khóa" → xác nhận. Cửa sổ ẩn danh: bấm Back tới trang trong (vd `/shipper`) hoặc tải lại. Mong đợi: vẫn ở trang Đăng nhập — **phiên cũ không sống lại** khi mở khóa.
- [ ] **E6** Làm: cửa sổ ẩn danh đăng nhập `thu_shipper` lại. Mong đợi: vào được.

## F. Đặt lại mật khẩu (UC01.3 A1)

- [ ] **F1** Làm: chi tiết `thu_shipper` → "Đặt lại mật khẩu". Mong đợi: nút "Đặt lại" bị khóa cho tới khi tick "Tôi đã xác minh danh tính…".
- [ ] **F2** Làm: tick → Đặt lại. Mong đợi: hộp "Mật khẩu tạm mới" hiện một lần; trạng thái "Chờ đổi mật khẩu"; lịch sử "Đặt lại mật khẩu — Nhân viên đã xác minh danh tính" (không có mật khẩu).
- [ ] **F3** Làm: cửa sổ ẩn danh (đang đăng nhập từ E6) bấm bất kỳ mục nào. Mong đợi: bị đưa về Đăng nhập.
- [ ] **F4** Làm: đăng nhập bằng mật khẩu **cũ**. Mong đợi: thông báo lỗi chung. Đăng nhập bằng mật khẩu tạm mới → bị buộc đổi mật khẩu.

## G. Tài khoản của chính mình (D1)

- [ ] **G1** Làm: danh sách → chi tiết `demo_nhanvien`. Mong đợi: hộp xanh "Đây là tài khoản của bạn…" với liên kết Thông tin cá nhân / Đổi mật khẩu; **không có** nút Chỉnh sửa / Khóa / Đặt lại.

## H. Tài khoản Nhân viên khác

- [ ] **H1** Làm: chi tiết `demo_superuser` → Khóa tài khoản. Mong đợi: hộp xác nhận **không** có câu về nhiệm vụ Shipper; khóa được (vẫn còn `demo_nhanvien` hoạt động).
- [ ] **H2** Làm: Mở khóa `demo_superuser`. Mong đợi: "Hoạt động" trở lại.

---

## Tổng kết

| Nhóm | Đạt / Tổng | Lỗi phát hiện |
|---|---|---|
| A. Vào màn hình, phân quyền | /5 | |
| B. Danh sách | /7 | |
| C. Tạo | /9 | |
| D. Sửa | /4 | |
| E. Khóa/mở khóa | /6 | |
| F. Đặt lại mật khẩu | /4 | |
| G. Chính mình | /1 | |
| H. Nhân viên khác | /2 | |

Người thử: …… · Ngày: …… · Trình duyệt: ……
