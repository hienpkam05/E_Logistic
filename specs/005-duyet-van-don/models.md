# Spec 005 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

## Tóm tắt

**Không có bảng/cột mới**; chỉ thêm/sửa index (Phase 2). Spec 004 đã tạo sẵn `tracking_code` (unique, nullable), `ShipmentEvent`. Spec 001 đã có `APPROVE_REQUEST`, `REJECT_REQUEST` trong bảng trạng thái, và `REQUEST_APPROVED`, `REQUEST_REJECTED` trong `NotificationKind`.

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Hằng số | `shipments/constants.py` | Thông điệp `409` duyệt/từ chối, mẫu tiêu đề/nội dung thông báo, số lần thử lại khi trùng mã (`TRACKING_CODE_MAX_ATTEMPTS = 5`) |
| Hàm | `shipments/services.py` | `generate_tracking_code(now)`, `approve_request`, `reject_request` |
| Quyền dữ liệu | `shipments/permissions.py` | `shipments_visible_to`: thêm nhánh ADMIN (toàn hệ thống) |
| Index mới | `shipments_shipment` | `ship_created_idx (-created_at, -id)`: danh sách toàn hệ thống của Nhân viên (trước đó quét toàn bảng + Sort, 64 ms / 30.000 đơn) |
| Index sửa | `shipments_shipment` | `ship_status_created_idx`: `(status, -created_at)` → `(status, -created_at, -id)`, khớp thứ tự sắp xếp nên tab Chờ xác nhận không cần Sort |
| Migration | `shipments/0002_staff_list_indexes` | 2 index trên. Đã áp dụng DB local 22/11/2026. Không đổi dữ liệu |

## Dữ liệu ghi khi duyệt / từ chối

| Thao tác | `Shipment` | `ShipmentEvent` | `Notification` (cho Shop) |
|---|---|---|---|
| Duyệt | `tracking_code` = mã mới, `status` = `AWAITING_PICKUP` (`holder_type` vẫn `SHOP`) | `APPROVE_REQUEST`, `PENDING_APPROVAL → AWAITING_PICKUP`, `actor` = Nhân viên, `changes = {"tracking_code": {"from": null, "to": "HTT…"}}` | `REQUEST_APPROVED`, `payload = {"shipment_id": id}` |
| Từ chối | `status` = `REJECTED` | `REJECT_REQUEST`, `PENDING_APPROVAL → REJECTED`, `actor`, `reason` (bắt buộc) | `REQUEST_REJECTED`, `payload = {"shipment_id": id}` |
| Gửi lại sau khi đã xong | Không đổi | Không ghi | Không gửi |

Cả 3 bảng ghi trong **một transaction**.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 22/11/2026 | Phase 2: `EXPLAIN` 30.000 đơn → migration `0002_staff_list_indexes` (thêm `ship_created_idx`, `ship_status_created_idx` thêm `-id`); sau đó mọi truy vấn danh sách Nhân viên dùng index, không Sort |
