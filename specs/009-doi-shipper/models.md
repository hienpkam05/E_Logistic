# Spec 009 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

Dùng lại bảng của spec 006–008. D1, D2, D9, D10 đã chốt 23/11/2026.

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Cột mới | `dispatch_task.swap_candidate_id` | FK User, null, PROTECT — người mới dự kiến khi Chờ bàn giao đổi Shipper (A1.2) |
| CHECK mới | `task_swap_candidate_only_pending` | `swap_candidate` có ⇔ `status = PENDING_SWAP_HANDOVER` |
| Enum sửa | `HandoverKind` | + `REASSIGN_INTAKE` "Nhận hàng về để đổi Shipper" |
| Enum sửa | `ShipmentAction` | + `SWAP_SHIPPER`, `CONFIRM_SWAP_HANDOVER`, `REPORT_SWAP_ISSUE`, `REPORT_SWAP_HANDOVER`, `RECALL_TO_HUB` (đều giữ nguyên trạng thái — `KEEP`) |
| Enum sửa | `NotificationKind` | + `SWAP_HANDOVER_REQUIRED`, `SWAP_HANDOVER_REPORTED` |
| Mã chung | `core/transitions.KEEP` | Đích "ở nguyên trạng thái" cho bảng chuyển trạng thái (D2) |
| Migration | `shipments/0006_action_swap_shipper`, `dispatch/0004_task_swap_candidate`, `notifications/0006_kind_swap_handover` — **đã áp dụng local 23/11/2026** | Cột + CHECK + đổi `choices` (SQL rỗng); CHECK `handover_kind_valid` tạo lại (DB 0 dòng bàn giao) |

## Task (thêm)

| Trường | Kiểu | Null | Ghi chú |
|---|---|---|---|
| `swap_candidate` | FK `User`, PROTECT | ✔ | Chỉ khi `PENDING_SWAP_HANDOVER`; xóa khi xác nhận (nhiệm vụ thành `REPLACED`). Index: không (chỉ đọc theo nhiệm vụ) |

Dùng lại: `replaced_by` (nhiệm vụ cũ → mới), `handover_reported_at` (người cũ báo đã đưa về khi chờ bàn giao), `needs_attention` (nhiệm vụ mới luôn `False`), `attempt_no` (nhiệm vụ giao thay thế chép số cũ).

## Dữ liệu ghi theo thao tác

| Thao tác | `Shipment` | `Task` | Bảng khác |
|---|---|---|---|
| Đổi Shipper — lấy (thay ngay) | `updated_at` (Đã phân công lấy giữ nguyên) | cũ `REPLACED` + `closed_at` + `replaced_by`; mới `PICKUP/ACTIVE` | Event `SWAP_SHIPPER` (lý do, cũ → mới) · Notification cũ + mới |
| Đổi Shipper — giao (bắt đầu chờ) | `updated_at` (Đang giao giữ nguyên) | cũ `PENDING_SWAP_HANDOVER` + `swap_candidate` | Event `SWAP_SHIPPER` (lý do, dự kiến) · Notification người cũ |
| Đổi người dự kiến | `updated_at` | `swap_candidate` đổi | Event `SWAP_SHIPPER` (lý do) |
| Người cũ báo đã đưa về | — | `handover_reported_at` | Event `REPORT_SWAP_HANDOVER` · Notification NV |
| Ghi sai lệch | `updated_at` | — | Event `REPORT_SWAP_ISSUE` (lý do) |
| Xác nhận bàn giao | holder `SHIPPER` = người mới | cũ `REPLACED` + `replaced_by`, `swap_candidate = null`; mới `DELIVERY/ACTIVE`, cùng `attempt_no` | `Handover(REASSIGN_INTAKE)` · Event `CONFIRM_SWAP_HANDOVER` · Notification cũ + mới |
| Nhận hàng về điểm tập kết | holder `HUB` | — | `Handover(REASSIGN_INTAKE, task = null)` · Event `RECALL_TO_HUB` |

Không ghi `TaskResult` cho nhiệm vụ bị thay (không phải kết quả cuối); `delivery_attempts` không đổi.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 23/11/2026 | Tạo bản nháp |
| 23/11/2026 | Phase 1: `KEEP` trong `core/transitions.py` (`resolve_transition` trả đích thật; `Transition.target_from`); bộ kiểm bảng hiểu `KEEP`; 5 hành động + 2 loại thông báo + `REASSIGN_INTAKE`; `Task.swap_candidate` + CHECK (`isnull` tường minh). 3 migration áp dụng local |
