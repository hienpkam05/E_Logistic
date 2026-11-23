# Spec 007 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md). Khuôn hành động Nhân viên / Shipper giống hệt [spec 006 api.md](../006-lay-hang-diem-tap-ket/api.md): Nhân viên gửi `updated_at`; `409 CONFLICT` / `INVALID_TRANSITION`; gửi lại khi đã xong → `200` trả hiện tại. D2 đã chốt 22/11/2026.

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | POST | `/api/v1/shipments/{id}/assign-delivery/` | Nhân viên | 06.6 |
| **Mới** | POST | `/api/v1/shipments/{id}/decide-redelivery/` | Nhân viên | 04.12 |
| **Mới** | POST | `/api/v1/shipments/{id}/decide-return/` | Nhân viên | 04.12 A1 |
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/confirm-delivery/` | Shipper phụ trách | 04.5, 04.7 |
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/fail-delivery/` | Shipper phụ trách | 04.6 |
| **Sửa** | GET | `/api/v1/dispatch/tasks/` | Shipper | 04.4 — `type` (đã có) đổi mặc định `PICKUP` → tất cả; thẻ giao có người nhận, COD, lần |
| **Sửa** | GET | `/api/v1/dispatch/tasks/{id}/` | Shipper | 04.4 — chi tiết theo loại (D3); ẩn SĐT khi đã đóng (cả nhiệm vụ lấy) |
| **Sửa** | GET | `/api/v1/shipments/{id}/` | Nhân viên / Shop | NV: `tasks[].attempt_no`, `tasks[].result.cod_expected/cod_collected`, `holder_locked`; mọi vai trò: `delivery` (null khi chưa Đã giao); `allowed_actions` lọc thêm theo số lần (D8) |
| **Sửa** | GET | `/api/v1/meta/choices/` | Công khai | Nhóm `delivery_fail_reasons`; `notification_kinds` thêm 2 loại |

## POST /api/v1/shipments/{id}/assign-delivery/

```json
{ "shipper_id": 7, "handed_over": true, "updated_at": "2026-11-22T08:00:00.123456Z" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | Chi tiết đơn (`OUT_FOR_DELIVERY`, `holder_shipper`, `tasks` mới nhất có `attempt_no`) |
| Thiếu / sai `handed_over` | 400 | `VALIDATION_ERROR`, `fields.handed_over` |
| Sai trạng thái (chưa nhập điểm tập kết…) | 409 | `INVALID_TRANSITION` |
| Đã 3 lần | 409 | `LIMIT_REACHED` |
| Giao lại mà hàng ở Shipper khác người được chọn | 409 | `CONFLICT`, nêu tên người đang giữ (D7) |
| Shipper bị khóa / không phải Shipper | 409 | `CONFLICT` — như `assign-pickup` |
| Đơn đã có nhiệm vụ mở | 409 | như `assign-pickup` |
| `updated_at` cũ | 409 | `CONFLICT` |

## POST /api/v1/shipments/{id}/decide-redelivery/ · decide-return/

```json
{ "reason": "Khách hẹn giao sau 17h", "updated_at": "…" }
```

`reason` 1–500 ký tự, bắt buộc. Redelivery khi đã 3 lần → `409 LIMIT_REACHED`. Gửi lại khi đơn đã ở trạng thái đích **do cùng quyết định** → `200` hiện tại.

## POST /api/v1/dispatch/tasks/{id}/confirm-delivery/

```json
{ "cod_collected": 350000 }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công / gửi lại khi đã thành công | 200 | Chi tiết nhiệm vụ (`status: SUCCEEDED`, `result.cod_collected`) |
| Thiếu `cod_collected` | 400 | `fields.cod_collected` (đơn không COD: gửi `0`) |
| Lệch | 400 | `fields.cod_collected`: "Thiếu 20.000 ₫ so với COD phải thu 350.000 ₫." / "Thừa …" |
| Âm, không phải số nguyên, > `cod_max_vnd` | 400 | `fields.cod_collected` |
| Nhiệm vụ đã thất bại / không phải nhiệm vụ giao | 409 | `INVALID_TRANSITION` |
| Không phải của mình | 404 | |

## POST /api/v1/dispatch/tasks/{id}/fail-delivery/

```json
{ "reason_code": "RECEIVER_UNREACHABLE", "note": "" }
```

`reason_code` thuộc `delivery_fail_reasons` (gửi mã lấy hàng → `400`); `OTHER` cần `note`. Trả chi tiết nhiệm vụ. Gửi lại khi đã thất bại → `200` hiện tại, không tăng lần. Đã thành công rồi gửi thất bại (hoặc ngược lại) → `409 INVALID_TRANSITION`.

## GET /api/v1/dispatch/tasks/

`type` = `PICKUP` | `DELIVERY` **đã có từ spec 006** với mặc định `PICKUP`; spec này đổi: bỏ trống = **tất cả** (mã lạ vẫn `400`). Frontend spec 006 không gửi `type` → kiểm lại màn Shipper khi đổi. Mỗi dòng thêm `type`, `attempt_no`; thẻ giao có `shipment.receiver_name`, `delivery_address` rút gọn, `cod_amount`.

## GET /api/v1/dispatch/tasks/{id}/ — nhiệm vụ giao

```json
{
  "id": 21, "type": "DELIVERY", "status": "ACTIVE", "attempt_no": 2,
  "shipment": {
    "tracking_code": "HTT261122K7Q2M", "shop_name": "Shop Hoa",
    "receiver_name": "Trần B", "receiver_phone": "0987654321",
    "delivery_address": "12 Ngõ 5", "delivery_ward": {"code": "W03", "name": "Phường Láng"},
    "package_description": "Áo", "package_count": 1, "weight_grams": 500, "note": "",
    "cod_amount": 350000
  },
  "allowed_actions": ["CONFIRM_DELIVERY", "FAIL_DELIVERY"],
  "result": null
}
```

Nhiệm vụ đã đóng: `receiver_phone` = `null` (nhiệm vụ lấy: `sender_phone` = `null`), `allowed_actions` = `[]`. Không có `max_attempts` trong phản hồi — frontend lấy `limits.max_delivery_attempts` từ `/meta/choices/` (một nguồn).

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 22/11/2026 | Tạo bản nháp |
| 22/11/2026 | Phase 0: chốt; sửa mô tả `type` (đã tồn tại, chỉ đổi mặc định) |
| 22/11/2026 | Phase 3: 2 endpoint Shipper; `GET /dispatch/tasks/` mặc định mọi loại, dòng có `attempt_no`, khối `shipment` theo loại; ẩn SĐT liên hệ khi nhiệm vụ đã đóng (cả nhiệm vụ lấy). Bỏ `max_attempts` khỏi mẫu (dùng `limits`); `delivery_ward` dạng `{code, name}` như `pickup_ward` |
| 22/11/2026 | Phase 2: 3 endpoint Nhân viên + `holder_locked`, `delivery`, `tasks[].attempt_no`, `result.cod_*` — đã làm. Sửa bảng lỗi: Shipper không phải Shipper → `409` (không phải `400`), giống `assign-pickup` |
| 22/11/2026 | Phase 1: `/meta/choices/` có nhóm `delivery_fail_reasons` (6 mục) và `notification_kinds` thêm `OUT_FOR_DELIVERY`, `REDELIVERY_SCHEDULED` — đã làm |
