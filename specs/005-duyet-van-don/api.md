# Spec 005 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md). Ghi cần CSRF; chặn mật khẩu tạm (spec 002). Đối tượng `Shipment`: [spec 004 api.md](../004-yeu-cau-gui-hang/api.md).

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Sửa** | GET | `/api/v1/shipments/` | Shop (của mình) · **Nhân viên (toàn hệ thống)** | 05.3, **05.9** |
| **Sửa** | GET | `/api/v1/shipments/{id}/` | Shop sở hữu · **Nhân viên** | 05.4, **05.7** |
| **Sửa** | GET | `/api/v1/shipments/{id}/events/` | Shop sở hữu · **Nhân viên** | 05.4, **05.7** |
| **Mới** | POST | `/api/v1/shipments/{id}/approve/` | Nhân viên | 05.6 |
| **Mới** | POST | `/api/v1/shipments/{id}/reject/` | Nhân viên | 05.8 |
| Không đổi | POST / PATCH | `/api/v1/shipments/`, `{id}/`, `{id}/cancel/` | Chỉ Shop. Nhân viên gọi → `403` | 05.1, 05.2, 05.5 |

Shipper gọi mọi endpoint trên → `403` (spec 006 mở phần của Shipper).

## Đối tượng `Shipment` — thêm trường

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `shop` | `{id, username, full_name, phone}` | Có ở bản rút gọn và chi tiết |
| `holder_type`, `delivery_attempts` | string, int | Chỉ ở chi tiết (UC05.7 bước 4: người giữ hàng, số lần giao). Thêm ở Phase 5 |
| `rejection_reason` | string \| null | Chỉ ở chi tiết; khác null khi `status = REJECTED` (lý do của lần từ chối) |
| `allowed_actions` | string[] | Đã có; nay tính theo **vai trò người xem**. Nhân viên + Chờ xác nhận → `["APPROVE_REQUEST", "REJECT_REQUEST"]` |

## GET /api/v1/shipments/ — tham số mới

| Tham số | Kiểu | Ghi chú |
|---|---|---|
| `created_from` | `YYYY-MM-DD` | Từ 00:00 ngày đó, giờ Việt Nam |
| `created_to` | `YYYY-MM-DD` | Đến hết ngày đó, giờ Việt Nam. `created_from > created_to` → `400 fields.created_to` |
| `ordering` | `created_at` \| `-created_at` | Mặc định `-created_at` (mới nhất trước). Giá trị khác → `400` |
| `q` | string ≤ 100 | Như spec 004. **Với Nhân viên** tìm thêm họ tên, tên đăng nhập, SĐT của Shop |

Ví dụ tab Chờ xác nhận: `GET /api/v1/shipments/?status=PENDING_APPROVAL&ordering=created_at`.

## POST /api/v1/shipments/{id}/approve/

```json
{ "updated_at": "2026-11-21T08:00:00.123456Z" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Duyệt thành công | 200 | `Shipment` (`status: AWAITING_PICKUP`, `tracking_code: "HTT261121K7Q2M"`) |
| Đã được duyệt trước đó (gửi lại / người khác vừa duyệt) | 200 | `Shipment` hiện tại, cùng mã; không ghi thêm lịch sử/thông báo |
| Thiếu `updated_at` | 400 | `VALIDATION_ERROR`, `fields.updated_at` |
| Đã hủy / bị từ chối | 409 | `INVALID_TRANSITION`, "Yêu cầu đang ở trạng thái Đã hủy nên không duyệt được." (tên trạng thái lấy theo nhãn) |
| Shop vừa sửa (`updated_at` cũ) | 409 | `CONFLICT`, "Yêu cầu vừa được Shop thay đổi. Vui lòng tải lại để kiểm tra trước khi xử lý." |
| Không tồn tại | 404 | `NOT_FOUND` |
| Shop / Shipper gọi | 403 | `PERMISSION_DENIED` |

## POST /api/v1/shipments/{id}/reject/

```json
{ "reason": "Địa chỉ giao không rõ số nhà", "updated_at": "2026-11-21T08:00:00.123456Z" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Từ chối thành công | 200 | `Shipment` (`status: REJECTED`, `tracking_code: null`, `rejection_reason`) |
| Đã bị từ chối trước đó | 200 | `Shipment` hiện tại; không ghi thêm |
| Lý do trống / quá 500 ký tự / thiếu `updated_at` | 400 | `VALIDATION_ERROR`, `fields.reason` / `fields.updated_at` |
| Đã duyệt / đã hủy | 409 | `INVALID_TRANSITION` |
| `updated_at` cũ | 409 | `CONFLICT` (như duyệt) |
| Shop / Shipper gọi | 403 | `PERMISSION_DENIED` |

## GET /api/v1/meta/choices/

`limits` thêm `reject_reason_max_length` (500) cho ô lý do từ chối (Phase 5). `shipment_actions` đã có `APPROVE_REQUEST`, `REJECT_REQUEST`; `notification_kinds` đã có `REQUEST_APPROVED`, `REQUEST_REJECTED`.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 22/11/2026 | Phase 2–3: triển khai đúng như mô tả. Thông điệp 409 trạng thái có nhãn thật, vd "Yêu cầu đang ở trạng thái Chờ lấy hàng nên không từ chối được." Duyệt/từ chối lặp trả 200 hiện tại, kể cả khi gửi `updated_at` cũ (kiểm "đã xong" trước phiên bản) |
| 22/11/2026 | Phase 5: chi tiết thêm `holder_type`, `delivery_attempts`; `/meta/choices/` `limits.reject_reason_max_length` |
