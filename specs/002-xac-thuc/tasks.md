# Spec 002 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Backend (Phase 1–3) và nền frontend (Phase 4) làm song song được; màn hình (Phase 5–6) cần cả hai.

```
Phase 0 ─┬─► Phase 1 ─► Phase 2 ─┐
         │              Phase 3 ─┼─► Phase 5 ─► Phase 6 ─► Phase 7
         └─► Phase 4 ────────────┘
```

Điều kiện chung: Docker DB đang chạy (`docker compose --env-file backend/.env up -d db`).

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D8 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt) (hoặc "theo đề xuất"). → Cả 8 điểm theo đề xuất.
- [x] **0.2** Có ít nhất một superuser (bước 1.7 spec 001) để thử bằng tay. → Người dùng chọn để Claude tạo tài khoản demo: lệnh `seed_demo` (`accounts/management/commands/seed_demo.py`) tạo `demo_superuser` (superuser, ADMIN), `demo_nhanvien` (ADMIN), `demo_shop` (SHOP), `demo_shipper` (SHIPPER). Mật khẩu ngẫu nhiên ghi vào `backend/.demo-accounts.txt` (đã thêm vào `.gitignore`), không in ra chat. Đã thử đăng nhập cả 4 bằng mật khẩu trong file.

Xong khi: mục 2 spec.md ghi rõ phương án đã chốt.

---

## Phase 1 — Backend: phiên, CSRF, đăng nhập/đăng xuất

- [x] **1.1** `core/errors.py`: thêm `INVALID_CREDENTIALS` (400), `PASSWORD_CHANGE_REQUIRED` (403); cập nhật bảng mã lỗi ở `specs/001-nen-tang/api.md`.
- [x] **1.2** `settings.py` + `backend/.env.example`: session 8 giờ, SameSite, cookie secure theo env, throttle `login`.
- [x] **1.3** `accounts/permissions.py`: `PasswordChangeNotRequired`; thêm vào `DEFAULT_PERMISSION_CLASSES`; đánh dấu `allow_when_password_change_required = True` cho `ChoicesView`. → `HasRole` kế thừa lớp chặn; cờ nhận tập method.
- [x] **1.4** `accounts/services.py`: `login_user`, `logout_user`, `register_logout_hook`. → Hook lỗi chỉ ghi log, không chặn đăng xuất.
- [x] **1.5** `accounts/serializers.py`: `LoginSerializer`, `MeSerializer` (chỉ trường ở api.md).
- [x] **1.6** `accounts/views.py` + `urls.py`: `csrf`, `login` (bật `csrf_protect`, throttle scope `login`), `logout`, `GET /me/`. → Dùng `SessionAuthentication().enforce_csrf` thay `csrf_protect` để lỗi CSRF trả JSON đúng định dạng.
- [x] **1.7** Test `accounts/tests/test_auth.py`:
  - ba vai trò đăng nhập được, response đúng trường, không có `password`/`is_staff`/`is_superuser`;
  - sai mật khẩu / sai username / tài khoản khóa → cùng mã + cùng thông điệp, không có cookie `sessionid`;
  - login không CSRF (client `enforce_csrf_checks=True`) → 403;
  - vượt giới hạn → 429 (đặt rate thấp bằng `override_settings` và xóa cache throttle giữa test);
  - session key đổi sau đăng nhập;
  - logout → phiên cũ gọi `/me/` 401; logout khi chưa đăng nhập → 204;
  - khóa tài khoản sau khi đăng nhập → request kế tiếp 401.
  → 24 test, thêm: đăng xuất cần CSRF khi đang đăng nhập, hook đăng xuất, thời hạn phiên, chặn mật khẩu tạm (view mặc định + view `HasRole` + endpoint được phép), **`GateCoverageTests` quét mọi API view**.

Xong khi: test 1.7 pass; `check` sạch.

---

## Phase 2 — Backend: hồ sơ, đổi mật khẩu, chặn mật khẩu tạm

- [x] **2.1** `MeUpdateSerializer` (chỉ `full_name`, `phone`, `address`) + `services.update_profile`. → Thông điệp trùng số điện thoại tiếng Việt; `IntegrityError` khi hai người lưu cùng lúc → lỗi trường `phone`.
- [x] **2.2** `ChangePasswordSerializer` + `services.change_password` (validators Django, khác mật khẩu cũ, `update_session_auth_hash`, tắt `must_change_password`). → Thêm `accounts/validators.py` (thông điệp độ dài tiếng Việt).
- [x] **2.3** View `PATCH /me/`, `POST /me/password/` (`allow_when_password_change_required` chỉ cho đổi mật khẩu). → Đổi mật khẩu có throttle `password_change` 10/phút/tài khoản.
- [x] **2.4** Test `accounts/tests/test_profile.py`:
  - sửa từng trường; gửi `role`/`is_active`/`username` → không đổi;
  - `phone` trùng / sai định dạng, `full_name` rỗng → 400 đúng `fields`, DB không đổi;
  - đổi mật khẩu: sai hiện tại, yếu, không khớp, trùng cũ → 400 đúng trường, mật khẩu cũ còn dùng được;
  - đổi thành công → 204, phiên hiện tại còn, phiên thứ hai (client khác) 401, đăng nhập bằng mật khẩu mới được;
  - `must_change_password=True` → `PATCH /me/` và API khác 403 `PASSWORD_CHANGE_REQUIRED`; `GET /me/`, đổi mật khẩu, logout, `/meta/choices/` vẫn dùng được; đổi xong → cờ `False`;
  - mật khẩu không xuất hiện trong response/log (`assertLogs` + kiểm tra body).
  → 14 test, thêm: tranh chấp số điện thoại, giới hạn đổi mật khẩu theo tài khoản, thông điệp tiếng Việt, đổi thất bại giữ cờ mật khẩu tạm.

Xong khi: test 2.4 pass.

---

## Phase 3 — Backend: API thông báo

- [x] **3.1** `notifications/serializers.py`: `NotificationSerializer`. → Thêm `NotificationListQuerySerializer` kiểm tra `unread`.
- [x] **3.2** `notifications/views.py` + `urls.py`: danh sách (lọc `unread`), `unread-count`, `{id}/read`, `read-all`; queryset luôn theo `request.user`. → Mọi truy vấn qua `own_notifications()`; đánh dấu đã đọc bằng `UPDATE … WHERE read_at IS NULL`.
- [x] **3.3** Test `notifications/tests/test_api.py`: chỉ thấy của mình; id người khác → 404; lọc chưa đọc; đếm; đánh dấu lặp giữ `read_at`; read-all trả đúng số; phân trang; chưa đăng nhập 401; số truy vấn danh sách không tăng theo số bản ghi (`assertNumQueries`).
  → 15 test, thêm: 404 của người khác giống hệt 404 không tồn tại, CSRF cho POST, chặn mật khẩu tạm, 405, tham số `unread` sai.
- [x] **3.4** *(phát sinh)* Thay index danh sách thông báo sau khi `EXPLAIN` cho thấy phải `Sort` — migration `notifications/0002`. Xem [models.md](models.md#index).

Xong khi: test 3.3 pass; toàn bộ test backend pass.

---

## Phase 4 — Frontend: nền xác thực + Vitest

- [x] **4.1** Thêm devDependency `vitest`, `@vue/test-utils`, `jsdom`; `vitest.config.js`; script `"test": "vitest run"`. → vitest 3.2.7 (sau `npm audit fix`), @vue/test-utils 2.4.6, jsdom 26.1.0; thêm `test:watch`.
- [x] **4.2** Test cho phần đã có ở spec 001: `http.js`, `stores/meta.js`, `utils/format.js`, `StatusBadge.vue` (chuyển từ script kiểm tra tạm của spec 001 vào repo). → Thêm `statusTones.spec.js` đọc thẳng `constants.py` backend để bắt lệch mã trạng thái.
- [x] **4.3** `http.js`: `setUnauthorizedHandler`, `setPasswordChangeRequiredHandler`. → Tùy chọn `skipSessionHandlers` cho login/logout/khôi phục phiên.
- [x] **4.4** `services/authService.js`, `services/notificationService.js`.
- [x] **4.5** `stores/auth.js`, `stores/notifications.js` (polling 60 giây, dừng khi tab ẩn/đăng xuất). → Chu kỳ đọc từ `src/config.js` (env `VITE_NOTIFICATION_POLL_MS`); `router/session.js` nối 401/mật khẩu tạm/polling.
- [x] **4.6** `router/roles.js` (`ROLE_HOME`) + guard trong `router/index.js`. → Logic guard tách thành hàm thuần `router/guard.js` (`resolveNavigation`, `safeNext` chống open redirect). Tạo **view tạm** cho 8 route mới (Phase 5–6 thay).
- [x] **4.7** Test Vitest: store auth (restore một lần, logout khi mất mạng vẫn xóa trạng thái), guard (chưa đăng nhập → `/login?next`, sai vai trò → trang chủ vai trò, phải đổi mật khẩu → `/account/password`, `next` ngoài origin bị bỏ qua), store notifications (dừng polling khi logout).
  → 58 test / 9 file, gồm `session.spec.js` (401 → về /login giữ `next`; mật khẩu tạm → trang đổi mật khẩu; polling bật/tắt theo đăng nhập).

Xong khi: `npm run test` pass; `npm run build` thành công.

---

## Phase 5 — Frontend: màn hình xác thực

- [x] **5.1** `layouts/AppLayout.vue` + layout trống cho trang công khai. → `App.vue` bọc `AppLayout` khi đã đăng nhập và trang không `public`. Thêm dùng chung: `components/common/FormField.vue`, `utils/formErrors.js`, style form/nút/alert/card trong `main.css`.
- [x] **5.2** `views/auth/LoginView.vue`. → Bỏ khoảng trắng username, xóa ô mật khẩu khi lỗi, `next` qua `safeNext`, thông báo đăng xuất chưa xác nhận / phiên hết hạn.
- [x] **5.3** `views/auth/ForgotPasswordView.vue` (đọc `VITE_SUPPORT_CONTACT`; thêm biến vào `frontend/.env.example`).
- [x] **5.4** `views/account/ChangePasswordView.vue` (cả chế độ bắt buộc).
- [x] **5.5** Trang chủ tạm `views/{shop,staff,shipper}/*HomeView.vue`; `HomeView.vue` hiện tại chuyển thành chuyển hướng theo trạng thái đăng nhập. → Ba trang dùng chung `components/common/RoleHome.vue`. Route `/` redirect `/login` (guard `guestOnly` đưa người đã đăng nhập về trang chủ vai trò). **`views/HomeView.vue` không còn dùng nhưng không xóa được** (quyền Windows, giống `dist/`) — không nằm trong build; chờ người dùng xóa.
- [x] **5.6** Test Vitest cho LoginView (hiện lỗi backend, khóa nút khi gửi) và ChangePasswordView (lỗi theo trường). → Thêm `AppLayout.spec.js`, `formErrors.spec.js`; tổng 76 test.

Xong khi: test pass; đăng nhập/đăng xuất/đổi mật khẩu chạy trên trình duyệt. *(Test + build + luồng API qua proxy Vite đạt; **chưa thử bằng trình duyệt thật** — làm ở Phase 7.)*

---

## Phase 6 — Frontend: hồ sơ và thông báo

- [x] **6.1** `views/account/ProfileView.vue` (xem, sửa, Hủy, "Chưa cập nhật", lỗi theo trường). → Luôn tải hồ sơ mới từ máy chủ khi mở (UC02.1), lỗi tải thì không hiện dữ liệu, có "Tải lại" (E1); lưu xong cập nhật cả store auth.
- [x] **6.2** `views/account/NotificationsView.vue` + chuông số chưa đọc trong `AppLayout`. → Bộ lọc/trang trên URL (`?unread=true&page=2`); bỏ kết quả cũ khi đổi bộ lọc liên tục; chuông đã có từ Phase 5.
- [x] **6.3** Test Vitest: Hủy không gọi API và khôi phục giá trị; đánh dấu đã đọc cập nhật số đếm. → 13 test (Profile 5, Notifications 8); tổng 89.

Xong khi: test pass; luồng trên trình duyệt chạy được. *(Test + build đạt; thử trình duyệt ở Phase 7.)*

---

## Phase 7 — Nghiệm thu

- [x] **7.1** `manage.py check`, `makemigrations --check` (không có migration mới), toàn bộ test backend. → sạch; migration mới duy nhất là `notifications/0002` (index, Phase 3); 157 test pass.
- [ ] **7.2** `npm run test`, `npm run build`. → Vitest 90/90 ✔; `npm audit --omit=dev` 0 lỗ hổng ✔; **`npm run build` vào `dist/` bị chặn** (quyền Windows trên `dist/` cũ) — build ra thư mục khác thành công.
- [ ] **7.3** Thử bằng tay trên trình duyệt với 3 tài khoản (SHOP, ADMIN, SHIPPER — tạo qua Django admin): toàn bộ tiêu chí [spec.md mục 5](spec.md#5-tiêu-chí-nghiệm-thu). → **Chờ người dùng** theo [manual-test.md](manual-test.md) (36 bước, 8 nhóm). Chuẩn bị: `seed_demo` thêm `demo_mktam` (mật khẩu tạm), `demo_khoa` (bị khóa), `--notifications` (31 thông báo mẫu); file mật khẩu giữ mật khẩu cũ khi chạy lại. Đã smoke test API cho cả hai tài khoản đặc biệt trên server đang chạy.
- [x] **7.4** Rà hardcode: mã vai trò trong frontend chỉ ở `router/roles.js`, `statusTones.js`, test. → Phát hiện `'PASSWORD_CHANGE_REQUIRED'` viết thẳng trong `http.js` → gom vào `API_ERROR` + test đối chiếu `core/errors.py`. Không có URL/host cứng; `import.meta.env` chỉ ở `config.js`/`http.js`.
- [x] **7.5** Đánh dấu tiêu chí; cập nhật `specs/README.md`, README gốc, `api.md`/`models.md` nếu lệch.

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 21/11/2026 | 0 | **Xong.** Chốt D1–D8 theo đề xuất. Thêm `seed_demo` (chỉ khi `DEBUG=True`, không ghi đè tài khoản có sẵn trừ `--reset`, ghi file **sau khi** DB commit) + 7 test. Lần chạy đầu phát hiện lỗi: console Windows cp1252 làm sập lệnh sau khi đã ghi file → DB rollback nhưng file chứa mật khẩu không hợp lệ. Sửa: ghi file sau commit, `manage.py` thay ký tự không in được bằng `?`; xóa file hỏng, chạy lại. 100 test pass. |
| 21/11/2026 | 1 | **Xong.** 4 endpoint (csrf, login, logout, me), chặn mật khẩu tạm, phiên 8 giờ, throttle 10/phút/IP. 124 test pass. Kiểm tra đột biến: thêm view quên chặn → `GateCoverageTests` bắt đúng route (lần đầu script kiểm tra sai chữ ký hàm, đã sửa). Smoke test trên server đang chạy với `demo_shop`: 7/7 bước đúng (CSRF, sai mật khẩu, thiếu CSRF, đúng, `/me/`, logout, dùng lại cookie cũ → 401). Test chạy chậm (80,6 s) vì PBKDF2 → bộ băm MD5 chỉ khi `manage.py test` → 1,7 s. |
| 21/11/2026 | 2 | **Xong.** `PATCH me/`, `POST me/password/`, luồng mật khẩu tạm hoàn chỉnh. Thêm ngoài spec: throttle đổi mật khẩu theo tài khoản; `IntegrityError` số điện thoại → lỗi trường. Phát hiện bản dịch Django `vi` thiếu câu "mật khẩu quá ngắn" (lẫn tiếng Anh) → validator riêng + test. 138 test pass. Smoke test trên server đang chạy với `demo_shop` 7/7 (gửi `role` bị bỏ qua, phiên khác mất sau đổi mật khẩu, mật khẩu cũ hết dùng) và đã trả mật khẩu/địa chỉ về như cũ. |
| 21/11/2026 | 3 | **Xong — backend spec 002 hoàn tất.** 4 endpoint thông báo. 153 test pass. `EXPLAIN` phát hiện index của spec 001 không phục vụ thứ tự sắp xếp (node `Sort` ở cả hai danh sách) → thay bằng `(recipient, -created_at, -id)` + bản partial chưa đọc; sau đổi: `Index Scan` không `Sort`, đếm chưa đọc `Index Only Scan`. Smoke test trên server đang chạy với `demo_shop` 8/8 (thông báo của `demo_shipper` không bị đụng tới); đã xóa 4 thông báo thử. |
| 21/11/2026 | 4 | **Xong.** Vitest + nền xác thực frontend (store auth/notifications, guard, xử lý 401/mật khẩu tạm, polling). 58 test pass. Kiểm tra đột biến 3 kiểu (bỏ chặn mật khẩu tạm, `safeNext` nhận `//evil`, logout không xóa khi mất mạng) — test đều bắt; file gốc khôi phục và đối chiếu `cmp`. Build ra thư mục tạm OK (56 module, code test không lọt vào build); `npm run build` vào `dist/` vẫn bị khóa quyền (chờ người dùng xóa). `npm audit`: production 0 lỗ hổng; dev còn 7 (2 critical ở tinypool/vitest — chỉ khai thác qua Vitest UI/mock redirect/cấu hình worker, không dùng) chỉ vá ở vitest 4.1.12 (major, rất mới) → **giữ vitest 3.2.7**, nâng khi vitest 4 ổn định. |
| 21/11/2026 | 5 | **Xong (chờ thử trình duyệt ở Phase 7).** Layout, đăng nhập, quên mật khẩu, đổi mật khẩu (thường + bắt buộc), trang chủ tạm 3 vai trò. 76 test Vitest pass, không cảnh báo Vue; build 60 module, `HomeView` và code test không lọt vào build. Luồng đăng nhập qua **proxy Vite** với `demo_shipper` 7/7. **Sự cố:** Vite của người dùng đang chạy ở 5173 → Vite của tôi không khởi động được, smoke test chạy qua Vite của người dùng; vòng dọn dẹp tắt theo cổng đã **tắt nhầm Vite của người dùng**. Đã báo người dùng chạy lại `npm run dev`; từ nay chỉ tắt PID do mình khởi động. |
| 21/11/2026 | 6 | **Xong (chờ thử trình duyệt ở Phase 7).** Màn hình Thông tin cá nhân (xem/sửa/Hủy) và Thông báo (lọc, đánh dấu, phân trang theo URL). 89 test Vitest pass, không cảnh báo Vue; build 62 module. Không bật server trong phase này (API đã smoke test ở Phase 2–3). Danh sách phân trang viết trực tiếp trong view — tách component dùng chung khi spec 004+ có danh sách thứ hai. |
| 21/11/2026 | 7 | Nghiệm thu: backend 157/157, Vitest 90/90, audit production 0. **15/16 tiêu chí đạt** bằng test + smoke; còn thử trình duyệt (manual-test.md). Sửa 1 hardcode (`API_ERROR`). `seed_demo`: thêm `demo_mktam`, `demo_khoa`, `--notifications`; sửa lỗi chạy lại `--output` làm mất mật khẩu cũ (nay giữ lại từ file) — sao lưu file trước khi chạy, xác nhận 6/6 mật khẩu đúng rồi xóa bản sao lưu. Smoke `demo_khoa`/`demo_mktam`/phân trang trên Django người dùng (không bật/tắt server). Còn chờ người dùng: thử trình duyệt, xóa `frontend/dist/` và `src/views/HomeView.vue`. |
| 21/11/2026 | Sửa lỗi | **Người dùng không đăng nhập được trên trình duyệt** ("Bạn không có quyền thực hiện thao tác này" — 403 CSRF). Nguyên nhân: proxy Vite dạng rút gọn `'/api': 'http://…'` tự bật `changeOrigin: true` → Django thấy `Host 127.0.0.1:8000` ≠ `Origin http://127.0.0.1:5173` → "Origin checking failed". Lọt qua mọi kiểm tra vì test client Django và các smoke script không gửi `Origin`. Sửa `frontend/vite.config.js` sang dạng đầy đủ `changeOrigin: false`; thêm 2 test backend gửi `Origin` như trình duyệt (cùng Host → 200; khác → 403). Tái hiện trước/sau qua Vite đang chạy: 403 → 200. |
