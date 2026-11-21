# Spec 001 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Mỗi phase kết thúc bằng lệnh kiểm tra; không sang phase phụ thuộc khi phase trước chưa đạt. Phase 2, 3, 4 có thể làm song song sau Phase 1.

```
Phase 0 ─► Phase 1 ─┬─► Phase 2 ─┐
                    ├─► Phase 3 ─┼─► Phase 5 ─► Phase 6 ─► Phase 7
                    └─► Phase 4 ─┘
```

---

## Phase 0 — Môi trường và quyết định chặn

Mục tiêu: chạy được Django trên PostgreSQL trước khi viết code.

- [x] **0.1** Chốt D6 (phiên bản Python). Nếu đổi sang 3.13: tạo lại `venv/`. Nếu giữ 3.14: ghi lại trong README. → Giữ 3.14 (máy không có 3.13; cài và `check` chạy sạch). Còn sửa README ở 7.6.
- [x] **0.2** Chốt D4 (trường `must_change_password`) — ảnh hưởng migration đầu tiên. → Theo đề xuất (tạm, đổi được tới trước Phase 1).
- [x] **0.3** `venv/Scripts/python -m pip install -r requirements.txt`.
- [x] **0.4** `docker compose --env-file backend/.env up -d db`; tạo `backend/.env` từ `.env.example`, đặt `DJANGO_SECRET_KEY` mới. → `.env` đã tạo (key 50 ký tự). Máy có PostgreSQL 18 cục bộ chiếm 5432 → chốt dùng Docker ở **cổng 5433** (`POSTGRES_PORT=5433`); `compose.yaml` đọc cổng từ env.
- [x] **0.5** **Không chạy `migrate`** ở phase này. → DB `htt_express` còn 0 bảng.

Xong khi: `python backend/manage.py check` không lỗi; container `db` ở trạng thái healthy.

---

## Phase 1 — Custom User (khó sửa nhất, làm trước)

Mục tiêu: migration đầu tiên của dự án là User tùy biến.

- [x] **1.1** `apps/accounts/constants.py`: `UserRole`, `PHONE_REGEX`.
- [x] **1.2** `apps/accounts/models.py`: `UserManager` (`create_user` bắt buộc `role`; `create_superuser` gán `ADMIN`), `User(AbstractUser)` theo [models.md](models.md#user), bỏ `first_name`/`last_name`, property `is_shop`/`is_admin_role`/`is_shipper`.
- [x] **1.3** `config/settings.py`: `AUTH_USER_MODEL = "accounts.User"`.
- [x] **1.4** `apps/accounts/admin.py`: `UserAdmin` tùy biến (danh sách: username, full_name, phone, role, is_active; lọc theo role, is_active; tìm theo username, full_name, phone).
- [x] **1.5** `apps/accounts/permissions.py`: `HasRole`.
- [x] **1.6** `makemigrations accounts` → xem lại `accounts/0001_initial.py` (có CheckConstraint role, unique phone).
- [x] **1.7** `migrate` lần đầu trên PostgreSQL; `createsuperuser`. → `migrate` đã chạy. Superuser `demo_superuser` (role ADMIN) tạo bằng `seed_demo` ở spec 002 Phase 0 (21/11/2026). Còn xem `/admin/` bằng tay.
- [x] **1.8** Test `apps/accounts/tests/test_user.py`: role sai bị DB từ chối, phone trùng/sai định dạng bị từ chối, superuser có role ADMIN, `HasRole` từ chối `is_active=False` và sai vai trò. → 16 test pass, gồm cả test trang Django admin render và thêm User qua admin.

Xong khi: test 1.8 pass; đăng nhập `/admin/` thấy User với đủ trường, không có first/last name.

---

## Phase 2 — Lỗi API và phân trang

- [x] **2.1** `apps/core/errors.py`: `ErrorCode`, `BusinessError` (map code → HTTP status mặc định). → Thêm `REQUEST_ERROR` cho 405/406/415/429 và helper `error_payload`.
- [x] **2.2** `apps/core/exception_handler.py`: chuẩn hóa mọi lỗi về `{"error": {code, message, fields}}` theo [api.md](api.md#định-dạng-lỗi). **Lưu ý:** với `SessionAuthentication`, DRF trả `NotAuthenticated` thành **403** (không có header `WWW-Authenticate`) — handler phải ép về **401** `NOT_AUTHENTICATED` như api.md quy định.
- [x] **2.3** 404 JSON cho đường dẫn không tồn tại dưới `/api/v1/` (handler404 hoặc route bắt cuối trong `config/urls.py`); ngoài `/api/` giữ hành vi Django. → Route bắt cuối `^api/(?:.*/)?$`, chỉ bắt URL có `/` cuối để `APPEND_SLASH` vẫn hoạt động.
- [x] **2.4** `apps/core/pagination.py`: `StandardPagination`.
- [x] **2.5** `settings.py`: `EXCEPTION_HANDLER`, `DEFAULT_PAGINATION_CLASS`, `CSRF_TRUSTED_ORIGINS` từ env; cập nhật `backend/.env.example`.
- [x] **2.6** Test `apps/core/tests/test_errors.py`: ValidationError (có `fields`), BusinessError, 401, 404 đều đúng định dạng; không lộ stack trace. → 19 test (dùng urlconf test `apps/core/tests/error_urls.py`), gồm cả lỗi Django ValidationError, JSON sai cú pháp, 405, phân trang.

Xong khi: test 2.6 pass.

---

## Phase 3 — Enum và bảng chuyển trạng thái

Không cần database.

- [x] **3.1** `apps/core/transitions.py`: `Transition`, `resolve_transition`. → Thêm `transition()` (cú pháp khai báo gọn) và `allowed_actions()`.
- [x] **3.2** `apps/shipments/constants.py`: `ShipmentStatus`, `TERMINAL_SHIPMENT_STATUSES`, `HolderType`, `ShipmentAction`, `SHIPMENT_TRANSITIONS`; hằng số D2/D3 (`REQUEST_CODE_PREFIX`, `TRACKING_CODE_PREFIX`, `TRACKING_CODE_RANDOM_LENGTH`, `TRACKING_CODE_ALPHABET`, `COD_MAX_VND`).
- [x] **3.3** `apps/dispatch/constants.py`: `MAX_DELIVERY_ATTEMPTS`, `TaskType`, `TaskStatus`, `TERMINAL_TASK_STATUSES`, `TaskAction`, `TASK_TRANSITIONS`. → Thêm `OPEN_TASK_STATUSES`.
- [x] **3.4** Test `apps/core/tests/test_transitions.py`: vai trò sai → `PERMISSION_DENIED`; nguồn sai → `INVALID_TRANSITION`.
- [x] **3.5** Test toàn vẹn bảng (`apps/shipments/tests/test_transitions_table.py`, `apps/dispatch/tests/test_transitions_table.py`): mọi source/target thuộc enum; trạng thái kết thúc không có hành động đi ra; mọi trạng thái không kết thúc có ít nhất một hành động đi ra; mọi trạng thái đến được từ `CREATE_REQUEST`/trạng thái đầu. → Bộ kiểm tra dùng chung `apps/core/tests/table_checks.py`; thêm: mọi trạng thái không kết thúc đều đi tới được trạng thái kết thúc, và **so khớp chính xác từng dòng với bảng mục 4 checklist** (thiếu hoặc thừa đều báo lỗi).

Xong khi: test 3.4–3.5 pass; đối chiếu bảng với mục 4 checklist không thiếu dòng.

---

## Phase 4 — Thông báo nội bộ

- [x] **4.1** `apps/notifications/constants.py`: `NotificationKind`.
- [x] **4.2** `apps/notifications/models.py`: `Notification` theo [models.md](models.md#notification). → FK `recipient` để `db_index=False` vì đã có index ghép.
- [x] **4.3** `apps/notifications/services.py`: `notify(recipients, kind, title, body, payload=None)` dùng `bulk_create`. → Tự chặn khi gọi ngoài transaction; bỏ trùng người nhận.
- [x] **4.4** `apps/notifications/admin.py`: đăng ký chỉ đọc (không cho sửa nội dung).
- [x] **4.5** `makemigrations notifications` → `0001_initial`; `migrate`.
- [x] **4.6** Test: `notify` tạo đúng số bản ghi cho nhiều người nhận; rollback transaction thì không còn thông báo. → 9 test, gồm gọi ngoài transaction, kind sai, payload không dùng chung, admin chỉ đọc.

Xong khi: test 4.6 pass.

---

## Phase 5 — Endpoint enum

- [x] **5.1** `apps/core/views.py`: `ChoicesView` (`AllowAny`), sinh dữ liệu từ các `TextChoices` + hằng số, không viết tay danh sách. → Danh sách nhóm tách ra `apps/core/choices.py` (`CHOICE_GROUPS`, `LIMITS`, `build_choices()`); thêm nhóm `task_actions`.
- [x] **5.2** `apps/core/urls.py`: `meta/choices/`.
- [x] **5.3** Test: không cần đăng nhập; đủ các nhóm theo [api.md](api.md#get-apiv1metachoices); `terminal` đúng; `limits` khớp hằng số. → 10 test, gồm test tự quét mọi `TextChoices` trong `constants.py`/`errors.py` để bắt enum quên đăng ký.

Xong khi: test 5.3 pass; `curl http://127.0.0.1:8000/api/v1/meta/choices/` trả JSON đúng.

---

## Phase 6 — Nền frontend

- [x] **6.1** `vite.config.js`: `loadEnv`, proxy đọc `VITE_PROXY_TARGET`; thêm biến vào `frontend/.env.example`. → Tạo `frontend/.env` từ example.
- [x] **6.2** `src/services/http.js`: API client + `ApiError` (gồm `NETWORK_ERROR`), CSRF header cho POST/PUT/PATCH/DELETE. → Base URL mặc định `/api/v1` nếu thiếu env; xử lý 204, lỗi không phải JSON, `AbortError`, params dạng mảng.
- [x] **6.3** `src/services/metaService.js`: `getChoices()`.
- [x] **6.4** `src/stores/meta.js`: tải một lần, `label()`, `isTerminal()`, `limits`, trạng thái `loading`/`error`. → Thêm `options(group)`, `ready`; các lời gọi đồng thời dùng chung một request.
- [x] **6.5** `src/utils/format.js`: `formatVnd`, `formatDateTime`, `formatPhone`. → Định dạng ngày giờ vi-VN thực tế: `09:30 20/11/2026`.
- [x] **6.6** `src/utils/statusTones.js` + biến màu tone trong `main.css`.
- [x] **6.7** `src/components/common/StatusBadge.vue`.
- [x] **6.8** `App.vue`: tải enum khi khởi động; lỗi tải không chặn trang chủ. → Có thanh báo lỗi + nút "Thử lại".

Xong khi: `npm.cmd run build` thành công; chạy dev, trang chủ hiển thị; thử tạm `StatusBadge` với vài trạng thái ra đúng nhãn tiếng Việt (bỏ phần thử trước khi bàn giao).

> Thay cho "thử tạm trên giao diện": kiểm tra bằng script Vite SSR ngoài repo (không thêm thư viện test, không sửa giao diện tạm) — 27/27 đạt. **Chưa có test frontend tự động trong repo**; cân nhắc thêm Vitest khi có màn hình nghiệp vụ (spec 002).
>
> **Lưu ý cho spec 002:** cookie `csrftoken` chỉ được Django đặt khi có view gọi `get_token`/`ensure_csrf_cookie`. Spec 002 cần endpoint cấp CSRF (vd `GET /api/v1/accounts/csrf/`) trước khi frontend gửi POST đăng nhập.

---

## Phase 7 — Nghiệm thu

- [x] **7.1** `python backend/manage.py check` → sạch. (`check --deploy`: 5 cảnh báo môi trường local, ghi ở spec.md mục 5.)
- [x] **7.2** `python backend/manage.py makemigrations --check --dry-run` không phát hiện thay đổi
- [x] **7.3** `python backend/manage.py test` trên PostgreSQL — toàn bộ pass → 93/93.
- [ ] **7.4** `npm.cmd run build` → **bị chặn** bởi quyền xóa file trong `frontend/dist/` cũ (EPERM). Build ra thư mục khác thành công. Cần người dùng xóa `frontend/dist/` bằng quyền Administrator rồi chạy lại.
- [x] **7.5** Rà hardcode: `rg -n "\"(SHOP|ADMIN|SHIPPER|PENDING_APPROVAL|DELIVERED)\"" backend/apps frontend/src` chỉ còn trong `constants.py`, `statusTones.js`, test → rà toàn bộ 28 mã trạng thái/vai trò/loại: chỉ còn trong `constants.py` và test; không có URL/host viết cứng trong `frontend/src`.
- [x] **7.6** Đánh dấu tiêu chí mục 5 trong [spec.md](spec.md); cập nhật cột Trạng thái trong [specs/README.md](../README.md); cập nhật README gốc (Python, biến env mới)

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 21/11/2026 | 0 | Python 3.14.2 + Django 5.2.19, DRF 3.16.1, psycopg 3.3.9 cài OK; `manage.py check` sạch. Tạo `backend/.env`. Chặn ở DB: cổng 5432 do PostgreSQL 18 cục bộ chiếm, Docker Desktop chưa chạy. |
| 21/11/2026 | 0 | **Xong.** Chốt Docker cổng 5433; `compose.yaml` đọc cổng từ env, chạy bằng `--env-file backend/.env`; README và `.env.example` cập nhật. Container `postgres:17` healthy tại `127.0.0.1:5433`; Django kết nối được, DB 0 bảng. |
| 21/11/2026 | 1 | User tùy biến + `HasRole` + admin. `accounts/0001_initial` áp dụng lên DB thật (15 cột, 5 ràng buộc). 16 test pass trên PostgreSQL. `makemigrations --check` sạch. Chờ người dùng `createsuperuser` để kiểm tra `/admin/` bằng tay. |
| 21/11/2026 | 2 | **Xong.** Định dạng lỗi thống nhất (401 thay 403 khi chưa đăng nhập; 500 không lộ chi tiết, traceback vào log), JSON 404 cho `/api/`, phân trang `page_size` ≤ 100, `CSRF_TRUSTED_ORIGINS` từ env. Toàn bộ 35 test pass trên PostgreSQL. |
| 21/11/2026 | 3 | **Xong.** Enum + bảng chuyển trạng thái vận đơn (17 trạng thái, 18 hành động) và nhiệm vụ (5 trạng thái, 5 hành động). Kiểm tra đột biến: cố ý làm hỏng bảng 5 kiểu (thiếu dòng UC06.7 A1.2, Shipper tự đóng luồng hoàn, mở lại đơn Đã giao, bỏ bước nhập điểm tập kết, nhiệm vụ thất bại → Đã thay thế) — test đều bắt được; phát hiện và sửa 1 lỗi trong chính test (đọc biến module thay vì bảng đang kiểm tra). 74 test pass. |
| 21/11/2026 | 4 | **Xong.** Model + service `notify` + admin chỉ đọc; `notifications/0001_initial` trên DB thật. Phát hiện index thừa trên `recipient_id` sau migrate → rút migration (bảng 0 bản ghi), đặt `db_index=False`, tạo lại. 83 test pass; `makemigrations --check` sạch. |
| 21/11/2026 | 5 | **Xong.** `GET /api/v1/meta/choices/` (9 nhóm). Kiểm tra đột biến: bỏ `task_actions` khỏi đăng ký → test bắt được. Gọi thật qua `runserver` + `curl`: 200, 4615 byte, UTF-8 đúng, nhãn tiếng Việt không bị escape. 93 test pass. |
| 21/11/2026 | 6 | **Xong.** API client, store meta, formatter, `StatusBadge`, proxy Vite đọc env. Build sạch (40 module). Script kiểm tra Vite SSR 27/27 đạt: http client với backend thật (404/405/mất mạng/CSRF/params/204/lỗi non-JSON), store tải 1 lần, badge render đúng nhãn + tông, `statusTones` khớp đủ mã backend, formatter. `npm run dev` thật: trang chủ 200, `/api` qua proxy 200 UTF-8. Phát sinh: JSON 404 `/api` bị escape `\uXXXX` → sửa `ensure_ascii=False` + test; 93 test backend pass. **Không chạy được `npm run build` vào `frontend/dist/`**: thư mục cũ (16/11, do công cụ khác tạo) không cho tài khoản hiện tại xóa file — build kiểm tra ra thư mục tạm. |
| 21/11/2026 | 7 | Nghiệm thu: check sạch, không còn migration thiếu, 93/93 test, rà hardcode đạt; README gốc viết lại (Python 3.14, migrate/createsuperuser, test, env, phạm vi). **6/8 tiêu chí đạt; 2 chờ người dùng**: tạo superuser + kiểm tra `/admin/` bằng tay (DB 0 superuser), xóa `frontend/dist/` cũ để `npm run build` chạy. |
