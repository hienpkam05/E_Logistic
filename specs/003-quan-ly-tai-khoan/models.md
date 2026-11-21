# Spec 003 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Trường mới | `accounts_user.session_version` | Vô hiệu hóa mọi phiên cũ khi khóa (spec.md mục 3.2) |
| Hành vi model | `User.get_session_auth_hash()` | Băm kèm `session_version` |
| Bảng mới | `accounts_accountevent` | Lịch sử thao tác quản lý tài khoản (D6) |
| Enum mới | `AccountAction` | Loại thao tác trong lịch sử |
| Hằng số mới | `TEMP_PASSWORD_LENGTH`, `TEMP_PASSWORD_ALPHABET` | Mật khẩu tạm |
| Migration | `accounts/0002_…` | Thêm cột + bảng |
| Index | `accounts_user` | `accounts_user_role_idx (role)` → `accounts_user_role_name_idx (role, username)` — migration `accounts/0003` |

## User — trường thêm

| Trường | Kiểu | Null | Mặc định | Ghi chú |
|---|---|---|---|---|
| `session_version` | PositiveIntegerField | | `0` | Tăng 1 mỗi lần khóa. Không bao giờ trả qua API |

`get_session_auth_hash()` **và** `get_session_auth_fallback_hash()` (dùng khi xoay `SECRET_KEY`): `salted_hmac(SESSION_HASH_SALT, f"{password}:{session_version}", algorithm="sha256")`. Đổi công thức → mọi phiên hiện có mất hiệu lực **một lần** sau khi deploy (đã xảy ra trên DB local 21/11/2026).

`User.invalidate_sessions()`: `UPDATE … SET session_version = session_version + 1` (bằng `F()`, đúng cả khi hai request gọi cùng lúc) rồi nạp lại giá trị.

Trường được Nhân viên ghi qua API quản lý: `full_name`, `phone`, `address` (sửa); `is_active`, `session_version` (khóa/mở khóa); `password`, `must_change_password` (tạo, đặt lại). **Không ghi:** `role` sau khi tạo (D2), `username` sau khi tạo, `email`, `is_staff`, `is_superuser`.

## AccountEvent

App `accounts` · Bảng `accounts_accountevent` · **Chỉ thêm** — không có API sửa/xóa; Django admin chỉ đọc.

| Trường | Kiểu | Null | Mặc định | Ghi chú |
|---|---|---|---|---|
| `id` | BigAutoField | | | PK |
| `account` | FK → User | | | Tài khoản bị tác động. `on_delete=PROTECT` (tài khoản có lịch sử không xóa được — BR1). `db_index=False` — index ghép bên dưới đã bắt đầu bằng `account` |
| `actor` | FK → User | ✔ | | Người thực hiện. `on_delete=PROTECT`; `NULL` chỉ cho thao tác hệ thống/lệnh quản trị. Giữ index FK (cho kiểm tra `PROTECT` khi xóa user) |
| `action` | CharField(20) | | | Choices `AccountAction` |
| `changes` | JSONField | | `{}` | `{"phone": {"from": "…", "to": "…"}}` khi sửa; **không bao giờ** chứa mật khẩu |
| `reason` | CharField(255) | | `""` | Lý do khóa (tùy chọn) |
| `created_at` | DateTimeField | | auto_now_add | |

Index (đã kiểm tra sau migrate): `acct_event_account_idx (account_id, created_at DESC, id DESC)` — lịch sử một tài khoản, khớp `ordering`; `accounts_accountevent_actor_id_…`; PK.

## Enum

| Enum | File | Giá trị |
|---|---|---|
| `AccountAction` | `accounts/constants.py` | `CREATED` (Tạo tài khoản), `UPDATED` (Cập nhật hồ sơ), `LOCKED` (Khóa), `UNLOCKED` (Mở khóa), `PASSWORD_RESET` (Đặt lại mật khẩu) |

Đăng ký vào `CHOICE_GROUPS` (`/meta/choices/`) nhóm `account_actions` — test `ChoicesRegistryTests` bắt buộc.

## Hằng số

| Hằng số | File | Giá trị |
|---|---|---|
| `TEMP_PASSWORD_LENGTH` | `accounts/constants.py` | `12` |
| `TEMP_PASSWORD_ALPHABET` | `accounts/constants.py` | chữ hoa/thường + số, bỏ `0 O 1 l I` |

## Migration

| Migration | Nội dung |
|---|---|
| `accounts/0002_session_version_accountevent` | `AddField session_version`; `CreateModel AccountEvent` + index. **Đã áp dụng** lên DB local |
| `accounts/0003_user_role_username_index` | `RemoveIndex accounts_user_role_idx` + `AddIndex accounts_user_role_name_idx (role, username)`. **Đã áp dụng** |

### Index `accounts_user` (Phase 2)

`EXPLAIN` danh sách quản lý (`ORDER BY role, username`) với index `role` đơn: `Incremental Sort` / `Sort` theo `username`. Thay bằng `(role, username)` → `Index Scan` không `Sort` cho cả danh sách đầy đủ và lọc `role`. Tìm kiếm `q` (`UPPER(...) LIKE '%...%'`) không dùng được B-tree — chấp nhận ở quy mô hiện tại; khi cần: extension `pg_trgm` + index GIN (đi cùng `unaccent` nếu làm tìm không dấu — D7).

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 2: index `(role, username)` thay `role` (migration `0003`); API ghi `full_name`/`phone`/`address` + `AccountEvent` `CREATED`/`UPDATED` |
| 21/11/2026 | Phase 1: triển khai đúng như trên; thêm `invalidate_sessions()`, ghi đè hash fallback, bỏ index FK `account` thừa |
