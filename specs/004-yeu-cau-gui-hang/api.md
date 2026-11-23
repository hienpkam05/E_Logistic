# Spec 004 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md). Ghi cần CSRF; chặn mật khẩu tạm (spec 002).

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | GET | `/api/v1/shipments/wards/` | Mọi vai trò đã đăng nhập | 05.1, 05.2 |
| **Mới** | GET | `/api/v1/shipments/` | Shop (đơn của mình) | 05.3 |
| **Mới** | POST | `/api/v1/shipments/` | Shop | 05.2 |
| **Mới** | GET | `/api/v1/shipments/{id}/` | Shop sở hữu | 05.4 |
| **Mới** | PATCH | `/api/v1/shipments/{id}/` | Shop sở hữu, Chờ xác nhận | 05.1 |
| **Mới** | POST | `/api/v1/shipments/{id}/cancel/` | Shop sở hữu, Chờ xác nhận | 05.5 |
| **Mới** | GET | `/api/v1/shipments/{id}/events/` | Shop sở hữu | 05.4 |
| **Sửa** | GET | `/api/v1/meta/choices/` | `shipment_actions` có thêm `UPDATE_REQUEST`; `limits` có thêm `package_count_min` (1), `package_count_max` (99), `weight_grams_max` (100000) cho form; **Phase 6:** `search_query_max_length` (100), `cancel_reason_max_length` (500) cho độ dài ô nhập | |
| Không có | DELETE | `/api/v1/shipments/{id}/` | `405` (UC05.5 BR1) | |

Lỗi chung: Nhân viên/Shipper → `403`; đơn của Shop khác hoặc không tồn tại → `404` giống hệt nhau.

---

## Đối tượng `Ward`

```json
{ "code": "00070", "name": "Phường Hoàn Kiếm" }
```

## GET /api/v1/shipments/wards/

`200 [Ward, …]` — chỉ phường đang dùng, sắp theo tên, không phân trang.

## Đối tượng `Shipment` (chi tiết)

```json
{
  "id": 15,
  "request_code": "YC00000015",
  "tracking_code": null,
  "status": "PENDING_APPROVAL",
  "sender_name": "Shop Hoa An", "sender_phone": "0901234567",
  "pickup_ward": { "code": "00070", "name": "Phường Hoàn Kiếm" }, "pickup_address": "12 Hàng Bạc",
  "receiver_name": "Trần Thị B", "receiver_phone": "0912345678",
  "delivery_ward": { "code": "00160", "name": "Phường Ba Đình" }, "delivery_address": "5 Đội Cấn",
  "package_description": "Áo thun", "package_count": 2, "weight_grams": 800,
  "cod_amount": 350000, "note": "Gọi trước khi giao",
  "created_at": "2026-11-21T10:00:00+07:00", "updated_at": "2026-11-21T10:00:00+07:00",
  "allowed_actions": ["CANCEL_REQUEST", "UPDATE_REQUEST"]
}
```

Không có `shop` (là chính người gọi), `holder_*`, `delivery_attempts` trong phạm vi spec này. `allowed_actions` lấy từ bảng chuyển trạng thái theo vai trò người gọi.

## GET /api/v1/shipments/

| Tham số | Ý nghĩa |
|---|---|
| `status` | Một hoặc nhiều (`?status=PENDING_APPROVAL&status=CANCELLED`); giá trị lạ → `400 fields.status` |
| `q` | Chứa chuỗi trong `request_code`, `tracking_code`, `receiver_name`, `receiver_phone` (không phân biệt hoa thường) |
| `page`, `page_size` | Phân trang chuẩn |

Mới nhất trước. `results` là bản rút gọn:

```json
{ "id": 15, "request_code": "YC00000015", "tracking_code": null, "status": "PENDING_APPROVAL",
  "receiver_name": "Trần Thị B", "receiver_phone": "0912345678",
  "delivery_ward": { "code": "00160", "name": "Phường Ba Đình" }, "cod_amount": 350000,
  "created_at": "2026-11-21T10:00:00+07:00" }
```

## POST /api/v1/shipments/

Body: các trường nội dung của `Shipment` (ward gửi bằng **mã**):

```json
{
  "sender_name": "Shop Hoa An", "sender_phone": "0901234567",
  "pickup_ward": "00070", "pickup_address": "12 Hàng Bạc",
  "receiver_name": "Trần Thị B", "receiver_phone": "0912345678",
  "delivery_ward": "00160", "delivery_address": "5 Đội Cấn",
  "package_description": "Áo thun", "package_count": 2, "weight_grams": 800,
  "cod_amount": 350000, "note": ""
}
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 201 | `Shipment` (Chờ xác nhận, `tracking_code: null`) |
| Thiếu/sai trường | 400 | `VALIDATION_ERROR`, `fields` đúng trường |
| Phường/xã không có trong danh mục hoặc ngừng dùng | 400 | `fields.pickup_ward` / `fields.delivery_ward` = "Địa chỉ phải thuộc Hà Nội (chọn phường/xã trong danh sách)." |

Bắt buộc: mọi trường trừ `weight_grams`, `note`. Trường `shop`, `status`, `request_code`, `tracking_code`, `holder_type`, `delivery_attempts`… gửi lên bị bỏ qua. Chuỗi được bỏ khoảng trắng hai đầu; chỉ khoảng trắng coi như rỗng. `cod_amount`, `package_count` mặc định 0 và 1 nếu không gửi.

## GET /api/v1/shipments/{id}/

`200 Shipment`.

## PATCH /api/v1/shipments/{id}/

Một phần các trường nội dung như POST, **bắt buộc** `updated_at` đã tải.

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | `Shipment` mới; có thay đổi → lịch sử `UPDATE_REQUEST` |
| Dữ liệu sai | 400 | `VALIDATION_ERROR` |
| Không còn Chờ xác nhận (đã duyệt/hủy/từ chối) | 409 | `INVALID_TRANSITION` — "Yêu cầu không còn ở trạng thái Chờ xác nhận nên không sửa được." |
| `updated_at` cũ | 409 | `CONFLICT` — "Yêu cầu vừa được thay đổi. Vui lòng tải lại." |

## POST /api/v1/shipments/{id}/cancel/

```json
{ "reason": "Khách đổi ý" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Hủy thành công | 200 | `Shipment` (`CANCELLED`, `allowed_actions: []`) |
| Đã hủy sẵn | 200 | `Shipment` hiện tại, không ghi lịch sử thêm |
| Đã duyệt / bị từ chối | 409 | `INVALID_TRANSITION` — "Yêu cầu không còn ở trạng thái Chờ xác nhận nên không hủy được." |

`reason` tùy chọn, ≤ 500 ký tự.

## GET /api/v1/shipments/{id}/events/

Phân trang chuẩn, mới nhất trước:

```json
{ "id": 3, "action": "UPDATE_REQUEST", "from_status": "PENDING_APPROVAL", "to_status": "PENDING_APPROVAL",
  "actor": { "id": 5, "username": "demo_shop", "full_name": "Shop Demo Hoàn Kiếm" },
  "reason": "", "changes": { "cod_amount": { "from": 300000, "to": 350000 } },
  "created_at": "2026-11-21T10:05:00+07:00" }
```

Nhãn `action`, `from_status`, `to_status` lấy từ `/meta/choices/`.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 6: `limits` thêm `search_query_max_length`, `cancel_reason_max_length` (frontend trước đây viết thẳng 100 ở ô tìm; ô lý do hủy chưa giới hạn). `q` của `/accounts/` và `/shipments/` cùng dùng `SEARCH_QUERY_MAX_LENGTH` — giá trị không đổi |
| 21/11/2026 | Phase 4: `/meta/choices/` `limits` thêm 3 giới hạn kiện hàng để frontend không chép số |
| 21/11/2026 | Phase 3: triển khai `PATCH {id}/`, `{id}/cancel/`, `{id}/events/`; kiểm trạng thái trước `updated_at`; thiếu `updated_at` → `400 fields.updated_at`; đơn của Shop khác → `404` trước lỗi dữ liệu; lịch sử phường ghi `{code, name}` |
| 21/11/2026 | Phase 2: triển khai `wards/`, `GET/POST shipments/`, `GET shipments/{id}/` đúng như mô tả; `allowed_actions` sắp theo chữ cái; Nhân viên/Shipper hiện `403` ở các endpoint vận đơn (Nhân viên mở ở spec 005) |
