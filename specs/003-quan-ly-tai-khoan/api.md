# Spec 003 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md). Mọi endpoint dưới đây: **chỉ `ADMIN`**, chặn mật khẩu tạm (spec 002), ghi cần CSRF.

## Tóm tắt

| Loại | Method | URL | UC |
|---|---|---|---|
| **Mới** | GET | `/api/v1/accounts/users/` | 02.4, 06.1 |
| **Mới** | POST | `/api/v1/accounts/users/` | 02.4 A1, 06.2 |
| **Mới** | GET | `/api/v1/accounts/users/{id}/` | 02.4, 06.3 |
| **Mới** | PATCH | `/api/v1/accounts/users/{id}/` | 02.4, 06.3 |
| **Mới** | POST | `/api/v1/accounts/users/{id}/lock/` | 02.4 A2, 06.4 |
| **Mới** | POST | `/api/v1/accounts/users/{id}/unlock/` | 02.4 A2, 06.4 A1 |
| **Mới** | POST | `/api/v1/accounts/users/{id}/reset-password/` | 01.3 A1 |
| **Mới** | GET | `/api/v1/accounts/users/{id}/events/` | 02.4 (ghi người thực hiện) |
| **Sửa** | GET | `/api/v1/meta/choices/` | thêm nhóm `account_actions` |
| Không có | DELETE | `/api/v1/accounts/users/{id}/` | `405` (BR1) |

Lỗi chung: không phải `ADMIN` → `403 PERMISSION_DENIED`; id không tồn tại → `404`; thao tác lên chính mình (PATCH, lock, unlock, reset-password) → `403 PERMISSION_DENIED`.

---

## Đối tượng `ManagedUser`

```json
{
  "id": 12,
  "username": "shipper_long",
  "full_name": "Nguyễn Văn Long",
  "phone": "0912345678",
  "address": "",
  "role": "SHIPPER",
  "is_active": true,
  "must_change_password": true,
  "last_login": null,
  "date_joined": "2026-11-21T09:00:00+07:00",
  "updated_at": "2026-11-21T09:00:00+07:00"
}
```

Không bao giờ có `password`, hash, `session_version`, `is_staff`, `is_superuser`, quyền/nhóm Django. `updated_at` dùng để chống ghi đè khi sửa.

## GET /api/v1/accounts/users/

| Tham số | Ý nghĩa |
|---|---|
| `role` | `SHOP` / `ADMIN` / `SHIPPER`; giá trị khác → `400 fields.role` |
| `is_active` | `true` / `false`; khác → `400 fields.is_active` |
| `q` | Tìm trong `username`, `full_name`, `phone` (chứa chuỗi, không phân biệt hoa thường, **có phân biệt dấu** — "hoan" không ra "Hoàn", D7). Chỉ khoảng trắng = không lọc |
| `page`, `page_size` | Phân trang chuẩn |

Sắp xếp: `role`, `username`. Response: phân trang chuẩn với `results: ManagedUser[]`.

## POST /api/v1/accounts/users/

```json
{ "username": "shipper_long", "full_name": "Nguyễn Văn Long", "phone": "0912345678", "address": "", "role": "SHIPPER" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 201 | `{ "user": ManagedUser, "temp_password": "Xk7mP2qR9vTs" }` — **mật khẩu tạm chỉ có trong response này** |
| Thiếu/sai trường, `username` hoặc `phone` trùng | 400 | `VALIDATION_ERROR`, `fields` đúng trường; không tạo gì |

`username`: 3–150 ký tự, chỉ chữ không dấu, số, `.`, `_`, `-` (`USERNAME_REGEX`); **không trùng kể cả khác hoa thường** (`Shop_A` trùng `shop_a`). `full_name` bắt buộc; `address` tùy chọn. Trường khác gửi lên (`password`, `is_active`, `is_superuser`…) bị bỏ qua. Tài khoản mới: `is_active=true`, `must_change_password=true`. Ghi `AccountEvent CREATED` (`changes.role`).

Thông điệp trùng: `fields.username` = "Tên đăng nhập đã được sử dụng.", `fields.phone` = "Số điện thoại đã được sử dụng." — kể cả khi hai Nhân viên tạo cùng lúc và DB chặn.

## GET /api/v1/accounts/users/{id}/

`200 ManagedUser`. (Spec 006 sẽ bổ sung `open_task_count` cho Shipper.)

## PATCH /api/v1/accounts/users/{id}/

```json
{ "full_name": "Nguyễn Văn Long", "phone": "0912345679", "address": "Cầu Giấy", "updated_at": "2026-11-21T09:00:00+07:00" }
```

- Nhận `full_name`, `phone`, `address`; **bắt buộc** `updated_at` đã tải (thiếu → `400 fields.updated_at`). Trường khác (`role`, `username`, `is_active`…) bị bỏ qua.
- So `updated_at` sau khi khóa bản ghi, nên hai Nhân viên lưu cùng lúc thì người sau nhận `409`.
- Không có trường nào thực sự đổi → `200`, không ghi lịch sử. Có đổi → `AccountEvent UPDATED` với `changes` trước/sau từng trường.
- Sửa được cả tài khoản đang khóa và tài khoản `ADMIN` khác.

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | `ManagedUser` mới |
| Dữ liệu sai/trùng | 400 | `VALIDATION_ERROR`, `fields` |
| `updated_at` khác bản hiện tại (người khác vừa sửa) | 409 | `CONFLICT` — "Tài khoản vừa được người khác thay đổi. Vui lòng tải lại." |
| Sửa chính mình | 403 | `PERMISSION_DENIED` |

## POST /api/v1/accounts/users/{id}/lock/

```json
{ "reason": "Nghỉ việc từ 22/11" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Khóa thành công | 200 | `ManagedUser` (`is_active: false`); mọi phiên của tài khoản mất hiệu lực |
| Đã khóa sẵn | 200 | `ManagedUser` hiện tại, không ghi lịch sử thêm |
| Admin hoạt động cuối cùng | 409 | `LIMIT_REACHED` — "Không thể khóa Nhân viên/Admin đang hoạt động cuối cùng." |
| Khóa chính mình | 403 | `PERMISSION_DENIED` |

`reason` tùy chọn, tối đa 255 ký tự (quá → `400 fields.reason`), bỏ khoảng trắng hai đầu. Khóa làm đổi `updated_at` — bản sửa hồ sơ đang mở dở sẽ nhận `409` và phải tải lại. Ghi `AccountEvent LOCKED` (kèm `reason`); khóa lặp không ghi thêm và không tăng `session_version`.

## POST /api/v1/accounts/users/{id}/unlock/

Không body. `200 ManagedUser` (`is_active: true`). Đã hoạt động sẵn → `200` hiện tại, không ghi lịch sử. Phiên cũ **không** dùng lại được — người dùng đăng nhập lại.

## POST /api/v1/accounts/users/{id}/reset-password/

```json
{ "identity_verified": true }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | `{ "user": ManagedUser, "temp_password": "…" }` — chỉ có trong response này; `must_change_password: true`; mọi phiên cũ mất hiệu lực |
| `identity_verified` thiếu/false | 400 | `VALIDATION_ERROR`, `fields.identity_verified` — "Cần xác minh danh tính trước khi đặt lại mật khẩu." |
| Đặt lại chính mình | 403 | `PERMISSION_DENIED` |

Đặt lại cho tài khoản đang khóa: được (mật khẩu tạm dùng sau khi mở khóa). Mỗi lần đặt lại sinh mật khẩu tạm mới; mật khẩu tạm trước đó hết hiệu lực. Ghi `AccountEvent PASSWORD_RESET` với `changes = {"identity_verified": true}` — không bao giờ có mật khẩu. Kiểm tra tồn tại trước (id sai → `404` dù thiếu `identity_verified`).

## GET /api/v1/accounts/users/{id}/events/

Phân trang chuẩn, mới nhất trước.

```json
{
  "count": 3, "next": null, "previous": null,
  "results": [
    { "id": 40, "action": "LOCKED", "actor": { "id": 2, "username": "demo_nhanvien", "full_name": "Nhân viên điều phối (demo)" },
      "changes": {}, "reason": "Nghỉ việc từ 22/11", "created_at": "2026-11-21T10:00:00+07:00" },
    { "id": 39, "action": "UPDATED", "actor": { "id": 2, "username": "demo_nhanvien", "full_name": "…" },
      "changes": { "phone": { "from": "0912345678", "to": "0912345679" } }, "reason": "", "created_at": "…" }
  ]
}
```

Nhãn `action` lấy từ `/meta/choices/` nhóm `account_actions`. `actor` là `null` với thao tác hệ thống. Chỉ đọc (`POST` → `405`); tài khoản không tồn tại → `404`. Số truy vấn không tăng theo số dòng (`select_related` người thực hiện).

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 3: triển khai `lock/`, `unlock/`, `reset-password/`, `events/`; ghi rõ khóa đổi `updated_at`, khóa lặp không ghi lịch sử, mật khẩu tạm cũ hết hiệu lực khi đặt lại |
| 21/11/2026 | Phase 2: triển khai `GET/POST users/`, `GET/PATCH users/{id}/`; ghi rõ quy tắc `username` (không trùng khác hoa thường), tìm có phân biệt dấu, thiếu `updated_at` → 400 |
| 21/11/2026 | Phase 1: `/meta/choices/` đã có nhóm `account_actions` (5 giá trị) |
