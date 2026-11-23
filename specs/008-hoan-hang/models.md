# Spec 008 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

Dùng lại bảng của [spec 006](../006-lay-hang-diem-tap-ket/models.md) / [spec 007](../007-giao-hang-cod/models.md). D1, D5, D6, D9 đã chốt 22/11/2026.

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Enum sửa | `HandoverKind` | + `RETURN_INTAKE` "Tiếp nhận hàng hoàn", `SHOP_PICKUP` "Shop nhận hàng hoàn" |
| Cột mới | `dispatch_handover.receiver_name` | CharField(100), null — tên người nhận phía Shop (UC04.11) |
| CHECK mới | `handover_receiver_only_shop_pickup` | `receiver_name` có (khác rỗng) ⇔ `kind = SHOP_PICKUP` |
| Enum sửa | `ShipmentAction` | + `REPORT_RETURN_ISSUE` "Ghi sai lệch hàng hoàn" (D5, E1; `RETURNING → RETURNING`, ADMIN) và `REPORT_RETURN_HANDOVER` "Shipper báo đã đưa hàng hoàn về" (D4; `RETURNING → RETURNING`, SHIPPER) |
| Enum sửa | `NotificationKind` | + `RETURN_HANDOVER_REPORTED` "Shipper đã đưa hàng hoàn về" (D9) |
| Cấu hình mới | `settings.HUB` | `{name, address, phone}` từ `.env` (`HUB_NAME`, `HUB_ADDRESS`, `HUB_PHONE`), có giá trị demo (D6) |
| Migration | `shipments/0005_action_return_reports`, `dispatch/0003_handover_return`, `notifications/0005_kind_return_handover` — **đã áp dụng local 22/11/2026** | Đổi `choices` (SQL rỗng) + cột/CHECK `receiver_name`; CHECK `handover_kind_valid` **tạo lại** (danh sách loại đổi — DB lúc đó 0 dòng bàn giao) |

## Handover (thêm / dùng lại)

| Trường | Ghi chú theo loại |
|---|---|
| `kind` | `HUB_INTAKE` (006), `RETURN_INTAKE`, `SHOP_PICKUP` (008); spec 009 thêm đổi Shipper |
| `task` | `RETURN_INTAKE`: nhiệm vụ hoàn vừa đóng (null nếu tiếp nhận thẳng A1.2); `SHOP_PICKUP`: null |
| `from_shipper` | `RETURN_INTAKE`: Shipper đang giữ; `SHOP_PICKUP`: null |
| `received_by` | **Nhân viên ghi nhận** (mọi loại). Đổi `verbose_name` từ "người nhận" → "nhân viên ghi nhận" (không đổi DB) |
| `receiver_name` | **Mới** — chỉ `SHOP_PICKUP`: người nhận phía Shop (bắt buộc, 1–100 ký tự) |
| `discrepancy_note` | `RETURN_INTAKE`: sai lệch khi nhận; `SHOP_PICKUP`: ghi chú bàn giao |

## Task — không đổi cột

- `type = RETURN`, `attempt_no` null (CHECK spec 007 giữ nguyên).
- `handover_reported_at`: Shipper báo đã đưa hàng về (D4). Nhiệm vụ vẫn `ACTIVE`.
- Đóng khi NV tiếp nhận: `SUCCEEDED` + `TaskResult(SUCCEEDED, recorded_by = Nhân viên)` (spec 001: `TASK_SUCCEED` cho RETURN do ADMIN).

## Dữ liệu ghi theo thao tác

| Thao tác | `Shipment` | `Task` | Bảng khác |
|---|---|---|---|
| Phân công hoàn | `RETURNING` (holder giữ Shipper) | tạo `RETURN/ACTIVE` | Event `ASSIGN_RETURN` · Notification Shipper |
| Shipper báo bàn giao | — (event `RETURNING → RETURNING`) | `handover_reported_at` | Event `REPORT_RETURN_HANDOVER` (task) · Notification NV |
| Ghi sai lệch | — (event `RETURNING → RETURNING`) | — | Event `REPORT_RETURN_ISSUE` (lý do) |
| Tiếp nhận hàng hoàn | `AWAITING_SHOP_PICKUP`, holder `HUB`, `holder_shipper = null` | `SUCCEEDED` (nếu có nhiệm vụ mở) | `TaskResult` · `Handover(RETURN_INTAKE)` · Event `RECEIVE_RETURN` · Notification Shop |
| Shop nhận | `RETURNED_TO_SHOP`, holder `SHOP` | — | `Handover(SHOP_PICKUP)` · Event `CONFIRM_SHOP_RECEIVED` · Notification Shop |

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 22/11/2026 | Tạo bản nháp |
| 22/11/2026 | Phase 1: 3 migration; CHECK `receiver_name` viết `isnull` tường minh (bài học spec 007); `RECEIVER_NAME_MAX_LENGTH = 100`; `settings.HUB` + `.env.example` |
