# Spec 008 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md); khuôn hành động như [spec 006](../006-lay-hang-diem-tap-ket/api.md) / [spec 007](../007-giao-hang-cod/api.md): NV gửi `updated_at`; `409 CONFLICT` / `INVALID_TRANSITION`; gửi lại khi đã xong → `200` hiện tại. D2 đã chốt 22/11/2026.

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | POST | `/api/v1/shipments/{id}/assign-return/` | Nhân viên | 06.7 |
| **Mới** | POST | `/api/v1/shipments/{id}/receive-return/` | Nhân viên | 04.9, 06.7 A1.2 |
| **Mới** | POST | `/api/v1/shipments/{id}/report-return-issue/` | Nhân viên | 04.9 E1 |
| **Mới** | POST | `/api/v1/shipments/{id}/confirm-shop-received/` | Nhân viên | 04.11 |
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/report-return-handover/` | Shipper phụ trách | 04.9 bước 1–3 |
| **Sửa** | GET | `/api/v1/dispatch/tasks/`, `/tasks/{id}/` | Shipper | 04.8 — `type=RETURN`; khối `shipment` cho nhiệm vụ hoàn (D8); `handover_reported_at` |
| **Sửa** | GET | `/api/v1/shipments/{id}/` | NV / Shop | `tasks[].handover_reported_at` (NV); `return_result` (mọi vai trò, khi Đã hoàn về Shop); `allowed_actions` lọc theo nơi giữ hàng (D3) |
| **Sửa** | GET | `/api/v1/meta/choices/` | Công khai | Nhóm `hub` `{name, address, phone}`; `handover_kinds` +2, `shipment_actions` +2 (`REPORT_RETURN_ISSUE`, `REPORT_RETURN_HANDOVER`), `notification_kinds` +1 |

## POST …/assign-return/

```json
{ "shipper_id": 7, "updated_at": "…" }
```

Lỗi như `assign-delivery` (spec 007): sai trạng thái `409 INVALID_TRANSITION`; hàng đã ở điểm tập kết → `409 INVALID_TRANSITION` (dùng "Tiếp nhận hàng hoàn"); người khác người đang giữ → `409 CONFLICT`; Shipper khóa → `409 CONFLICT`. Không có `handed_over` (D3).

## POST …/receive-return/

```json
{ "discrepancy_note": "", "updated_at": "…" }
```

Từ Đang hoàn, hoặc Chờ xử lý hoàn khi hàng đã ở điểm tập kết (A1.2). Trả chi tiết đơn (`AWAITING_SHOP_PICKUP`). Gửi lại → `200`.

## POST …/report-return-issue/

```json
{ "reason": "Thiếu 1 kiện so với vận đơn", "updated_at": "…" }
```

`reason` 1–500 bắt buộc. Đơn giữ Đang hoàn; lịch sử có mốc `REPORT_RETURN_ISSUE`.

## POST …/confirm-shop-received/

```json
{ "receiver_name": "Nguyễn Văn Hoa", "verified": true, "note": "", "updated_at": "…" }
```

`receiver_name` 1–100 bắt buộc; `verified` phải `true` (`400` nếu không). Trả chi tiết đơn (`RETURNED_TO_SHOP`, `return_result`).

## POST /api/v1/dispatch/tasks/{id}/report-return-handover/

Không body. Nhiệm vụ RETURN `ACTIVE` của mình. Trả chi tiết nhiệm vụ (`handover_reported_at` có giá trị, `allowed_actions` không còn `REPORT_RETURN_HANDOVER`). Gửi lại → `200`. Nhiệm vụ đã đóng → `409`.

## GET /api/v1/dispatch/tasks/{id}/ — nhiệm vụ hoàn

```json
{
  "id": 61, "type": "RETURN", "status": "ACTIVE", "attempt_no": null, "handover_reported_at": null,
  "shipment": {
    "tracking_code": "HTT…", "shop_name": "Shop Hoa", "package_description": "Áo", "package_count": 1,
    "weight_grams": null, "note": "", "return_reason": "Khách từ chối nhận"
  },
  "allowed_actions": ["REPORT_RETURN_HANDOVER"], "result": null
}
```

Điểm tập kết lấy từ `/meta/choices/` `hub` (một nguồn).

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 22/11/2026 | Tạo bản nháp |
| 23/11/2026 | Phase 5: `/meta/choices/` `limits` thêm `handover_receiver_name_max_length` (100) cho ô tên người nhận ở hộp "Xác nhận Shop đã nhận" |
| 22/11/2026 | Phase 3: `report-return-handover` + khối `shipment` nhiệm vụ hoàn (`return_reason` chỉ ở chi tiết — danh sách không cần, tránh truy vấn mỗi dòng); dòng nhiệm vụ có `handover_reported_at`; `allowed_actions` bỏ hành động một lần đã làm (`TASK_ONE_TIME_ACTIONS`). Báo bàn giao **không** tăng `updated_at` của đơn (D5) |
| 22/11/2026 | Phase 2: 4 endpoint NV; `tasks[].handover_reported_at`, `return_result` — đã làm. `assign-return` / `receive-return` dùng lại serializer của `assign-pickup` / `receive-at-hub` (cùng dữ liệu). `report-return-issue` tăng `updated_at` của đơn; gửi lại đúng ghi chú vừa ghi → `200` không ghi trùng |
| 22/11/2026 | Phase 1: `/meta/choices/` có `hub` (từ `settings.HUB`), mã mới trong `handover_kinds`, `shipment_actions`, `notification_kinds` — đã làm |
