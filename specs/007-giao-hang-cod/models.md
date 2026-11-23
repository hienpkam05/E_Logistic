# Spec 007 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

Dùng lại bảng của [spec 006](../006-lay-hang-diem-tap-ket/models.md); theo thiết kế [spec 001 mục 6](../001-nen-tang/spec.md#6-thiết-kế-tham-chiếu-cho-spec-sau-chưa-tạo-bảng). D1, D4, D10 đã chốt 22/11/2026.

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Cột mới | `dispatch_taskresult.cod_expected` | VND phải thu, chụp từ `Shipment.cod_amount` lúc ghi kết quả thành công |
| Cột mới | `dispatch_taskresult.cod_collected` | VND thực thu |
| Cột sửa | `dispatch_taskresult.reason_code` | `choices` = `PickupFailReason` ∪ `DeliveryFailReason` (D4) |
| CHECK mới | `taskresult_cod_pair`, `taskresult_cod_only_success_matching` | D1 — xem dưới |
| CHECK mới | `ship_delivery_attempts_max` | `0 ≤ delivery_attempts ≤ MAX_DELIVERY_ATTEMPTS` |
| CHECK thay | `task_attempt_only_delivery` → `task_attempt_matches_type` | Siết thêm: GIAO **bắt buộc** `attempt_no` 1..3; loại khác trống |
| Hằng số chuyển | `MAX_DELIVERY_ATTEMPTS` | `dispatch/constants.py` → `shipments/constants.py` (ràng buộc nằm trên `Shipment`; `shipments` không import `dispatch`). `dispatch.constants` nhập lại — mọi chỗ dùng cũ không đổi |
| Enum mới | `DeliveryFailReason` (`dispatch/constants.py`) | 6 lý do (D4): `RECEIVER_UNREACHABLE`, `RECEIVER_RESCHEDULED`, `RECEIVER_REFUSED`, `COD_NOT_READY`, `ADDRESS_NOT_FOUND`, `OTHER`; nhóm `delivery_fail_reasons` ở `/meta/choices/` |
| Enum sửa | `NotificationKind` | Thêm `OUT_FOR_DELIVERY` "Đơn đang được giao", `REDELIVERY_SCHEDULED` "Sẽ giao lại" (D10) |
| Migration | `shipments/0004_delivery_attempts_max`, `dispatch/0002_delivery_cod`, `notifications/0004_kind_delivery` — **đã áp dụng DB local 22/11/2026** | `notifications 0004` chỉ đổi `choices` (SQL rỗng). Đột biến CHECK phải sửa **file migration** (DB test dựng từ migration) |

## TaskResult (thêm / sửa)

| Trường | Kiểu | Null | Ghi chú |
|---|---|---|---|
| `reason_code` | CharField(40) | ✔ | Nhóm hợp lệ theo `task.type` — kiểm ở serializer/service (DB không tham chiếu bảng `Task` trong CHECK được). Hai enum chỉ được trùng mã khi **cùng nhãn** (hiện chỉ `OTHER` "Khác") — test canh; lý do giao sai địa chỉ dùng `ADDRESS_NOT_FOUND` vì `WRONG_ADDRESS` đã là "Sai địa chỉ lấy" |
| `cod_expected` | PositiveBigInteger | ✔ | Có ⇔ nhiệm vụ GIAO thành công |
| `cod_collected` | PositiveBigInteger | ✔ | Bằng `cod_expected`; đơn không COD → 0 / 0 |

Ràng buộc:
- `taskresult_cod_pair`: `cod_expected IS NULL` ⇔ `cod_collected IS NULL`.
- `taskresult_cod_only_success_matching`: `cod_collected IS NULL` **hoặc** (`outcome = SUCCEEDED` **và** `cod_collected = cod_expected`) — "không thu một phần" chặn ở DB (UC04.7 BR1).
- Giữ `taskresult_reason_matches_outcome` (spec 006).
- "Nhiệm vụ GIAO thành công thì phải có COD" không viết được bằng CHECK (cần `task.type`) → service luôn ghi + test.

`PositiveBigIntegerField` cùng kiểu với `Shipment.cod_amount` → không cần CHECK `≥ 0` riêng (Django sinh sẵn).

## Shipment (thêm ràng buộc)

| Ràng buộc | Điều kiện |
|---|---|
| `ship_delivery_attempts_max` | `delivery_attempts <= MAX_DELIVERY_ATTEMPTS` (cột `PositiveSmallInteger` đã chặn âm) |

Trước khi thêm: kiểm DB local không có dòng vi phạm (hiện 0 đơn).

## Task — không đổi cột, thay một CHECK

CHECK `task_attempt_matches_type` = (`type = DELIVERY` **và** `attempt_no IS NOT NULL` **và** 1 ≤ `attempt_no` ≤ 3) **hoặc** (`type ≠ DELIVERY` **và** `attempt_no IS NULL`).

> **Bài học:** phải có `IS NOT NULL` tường minh. So sánh với NULL ra NULL, mà PostgreSQL chỉ chặn khi CHECK ra FALSE → thiếu vế này thì nhiệm vụ GIAO không có `attempt_no` vẫn lọt (test Phase 1 bắt được ngay lần chạy đầu).

`attempt_no` (spec 006 đã tạo, CHECK chỉ DELIVERY) bắt đầu được ghi:
- Phân công giao: `attempt_no = shipment.delivery_attempts + 1`.
- Ghi kết quả: `shipment.delivery_attempts = task.attempt_no` (gán, **không** `+= 1` → gửi lại không tăng trùng).

Không thêm UNIQUE `(shipment, attempt_no)`: nhiệm vụ thay người ở spec 009 dùng lại cùng `attempt_no` (đổi người không cấp lượt).

## Dữ liệu ghi theo thao tác

| Thao tác | `Shipment` | `Task` | Bảng khác |
|---|---|---|---|
| Phân công giao | `OUT_FOR_DELIVERY`, holder `SHIPPER` + `holder_shipper` | tạo `DELIVERY/ACTIVE`, `attempt_no` | Event `ASSIGN_DELIVERY` (task, shipper, lần) · Notification Shipper + Shop |
| Giao thành công | `DELIVERED`, holder `RECIPIENT`, `holder_shipper = null`, `delivery_attempts = attempt_no` | `SUCCEEDED`, `closed_at` | `TaskResult(SUCCEEDED, cod_expected, cod_collected)` · Event `CONFIRM_DELIVERY` (COD) · Notification Shop |
| Giao thất bại | `DELIVERY_FAILED` (holder giữ `SHIPPER`), `delivery_attempts = attempt_no` | `FAILED`, `closed_at` | `TaskResult(FAILED, lý do)` · Event `FAIL_DELIVERY` (lý do, lần) · Notification Shop + NV |
| Giao lại | `AWAITING_REDELIVERY` | — | Event `DECIDE_REDELIVERY` (lý do) · Notification Shop |
| Hoàn | `AWAITING_RETURN` | — | Event `DECIDE_RETURN` (lý do) · Notification Shop |

## Hằng số mới (`dispatch/constants.py`)

Thông điệp: thiếu/thừa COD (`COD_SHORT_MESSAGE`, `COD_OVER_MESSAGE` có `{amount}`), hàng đang ở Shipper khác (`HOLDER_ONLY_MESSAGE`), chưa xác nhận bàn giao (`HANDOVER_REQUIRED_MESSAGE`), hết lượt giao (`DELIVERY_LIMIT_MESSAGE`); tiêu đề thông báo cho 5 loại ở D10. Không có giới hạn số mới — dùng `RESULT_NOTE_MAX_LENGTH`, `COD_MAX_VND`, `MAX_DELIVERY_ATTEMPTS`.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 22/11/2026 | Tạo bản nháp |
| 22/11/2026 | Phase 0: chốt; đặt mã `DeliveryFailReason` (tránh trùng `WRONG_ADDRESS` của lấy hàng) |
| 22/11/2026 | Phase 1: 2 cột COD + 2 CHECK; CHECK số lần trên `Shipment`; thay CHECK `attempt_no` (siết); chuyển `MAX_DELIVERY_ATTEMPTS` sang `shipments`. 3 migration đã áp dụng local |
