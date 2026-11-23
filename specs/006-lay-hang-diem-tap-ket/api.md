# Spec 006 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md). Ghi cần CSRF; chặn mật khẩu tạm. Hành động của Nhân viên trên đơn: cùng khuôn duyệt/từ chối ([spec 005](../005-duyet-van-don/api.md)) — gửi `updated_at`, `409 CONFLICT`/`INVALID_TRANSITION`, gửi lại khi đã xong → `200` hiện tại.

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | GET | `/api/v1/dispatch/shippers/` | Nhân viên | 06.5 |
| **Mới** | POST | `/api/v1/shipments/{id}/assign-pickup/` | Nhân viên | 06.5 |
| **Mới** | POST | `/api/v1/shipments/{id}/receive-at-hub/` | Nhân viên | 04.10 |
| **Mới** | POST | `/api/v1/shipments/{id}/retry-pickup/` | Nhân viên | 04.13 |
| **Mới** | POST | `/api/v1/shipments/{id}/abandon-pickup/` | Nhân viên | 04.13 A1 |
| **Mới** | GET | `/api/v1/dispatch/tasks/` | Shipper (của mình) | 04.1 |
| **Mới** | GET | `/api/v1/dispatch/tasks/{id}/` | Shipper phụ trách | 04.1 |
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/confirm-pickup/` | Shipper phụ trách | 04.2 |
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/fail-pickup/` | Shipper phụ trách | 04.3 |
| **Sửa** | GET | `/api/v1/shipments/{id}/` | Nhân viên | 05.7 — thêm `holder_shipper`, `tasks` |
| **Sửa** | GET | `/api/v1/shipments/` | Nhân viên | Tab hàng việc dùng `status` sẵn có — không thêm tham số |
| **Sửa** | GET | `/api/v1/meta/choices/` | Công khai | Thêm nhóm `pickup_fail_reasons`, `handover_kinds`; `notification_kinds` có `PICKUP_RETRY` |

Shipper gọi API vận đơn (`/shipments/…`) → vẫn `403` (D2).

## GET /api/v1/dispatch/shippers/

Shipper **đang hoạt động** để chọn khi phân công, sắp theo số nhiệm vụ mở tăng dần rồi tên. Tham số `q` (tên, tên đăng nhập, SĐT). Không phân trang (số Shipper nhỏ; giới hạn trên ghi ở hằng số).

```json
[{ "id": 7, "username": "shipper_long", "full_name": "Nguyễn Văn Long", "phone": "0912345678", "open_task_count": 2 }]
```

## POST /api/v1/shipments/{id}/assign-pickup/

```json
{ "shipper_id": 7, "updated_at": "2026-11-22T08:00:00.123456Z" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Thành công | 200 | `Shipment` (`PICKUP_ASSIGNED`, `tasks[0]` là nhiệm vụ mới) |
| Không phải Chờ lấy hàng | 409 | `INVALID_TRANSITION` (nêu trạng thái hiện tại) |
| Đã có nhiệm vụ lấy đang mở | 409 | `CONFLICT` "Đơn đã được phân công…" |
| Shipper không tồn tại / không phải Shipper / bị khóa | 409 | `CONFLICT` "Shipper không còn hoạt động…" (UC06.5 E1) |
| `updated_at` cũ | 409 | `CONFLICT` |

## POST /api/v1/shipments/{id}/receive-at-hub/

```json
{ "discrepancy_note": "", "updated_at": "…" }
```

`200` → `AT_HUB`, `holder_type: HUB`. Đã `AT_HUB` → `200` hiện tại. Trạng thái khác → `409`.

## POST /api/v1/shipments/{id}/retry-pickup/ · /abandon-pickup/

```json
{ "reason": "Shop hẹn lấy lại chiều mai", "updated_at": "…" }
```

Lý do bắt buộc (1–500). `retry` → `AWAITING_PICKUP`; `abandon` → `PICKUP_ABANDONED`. Chỉ từ `PICKUP_FAILED`.

## GET /api/v1/dispatch/tasks/

Tham số: `type` (mặc định `PICKUP`), `open` (`true` = đang làm, `false` = đã xong), `page`. Mới phân công trước.

```json
{ "count": 1, "next": null, "previous": null, "results": [{
  "id": 31, "type": "PICKUP", "status": "ACTIVE", "assigned_at": "…", "needs_attention": false,
  "shipment": { "id": 12, "tracking_code": "HTT261122K7Q2M", "status": "PICKUP_ASSIGNED",
                "shop_name": "Shop Demo", "sender_phone": "0999000003",
                "pickup_ward": {"code": "DEMO-01", "name": "[Demo] Phường A"}, "pickup_address": "1 Tràng Tiền",
                "package_count": 2 }
}]}
```

## GET /api/v1/dispatch/tasks/{id}/

Như dòng danh sách + `package_description`, `weight_grams`, `note`, `sender_name`, `allowed_actions` (`CONFIRM_PICKUP`, `FAIL_PICKUP` khi `ACTIVE`), `result` (khi đã đóng). **Không có** người nhận, địa chỉ giao, COD (D3). Nhiệm vụ của người khác → `404`.

## POST /api/v1/dispatch/tasks/{id}/confirm-pickup/

Không body. `200` → nhiệm vụ `SUCCEEDED`. Gửi lại khi đã hoàn tất bởi chính mình → `200` hiện tại. Đã thất bại / bị thay → `409 INVALID_TRANSITION`.

## POST /api/v1/dispatch/tasks/{id}/fail-pickup/

```json
{ "reason_code": "SHOP_ABSENT", "note": "" }
```

`reason_code` thuộc `pickup_fail_reasons`; `OTHER` → `note` bắt buộc (`400 fields.note`). `200` → nhiệm vụ `FAILED`.

## Đối tượng `Shipment` (Nhân viên) — thêm

| Trường | Ghi chú |
|---|---|
| `holder_shipper` | `{id, username, full_name, phone}` hoặc null |
| `tasks` | `[{id, type, status, shipper{…}, assigned_by{…}, assigned_at, closed_at, needs_attention, result{outcome, reason_code, note, recorded_at}}]`, mới nhất trước. Shop **không** nhận trường này (quyền tối thiểu) |

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 22/11/2026 | Tạo bản đầu |
| 22/11/2026 | Phase 2: triển khai `dispatch/shippers/` và 4 hành động trên đơn đúng mô tả. Gửi lại: phân công cùng Shipper → 200; nhập điểm tập kết / lấy lại / kết thúc lặp bởi **cùng** Nhân viên → 200, người khác → 409 nêu trạng thái (quy ước spec 001 mục 3.6 điểm 3). Thông điệp chặn: "Vận đơn đang ở trạng thái {nhãn} nên không {thao tác} được.". Lịch sử phân công/nhập kho ghi `changes.shipper`, `changes.holder` (`{id, name}`), `changes.discrepancy_note` |
| 22/11/2026 | Phase 3: triển khai `dispatch/tasks/`, `tasks/{id}/`, `confirm-pickup/`, `fail-pickup/` đúng mô tả. Danh sách: `?open=true|false` (bỏ trống = mọi nhiệm vụ), `?type=` (mặc định PICKUP, sai → 400). `allowed_actions` chỉ có khi nhiệm vụ còn mở. Lấy thất bại: `reason` lịch sử = "{nhãn lý do} — {ghi chú}". Nhiệm vụ đã đóng / không phải lấy hàng → `409 INVALID_TRANSITION` "Nhiệm vụ đã kết thúc hoặc đã chuyển cho người khác…" |
| 22/11/2026 | Phase 5: `/meta/choices/` `limits` thêm `task_note_max_length` (500), `handover_note_max_length` (500) cho ô lý do lấy lại / kết thúc, ghi chú lấy thất bại, ghi chú sai lệch |
