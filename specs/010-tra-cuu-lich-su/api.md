# Spec 010 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md)

Quy ước chung: [spec 001 api.md](../001-nen-tang/api.md). Backend Phase 1 đã triển khai theo đề xuất D1–D7
và các điểm làm rõ khi người dùng yêu cầu làm tiếp Phase 1; xem spec.md. Frontend Phase 2 đã nối API này, không đổi hợp đồng backend.

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | GET | `/api/v1/shipments/lookup/?code=` | Shop (đơn mình), Nhân viên | 03.1 |
| **Sửa** | GET | `/api/v1/shipments/{id}/events/` | Shop (đơn mình), Nhân viên | 03.2 — mỗi mốc thêm `task`; tham số `ordering` |

## GET /api/v1/shipments/lookup/?code=HTT261123XFCUZ

| Kết quả | HTTP | Body |
|---|---|---|
| Thấy trong phạm vi được xem | 200 | `ShipmentLookupSerializer` kế thừa serializer danh sách: `id`, `request_code`, `tracking_code`, `status`, `shop`, `receiver_name`, `receiver_phone`, `delivery_ward`, `cod_amount`, `created_at`, **`updated_at`** |
| Không có / thuộc Shop khác | 404 | `NOT_FOUND` — **cùng** thông điệp cho cả hai (không lộ) |
| `code` rỗng / quá dài | 400 | `VALIDATION_ERROR`, `fields.code` |
| Shipper | 403 | |

Khớp đúng mã, cắt khoảng trắng đầu/cuối và đổi chữ hoa; không xóa khoảng trắng giữa mã, không tìm gần đúng.
Thiếu `code`, chỉ khoảng trắng hoặc quá `SEARCH_QUERY_MAX_LENGTH` → 400. Chưa đăng nhập → 401, Shipper → 403,
kể cả khi mã rỗng. Chỉ GET/HEAD/OPTIONS; tra cứu không thay đổi bản ghi hoặc lịch sử.

Prefix `YC` chọn `request_code`, còn lại chọn `tracking_code` (mã vận đơn sinh prefix `HTT`).
Scalar subquery tìm pk qua cột unique trước, query ngoài vẫn dùng `shipments_visible_to` để lọc quyền;
cùng `404 NOT_FOUND` và body cho mã không tồn tại/đơn ngoài quyền, không trả thông tin từ tập chưa lọc quyền.
Không sửa serializer/hợp đồng API danh sách hiện có; chỉ lookup thêm `updated_at`.

## GET /api/v1/shipments/{id}/events/ — thêm

```json
{ "id": 9, "action": "FAIL_DELIVERY", "…": "…", "task": { "id": 41, "type": "DELIVERY", "attempt_no": 2, "pickup_no": null } }
```

`task` = `null` với mốc không gắn nhiệm vụ (tạo, duyệt, quyết định…). `ordering` = `-created_at` (mặc định) | `created_at`;
giá trị lạ hoặc rỗng → `400 VALIDATION_ERROR`, `fields.ordering`. Thứ tự phụ cùng chiều `id` để phân trang ổn định
khi các mốc trùng thời gian. Kiểm quyền đơn trước dữ liệu truy vấn: đơn ngoài quyền/không tồn tại trả cùng 404.

- `task.pickup_no`: số đợt nhiệm vụ lấy từ 1, tính trên **toàn bộ** nhiệm vụ PICKUP của đơn theo `(assigned_at,id)`;
  nhiệm vụ lấy bị thay và nhiệm vụ mới là các đợt phân công riêng. Nhiều mốc gắn cùng task có cùng số.
  Không đếm trên một trang kết quả. Giao/hoàn trả `pickup_no: null`.
- `task.attempt_no` vẫn là giá trị DB: lấy/hoàn `null`, giao là lần giao hiện có; nhiệm vụ giao thay thế giữ cùng số.
- Actor Shop nhận `{id, full_name}` hoặc null (hệ thống); không `username`/SĐT nội bộ trong payload actor.
  Nhân viên giữ `{id, username, full_name}` như trước, không SĐT. Không sửa EventActorSerializer dùng chung accounts.
- Query `select_related("actor","task")` + một query lấy thứ tự nhiệm vụ lấy toàn đơn; không N+1 theo số mốc.
- Response phân trang giữ `count`, `next`, `previous`, `results`, thêm **`has_transport_activity`** boolean:
  true nếu toàn đơn có ít nhất một sự kiện ngoài tạo/sửa/hủy/duyệt/từ chối; false nếu chỉ các mốc đó hoặc chưa có.
  Cờ không phụ thuộc trang/thứ tự, để frontend hiển thị đúng "Chưa phát sinh vận chuyển".

Ví dụ đợt lấy thứ 2 và metadata phân trang:

```json
{
  "count": 1, "next": null, "previous": null, "has_transport_activity": true,
  "results": [{
    "id": 10, "action": "ASSIGN_PICKUP", "from_status": "AWAITING_PICKUP", "to_status": "PICKUP_ASSIGNED",
    "actor": {"id": 4, "full_name": "Nhân viên A"}, "reason": "", "changes": {},
    "created_at": "2026-11-23T15:00:00Z",
    "task": {"id": 42, "type": "PICKUP", "attempt_no": null, "pickup_no": 2}
  }]
}
```

Lịch sử chỉ đọc, không đánh lại số trong DB và không ghi đè sự kiện đã lưu.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 23/11/2026 | Tạo bản nháp |
| 23/11/2026 | Phase 1: lookup + updated_at; task/pickup_no, ordering/id, has_transport_activity toàn đơn và actor theo vai trò. Không migration. |
