# Spec 002 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung (lỗi, phân trang, CSRF, gửi lại yêu cầu): [spec 001 api.md](../001-nen-tang/api.md).

## Tóm tắt

| Loại | Method | URL | Quyền | Khi phải đổi mật khẩu | UC |
|---|---|---|---|---|---|
| **Mới** | GET | `/api/v1/accounts/auth/csrf/` | Công khai | Cho phép | 01.1 |
| **Mới** | POST | `/api/v1/accounts/auth/login/` | Công khai, cần CSRF, giới hạn 10/phút/IP | Cho phép | 01.1 |
| **Mới** | POST | `/api/v1/accounts/auth/logout/` | Công khai (idempotent) | Cho phép | 01.2 |
| **Mới** | GET | `/api/v1/accounts/me/` | Đã đăng nhập | Cho phép | 02.1, 01.1 A1 |
| **Mới** | PATCH | `/api/v1/accounts/me/` | Đã đăng nhập | **Chặn** | 02.2 |
| **Mới** | POST | `/api/v1/accounts/me/password/` | Đã đăng nhập, giới hạn 10/phút/tài khoản | Cho phép | 02.3, 01.3 |
| **Mới** | GET | `/api/v1/notifications/` | Đã đăng nhập | Chặn | thông báo |
| **Mới** | GET | `/api/v1/notifications/unread-count/` | Đã đăng nhập | Chặn | thông báo |
| **Mới** | POST | `/api/v1/notifications/{id}/read/` | Đã đăng nhập, người nhận | Chặn | thông báo |
| **Mới** | POST | `/api/v1/notifications/read-all/` | Đã đăng nhập | Chặn | thông báo |
| **Sửa chung** | * | Mọi API cần đăng nhập | — | `403 PASSWORD_CHANGE_REQUIRED` nếu chưa đổi mật khẩu tạm | D5 |
| Giữ nguyên | GET | `/api/v1/meta/choices/`, `/api/v1/health/` | Công khai | Cho phép | |

Mã lỗi mới: `INVALID_CREDENTIALS` (400), `PASSWORD_CHANGE_REQUIRED` (403).

---

## Đối tượng `User` (hồ sơ của chính mình)

```json
{
  "id": 7,
  "username": "shop_hoaan",
  "full_name": "Shop Hoa An",
  "phone": "0901234567",
  "address": "",
  "role": "SHOP",
  "must_change_password": false,
  "date_joined": "2026-11-21T09:30:00+07:00"
}
```

Không bao giờ chứa `password`, `is_staff`, `is_superuser`, `is_active`, `last_login`, quyền/nhóm Django. `address` rỗng → frontend hiện "Chưa cập nhật".

## GET /api/v1/accounts/auth/csrf/

Đặt cookie `csrftoken` (không HttpOnly để JS đọc). Response `204`, không body. Gọi trước `login` và trước request ghi đầu tiên nếu chưa có cookie.

## POST /api/v1/accounts/auth/login/

Header `X-CSRFToken` bắt buộc.

```json
{ "username": "shop_hoaan", "password": "..." }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | `User`. Set cookie `sessionid` mới (session key được xoay) |
| Thiếu trường | 400 | `VALIDATION_ERROR`, `fields.username` / `fields.password` |
| Sai tên đăng nhập, sai mật khẩu **hoặc** tài khoản khóa | 400 | `INVALID_CREDENTIALS` — một thông điệp chung |
| Thiếu/sai CSRF | 403 | `PERMISSION_DENIED` |
| Quá 10 lần/phút/IP | 429 | `REQUEST_ERROR`, header `Retry-After` |

Đang có phiên của người khác mà đăng nhập tài khoản mới → phiên cũ bị thay. `must_change_password: true` trong response → frontend chuyển sang đổi mật khẩu.

## POST /api/v1/accounts/auth/logout/

Không body. Luôn `204` — kể cả khi phiên đã hết hạn hoặc chưa đăng nhập (UC01.2 A1). Đang đăng nhập thì phải gửi `X-CSRFToken`, thiếu → `403 PERMISSION_DENIED`. Xóa phiên phía server; cookie `sessionid` cũ không dùng lại được. Không đổi nhiệm vụ của Shipper.

## GET /api/v1/accounts/me/

`200 User`. Chưa đăng nhập/phiên hết/tài khoản khóa → `401 NOT_AUTHENTICATED`. Frontend gọi khi mở app để khôi phục phiên (UC01.1 A1).

## PATCH /api/v1/accounts/me/

Chỉ nhận `full_name`, `phone`, `address` (gửi một phần cũng được). Trường khác (`role`, `is_active`, `username`, `email`…) **bị bỏ qua**, không báo lỗi, không đổi.

```json
{ "phone": "0912345678", "address": "12 Hàng Bạc, Hoàn Kiếm" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | `User` sau khi sửa |
| `full_name` rỗng/chỉ khoảng trắng, `phone` sai định dạng hoặc trùng | 400 | `VALIDATION_ERROR`, `fields` chỉ đúng trường lỗi; không trường nào bị lưu. Trùng → "Số điện thoại đã được sử dụng." (kể cả khi hai người lưu cùng lúc và DB chặn) |
| Đang phải đổi mật khẩu | 403 | `PASSWORD_CHANGE_REQUIRED` |

## POST /api/v1/accounts/me/password/

```json
{ "current_password": "...", "new_password": "...", "new_password_confirm": "..." }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 204 | Phiên hiện tại giữ nguyên; phiên khác của tài khoản hết hiệu lực; `must_change_password` → `false` |
| Sai mật khẩu hiện tại | 400 | `VALIDATION_ERROR`, `fields.current_password` |
| Mật khẩu mới yếu (theo `AUTH_PASSWORD_VALIDATORS`) hoặc trùng mật khẩu hiện tại | 400 | `fields.new_password` |
| Hai lần nhập không khớp | 400 | `fields.new_password_confirm` |
| Quá 10 lần/phút **trên cùng tài khoản** (env `DJANGO_PASSWORD_CHANGE_RATE`) | 429 | `REQUEST_ERROR`, header `Retry-After` — chặn dò mật khẩu hiện tại bằng phiên bị chiếm |

Một request có thể trả nhiều lỗi cùng lúc (vd sai mật khẩu hiện tại **và** mật khẩu mới yếu); `fields.new_password` có thể chứa nhiều thông điệp. Thông điệp đều bằng tiếng Việt.

Mật khẩu không xuất hiện trong response, log hay thông báo.

## GET /api/v1/notifications/

Phân trang chuẩn. Tham số: `unread=true` (chỉ chưa đọc) / `unread=false` (chỉ đã đọc), `page`, `page_size`. Giá trị `unread` khác kiểu đúng/sai → `400 VALIDATION_ERROR` (`fields.unread`). Chỉ thông báo của người đang đăng nhập, mới nhất trước (`created_at`, rồi `id` giảm dần).

```json
{
  "count": 2, "next": null, "previous": null,
  "results": [
    {
      "id": 31, "kind": "REQUEST_APPROVED", "title": "Yêu cầu YC00000012 đã được duyệt",
      "body": "Mã vận đơn HTT261121K7Q2M.", "payload": { "shipment_id": 12 },
      "created_at": "2026-11-21T10:05:00+07:00", "read_at": null, "is_read": false
    }
  ]
}
```

Nhãn `kind` lấy từ `/meta/choices/` nhóm `notification_kinds`.

## GET /api/v1/notifications/unread-count/

`200 { "count": 3 }`.

## POST /api/v1/notifications/{id}/read/

`200` thông báo sau khi đánh dấu. Đã đọc rồi → `200`, giữ nguyên `read_at` cũ (kể cả hai tab bấm cùng lúc). Không phải của mình hoặc không tồn tại → `404 NOT_FOUND`, hai trường hợp trả **giống hệt** nhau.

## POST /api/v1/notifications/read-all/

`200 { "updated": 3 }` — số thông báo vừa chuyển sang đã đọc.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 3: triển khai 4 endpoint thông báo; thêm `unread=false`, lỗi `fields.unread` khi giá trị sai; ghi rõ thứ tự sắp xếp |
| 21/11/2026 | Phase 2: triển khai `PATCH me/`, `POST me/password/`; thêm giới hạn 10/phút/tài khoản cho đổi mật khẩu; thông điệp lỗi tiếng Việt cho số điện thoại trùng và mật khẩu ngắn |
| 21/11/2026 | Phase 1: triển khai `auth/csrf`, `auth/login`, `auth/logout`, `GET me/`. Đăng xuất khi đang đăng nhập **cần CSRF header** (DRF kiểm tra CSRF cho phiên đã đăng nhập); khi chưa đăng nhập thì không cần. Sau đăng nhập Django **xoay CSRF token** — frontend đọc lại cookie `csrftoken` trước request ghi kế tiếp |
