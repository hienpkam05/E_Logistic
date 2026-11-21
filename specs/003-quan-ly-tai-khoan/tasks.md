# Spec 003 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Backend (1–3) và nền frontend (4) làm song song được.

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung: Docker DB đang chạy. **Không tắt server người dùng đang chạy**; nếu cần server riêng, chỉ tắt đúng PID mình bật.

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D7 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt). → Cả 7 điểm theo đề xuất.

Xong khi: mục 2 ghi rõ phương án đã chốt.

---

## Phase 1 — Backend: model, phiên khi khóa, lịch sử

- [x] **1.1** `accounts/constants.py`: `AccountAction`, `TEMP_PASSWORD_LENGTH`, `TEMP_PASSWORD_ALPHABET`; đăng ký `account_actions` vào `core/choices.py`.
- [x] **1.2** `User.session_version` + ghi đè `get_session_auth_hash()`. → Ghi đè **cả** `get_session_auth_fallback_hash()` (nhánh xoay `SECRET_KEY`), không dựa vào hàm private của Django; thêm `User.invalidate_sessions()` (tăng bằng `F()`, an toàn đồng thời).
- [x] **1.3** Model `AccountEvent` (chỉ thêm) + admin chỉ đọc. → FK `account` `db_index=False` (index ghép đã bắt đầu bằng `account`); giữ index `actor_id` cho kiểm tra `PROTECT`.
- [x] **1.4** Migration `accounts/0002`; `migrate` trên DB local (lưu ý: mọi phiên hiện có mất hiệu lực một lần). → Tạo lại một lần trước khi áp dụng để bỏ index thừa; 5 tài khoản demo hoạt động vẫn đăng nhập được sau migrate.
- [x] **1.5** Test: tăng `session_version` → phiên cũ `401`; trả `is_active` về `true` không làm phiên cũ sống lại; tự đổi mật khẩu (spec 002) vẫn giữ phiên hiện tại; `AccountEvent` không xóa được tài khoản có lịch sử (`PROTECT`).
  → `test_session_version.py` 12 test, gồm **test đối chứng** chứng minh lỗ hổng (chỉ đổi `is_active` thì mở khóa làm phiên cũ sống lại), hash fallback, tăng đồng thời, admin chỉ đọc.

Xong khi: test pass; toàn bộ test spec 001–002 vẫn pass.

---

## Phase 2 — Backend: danh sách, chi tiết, tạo, sửa

- [x] **2.1** `services.create_account`, `services.update_account`, sinh mật khẩu tạm qua validators. → So `updated_at` **sau** `select_for_update`; `IntegrityError` (tranh chấp) → lỗi đúng trường; không có thay đổi thì không ghi lịch sử.
- [x] **2.2** Serializer `ManagedUserSerializer`, `AccountCreateSerializer`, `AccountUpdateSerializer`, `AccountListQuerySerializer`. → Tách `phone_field()` dùng chung với hồ sơ spec 002; `username` không trùng **không phân biệt hoa thường**.
- [x] **2.3** View + URL: `users/` (GET, POST), `users/{id}/` (GET, PATCH); quyền `HasRole.of(ADMIN)`; chặn thao tác lên chính mình.
- [x] **2.4** Test `accounts/tests/test_management.py` (phần 1): quyền theo vai trò, lọc/tìm/phân trang, không lộ trường nhạy cảm, tạo (trùng → không tạo gì, mật khẩu tạm dùng được + bị buộc đổi), sửa (trường cấm bị bỏ qua, `409` khi `updated_at` cũ), `DELETE` → `405`, `EXPLAIN` danh sách.
  → 31 test; `EXPLAIN` cho thấy index `role` đơn vẫn phải `Sort` theo `username` → thay bằng `(role, username)` (migration `accounts/0003`), sau đổi `Index Scan` không `Sort`. Tìm `icontains` không dùng được index B-tree — chấp nhận ở quy mô vài trăm tài khoản, ghi hướng nâng cấp `pg_trgm`.

Xong khi: test pass.

---

## Phase 3 — Backend: khóa, mở khóa, đặt lại mật khẩu, lịch sử

- [x] **3.1** `services.lock_account`, `unlock_account`, `reset_password`, `register_account_locked_hook`. → Hook chạy **trong** transaction khóa (hook lỗi thì khóa cũng hủy).
- [x] **3.2** Quy tắc Admin hoạt động cuối cùng với `select_for_update`. → Khóa **mọi** ADMIN đang hoạt động theo thứ tự `id` **trước** khi khóa dòng mục tiêu, tránh deadlock.
- [x] **3.3** View + URL: `lock/`, `unlock/`, `reset-password/`, `events/`.
- [x] **3.4** Test (phần 2): khóa → không đăng nhập được + phiên cũ `401` + mở khóa phải đăng nhập lại; lặp khóa/mở khóa không ghi trùng; Admin cuối cùng; chính mình `403`; đặt lại thiếu xác minh `400`, thành công → phiên cũ `401`, mật khẩu tạm dùng được + buộc đổi; lịch sử đủ dòng, có người thực hiện, không chứa mật khẩu; mật khẩu tạm không có trong log; hook chạy khi khóa.
  → `test_management_actions.py` 21 test, gồm **test 2 luồng song song thật** (`TransactionTestCase`, 2 kết nối DB) — đạt 5/5 lần chạy; kiểm tra đột biến bỏ khóa danh sách Admin → test fail với `['ok','ok']` (mất hết Admin) hoặc `deadlock detected`.
- [x] **3.5** Smoke test trên server đang chạy (không bật/tắt server của người dùng) với tài khoản demo; trả dữ liệu demo về như cũ. → 10/10 trên tài khoản thử tạo riêng (không khóa tài khoản demo); đã xóa tài khoản thử + 4 dòng lịch sử.

Xong khi: test pass; smoke đạt.

---

## Phase 4 — Frontend: nền dùng chung

- [x] **4.1** Tách `components/common/PaginationBar.vue` từ `NotificationsView` (test cũ vẫn pass). → 8/8 test `NotificationsView` vẫn pass.
- [x] **4.2** `components/common/ConfirmDialog.vue`, `components/common/OneTimeSecret.vue`. → `ConfirmDialog` dùng `<dialog>` + `showModal()` (bẫy focus, Esc), **fallback thuộc tính `open`** khi không có (jsdom không có `showModal`/`close` — đã kiểm tra); Esc bị chặn để component cha quyết định. `OneTimeSecret`: clipboard bị chặn thì chọn sẵn chữ + hướng dẫn Ctrl+C. Thêm `.btn--danger`.
- [x] **4.3** `services/accountService.js`.
- [x] **4.4** Route `/staff/accounts`, `/staff/accounts/new`, `/staff/accounts/:id` (`meta.roles: [ROLES.ADMIN]`); menu Nhân viên. → Menu theo vai trò khai báo **một chỗ** `router/roles.js` (`ROLE_MENU`, `menuFor`), dùng ở cả `AppLayout` và trang chủ (`RoleHome`). Route `:id(\d+)`. 3 view tạm (Phase 5 thay).
- [x] **4.5** Test Vitest cho 3 component. → + `accountService.spec.js` (đúng URL/tham số/body theo api.md), menu theo vai trò trong `AppLayout.spec.js`; tổng 109 test.

Xong khi: `npm run test` pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** `AccountListView.vue` (tab vai trò, lọc trạng thái, tìm, URL, trống/lỗi). → Tìm theo nút/Enter (không gọi API mỗi phím); tab "Quản lý Shipper" đổi tiêu đề + nút "Thêm Shipper".
- [x] **5.2** `AccountCreateView.vue` (khóa vai trò khi `?role=SHIPPER`, Hủy, lỗi trường, hộp mật khẩu tạm). → Rời trang khi mật khẩu tạm đang hiện mà chưa bấm "Tôi đã ghi lại" → hỏi xác nhận.
- [x] **5.3** `AccountDetailView.vue` (xem/sửa/Hủy, `409` → nút tải lại, khóa/mở khóa có xác nhận, đặt lại mật khẩu có ô xác minh, lịch sử, ẩn thao tác với chính mình). → Hộp khóa nêu ảnh hưởng (Shipper: nhiệm vụ mở vẫn giữ); lỗi `LIMIT_REACHED` hiện trong hộp; lịch sử diễn giải thay đổi trước/sau.
- [x] **5.4** Test Vitest cho 3 màn hình. → 27 test; thêm helper `mountRouted` (mount qua `<RouterView>` để thử `onBeforeRouteLeave`); tổng 136.

Xong khi: test pass; build.

---

## Phase 6 — Nghiệm thu

- [ ] **6.1** `check`, `makemigrations --check`, toàn bộ test backend; `npm run test`, build. → backend 221/221 ✔, Vitest 136/136 ✔, audit production 0 ✔; **`npm run build` vào `dist/` vẫn bị chặn quyền** (build ra thư mục khác thành công).
- [x] **6.2** Rà hardcode (mã vai trò frontend chỉ ở `router/roles.js`). → Backend: không còn mã/thông điệp viết thẳng ngoài `constants.py`/`errors.py`; frontend: chỉ `roles.js`, `http.js`, test; không có URL/host cứng.
- [ ] **6.3** `manual-test.md` + người dùng thử trình duyệt. → [manual-test.md](manual-test.md) sẵn sàng (38 bước, 8 nhóm, dùng 2 cửa sổ để thử phiên khi khóa/mở khóa/đặt lại). **Chờ người dùng.**
- [x] **6.4** Đánh dấu tiêu chí; cập nhật `specs/README.md`, README gốc, `api.md`/`models.md` nếu lệch. → 13/14 tiêu chí `[x]`; api.md/models.md đã cập nhật theo từng phase, không lệch.

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 21/11/2026 | 0 | **Xong.** Người dùng chốt D1–D7 theo đề xuất: ADMIN quản lý cả 3 vai trò (trừ chính mình, trừ khóa Admin cuối cùng); mật khẩu tạm do hệ thống sinh, hiện một lần; không đổi vai trò sau tạo; đặt lại mật khẩu cần xác nhận đã xác minh; lý do khóa tùy chọn; lịch sử chỉ thêm; tìm kiếm có phân biệt dấu. |
| 21/11/2026 | 1 | **Xong.** `session_version` + ghi đè hash phiên (cả fallback), `AccountEvent` chỉ thêm, nhóm `account_actions` ở `/meta/choices/`. 169 test pass. Migration `accounts/0002` tạo lại một lần trước khi áp dụng để bỏ index FK thừa (cùng lỗi đã gặp ở spec 001–002), rồi áp dụng lên DB local. Sau migrate: 5 tài khoản demo đăng nhập được; server người dùng (PID 584, không động tới) trả `account_actions`. Sự cố nhỏ: một lệnh của tôi treo do `python -` thừa chờ stdin — đã dừng, phần ghi file trước đó không ảnh hưởng. |
| 21/11/2026 | 2 | **Xong.** API danh sách/chi tiết/tạo/sửa. 200 test pass (1 test của tôi viết sai — gọi `make_user` trong khối mock và mô phỏng tranh chấp qua API, nơi serializer bắt trước — viết lại gọi thẳng service). Index `(role, username)` thay index `role` (migration `0003`, đã áp dụng). Smoke trên server người dùng (PID 34544, không động tới) với `demo_nhanvien` 11/11: lọc, tạo + mật khẩu tạm đăng nhập được và bị buộc đổi, trùng SĐT, sửa + `role` bị bỏ qua, `409` bản cũ, tự sửa `403`, `DELETE` `405`, Shop `403`; tìm "hoan" không ra "Hoàn" — đúng D7. Đã xóa tài khoản thử + 2 dòng lịch sử. |
| 21/11/2026 | 3 | **Xong — backend spec 003 hoàn tất.** Khóa/mở khóa/đặt lại mật khẩu/lịch sử. 221 test pass (1 test đo truy vấn của tôi sai mốc: trang rỗng Django bỏ câu truy vấn dữ liệu — đo lại từ 1 bản ghi). Quy tắc Admin cuối cùng chứng minh bằng test 2 luồng thật + đột biến. Smoke trên server người dùng (PID 12972) 10/10: phiên chết khi khóa và **không sống lại khi mở khóa**, đăng nhập khi khóa = lỗi chung, đặt lại thiếu xác minh 400, mật khẩu tạm cũ hết hiệu lực, tự khóa 403, lịch sử 4 dòng không có mật khẩu. |
| 21/11/2026 | 4 | **Xong.** `PaginationBar` (tách từ Thông báo), `ConfirmDialog`, `OneTimeSecret`, `accountService`, 3 route + menu Nhân viên từ một nguồn. 109 test Vitest pass, 0 cảnh báo Vue; build 67 module ra thư mục tạm (`dist/` vẫn khóa quyền). Phát hiện trước khi viết: jsdom không có `showModal()` → thiết kế fallback. Không bật/tắt server. |
| 21/11/2026 | 5 | **Xong (chờ thử trình duyệt ở Phase 6).** 3 màn hình danh sách/tạo/chi tiết + `utils/accountStatus.js` dùng chung. 136 test Vitest pass, 0 cảnh báo Vue; build 76 module. **Lỗi thật test phát hiện:** kiểm tra `?role=` bằng danh mục meta (tải bất đồng bộ) → mở thẳng `/staff/accounts?role=SHIPPER` lần tải đầu bỏ qua lọc và không tải lại khi meta về → sửa bằng `isRole()` đồng bộ trong `roles.js`, thêm test hồi quy. Test `onBeforeRouteLeave` ban đầu không chạy vì mount trực tiếp (guard chỉ đăng ký qua RouterView) → helper `mountRouted`. Hardcode lọt (`'CONFLICT'`) → `API_ERROR.CONFLICT`; rà lại: không còn mã cứng ngoài `roles.js`/`http.js`/test. |
| 21/11/2026 | 6 | Nghiệm thu: backend 221/221, Vitest 136/136, audit production 0, rà hardcode sạch cả backend lẫn frontend. **13/14 tiêu chí đạt**; còn thử trình duyệt theo `manual-test.md` (38 bước). Đã đọc (không sửa) trạng thái 6 tài khoản demo để kịch bản khớp dữ liệu thật; nêu cách đưa demo về như cũ sau khi thử. Không bật/tắt server (Django người dùng PID 12972). |
