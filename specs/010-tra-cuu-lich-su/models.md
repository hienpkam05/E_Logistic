# Spec 010 — Dữ liệu và hằng số

Không thêm/sửa bảng, cột, index, enum hoặc migration. Lookup dùng cột `request_code`, `tracking_code`
đã unique; lịch sử dùng quan hệ `ShipmentEvent.task`, `Task.assigned_at`, `Task.id`, `Task.attempt_no` hiện có.

| Thay đổi | Vị trí | Nguồn | Ý nghĩa |
|---|---|---|---|
| Hằng mới `PRE_TRANSPORT_ACTIONS` | `shipments/constants.py` | UC03.2 A1, D4 | Tập `CREATE_REQUEST`, `UPDATE_REQUEST`, `CANCEL_REQUEST`, `APPROVE_REQUEST`, `REJECT_REQUEST`; chỉ có các mốc này hoặc chưa mốc nào thì `has_transport_activity = false` |
| Dùng lại `SHIPMENT_LIST_ORDERINGS` | `shipments/constants.py` | UC03.2 bước 4, D5 | Ánh xạ ordering → `(created_at,id)` cùng chiều; không định nghĩa trùng bảng sắp xếp |
| `pickup_no` tính khi đọc | `shipments/queries.py` | UC03.2 bước 5, D3 | Số đợt nhiệm vụ lấy toàn đơn từ 1, theo assigned_at/id; không lưu hoặc sửa Task.attempt_no |

`updated_at` trong lookup và metadata/task/actor lịch sử là thay đổi serialization, xem [api.md](api.md).
Đọc API không sửa `Shipment.updated_at`, Task, TaskResult hay ShipmentEvent.

## Nhật ký

| Ngày | Thay đổi |
|---|---|
| 23/11/2026 | Phase 1: thêm PRE_TRANSPORT_ACTIONS, dùng dữ liệu/ordering hiện có; makemigrations check không thay đổi. |
