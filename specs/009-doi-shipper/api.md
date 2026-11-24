# Spec 009 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md); khuôn hành động như spec 006–008: NV gửi `updated_at`; `409 CONFLICT` / `INVALID_TRANSITION`; gửi lại khi đã xong → `200` hiện tại. D9 đã chốt 23/11/2026.

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | POST | `/api/v1/shipments/{id}/swap-shipper/` | Nhân viên | 06.8 bước 1–7, A1.1–A1.2 |
| **Mới** | POST | `/api/v1/shipments/{id}/confirm-swap-handover/` | Nhân viên | 06.8 A1.4–A1.5, E1.2–E1.3 |
| **Mới** | POST | `/api/v1/shipments/{id}/report-swap-issue/` | Nhân viên | 06.8 E1.1 |
| **Mới** | POST | `/api/v1/shipments/{id}/recall-to-hub/` | Nhân viên | 06.6 A2, 06.7 A1.1 |
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/report-swap-handover/` | Shipper cũ | 06.8 A1.3 |
| **Mới** | GET | `/api/v1/dispatch/shippers/{id}/open-tasks/` | Nhân viên | 06.4 bước 2 |
| **Sửa** | GET | `/api/v1/shipments/{id}/` | NV | `tasks[].swap_candidate`, `tasks[].replaced_by`; `allowed_actions` thêm mã mới theo nhiệm vụ / nơi giữ hàng |
| **Sửa** | GET | `/api/v1/dispatch/tasks/{id}/` | Shipper | Nhiệm vụ chờ bàn giao: `allowed_actions` chỉ `REPORT_SWAP_HANDOVER` (khi chưa báo) |
| **Sửa** | GET | `/api/v1/meta/choices/` | Công khai | Mã mới trong `shipment_actions`, `handover_kinds`, `notification_kinds` |

## POST …/swap-shipper/

```json
{ "shipper_id": 9, "reason": "Shipper ốm, nghỉ đột xuất", "updated_at": "…" }
```

| Tình huống | Kết quả |
|---|---|
| Nhiệm vụ lấy đang mở | `200` — nhiệm vụ mới cho `shipper_id`, cũ Đã thay thế |
| Nhiệm vụ giao đang mở | `200` — cũ Chờ bàn giao, `swap_candidate = shipper_id` |
| Đang chờ bàn giao | `200` — đổi `swap_candidate` |
| Gửi lại cùng người | `200` hiện tại |
| `shipper_id` = người cũ | `400` `fields.shipper_id` |
| Người mới không hoạt động / không phải Shipper | `409 CONFLICT` |
| Không có nhiệm vụ lấy/giao đang mở (hoàn, đã thất bại, đơn kết thúc) | `409 INVALID_TRANSITION` |
| `reason` trống | `400` `fields.reason` |

## POST …/confirm-swap-handover/

```json
{ "handed_over": true, "discrepancy_note": "", "updated_at": "…" }
```

`handed_over` = Shipper mới đã nhận hàng tại điểm tập kết (bắt buộc `true`). Người dự kiến không còn hoạt động → `409 CONFLICT`, không ghi gì. Gửi lại → `200`.

## POST …/report-swap-issue/ · …/recall-to-hub/

`report-swap-issue`: `{ "reason": "…", "updated_at": "…" }` — chỉ khi đang chờ bàn giao.
`recall-to-hub`: `{ "discrepancy_note": "", "updated_at": "…" }` — Chờ giao lại / Chờ xử lý hoàn, không nhiệm vụ mở, hàng ở Shipper.

## GET /api/v1/dispatch/shippers/{id}/open-tasks/

```json
[{ "id": 41, "type": "DELIVERY", "status": "ACTIVE", "needs_attention": false,
   "shipment": { "id": 12, "tracking_code": "HTT…", "status": "OUT_FOR_DELIVERY" } }]
```

Không phân trang (số nhiệm vụ mở của một người nhỏ — đo `EXPLAIN` ở Phase 3). Không phải Shipper → `404`.

Bao gồm Shipper bị khóa và nhiệm vụ `ACTIVE` / `PENDING_SWAP_HANDOVER`; không trả nhiệm vụ đã đóng.
Chỉ Nhân viên gọi được (`403` cho Shop/Shipper, `401` khi chưa đăng nhập).

## GET /api/v1/shipments/{id}/ — trường nhiệm vụ phía Nhân viên

Mỗi phần tử `tasks` thêm hai trường nullable; các trường hiện có giữ nguyên:

```json
{
  "swap_candidate": { "id": 9, "username": "shipper_b", "full_name": "Shipper B" },
  "replaced_by": null
}
```

Sau khi thay thành công, nhiệm vụ cũ có `swap_candidate: null` và:

```json
{
  "replaced_by": {
    "id": 42,
    "shipper": { "id": 9, "username": "shipper_b", "full_name": "Shipper B" }
  }
}
```

Dùng lại cấu trúc người xử lý `EventActorSerializer`; Shop không nhận trường `tasks`.
Query chi tiết prefetch cả người dự kiến và người của nhiệm vụ thay thế để không N+1.

## Kết quả các thao tác Nhân viên

Bốn POST trả `200` với chi tiết đơn mới như `GET /shipments/{id}/`.
Không có đơn → `404` trước kiểm dữ liệu; sai vai trò → `403`; thiếu phiên → `401`.
Thiếu/sai `updated_at`, lý do rỗng hoặc chưa xác nhận `handed_over` → `400 VALIDATION_ERROR`.
Phiên bản cũ → `409 CONFLICT`; không thỏa điều kiện nhiệm vụ/người giữ → `409 INVALID_TRANSITION`.

Gửi lại yêu cầu đã thực hiện không thêm nhiệm vụ, bàn giao, lịch sử hay thông báo:
- Đổi lấy: người được chọn đang làm nhiệm vụ thay thế của lần đổi gần nhất.
- Đổi giao: người được chọn đã là người dự kiến trong lúc chờ.
- Xác nhận bàn giao / nhận về điểm tập kết: sự kiện gần nhất là đúng thao tác do cùng Nhân viên thực hiện.
- Ghi sai lệch: sự kiện gần nhất cùng thao tác, Nhân viên và lý do.

Nhận hàng về điểm tập kết không gửi thông báo (D10); không thay đổi số lần giao hay trạng thái đơn.
Người dự kiến bị khóa lúc xác nhận → `409`, toàn bộ giao dịch giữ nguyên để Nhân viên chọn lại.

## POST /api/v1/dispatch/tasks/{id}/report-swap-handover/

Đã triển khai Phase 3 — UC06.8 A1.3. Chỉ Shipper cũ đang phụ trách nhiệm vụ giao
`PENDING_SWAP_HANDOVER`, vận đơn `OUT_FOR_DELIVERY`, được báo đã đưa hàng về điểm tập kết.
Không cần body hoặc `updated_at`; phải có session và CSRF như mọi POST.

Trả `200` với chi tiết nhiệm vụ (cùng cấu trúc GET nhiệm vụ):

```json
{
  "id": 41,
  "type": "DELIVERY",
  "status": "PENDING_SWAP_HANDOVER",
  "attempt_no": 2,
  "handover_reported_at": "2026-11-23T15:00:00Z",
  "allowed_actions": []
}
```

Ví dụ trên chỉ trích các trường liên quan; response vẫn có `shipment`, `result`, thời gian phân công/đóng
và `needs_attention` như GET. Trước khi báo, `allowed_actions = ["REPORT_SWAP_HANDOVER"]`.

- Ghi thời điểm báo và một sự kiện `REPORT_SWAP_HANDOVER`; báo mọi Nhân viên đang hoạt động
  bằng `SWAP_HANDOVER_REPORTED`, payload `{"shipment_id": …}`. Không báo Shop/người dự kiến.
- Chưa ghi `Handover`, chưa thay người giữ hay tạo nhiệm vụ mới; số lần giao, COD và trạng thái đơn không đổi.
- Không tăng `Shipment.updated_at`: Nhân viên vẫn xác nhận trên phiên bản đã mở trước khi Shipper báo.
- Gửi lại lần đã báo → `200` hiện tại, kể cả sau khi nhiệm vụ đóng; không thêm lịch sử/thông báo hay đổi thời điểm.
- Không phải nhiệm vụ của mình (kể cả người dự kiến), hoặc không tồn tại → `404 NOT_FOUND`.
- Chưa đăng nhập / tài khoản bị khóa → `401`; Shop/Nhân viên → `403`.
- Báo lần đầu khi sai loại, chưa chờ bàn giao, trạng thái đơn không phù hợp hoặc nhiệm vụ đã đóng →
  `409 INVALID_TRANSITION`. Sau khi đổi người, người cũ không thể ghi kết quả/COD cho nhiệm vụ cũ.

Việc báo bàn giao và thông báo trong cùng transaction; lỗi giữa chừng rollback cả thời điểm và lịch sử.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 23/11/2026 | Tạo bản nháp |
| 23/11/2026 | Phase 1: `allowed_actions` đã lọc theo điều kiện spec 009 (làm sớm từ Phase 2.1 / 3.1 — xem tasks.md): NV thấy `SWAP_SHIPPER` khi có nhiệm vụ lấy/giao mở, `RECALL_TO_HUB` khi hàng ở Shipper mà không nhiệm vụ mở; Shipper đang chờ bàn giao chỉ còn `REPORT_SWAP_HANDOVER` (một lần) |
| 23/11/2026 | Phase 2: triển khai 4 POST phía Nhân viên, GET nhiệm vụ mở theo Shipper, `tasks[].swap_candidate` và `replaced_by`; mô tả cấu trúc trả về và điều kiện gửi lại ở trên. Không thêm/sửa model hoặc migration. |
| 23/11/2026 | Phase 3: thêm POST báo bàn giao đổi Shipper; mô tả gửi lại, quyền, lỗi, transaction và không tăng phiên bản đơn. Dùng chung helper báo bàn giao với hoàn hàng; không thay đổi hợp đồng báo hoàn. |
| 23/11/2026 | Phase 6: kiểm lại tài khoản người báo sau khi lấy khóa user, trước task; khóa tài khoản thắng trước trả `401` đúng hợp đồng, tránh deadlock lúc kiểm FK actor. `TASK_REPLACED` sau xác nhận dùng lý do sự kiện đổi người, không dùng ghi chú nhận hàng. Không thêm trường/endpoint/migration. |
