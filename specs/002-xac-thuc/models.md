# Spec 002 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Bảng | — | Không có bảng mới, không thêm/sửa cột |
| Index | `notifications_notification` | **Thay index** cho danh sách thông báo — migration `notifications/0002_notification_list_indexes` (xem mục Index) |
| Enum | `ErrorCode` (`core/errors.py`) | Thêm `INVALID_CREDENTIALS`, `PASSWORD_CHANGE_REQUIRED` |
| Cấu hình | `settings.py` + `backend/.env.example` | Thời hạn phiên, cookie, giới hạn đăng nhập |
| Cấu hình frontend | `frontend/.env.example` | `VITE_SUPPORT_CONTACT` |

Spec này dùng lại bảng đã có: `accounts_user` (đọc/sửa `full_name`, `phone`, `address`, `password`, `must_change_password`), `notifications_notification` (đọc, sửa `read_at`), `django_session` (Django quản lý).

## Trường được ghi

| Bảng.trường | Ai ghi | Khi nào |
|---|---|---|
| `accounts_user.full_name`, `phone`, `address` | Chính người dùng | UC02.2 — chỉ ba trường này (D4) |
| `accounts_user.password` | Chính người dùng | UC02.3 — luôn băm |
| `accounts_user.must_change_password` | Hệ thống | Về `False` khi đổi mật khẩu thành công (bật `True` ở spec 003) |
| `accounts_user.last_login` | Django | Khi đăng nhập thành công |
| `notifications_notification.read_at` | Người nhận | Lần đầu đánh dấu đã đọc; không ghi đè lần sau |
| `django_session` | Django | Tạo khi đăng nhập (xoay key), xóa khi đăng xuất |

Không trường nào trong spec này được sửa qua API: `username`, `email`, `role`, `is_active`, `is_staff`, `is_superuser`, `date_joined`, `notifications_notification.*` ngoài `read_at`.

## Index

Phát hiện ở Phase 3 khi xem `EXPLAIN`: index `notif_recipient_read_idx (recipient, read_at, -created_at)` của spec 001 **không phục vụ được thứ tự sắp xếp** của danh sách (`-created_at, -id`): danh sách đầy đủ có `read_at` chen giữa, cả hai danh sách thiếu `id` để phân định → PostgreSQL phải `Sort` toàn bộ thông báo của người dùng mỗi lần xem trang 1.

| Index | Định nghĩa | Phục vụ | Kế hoạch truy vấn (đã kiểm tra) |
|---|---|---|---|
| ~~`notif_recipient_read_idx`~~ | `(recipient_id, read_at, created_at DESC)` | — | **Bỏ** |
| `notif_recipient_created_idx` | `(recipient_id, created_at DESC, id DESC)` | `GET /notifications/` | `Index Scan`, không `Sort` |
| `notif_recipient_unread_idx` | `(recipient_id, created_at DESC, id DESC) WHERE read_at IS NULL` (partial) | `?unread=true`, `unread-count/` | `Index Scan` / `Index Only Scan`, không `Sort` |

Index partial chỉ chứa thông báo chưa đọc nên luôn nhỏ. FK `recipient_id` vẫn `db_index=False` (cả hai index đều bắt đầu bằng `recipient_id`).

Migration: `notifications/0002_notification_list_indexes` — `RemoveIndex` + 2 `AddIndex`, đã áp dụng lên DB local.

## Enum

| Enum | Giá trị thêm | HTTP | Nhãn (thông điệp mặc định) |
|---|---|---|---|
| `ErrorCode` | `INVALID_CREDENTIALS` | 400 | Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản không thể đăng nhập. Vui lòng kiểm tra lại hoặc liên hệ Nhân viên. |
| `ErrorCode` | `PASSWORD_CHANGE_REQUIRED` | 403 | Bạn cần đổi mật khẩu trước khi tiếp tục. |

Cập nhật kèm bảng mã lỗi chung ở [spec 001 api.md](../001-nen-tang/api.md#định-dạng-lỗi).

## Cấu hình

| Setting | Env | Mặc định | Quyết định |
|---|---|---|---|
| `SESSION_COOKIE_AGE` | `DJANGO_SESSION_AGE_SECONDS` | `28800` (8 giờ) | D2 |
| `SESSION_SAVE_EVERY_REQUEST` | — | `False` (hết hạn tuyệt đối) | D2 |
| `SESSION_COOKIE_SAMESITE`, `CSRF_COOKIE_SAMESITE` | — | `"Lax"` | |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | `DJANGO_SECURE_COOKIES` | `False` | Bật khi có HTTPS |
| `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES.login` | `DJANGO_LOGIN_RATE` | `"10/min"` | D3 |
| `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES.password_change` | `DJANGO_PASSWORD_CHANGE_RATE` | `"10/min"` (theo tài khoản) | Thêm ở Phase 2 |
| `AUTH_PASSWORD_VALIDATORS` | — | `MinimumLengthValidator` thay bằng `apps.accounts.validators.MinimumLengthValidator` (cùng luật 8 ký tự, thông điệp tiếng Việt — bản dịch Django `vi` thiếu câu này) | Thêm ở Phase 2 |
| `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES` | — | thêm `PasswordChangeNotRequired` | D5 |
| `VITE_SUPPORT_CONTACT` (frontend) | `VITE_SUPPORT_CONTACT` | rỗng | D7 |
| `NOTIFICATION_POLL_MS` (frontend, `src/config.js`) | `VITE_NOTIFICATION_POLL_MS` | `60000` | D8 — thêm ở Phase 4 |
| `PASSWORD_HASHERS` | — | **Chỉ khi `manage.py test`**: `MD5PasswordHasher` cho nhanh (124 test: 80,6 s → 1,7 s). Chạy thật vẫn PBKDF2 mặc định | |

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 4: env frontend `VITE_NOTIFICATION_POLL_MS`, `VITE_SUPPORT_CONTACT` (đọc tập trung ở `src/config.js`) |
| 21/11/2026 | Phase 3: thay index danh sách thông báo (migration `notifications/0002`); ghi `read_at` qua API |
| 21/11/2026 | Phase 2: ghi `full_name`/`phone`/`address`, `password`, `must_change_password` qua API; thêm throttle `password_change`, validator độ dài mật khẩu tiếng Việt. Không có migration |
| 21/11/2026 | Phase 1: thêm 2 mã lỗi, cấu hình phiên/cookie/throttle (đã áp dụng); bộ băm nhanh khi chạy test |
