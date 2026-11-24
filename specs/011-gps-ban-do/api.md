# Spec 011 — Thay đổi API

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · Model: [models.md](models.md).
**Phase 1–2: POST nhận GPS, metadata và GET xem vị trí đã triển khai theo phương án trình bày ở Phase 0.
Phase 4 đã nối vào màn Shipper/Shop/NV và chỉ đường ngoài ứng dụng; không đổi endpoint/backend contract.**
Lỗi/session/CSRF theo [quy ước chung](../001-nen-tang/api.md).

## Tóm tắt

| Loại | Method | URL | Quyền | UC |
|---|---|---|---|---|
| **Mới** | POST | `/api/v1/dispatch/tasks/{id}/locations/` | Shipper phụ trách | 03.5 |
| **Mới** | GET | `/api/v1/shipments/{id}/location/` | Shop (đơn mình), Nhân viên | 03.3 |
| **Sửa** | GET | `/api/v1/meta/choices/` | Công khai | `limits` thêm nhịp gửi / ngưỡng cũ để frontend không viết số |

## POST /api/v1/dispatch/tasks/{id}/locations/

```json
{ "lat": 21.028511, "lng": 105.804817, "accuracy": 12, "recorded_at": "2026-11-23T08:00:05Z" }
```

| Kết quả | HTTP | Body |
|---|---|---|
| Lưu | 201 | `{ "stored": true }` |
| Quá dày (< 15 giây sau điểm trước) | 200 | `{ "stored": false }` — không phải lỗi |
| Timestamp trùng/lùi so với điểm đã lưu, nhưng vẫn trong cửa sổ tuổi hợp lệ | 200 | `{ "stored": false }` — không ghi đè/không thêm |
| Tọa độ / độ chính xác sai, quá cũ, ở tương lai | 400 | `VALIDATION_ERROR` + trường |
| Nhiệm vụ không phải của mình | 404 | |
| Nhiệm vụ đã đóng | 409 | `INVALID_TRANSITION` — giao diện dừng chia sẻ |
| Không phải Shipper | 403 | |
| Chưa đăng nhập / tài khoản đã bị khóa | 401 | Theo cơ chế xác thực hiện có |

`lat`, `lng`, `recorded_at` bắt buộc; `accuracy` tùy chọn/null hoặc số hữu hạn 0..1.000 mét, nhận phần lẻ.
Tọa độ hữu hạn trong khoảng lat −90..90, lng −180..180; không nhận boolean làm tọa độ.
`recorded_at` ISO 8601 có timezone, không trước `task.assigned_at`, không cũ hơn 120 giây hoặc tương lai quá 60 giây.
Đúng các biên trên được nhận. Không nhận task/shipper từ body; URL xác định task, phiên xác định shipper.
Body có trường ngoài lat/lng/accuracy/recorded_at trả 400 theo trường, không âm thầm bỏ qua trường ngoài hợp đồng.

Kiểm theo thứ tự phiên/active → vai trò → task của mình → trạng thái → dữ liệu → trùng/nhịp → lưu.
Chỉ `OPEN_TASK_STATUSES` (ACTIVE/PENDING_SWAP_HANDOVER); swap_candidate không có quyền thay người cũ.
`received_at` là giờ máy chủ sau khóa; nhịp so với lần lưu trước, không theo giờ thiết bị và không theo lần request bị bỏ.
Giới hạn nhịp được kiểm trong transaction có khóa; cần test đồng thời và đua với đóng task/khóa user.

## GET /api/v1/shipments/{id}/location/

```json
{ "task": { "id": 41, "type": "DELIVERY" },
  "location": { "lat": 21.028511, "lng": 105.804817, "accuracy": 12,
                "recorded_at": "2026-11-23T08:00:05Z",
                "received_at": "2026-11-23T08:00:06Z", "stale": false } }
```

Không có nhiệm vụ mở → `{ "task": null, "location": null }`. Có nhiệm vụ nhưng chưa có điểm → `location: null`. Không trả tên / SĐT Shipper (D9). Shop xem đơn khác → `404`.

Chỉ Shop/NV; Shipper 403, không phiên/active 401. Ngoài quyền và không tồn tại cùng 404/body.
`task` chỉ có id/type của nhiệm vụ mở hiện tại. Điểm lấy theo `recorded_at DESC, id DESC` của **chính task đó**,
không lấy theo shipper/đơn qua nhiều nhiệm vụ. `stale = now - recorded_at > 300 giây`.
Các giá trị lat/lng/accuracy trả JSON number (accuracy có thể null), serializer cấu hình rõ việc đổi Decimal;
không để frontend phụ thuộc chuỗi Decimal ngầm định.
Đã đóng/thay người thì không trả điểm task cũ, kể cả còn trong thời hạn lưu 30 ngày.
Không có API danh sách hành trình hoặc lọc theo Shipper. Đọc không làm thay đổi task/đơn/sự kiện.

Route name: `shipment-location`. Sau truy vấn kiểm phạm vi đơn, một SQL chọn task mở và điểm gần nhất bằng
correlated subquery + JSON whitelist trong cùng snapshot; không chọn task ở một lần đọc rồi lấy GPS ở lần đọc khác.
Vì mỗi đơn chỉ có tối đa một task mở, không cần gom nhiều Shipper/điểm. Query count cố định khi tăng số điểm.
`received_at`/`recorded_at` là ISO 8601 có timezone (có thể `+00:00` thay cho `Z`); lat/lng/accuracy là số JSON,
accuracy null vẫn giữ null. Không hứa thu hồi response của snapshot đã bắt đầu trước lúc task đóng.

## GET /api/v1/meta/choices/ (sửa, không bỏ khóa cũ)

Đã thêm các khóa `limits` trong Phase 1 (đơn vị giây trừ accuracy mét/retention ngày), lấy từ constants tracking:

```json
{
  "location_ping_max_age_seconds": 120,
  "location_ping_max_future_seconds": 60,
  "location_ping_min_interval_seconds": 15,
  "location_ping_max_accuracy_m": 1000,
  "location_stale_seconds": 300,
  "location_poll_interval_seconds": 15,
  "location_retention_days": 30
}
```

Đây là phần bổ sung bên trong `limits`, không thay toàn bộ response metadata. Frontend dùng metadata cho
nhịp gửi/đọc/kiểm freshness; backend vẫn tự kiểm, không tin giới hạn client gửi lên.

## Nhật ký thay đổi

Phase 3 không đổi endpoint/response/metadata backend. Frontend thêm:

- `trackingService.sendLocation(taskId, point, {signal})` → POST ở trên; point chỉ có lat/lng/accuracy/recorded_at.
- `trackingService.getLocation(shipmentId, {signal})` → GET ở trên; encode id, cùng client session/CSRF/lỗi.
- `taskService.get(id, options = {})` thêm options tương thích, dùng AbortSignal khi kiểm task; API GET task không đổi.
- `useLocationSharing` chỉ coi `stored:true` là có điểm lưu mới, giữ nguyên timestamp thiết bị; 200 stored:false
  không đổi lastRecordedAt. Dừng phiên chia sẻ khi API 401/403/404/409, không phát lại hàng đợi GPS.

Phase 4 vẫn giữ nguyên backend contract. Composable thêm callback `onTask(task)` cho kết quả kiểm task còn hiệu lực,
chỉ gọi khi phiên chia sẻ hiện tại còn đúng; view cập nhật trạng thái/điểm đến/allowed_actions theo task này.
Component map thêm prop trình bày `onlyWhenOpen`, không phát sinh API khác hoặc truy vấn theo Shipper.
Google Maps là link điều hướng do người dùng bấm, không phải API định tuyến từ backend.

| Ngày | Thay đổi |
|---|---|
| 24/11/2026 | Phase 4: UI dùng POST/GET GPS và GET task hiện có qua session/CSRF chung; onTask cập nhật view. Không thêm/sửa API backend; hướng đi Maps chỉ có api=1 + destination địa chỉ. |
| 24/11/2026 | Phase 3: nối client GPS/AbortSignal và GET kiểm nhiệm vụ; không đổi hợp đồng backend. Component map đọc vị trí và metadata, không nhận history/shipper identity. |
| 23/11/2026 | Tạo bản nháp |
| 24/11/2026 | Phase 2: GET shipment-location đã triển khai. Kiểm scope bằng shipments_visible_to, chỉ Shop/NV; task mở + điểm cùng snapshot, chỉ whitelist GPS/thời gian/stale, không danh tính Shipper/hành trình. Không đổi hợp đồng POST/metadata. |
| 23/11/2026 | Phase 1: triển khai task-location-create, POST 201/200; kiểm quyền/trạng thái trước dữ liệu, kiểm thời gian/replay/nhịp dưới khóa transaction; bổ sung 7 khóa limits. Từ chối trường lạ trong body. GET vị trí chưa triển khai. |
| 23/11/2026 | Phase 0 làm rõ lỗi/quyền/thứ tự validate, replay và nhịp theo máy chủ; thời điểm nhận và JSON number trên GET; tên khóa metadata. Không triển khai endpoint ở Phase 0. |
