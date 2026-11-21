# Spec 002 — Xác thực, hồ sơ cá nhân, thông báo

Trạng thái: **Đã triển khai (21/11/2026)** — 15/16 tiêu chí đạt bằng test tự động + smoke test; còn thử trên trình duyệt ([manual-test.md](manual-test.md)). D1–D8 theo đề xuất. Ngày lập: 21/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md)

Nguồn: [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md) UC01.1–01.3, UC02.1–02.3, mục 2 (quy tắc chung) · [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md) mục 3, 4, 5 (quy tắc 1, 4, 8, 10), mục 6 · [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md) UC01–UC02, "Thông báo nội bộ" · Nền tảng: [spec 001](../001-nen-tang/spec.md).

## 1. Mục tiêu và phạm vi

Người dùng của cả ba vai trò đăng nhập, dùng hệ thống trong phiên an toàn, xem/sửa hồ sơ của mình, đổi mật khẩu, xem thông báo nội bộ. Đây là điều kiện để mọi spec nghiệp vụ sau có người dùng thật.

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC01.1 | Đăng nhập | Toàn bộ, gồm A1 (đã có phiên) và E1 (sai/khóa) |
| UC01.2 | Đăng xuất | Toàn bộ, gồm A1 (phiên đã hết) và E1 (mất kết nối) |
| UC01.3 | Quên mật khẩu | **Phía người dùng**: trang hướng dẫn liên hệ Nhân viên; bắt buộc đổi mật khẩu tạm khi đăng nhập lại. Thao tác Nhân viên đặt mật khẩu tạm thuộc UC02.4 → **spec 003** |
| UC02.1 | Xem thông tin tài khoản | Toàn bộ |
| UC02.2 | Cập nhật thông tin cá nhân | Toàn bộ |
| UC02.3 | Đổi mật khẩu | Toàn bộ, gồm A1 (dẫn sang Quên mật khẩu) |
| — | Thông báo nội bộ (xử lý dùng chung, checklist mục 3) | API + giao diện danh sách, đếm chưa đọc, đánh dấu đã đọc |

Kèm theo nền giao diện cho các spec sau: layout sau đăng nhập, guard router theo vai trò, trang chủ tạm cho từng vai trò, Vitest.

**Ngoài phạm vi:** quản lý tài khoản người khác, tạo tài khoản, khóa/mở khóa, Nhân viên đặt mật khẩu tạm (spec 003); OTP/email/SMS; tự đăng ký; dừng GPS khi đăng xuất (chỉ để sẵn điểm móc, GPS ở spec 011).

## 2. Quyết định cần chốt

**Đã chốt 21/11/2026: cả 8 điểm theo đề xuất.**

| # | Vấn đề | Phương án |
|---|---|---|
| D1 | Định danh đăng nhập | Chỉ `username` (đúng UC01.1 "tên đăng nhập"). Không đăng nhập bằng số điện thoại |
| D2 | Thời hạn phiên | Hết hạn tuyệt đối **8 giờ** sau đăng nhập (một ca làm việc), không gia hạn theo hoạt động. Cấu hình qua env `DJANGO_SESSION_AGE_SECONDS` |
| D3 | Chống dò mật khẩu | Giới hạn **10 lần đăng nhập/phút/IP**; vượt → `429`. Cấu hình qua env `DJANGO_LOGIN_RATE` |
| D4 | Trường hồ sơ được tự sửa | `full_name`, `phone`, `address`. Không sửa `username`, `email`, `role`, `is_active`, cờ quản trị |
| D5 | Mật khẩu tạm (D4 của spec 001) | Khi `must_change_password = true`, **backend chặn** mọi API trừ: xem hồ sơ của mình, đổi mật khẩu, đăng xuất, cấp CSRF, enum — lỗi `403 PASSWORD_CHANGE_REQUIRED` |
| D6 | Test frontend | Thêm devDependency **Vitest + @vue/test-utils + jsdom** (spec 001 đã ghi nhận thiếu test frontend) |
| D7 | Thông tin liên hệ ở trang Quên mật khẩu | Đọc từ env `VITE_SUPPORT_CONTACT` (vd "Hotline điều phối 0900 000 000"); để trống thì hiện "Liên hệ Nhân viên HTT Express" |
| D8 | Cập nhật số thông báo chưa đọc | Tải khi đăng nhập, khi chuyển trang và định kỳ **60 giây** khi tab đang mở; không dùng WebSocket |

## 3. Backend

### 3.1. Phiên, CSRF và cấu hình

- Xác thực bằng **session cookie Django** (đã cấu hình `SessionAuthentication` ở spec 001). Không dùng JWT.
- `settings.py` (đọc env, mẫu trong `backend/.env.example`):
  - `SESSION_COOKIE_AGE = DJANGO_SESSION_AGE_SECONDS` (mặc định `28800`), `SESSION_EXPIRE_AT_BROWSER_CLOSE = False`, `SESSION_SAVE_EVERY_REQUEST = False`.
  - `SESSION_COOKIE_HTTPONLY = True` (mặc định Django), `SESSION_COOKIE_SAMESITE = "Lax"`, `CSRF_COOKIE_SAMESITE = "Lax"`.
  - `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` đọc env `DJANGO_SECURE_COOKIES` (mặc định `False` khi local).
  - `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"login": DJANGO_LOGIN_RATE}` (mặc định `10/min`).
- **CSRF cho đăng nhập:** view đăng nhập của DRF mặc định miễn CSRF với người chưa đăng nhập → phải bật `csrf_protect` tường minh để chống login CSRF. Frontend gọi `GET /auth/csrf/` trước để có cookie `csrftoken` (đã ghi nhận ở spec 001).
- **Tài khoản bị khóa:** `ModelBackend.get_user` trả `None` khi `is_active = False`, nên phiên của tài khoản bị khóa tự hết hiệu lực ở request kế tiếp (phân quyền quy tắc 10). Spec này chỉ thêm test; thao tác khóa thuộc spec 003.
- **Đổi mật khẩu:** gọi `update_session_auth_hash` để giữ phiên hiện tại; các phiên khác của cùng tài khoản tự mất hiệu lực (Django đối chiếu hash mật khẩu trong phiên).

### 3.2. Mã lỗi mới — `core/errors.py`

| Mã | HTTP | Khi nào |
|---|---|---|
| `INVALID_CREDENTIALS` | 400 | Sai tên đăng nhập/mật khẩu **hoặc** tài khoản bị khóa — cùng một thông điệp, không tiết lộ tài khoản có tồn tại hay bị khóa (UC01.1 E1) |
| `PASSWORD_CHANGE_REQUIRED` | 403 | Tài khoản đang dùng mật khẩu tạm gọi API khác ngoài danh sách cho phép (D5) |

Thông điệp `INVALID_CREDENTIALS`: "Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản không thể đăng nhập. Vui lòng kiểm tra lại hoặc liên hệ Nhân viên."

### 3.3. Chặn khi phải đổi mật khẩu — `accounts/permissions.py`

`PasswordChangeNotRequired` (DRF permission) thêm vào `DEFAULT_PERMISSION_CLASSES` sau `IsAuthenticated`:

- Người dùng đã đăng nhập có `must_change_password = True` → `PASSWORD_CHANGE_REQUIRED`, **trừ** view khai báo thuộc tính `allow_when_password_change_required = True` (csrf, login, logout, `GET /me/`, đổi mật khẩu, `/meta/choices/`).
- Người chưa đăng nhập: để `IsAuthenticated` xử lý như cũ.
- Cờ nhận `True` (mọi method) hoặc tập method, vd `{"GET"}` cho `MeView` (xem được, chưa sửa được).
- `HasRole` **kế thừa** `PasswordChangeNotRequired`, vì view tự khai báo `permission_classes` sẽ không dùng `DEFAULT_PERMISSION_CLASSES`. Test `GateCoverageTests` quét mọi API view: view không chặn và không khai báo cờ → test fail. View công khai (`AllowAny`) cũng phải khai báo cờ rõ ràng.

### 3.4. Service — `accounts/services.py`

| Hàm | Việc làm |
|---|---|
| `login_user(request, username, password)` | `authenticate` → sai/khóa raise `BusinessError(INVALID_CREDENTIALS)`; đúng → `django.contrib.auth.login` (xoay session key) và trả user |
| `logout_user(request)` | `django.contrib.auth.logout` (xóa phiên phía server). Không đụng tới nhiệm vụ (UC01.2 BR1). Có danh sách hàm dọn dẹp đăng ký được (`register_logout_hook`) để spec 011 dừng GPS |
| `update_profile(user, data)` | Chỉ ghi các trường D4; kiểm tra định dạng/trùng `phone` qua serializer + ràng buộc DB; trả user |
| `change_password(request, current, new)` | Sai mật khẩu hiện tại → `VALIDATION_ERROR` trường `current_password`; mật khẩu mới qua `AUTH_PASSWORD_VALIDATORS` + phải khác mật khẩu hiện tại; lưu băm; `must_change_password = False`; `update_session_auth_hash`. Không ghi mật khẩu vào log/thông báo (UC02.3 BR2) |

Đổi `phone`/`full_name` không sửa dữ liệu nghiệp vụ đã phát sinh (UC02.2 BR2) — các spec sau phải chụp lại (snapshot) thông tin người gửi/nhận trên vận đơn, không tham chiếu động tới hồ sơ.

### 3.5. Thông báo — `notifications`

- Queryset luôn lọc `recipient = request.user`; id của người khác → `404` (không lộ sự tồn tại).
- Danh sách mới nhất trước, phân trang chuẩn, lọc `?unread=true`.
- Đánh dấu đã đọc **idempotent**: đã đọc rồi thì giữ nguyên `read_at` cũ, vẫn trả 200.
- Đánh dấu tất cả: một câu `UPDATE` cho các bản ghi chưa đọc của người dùng.

Chi tiết endpoint: [api.md](api.md).

## 4. Frontend

### 4.1. Nền

| File | Nội dung |
|---|---|
| `src/services/http.js` | Thêm `setUnauthorizedHandler(fn)`: khi API (trừ `/auth/*`, `/accounts/me/` lúc khởi động) trả `401` → gọi handler; khi trả `403 PASSWORD_CHANGE_REQUIRED` → handler riêng. Tránh import vòng giữa http và store |
| `src/services/authService.js` | `fetchCsrf()`, `login()`, `logout()`, `getMe()`, `updateMe()`, `changePassword()` |
| `src/services/notificationService.js` | `list()`, `unreadCount()`, `markRead(id)`, `markAllRead()` |
| `src/stores/auth.js` | `user`, `status` (`unknown`/`authenticated`/`anonymous`), `restore()` (gọi `GET /me/` một lần khi mở app — UC01.1 A1), `login()`, `logout()` (luôn xóa trạng thái cục bộ kể cả khi mất mạng — UC01.2 E1, và báo "chưa xác nhận được với máy chủ"), `mustChangePassword`, `role` |
| `src/stores/notifications.js` | `unreadCount`, `refreshCount()`, polling 60 giây khi `document.visibilityState === 'visible'`, dừng khi đăng xuất |
| `src/router/roles.js` | **Nơi duy nhất** ánh xạ mã vai trò → route trang chủ (`ROLE_HOME`). Cùng `statusTones.js` là các file frontend được phép chứa mã vai trò/trạng thái |
| `src/router/index.js` | `meta: { public: true }` hoặc `meta: { roles: [...] }`. Guard: chờ `auth.restore()` → chưa đăng nhập vào trang cần đăng nhập → `/login?next=...`; đã đăng nhập vào `/login` → trang chủ vai trò (A1); sai vai trò → trang chủ vai trò; `mustChangePassword` → chỉ cho `/account/password` |
| `vitest.config.js`, `src/**/__tests__/` | Vitest + jsdom |

### 4.2. Màn hình

| Route | View | Quyền | UC |
|---|---|---|---|
| `/login` | `views/auth/LoginView.vue` | công khai | 01.1 |
| `/forgot-password` | `views/auth/ForgotPasswordView.vue` | công khai | 01.3 |
| `/account/profile` | `views/account/ProfileView.vue` | 3 vai trò | 02.1, 02.2 |
| `/account/password` | `views/account/ChangePasswordView.vue` | 3 vai trò (kể cả khi phải đổi mật khẩu) | 02.3, 01.3 |
| `/notifications` | `views/account/NotificationsView.vue` | 3 vai trò | thông báo |
| `/shop`, `/staff`, `/shipper` | `views/{shop,staff,shipper}/*HomeView.vue` | đúng vai trò | trang chủ tạm, nội dung ở spec sau |

Thư mục mới `views/account/` cho màn hình dùng chung cả ba vai trò (không chép vào từng thư mục vai trò).

`layouts/AppLayout.vue` (mọi route cần đăng nhập): tên hệ thống, nhãn vai trò (lấy từ store meta), chuông thông báo kèm số chưa đọc, menu: Thông tin cá nhân, Đổi mật khẩu, Đăng xuất. Trang công khai dùng layout trống.

Hành vi chính:

- **Đăng nhập:** gọi CSRF → login; lỗi hiện thông điệp từ backend; nút khóa khi đang gửi; thành công → `next` (nếu hợp lệ, cùng origin) hoặc trang chủ vai trò; `mustChangePassword` → `/account/password` với thông báo bắt buộc đổi.
- **Đăng xuất:** gọi API; dù thành công hay mất mạng đều xóa trạng thái cục bộ, dừng polling, về `/login`; mất mạng thì báo "Đã đăng xuất trên thiết bị này nhưng chưa xác nhận được với máy chủ".
- **Hồ sơ:** trường trống hiện "Chưa cập nhật" (UC02.1 A1); chế độ sửa có Lưu/Hủy (UC02.2 A1 — Hủy khôi phục giá trị cũ, không gọi API); lỗi theo trường từ `fields`.
- **Đổi mật khẩu:** ba trường; lỗi theo trường; liên kết "Quên mật khẩu hiện tại?" → `/forgot-password` (UC02.3 A1); sau khi đổi thành công lúc bắt buộc → về trang chủ vai trò.
- **Quên mật khẩu:** hướng dẫn liên hệ Nhân viên + thông tin liên hệ D7; nói rõ phải xác minh danh tính, Nhân viên cấp mật khẩu tạm và phải đổi ở lần đăng nhập sau.
- **Thông báo:** danh sách (mới nhất trước, phân trang, lọc chưa đọc), bấm vào → đánh dấu đã đọc; nút "Đánh dấu tất cả đã đọc"; thời gian qua `formatDateTime`.
- Mọi màn hình có trạng thái đang tải, rỗng, lỗi (kèm "Thử lại").

## 5. Tiêu chí nghiệm thu

Checklist UC01–UC02 và tình huống phân quyền mục 6 liên quan:

Bằng chứng: test backend (`apps.accounts`, `apps.notifications`) + test Vitest + smoke test trên server đang chạy (ghi trong [tasks.md](tasks.md) nhật ký Phase 1–7).

- [x] Ba vai trò đăng nhập được, vào đúng trang chủ theo vai trò lấy từ tài khoản (UC01.1 BR2). *(test_auth, LoginView.spec, smoke 3 vai trò)*
- [x] Sai mật khẩu, sai tên đăng nhập, tài khoản khóa → **cùng** mã `INVALID_CREDENTIALS` và cùng thông điệp; không tạo phiên. *(test_auth; smoke `demo_khoa` = sai mật khẩu)*
- [x] Đăng nhập không kèm CSRF token bị từ chối (`403`). *(test_auth; smoke trực tiếp + qua proxy Vite)*
- [x] Đăng nhập quá 10 lần/phút từ một IP → `429`. *(test_auth)*
- [x] Đã đăng nhập mở `/login` → chuyển thẳng trang chủ vai trò (UC01.1 A1). *(guard.spec)*
- [x] Sau đăng xuất, cookie phiên cũ gọi API có quyền → `401` (UC01.2 BR2). Đăng xuất khi phiên đã hết → vẫn `204`. *(test_auth; smoke dùng lại cookie cũ)*
- [x] Tài khoản bị khóa (đặt `is_active=False` trực tiếp trong test) → request kế tiếp bằng phiên cũ `401`. *(test_auth)*
- [x] `GET /me/` không chứa `password`, `is_staff`, `is_superuser` (UC02.1 BR1). *(test_auth; smoke liệt kê khóa trả về)*
- [x] Gửi `role`, `is_active`, `username` khi sửa hồ sơ → không đổi các trường đó (phân quyền mục 6). *(test_profile; smoke gửi `role: ADMIN`)*
- [x] Sửa hồ sơ với `phone` trùng/sai định dạng → `400` có `fields.phone`; dữ liệu cũ giữ nguyên. *(test_profile, ProfileView.spec)*
- [x] Đổi mật khẩu sai mật khẩu hiện tại hoặc mật khẩu mới yếu/không khớp → `400`, mật khẩu cũ vẫn dùng được. *(test_profile, ChangePasswordView.spec)*
- [x] Đổi mật khẩu thành công: phiên hiện tại còn dùng được, phiên khác của cùng tài khoản → `401`. *(test_profile; smoke 2 phiên)*
- [x] `must_change_password = true`: gọi API khác → `403 PASSWORD_CHANGE_REQUIRED`; đổi mật khẩu xong → cờ về `false`, API khác dùng được; frontend ép vào trang đổi mật khẩu. *(test_auth/test_profile, GateCoverageTests, guard.spec, session.spec; smoke `demo_mktam`)*
- [x] Không đọc/đánh dấu được thông báo của người khác (`404`); đếm chưa đọc đúng; đánh dấu đã đọc lặp không đổi `read_at`. *(notifications test_api; smoke)*
- [x] Mật khẩu không xuất hiện trong log, thông báo hay response. *(test_profile kiểm tra log + body)*
- [ ] Frontend: `npm run test` (Vitest) pass; `npm run build` thành công; luồng đăng nhập → hồ sơ → đổi mật khẩu → thông báo → đăng xuất chạy được trên trình duyệt với ba tài khoản ba vai trò. *(Vitest 90/90 ✔; build ✔ khi xuất ra thư mục khác — `frontend/dist/` cũ bị khóa quyền xóa; **chờ người dùng thử trình duyệt theo [manual-test.md](manual-test.md)**.)*

## 6. Ghi chú cho spec sau

- **Spec 003:** Nhân viên đặt mật khẩu tạm = `set_password` + `must_change_password = True`; khóa tài khoản dùng `is_active` (phiên tự hết hiệu lực nhờ 3.1). Không khóa/đặt lại Admin hoạt động cuối cùng.
- **Spec 004+:** chụp thông tin người gửi/nhận vào vận đơn (3.4); dùng `layouts/AppLayout.vue`, `router/roles.js`, guard `meta.roles`.
- **Spec 011:** đăng ký hàm dừng GPS qua `register_logout_hook` (backend) và trong `auth.logout()` (frontend).
- **Triển khai thật:** throttle dùng cache mặc định (bộ nhớ từng tiến trình) — cần cache dùng chung (vd Redis) khi chạy nhiều tiến trình; bật `DJANGO_SECURE_COOKIES=True` khi có HTTPS.
