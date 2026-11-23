# Spec 001 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

File này liệt kê **mọi endpoint mới, endpoint bị sửa và thay đổi áp dụng cho toàn bộ API** trong spec 001. Khi code lệch khỏi file này, sửa file này trong cùng thay đổi.

## Tóm tắt

| Loại | Method | URL | Quyền | Ghi chú |
|---|---|---|---|---|
| **Mới** | GET | `/api/v1/meta/choices/` | Công khai | Enum và giới hạn nghiệp vụ cho frontend |
| Giữ nguyên | GET | `/api/v1/health/` | Công khai | Không đổi |
| **Thay đổi chung** | * | `/api/v1/**` | — | Định dạng lỗi thống nhất |
| **Thay đổi chung** | GET | Mọi API danh sách | — | Tham số `page`, `page_size` |
| **Thay đổi chung** | * | `/api/v1/<không tồn tại>` | — | Trả JSON 404 thay cho trang HTML |
| Thay đổi | — | `/admin/` | Superuser/staff | Dùng User tùy biến |

Chưa có API đăng nhập hay API nghiệp vụ trong spec này (spec 002 trở đi).

---

## Quy ước chung (áp dụng từ spec này cho mọi API)

- Tiền tố: `/api/v1/`. JSON UTF-8. Thời gian dạng ISO 8601 có múi giờ (`2026-11-20T09:30:00+07:00`). Tiền là số nguyên VND.
- Xác thực: session cookie của Django. Request ghi (POST/PUT/PATCH/DELETE) phải gửi header `X-CSRFToken` lấy từ cookie `csrftoken`. Khi frontend chạy khác origin (production), khai báo origin trong env `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Django còn so header `Origin` của trình duyệt với `Host` nhận được. Proxy/reverse proxy đứng trước Django phải **giữ nguyên `Host`** (Vite: `changeOrigin: false`; nginx: `proxy_set_header Host $host`), nếu không mọi request ghi bị `403` (lỗi đã gặp 21/11/2026 — spec 002 tasks.md).
- Mặc định mọi endpoint yêu cầu đăng nhập; endpoint công khai ghi rõ trong file api.md của spec.
- Hành động nghiệp vụ là endpoint riêng (vd `POST .../approve/`); không có API nhận trạng thái đích từ client.

### Định dạng lỗi

Mọi lỗi dưới `/api/v1/`:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dữ liệu chưa hợp lệ.",
    "fields": { "phone": ["Số điện thoại đã tồn tại."] }
  }
}
```

| `code` | HTTP | Khi nào |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Dữ liệu đầu vào sai; `fields` chỉ ra trường lỗi |
| `NOT_AUTHENTICATED` | 401 | Chưa đăng nhập, phiên hết hạn hoặc tài khoản bị khóa |
| `PERMISSION_DENIED` | 403 | Đúng phiên nhưng sai vai trò cho hành động |
| `NOT_FOUND` | 404 | Không tồn tại **hoặc** không thuộc quyền xem (không phân biệt hai trường hợp) |
| `INVALID_TRANSITION` | 409 | Trạng thái hiện tại không cho phép hành động |
| `CONFLICT` | 409 | Dữ liệu vừa bị người khác thay đổi; client tải lại |
| `LIMIT_REACHED` | 409 | Vượt giới hạn nghiệp vụ (vd đã đủ 3 lần giao) |
| `REQUEST_ERROR` | giữ mã gốc (405, 406, 415, 429…) | Sai method, định dạng không hỗ trợ, gửi quá nhiều yêu cầu |
| `INVALID_CREDENTIALS` | 400 | *(spec 002)* Đăng nhập sai tên/mật khẩu hoặc tài khoản bị khóa — một thông điệp chung |
| `PASSWORD_CHANGE_REQUIRED` | 403 | *(spec 002)* Tài khoản đang dùng mật khẩu tạm gọi API ngoài danh sách cho phép |
| `SERVER_ERROR` | 500 | Lỗi không lường trước; `message` chung, không lộ chi tiết (traceback chỉ ghi vào log server) |

`fields` là `{}` khi lỗi không gắn với trường cụ thể. JSON gửi lên sai cú pháp → `VALIDATION_ERROR` 400. Trang phân trang không tồn tại (`?page=999`) → `NOT_FOUND` 404.

`message` mặc định là nhãn tiếng Việt của mã lỗi (`ErrorCode` trong `core/errors.py`); service có thể truyền thông điệp cụ thể hơn qua `BusinessError(code, message)`.

Đường dẫn chưa khai báo dưới `/api/` (có dấu `/` cuối) trả JSON `NOT_FOUND`; URL thiếu `/` cuối vẫn được chuyển hướng 301 sang URL có `/`. Frontend còn dùng thêm mã `NETWORK_ERROR` (chỉ phía client, khi không nhận được phản hồi).

### Phân trang

Mọi API danh sách:

| Tham số | Mặc định | Giới hạn |
|---|---|---|
| `page` | 1 | |
| `page_size` | 20 | tối đa 100 |

```json
{ "count": 57, "next": "http://.../?page=2", "previous": null, "results": [ ... ] }
```

### Gửi lại yêu cầu

Nếu một hành động đã được ghi nhận (cùng người, cùng đối tượng, đã ở trạng thái đích), gửi lại trả **200 với dữ liệu hiện tại**, không tạo bản ghi mới. Chi tiết: [spec.md mục 3.6](spec.md#36-quy-ước-giao-dịch-đồng-thời-chống-trùng).

---

## GET /api/v1/meta/choices/

**Mới.** Trả mọi enum và giới hạn nghiệp vụ để frontend hiển thị nhãn, không tự chép danh sách.

- Quyền: công khai (`AllowAny`), không chứa dữ liệu nhạy cảm.
- Tham số: không có.
- Cache: frontend tải một lần mỗi phiên trình duyệt.

Response `200`:

```json
{
  "user_roles": [
    { "value": "SHOP", "label": "Shop" },
    { "value": "ADMIN", "label": "Nhân viên/Admin" },
    { "value": "SHIPPER", "label": "Shipper" }
  ],
  "shipment_statuses": [
    { "value": "PENDING_APPROVAL", "label": "Chờ xác nhận", "terminal": false },
    { "value": "DELIVERED", "label": "Đã giao hàng", "terminal": true }
  ],
  "shipment_actions": [ { "value": "APPROVE_REQUEST", "label": "Duyệt yêu cầu" } ],
  "holder_types": [ { "value": "HUB", "label": "Điểm tập kết" } ],
  "task_types": [ { "value": "PICKUP", "label": "Lấy hàng" } ],
  "task_statuses": [ { "value": "ACTIVE", "label": "Đang thực hiện", "terminal": false } ],
  "task_actions": [ { "value": "TASK_REPLACE", "label": "Thay Shipper" } ],
  "notification_kinds": [ { "value": "REQUEST_APPROVED", "label": "Yêu cầu đã được duyệt" } ],
  "limits": { "max_delivery_attempts": 3, "cod_max_vnd": 50000000 }
}
```

(Ví dụ rút gọn; response thật chứa đủ giá trị của từng enum theo [models.md](models.md#enum). `limits` được các spec sau bổ sung — spec 004 thêm `package_count_min/max`, `weight_grams_max`, `search_query_max_length`, `cancel_reason_max_length`.)

| Nhóm | Nguồn |
|---|---|
| `user_roles` | `UserRole` |
| `shipment_statuses` | `ShipmentStatus` + `TERMINAL_SHIPMENT_STATUSES` |
| `shipment_actions` | `ShipmentAction` |
| `holder_types` | `HolderType` |
| `task_types` | `TaskType` |
| `task_statuses` | `TaskStatus` + `TERMINAL_TASK_STATUSES` |
| `task_actions` | `TaskAction` |
| `notification_kinds` | `NotificationKind` |
| `limits` | `MAX_DELIVERY_ATTEMPTS`, `COD_MAX_VND` |

- Thứ tự phần tử trong mỗi nhóm giữ đúng thứ tự khai báo enum.
- `terminal` chỉ có ở nhóm trạng thái (`shipment_statuses`, `task_statuses`).
- Body là UTF-8, nhãn tiếng Việt không bị escape `\uXXXX`.
- Danh sách nhóm khai báo tại `apps/core/choices.py` (`CHOICE_GROUPS`). Thêm enum mới vào `constants.py` mà quên đăng ký thì test `ChoicesRegistryTests` báo lỗi. `ErrorCode` không trả qua endpoint này (mã lỗi đã có trong mỗi phản hồi lỗi).
- Method khác GET (POST…) → `405 REQUEST_ERROR`. Kết quả giống nhau dù đã đăng nhập hay chưa.

Lỗi: không có lỗi nghiệp vụ; lỗi server theo định dạng chung.

---

## GET /api/v1/health/

**Giữ nguyên.** `200 {"status": "ok", "service": "htt-express-api"}`. Chỉ kiểm tra ứng dụng chạy, không kiểm tra DB.

## /admin/

**Thay đổi:** quản lý `User` tùy biến (có `full_name`, `phone`, `role`, `must_change_password`; không có first/last name) và xem `Notification` ở chế độ chỉ đọc. Đây là công cụ kỹ thuật, không thay thế API quản lý tài khoản của spec 003.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 20/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 6: JSON 404 cho đường dẫn `/api/` không tồn tại trả UTF-8 thật (trước đó escape `\uXXXX`), nhất quán với phản hồi DRF |
| 21/11/2026 | Phase 5: triển khai `GET /api/v1/meta/choices/`; thêm nhóm `task_actions` so với bản thiết kế; ghi rõ thứ tự, `terminal`, UTF-8, cơ chế đăng ký nhóm |
| 21/11/2026 | Phase 2: thêm mã `REQUEST_ERROR` (lỗi 4xx khác); ghi rõ JSON sai cú pháp, trang phân trang không tồn tại, URL thiếu `/`; biến env `DJANGO_CSRF_TRUSTED_ORIGINS` |
