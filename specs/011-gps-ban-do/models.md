# Spec 011 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md).
**Phase 1 đã tạo LocationPing, constants và migration 0001_initial theo phương án đã trình bày;
chưa migrate database đang dùng của người dùng.** Phase 2 đã thêm purge, không đổi schema/migration.

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Bảng mới | `tracking_locationping` | Điểm vị trí của Shipper khi làm nhiệm vụ |
| Hằng số | `tracking/constants.py` | `PING_MAX_AGE_SECONDS = 120`, `PING_MAX_FUTURE_SECONDS = 60`, `PING_MIN_INTERVAL_SECONDS = 15`, `PING_MAX_ACCURACY_M = 1000`, `LOCATION_STALE_SECONDS = 300`, `LOCATION_RETENTION_DAYS = 30`, `LOCATION_POLL_INTERVAL_SECONDS = 15`; biên lat/lng dùng hằng chung cho serializer/CHECK |
| Migration | `tracking/0001_initial` | |

## LocationPing

| Trường | Kiểu | Null | Ghi chú |
|---|---|---|---|
| `id` | BigAutoField | | Khóa chính theo mặc định dự án |
| `task` | FK `dispatch.Task`, CASCADE, `db_index=False` | | Index ghép đã có task ở đầu; CASCADE nếu task bị xóa theo quy trình quản trị, không suy rằng FK của Task chặn xóa chính Task |
| `shipper` | FK `User`, PROTECT, `db_index=False` | | Người gửi — luôn = `task.shipper` lúc gửi (kiểm ở service), lấy từ phiên; không nhận shipper_id từ client |
| `lat` | Decimal(9, 6) | | CHECK −90..90 |
| `lng` | Decimal(9, 6) | | CHECK −180..180 |
| `accuracy_m` | Decimal(7, 3) | ✔ | Đơn vị mét, 0..1.000, nhận được phần lẻ của browser; API gọi là `accuracy` |
| `recorded_at` | DateTime | | Thời điểm thiết bị đo |
| `received_at` | DateTime | | `timezone.now` máy chủ khi lưu sau khóa; client không được gán |

Index `(task, -recorded_at, -id)` — điểm gần nhất theo nhiệm vụ, khóa phụ id ổn định.
Index `received_at` — xóa điểm cũ theo thời gian máy chủ. Không index riêng theo `shipper`
(không có API hành trình theo người — BR2). Chỉ thêm, không sửa; lệnh retention được phép xóa.

CHECK DB: lat trong −90..90, lng trong −180..180; accuracy null hoặc 0..PING_MAX_ACCURACY_M.
Serializer còn phải chặn NaN/Infinity, boolean thay cho số, timestamp thiếu timezone/sai kiểu;
không dựa vào làm tròn Decimal để nhận tọa độ vượt biên.
Tuổi điểm, nhịp gửi, task mở, user active và quan hệ shipper/task kiểm trong service sau khóa;
không đưa `now()` hoặc so sánh bảng khác vào CHECK.

Không đổi schema Task/Shipment/User, không thêm tọa độ địa chỉ Shop/điểm tập kết ở phương án D7 đề xuất.
`tracking/0001_initial` là migration nghiệp vụ đầu tiên của app khung đã có.
`purge_location_pings` mặc định dùng 30 ngày, lọc `received_at < now - days`, không xóa Task/Shipment;
`--days` phải là số nguyên dương, override được ghi rõ khi vận hành. Cần người vận hành lên lịch chạy hằng ngày;
không tuyên bố dữ liệu tự biến mất đúng giây thứ 30 ngày nếu chưa cấu hình lịch chạy.

**Lệnh đã triển khai ở Phase 2:**

```powershell
.\venv\Scripts\python.exe backend/manage.py purge_location_pings
# Override có chủ đích, ví dụ giữ 7 ngày:
.\venv\Scripts\python.exe backend/manage.py purge_location_pings --days 7
```

Lệnh mặc định giữ theo `LOCATION_RETENTION_DAYS`, xóa **received_at < cutoff** (giữ điểm đúng biên),
không dùng recorded_at của thiết bị. Lệnh báo số điểm xóa và số ngày giữ; từ chối days không nguyên dương
hoặc vượt phạm vi datetime. Không tự tạo lịch chạy; không chạy lệnh trên DB đang dùng trong lượt triển khai này.

## Nhật ký thay đổi

Phase 3 **không đổi DB/backend model/enum/migration**. Các hằng frontend mới:

| Nguồn | Hằng / ý nghĩa |
|---|---|
| `src/config.js` | `MAP_TILE_URL`, `MAP_TILE_ATTRIBUTION` từ env, mặc định OSM; `MAP_INITIAL_ZOOM = 15`, `MAP_MAX_ZOOM = 19` là mặc định trình bày map |
| `src/utils/location.js` | `LOCATION_SHARING_STATE`: idle/starting/waiting/sharing/stopped/denied/unavailable/network-error/error/unsupported, chỉ là trạng thái UI cục bộ |
| `src/utils/location.js` | `OPEN_LOCATION_TASK_STATUSES` tham chiếu TASK_STATUS hiện có; `LOCATION_STOP_HTTP_STATUSES` = 401/403/404/409; `GEO_PERMISSION_DENIED` = 1 theo Web API |

`locationLimits()` đọc các khóa metadata Phase 1, không chép ngưỡng 15/120/300/1.000 vào logic frontend.
Không thêm tọa độ địa chỉ hoặc dữ liệu hành trình phía frontend; browser chỉ giữ mẫu đang xử lý trong phiên bật.

Phase 4 không đổi DB/schema/hằng backend. Thêm `MAP_DIRECTIONS_URL` trong config frontend (Google Maps dir),
`LOCATION_SHARING_LABEL` là nhãn tiếng Việt cho trạng thái UI đã có; helper taskDestination/directionsUrl
dùng enum task và địa chỉ đã được phép xem, không tạo tọa độ địa chỉ hay lưu tuyến.

| Ngày | Thay đổi |
|---|---|
| 24/11/2026 | Phase 4: không đổi schema/migration; thêm hằng URL chỉ đường và nhãn trạng thái UI. Địa chỉ hub tiếp tục lấy meta.hub, không thêm địa chỉ/ID hardcode vào view. |
| 24/11/2026 | Phase 3: không thay schema. Ghi hằng cấu hình map và trạng thái UI frontend; Leaflet 1.9.4, provider URL/attribution qua env. Không migrate/purge DB trong phase frontend. |
| 23/11/2026 | Tạo bản nháp |
| 24/11/2026 | Phase 2: không đổi schema. Thêm purge_location_pings theo received_at, default 30 ngày, kiểm --days và biên thời gian; kiểm thử chỉ xóa GPS, không đổi Task/Shipment. EXPLAIN dùng fixture âm/rollback trên PostgreSQL test DB để không cần migrate DB người dùng. |
| 23/11/2026 | Phase 1: tạo LocationPing và migration 0001_initial phụ thuộc dispatch.0004_task_swap_candidate + User; 3 CHECK, 2 index đúng thiết kế. Constants gồm ngưỡng thời gian, nhịp, sai số, retention và biên tọa độ. Chỉ test DB được migrate khi chạy test, không migrate DB dùng chung. |
| 23/11/2026 | Phase 0: xác minh app tracking đã có khung; làm rõ độ chính xác có phần lẻ/null, 2 index, thời gian retention máy chủ, CHECK và giới hạn kiểm ở service. Chưa có migration/code mới; các mức còn là đề xuất. |
