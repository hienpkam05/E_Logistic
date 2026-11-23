# Spec 006 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

Theo thiết kế tham chiếu [spec 001 mục 6](../001-nen-tang/spec.md#6-thiết-kế-tham-chiếu-cho-spec-sau-chưa-tạo-bảng). Khác biệt so với thiết kế đó ghi ở cột "Ghi chú".

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Bảng mới | `dispatch_task` | Nhiệm vụ của Shipper trên một vận đơn |
| Bảng mới | `dispatch_taskresult` | Kết quả cuối của nhiệm vụ (một-một) |
| Bảng mới | `dispatch_handover` | Bàn giao hàng (spec này: nhập điểm tập kết) |
| Cột mới | `shipments_shipmentevent.task_id` | FK null tới `dispatch_task` |
| Enum mới | `PickupFailReason` (`dispatch/constants.py`) | Lý do lấy thất bại (D4), có ở `/meta/choices/` |
| Enum mới | `HandoverKind` (`dispatch/constants.py`) | `HUB_INTAKE` (spec 008–009 thêm loại) |
| Enum sửa | `NotificationKind` | Thêm `PICKUP_RETRY` "Sẽ lấy hàng lại" (D8) |
| Migration | `dispatch/0001_initial`, `shipments/0003_shipmentevent_task`, `notifications/0003_kind_pickup_retry` | Thứ tự phụ thuộc: `shipments 0002` → `dispatch 0001` → `shipments 0003` (tránh vòng phụ thuộc). `notifications 0003` chỉ đổi `choices` (SQL rỗng) — **thêm giá trị enum luôn cần migration loại này**. Đã áp dụng DB local 22/11/2026 |

## Task

| Trường | Kiểu | Null | Mặc định | Ghi chú |
|---|---|---|---|---|
| `shipment` | FK `Shipment`, PROTECT | | | `related_name="tasks"`; không `db_index` riêng (đã có index ghép) |
| `type` | CharField(20), `TaskType` | | | Spec này chỉ `PICKUP` |
| `status` | CharField(30), `TaskStatus` | | `ACTIVE` | |
| `shipper` | FK `User`, PROTECT | | | CHECK vai trò ở service (DB không tham chiếu cột role được) |
| `assigned_by` | FK `User`, PROTECT | | | Nhân viên phân công |
| `assigned_at` | DateTime | | `now` | |
| `closed_at` | DateTime | ✔ | | Khi sang trạng thái kết thúc |
| `replaced_by` | FK self, SET_NULL | ✔ | | Dùng ở spec 009 |
| `handover_reported_at` | DateTime | ✔ | | Dùng ở spec 008–009 |
| `needs_attention` | Boolean | | `False` | D9: Shipper bị khóa khi nhiệm vụ còn mở |
| `attempt_no` | PositiveSmallInteger | ✔ | | Chỉ DELIVERY (spec 007) |
| `created_at`, `updated_at` | DateTime | | | |

Ràng buộc / index:
- **Partial unique** `task_one_open_per_shipment`: `(shipment)` khi `status IN (ACTIVE, PENDING_SWAP_HANDOVER)` (D1). Giá trị lấy từ `OPEN_TASK_STATUSES`.
- CHECK `type`, `status` thuộc enum; CHECK `closed_at` có giá trị ⇔ trạng thái kết thúc.
- Index `(shipper, -assigned_at, -id)`: danh sách nhiệm vụ của Shipper. Kiểm `EXPLAIN` ở Phase 3.
- Index `(shipment, -assigned_at)`: lịch sử nhiệm vụ ở chi tiết đơn.

## TaskResult

| Trường | Kiểu | Null | Ghi chú |
|---|---|---|---|
| `task` | OneToOne `Task`, PROTECT | | Mỗi nhiệm vụ một kết quả — chặn ghi kết quả 2 lần ở DB |
| `outcome` | CharField(20) | | `SUCCEEDED` / `FAILED` (`TASK_OUTCOMES`, tập con của `TaskStatus`) |
| `reason_code` | CharField(40), `PickupFailReason` | ✔ | Bắt buộc khi FAILED (CHECK) |
| `note` | CharField(500) | | `""`; bắt buộc khi `reason_code = OTHER` (kiểm ở serializer) |
| `recorded_by` | FK `User`, PROTECT | | |
| `recorded_at` | DateTime | | |

Ràng buộc: CHECK `taskresult_reason_matches_outcome` = (FAILED **và** có lý do) **hoặc** (SUCCEEDED **và** không lý do) — tự nó đã giới hạn `outcome` vào 2 giá trị, nên **không** có CHECK riêng cho `outcome` (đột biến Phase 1 chứng minh CHECK riêng đó thừa).

Cột `cod_expected`, `cod_collected` của thiết kế spec 001: **để spec 007** thêm, không tạo cột chưa dùng.

## Handover

| Trường | Kiểu | Null | Ghi chú |
|---|---|---|---|
| `shipment` | FK `Shipment`, PROTECT | | |
| `task` | FK `Task`, PROTECT | ✔ | Nhiệm vụ lấy vừa hoàn tất |
| `kind` | CharField(30), `HandoverKind` | | `HUB_INTAKE` |
| `from_shipper` | FK `User`, PROTECT | ✔ | Người giao (Shipper đang giữ). Thiết kế spec 001 gọi `from_party` — đổi tên cho rõ nghĩa |
| `received_by` | FK `User`, PROTECT | | Nhân viên nhận |
| `received_at` | DateTime | | |
| `discrepancy_note` | CharField(500) | | `""` (E1.2) |

Chỉ thêm, không sửa/xóa (admin chỉ xem).

## Dữ liệu ghi theo thao tác

| Thao tác | `Shipment` | `Task` | Bảng khác |
|---|---|---|---|
| Phân công lấy | `PICKUP_ASSIGNED` | tạo `PICKUP/ACTIVE` | Event `ASSIGN_PICKUP` (task) · Notification Shipper |
| Lấy được | `PICKED_UP`, holder `SHIPPER` + `holder_shipper` | `SUCCEEDED`, `closed_at` | `TaskResult(SUCCEEDED)` · Event `CONFIRM_PICKUP` · Notification Shop |
| Lấy thất bại | `PICKUP_FAILED` (holder vẫn `SHOP`) | `FAILED`, `closed_at` | `TaskResult(FAILED, lý do)` · Event `FAIL_PICKUP` · Notification Shop + NV |
| Nhập điểm tập kết | `AT_HUB`, holder `HUB`, `holder_shipper = null` | — | `Handover(HUB_INTAKE)` · Event `RECEIVE_AT_HUB` |
| Lấy lại | `AWAITING_PICKUP` | — | Event `RETRY_PICKUP` (lý do) · Notification Shop |
| Kết thúc | `PICKUP_ABANDONED` | — | Event `ABANDON_PICKUP` (lý do) · Notification Shop |
| Khóa Shipper | — | `needs_attention = True` (nhiệm vụ mở) | Notification `ACCOUNT_LOCKED_TASKS` cho NV |

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 22/11/2026 | Tạo bản đầu |
| 22/11/2026 | Phase 1: tạo 3 bảng + `ShipmentEvent.task`; 6 CHECK/UNIQUE trên `dispatch`. Bỏ CHECK `outcome` thừa (lùi migration local chưa có dữ liệu rồi sinh lại). Thêm `notifications/0003` (choices) |
