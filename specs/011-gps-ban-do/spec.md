# Spec 011 — GPS và bản đồ ("Nên có")

Trạng thái: **Phase 1–4 đã triển khai/kiểm thử, gồm flow GPS thật qua API/PostgreSQL. Còn nghiệm thu Phase 5 và người dùng tự thử.** Ngày lập: 23/11/2026.

Phase 4 hoàn tất 24/11/2026: 384 Vitest, build app, Chrome app/API thật với GPS/tile giả lập,
10 ảnh 1440/390, 0 Vue warning/page error. [Bằng chứng](artifacts/phase4/README.md) · [Thử tay](manual-test.md).

Phase 2 hoàn tất 24/11/2026: 585 test backend xuôi/ngược, 6/6 đột biến, EXPLAIN dùng index hiện có.
Bằng chứng: [artifacts/phase2/README.md](artifacts/phase2/README.md).

Phase 3 hoàn tất 24/11/2026: 373 Vitest, build app/fixture, Chrome kiểm Leaflet/geolocation với API/tile fixture.
Audit production 0, dev còn 7 mục cũ. Bằng chứng: [artifacts/phase3/README.md](artifacts/phase3/README.md).

Sau câu hỏi Phase 0, người dùng yêu cầu “làm phase 1 spec 11”. Tiến hành phần lưu/gửi theo D1–D3 và
các chi tiết đã trình bày, không ghi rằng đã nhận xác nhận riêng cả D1–D10. Khi người dùng yêu cầu làm Phase 4,
thực hiện D7 theo phương án đã đề xuất: mở Google Maps ngoài ứng dụng bằng địa chỉ văn bản.
Đã thông báo cơ sở này trước triển khai; không ghi giả là có lựa chọn riêng đầy đủ D1–D10.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md)

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC03.3, UC03.4, UC03.5; UC04.5 bước 7 ("dừng chia sẻ vị trí của nhiệm vụ"), UC06.8 A1.3 (người cũ chia sẻ vị trí phục vụ bàn giao).
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): UC03.3–03.5, kịch bản "GPS" (mất quyền vị trí vẫn có địa chỉ; kết thúc nhiệm vụ thì dừng; Shop không theo dõi ngoài nhiệm vụ liên quan).
- Nền: nhiệm vụ lấy / giao / hoàn (spec 006–008), đổi Shipper (spec 009 — nhiệm vụ chờ bàn giao vẫn mở), `HubCard` / `meta.hub` (spec 008), giao diện Shipper cho điện thoại.

## 1. Mục tiêu và phạm vi

Shipper chia sẻ vị trí **chỉ trong lúc làm nhiệm vụ**; Shop / Nhân viên xem **vị trí gần nhất** của nhiệm vụ đang chạy; Shipper có bản đồ / chỉ đường tới điểm đến. Đây là nhóm **"Nên có"** — đặt sau cùng, phụ thuộc 006–009.

| UC | Phần làm |
|---|---|
| UC03.5 | Xin quyền vị trí (có giải thích); gửi định kỳ khi nhiệm vụ còn mở; backend kiểm phiên + đúng Shipper + nhiệm vụ còn hiệu lực; dừng khi nhiệm vụ đóng / rời trang / đăng xuất; A1 từ chối quyền; E1 mất tín hiệu — không gửi tọa độ cũ như mới; BR1 không gửi thay người khác; BR3 người cũ khi chờ bàn giao đổi Shipper. |
| UC03.3 | Shop (đơn mình) / NV xem **điểm gần nhất** + thời điểm + trạng thái "đang cập nhật / đã cũ / chưa có"; tự làm mới khi màn hình mở; E1 nhiệm vụ kết thúc → dừng, không trả tọa độ. BR2 không trả cả hành trình. |
| UC03.4 | Shipper xem điểm đến theo loại nhiệm vụ (lấy: địa chỉ lấy; giao: địa chỉ giao; hoàn: điểm tập kết) + mở chỉ đường; A1 không cấp quyền vẫn có địa chỉ, **không vẽ tuyến giả**; E1 dịch vụ bản đồ lỗi vẫn giữ địa chỉ. |

**Ngoài phạm vi:** theo dõi nền khi tắt màn hình / ứng dụng di động gốc (chỉ web — trình duyệt chỉ lấy vị trí khi trang đang mở); tối ưu tuyến nhiều điểm; tính phí theo quãng đường.

## 2. Quyết định cần chốt

Kiểm tra trước khi chốt:
- Trình duyệt chỉ cho Geolocation ở **HTTPS hoặc `localhost`** → thử trên điện thoại qua `http://<IP máy>` sẽ **không** lấy được vị trí; demo trên máy tính dùng `localhost` + giả lập vị trí của DevTools, hoặc cần HTTPS.
- Dự án chưa có dịch vụ bản đồ / khóa API nào; địa chỉ đơn là văn bản (chưa có tọa độ).

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **Lưu vị trí** | Bảng mới `LocationPing(task, shipper, lat, lng, accuracy_m, recorded_at (thiết bị), received_at (máy chủ))`. Chỉ thêm. Index `(task, -recorded_at, -id)` và `received_at` để dọn. Đề xuất **giữ 30 ngày tính từ received_at** rồi xóa bằng lệnh `purge_location_pings`; cần lịch chạy ngoài ứng dụng, bản thân lệnh không tự chạy định kỳ. |
| D2 | **Khi nào được gửi** (UC03.5 BR1–BR3) | Chỉ Shipper **phụ trách** nhiệm vụ đang mở: `ACTIVE`, hoặc `PENDING_SWAP_HANDOVER` (người cũ đi bàn giao — BR3). Nhiệm vụ đóng / của người khác → `409` / `404`. Vai trò khác → `403`. |
| D3 | **Chống dữ liệu sai** (E1.2) | Từ chối điểm có `recorded_at` **cũ hơn 2 phút** hoặc **ở tương lai quá 1 phút** so với máy chủ; trước `assigned_at`; tọa độ ngoài khoảng hợp lệ/không hữu hạn; `accuracy` âm hoặc > 1.000 m → 400. `accuracy` có thể null nếu không biết. Giới hạn **1 điểm / 15 giây / nhiệm vụ theo received_at máy chủ** (điểm dày hơn → `200` không lưu). Điểm trùng/cũ hơn điểm đã lưu cũng không lưu; không ghi đè. Ngưỡng là hằng số backend. |
| D4 | **Cách gửi trên trình duyệt** | Trang chi tiết nhiệm vụ mở + nhiệm vụ còn mở → nút **"Bật chia sẻ vị trí"** (giải thích trước khi trình duyệt hỏi quyền — bước 2); bật thì `watchPosition`, gửi theo nhịp D3; dừng khi rời trang, đóng nhiệm vụ, tắt nút, đăng xuất (bước 7). Trạng thái hiển thị: Đang chia sẻ · Chưa cấp quyền (A1) · Mất tín hiệu / mất mạng (E1). **Không tự bật** khi chưa bấm. |
| D5 | **Xem vị trí** (UC03.3) | `GET /shipments/{id}/location/` → điểm **gần nhất** của nhiệm vụ đang mở (`recorded_at`, `received_at`, `accuracy`, `stale` nếu thời điểm đo cũ hơn 5 phút) hoặc `null`; nhiệm vụ đóng → `task: null, location: null`, UI giải thích đã hết nhiệm vụ theo dõi (E1). Shop chỉ đơn mình; NV mọi đơn. Giao diện tự gọi lại **mỗi 15 giây** khi khối bản đồ đang hiện; dừng khi nhiệm vụ kết thúc. Không có API lịch sử hành trình (BR2). |
| D6 | **Bản đồ** | **Leaflet** + nền **OpenStreetMap** (không cần khóa API). Có ghi nguồn bản đồ theo yêu cầu của OSM. Lưu ý: nền bản đồ tải từ máy chủ OSM — dùng thật nhiều người cần nhà cung cấp nền riêng (cấu hình URL nền qua biến môi trường frontend). |
| D7 | **Chỉ đường** (UC03.4) | **Triển khai Phase 4 theo phương án đã trình bày và yêu cầu tiếp tục của người dùng:** nút "Chỉ đường" mở Google Maps ngoài ứng dụng bằng địa chỉ văn bản, không tích hợp dịch vụ định tuyến/geocoding. Đây là điều chỉnh so với bước 5–6 UC03.4 mô tả tuyến nhúng; không tuyên bố đã có tuyến trong hệ thống. URL `https://www.google.com/maps/dir/?api=1&destination=…`, encode địa chỉ, không truyền tên/SĐT/COD/mã đơn/vị trí hiện tại. Link mở tab mới, giữ địa chỉ ở tab gốc; không cần quyền GPS để tạo link. Không có câu trả lời chọn riêng D7, cơ sở tiến hành là yêu cầu làm Phase 4 sau đề xuất. |
| D8 | **Dừng khi nhiệm vụ đóng** (UC04.5 bước 7) | Không cần thao tác riêng: backend từ chối điểm của nhiệm vụ đã đóng (D2); giao diện tự dừng khi nhận trạng thái đóng / `409`. |
| D9 | **Quyền riêng tư** | Shop chỉ thấy vị trí khi đơn mình đang có nhiệm vụ mở; không thấy tên tài khoản / SĐT Shipper ở khối vị trí; Shipper thấy rõ khi nào đang chia sẻ. Ghi chú trong README: vị trí lưu 30 ngày. |
| D10 | **Thử / demo** | Ảnh chụp và bấm thật dùng **giả lập vị trí** của trình duyệt (Playwright `geolocation`) trên `localhost`; ghi rõ trong `manual-test.md` cách bật giả lập vị trí của Chrome DevTools và hạn chế HTTPS trên điện thoại. |

## 3. Backend

### Kết quả rà soát Phase 0

- `apps.tracking` đã có trong `INSTALLED_APPS`, có model/service/serializer/permission/URL khung và migrations rỗng.
  **Mở rộng app hiện có**, không tạo app thứ hai. Logic GPS thuộc tracking, đăng ký view tại URL dispatch/shipments hiện có;
  không thêm endpoint tương đương dưới `/tracking/`.
- `task_one_open_per_shipment` đã đảm bảo mỗi đơn tối đa một nhiệm vụ mở. Dùng lại `OPEN_TASK_STATUSES`,
  `tasks_visible_to`, `shipments_visible_to`, session/CSRF, lỗi chung, metadata và HubCard.
- `Task.shipper` là người được gửi; `swap_candidate` không được gửi cho nhiệm vụ người cũ. Sau thay người,
  nhiệm vụ mới chưa có GPS; **không lấy điểm nhiệm vụ cũ làm vị trí người mới**.
- GPS không đổi trạng thái Task/Shipment, không ghi ShipmentEvent/thông báo cho từng điểm và không dùng làm bằng chứng giao nhận/COD.
- Thứ tự khóa khi POST: đơn → user Shipper → task, cùng nguyên tắc `_lock_own_task(..., lock_actor=True)`;
  kiểm lại active, người phụ trách, trạng thái sau khóa rồi mới validate/lưu/throttle. Hai request đồng thời không cùng vượt nhịp;
  chốt nhiệm vụ/khóa tài khoản không được để GPS tiếp tục sau đó. Không gọi helper chuyển kết quả vốn chặn nhiệm vụ chờ bàn giao.
- GET đọc trạng thái nhiệm vụ và điểm trong cùng truy vấn/snapshot (hoặc khóa phù hợp), tránh chọn nhiệm vụ mở rồi trả điểm
  theo một lần đọc trạng thái cũ. Mọi lần gọi lại phải kiểm quyền từ đầu. Không hứa thu hồi response đã gửi trước khi task đóng.

### Các biên cần thống nhất trước triển khai

Các chi tiết dưới đây là hướng thiết kế đề xuất của Phase 0, chưa được ghi là lựa chọn người dùng đã xác nhận:

1. Thời gian có múi giờ; biên đúng 120 giây cũ/60 giây tương lai/15 giây nhịp vẫn được nhận;
   `stale` chỉ true khi **lớn hơn** 300 giây. GPS timestamp thật lấy từ `position.timestamp`, không gán lại giờ gửi.
2. Sau kiểm quyền/trạng thái, validate dữ liệu trước khi xét bỏ vì quá dày. Trong cửa sổ tuổi hợp lệ,
   timestamp trùng/lùi trả `200 stored:false`; timestamp mới nhưng chưa đủ nhịp cũng vậy. Điểm ngoài cửa sổ tuổi trả 400.
3. Shipper chỉ gửi khi chủ động bật. Dừng watch/timer khi tắt, rời trang, đổi task, đăng xuất, thu hồi quyền,
   hoặc API trả 401/403/404/409; phản hồi cũ không bật lại phiên đã dừng. Không gom hàng đợi GPS offline, không gửi lại điểm cũ như mới.
4. Khi chia sẻ, kiểm trạng thái task theo nhịp 15 giây kể cả thiết bị đứng yên không có callback GPS;
   nếu phiên/tab không được trình duyệt chạy thì không cam kết cập nhật liên tục. Không tự bật sau tải lại trang.
5. Shop/NV ngừng polling và bỏ tọa độ cũ khi task null hoặc mất quyền; đổi task phải xóa marker cũ.
   Lỗi mạng báo không cập nhật được, hiển thị tuổi điểm từ timestamp, không tiếp tục ghi “đang cập nhật” cho dữ liệu cũ.
6. Điểm đến lấy là địa chỉ Shop; giao là địa chỉ người nhận; hoàn và **chờ bàn giao đổi người** là `meta.hub.address`.
   Khi chỉ có địa chỉ chữ thì không đặt marker đích/tuyến giả. Không gửi địa chỉ tới bên ngoài trước khi bấm Chỉ đường.
7. Leaflet chỉ hiển thị điểm GPS; tile URL và attribution đọc tập trung từ `src/config.js`, đề xuất env
   `VITE_MAP_TILE_URL`, `VITE_MAP_TILE_ATTRIBUTION` (thêm `.env.example` khi triển khai). Có thông báo tile lỗi,
   giữ thời gian/tọa độ/địa chỉ; không phụ thuộc tile để ghi kết quả nhiệm vụ.

### Cơ sở kỹ thuật đã kiểm tra ngày 23/11/2026

- [W3C Geolocation](https://www.w3.org/TR/geolocation/): quyền người dùng, secure context và timestamp thời điểm đo.
  Giả lập localhost cho demo; HTTP địa chỉ LAN điện thoại không được coi là môi trường GPS đã kiểm chứng.
- [Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started): URL mở chỉ đường,
  `api=1`, địa chỉ được encode, không cần API key. App không xác nhận được tuyến bên ngoài đã tải thành công;
  chỉ kiểm URL/điểm đến và luôn có địa chỉ dự phòng.
- [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/): tile HTTPS, attribution luôn nhìn thấy,
  giữ Referer/caching mặc định trình duyệt, không bulk/prefetch/offline tiles. Dùng URL có thể cấu hình;
  OSM cộng đồng không có cam kết sẵn sàng. Chỉ nêu các yêu cầu tích hợp liên quan, không coi dịch vụ là không giới hạn.

**Đầu vào spec 009 đã có (23/11/2026):** `OPEN_TASK_STATUSES` gồm `ACTIVE` và `PENDING_SWAP_HANDOVER`;
người cũ vẫn phụ trách trong lúc chờ, người dự kiến chưa có nhiệm vụ/quyền. Báo đã đưa về chỉ ghi timestamp,
chưa đóng nhiệm vụ; NV xác nhận mới chuyển cũ thành `REPLACED` và tạo nhiệm vụ cho người mới.
GPS sau này phải kiểm `Task.shipper`, dừng cho nhiệm vụ cũ sau khi bị thay; chỉ đường lúc chờ phải về điểm tập kết.
Spec 009 chưa triển khai GPS. Các lựa chọn D1–D10 chưa có xác nhận riêng từ người dùng;
phần lưu/gửi được tiến hành theo yêu cầu Phase 1 như ghi ở đầu spec.

Chi tiết: [models.md](models.md), [api.md](api.md).
- Mở rộng app `tracking` hiện có; phụ thuộc model `dispatch.Task` một chiều. URL dispatch/shipments chỉ đăng ký view GPS của tracking.
- `POST /dispatch/tasks/{id}/locations/` (Shipper) · `GET /shipments/{id}/location/` (Shop đơn mình, NV).
- Lệnh `purge_location_pings --days 30`.

## 4. Frontend

- Composable `useLocationSharing(taskId, { taskStatus, onTask })` nhận ref/getter, dùng trong Vue scope có Pinia;
  trả `enabled/state/message/lastRecordedAt/start/stop`. Kiểm task qua API trước watchPosition, không tự bật;
  nhịp gửi/freshness/health check lấy metadata. Dừng khi logout bắt đầu, đổi/đóng task, mất quyền hoặc scope bị hủy.
- Component `LiveLocationMap` nhận `shipmentId`, `active` (mặc định true), `onlyWhenOpen` (mặc định false), slot tiêu đề;
  phát `ended` khi không còn task mở;
  tự gọi API, lazy load Leaflet và dọn tài nguyên. Shop/NV đúng phiên; ẩn tab/active=false dừng, hiện lại tải mới.
  Stale xét cả server và thời gian trôi, giữ nhãn last-known khi lỗi mạng; task đổi/đóng/mất quyền xóa điểm cũ.
- Nút "Chỉ đường" trong thẻ điểm đến (lấy / giao / `HubCard` hoàn).
- Đã thêm `leaflet` 1.9.4; CSS kèm, circle marker lấy màu design token, attribution luôn hiện.
  `src/config.js` đọc `VITE_MAP_TILE_URL` / `VITE_MAP_TILE_ATTRIBUTION`; mặc định nền OSM HTTPS.
  Provider riêng cần cả hai giá trị. Tile dùng referrer policy gửi origin, caching trình duyệt, không bulk/prefetch.
- Phase 4 đã nối `LocationSharingCard` vào TaskDetailView chỉ cho task mở, giải thích trước nút bật và hiển thị trạng thái/
  thời điểm gửi; tắt/rời view/đóng task dừng watcher. `onTask` cập nhật task mới từ health check vào view,
  nên khi chờ bàn giao điểm đến đổi về hub và không còn giao/COD theo giao diện spec 009.
- `DirectionsLink` dùng chung các thẻ điểm đến lấy/giao/hoàn/chờ bàn giao; chỉ dùng địa chỉ cho URL Google Maps,
  không phụ thuộc quyền GPS và không vẽ tuyến/đích giả. App giữ địa chỉ khi dịch vụ Maps ngoài chưa tải được;
  app không kiểm chứng được kết quả tìm tuyến bên ngoài.
- Shop/NV gắn map theo scope đơn; `onlyWhenOpen` ẩn khi không có task, vẫn báo lỗi đọc nếu có.
  Khi mutation cùng đơn đổi updated_at, dựng lại khối để đọc task mới ngay cả khi polling cũ đã dừng.
  Load chi tiết cả ba view có request counter + hủy hiệu lực khi unmount để phản hồi cũ không đè route mới.

## 5. Tiêu chí nghiệm thu

- [x] Chỉ Shipper phụ trách nhiệm vụ mở (kể cả chờ bàn giao) gửi được; người khác / nhiệm vụ đóng bị từ chối; không gửi thay người khác.
- [x] Điểm cũ / tương lai / sai tọa độ / quá dày bị loại; không coi tọa độ cũ là mới.
- [x] Shop chỉ xem vị trí đơn mình khi nhiệm vụ mở; nhiệm vụ đóng → không trả tọa độ; chỉ điểm gần nhất (không hành trình).
- [x] Giao diện Shipper: giải thích trước khi xin quyền; từ chối quyền vẫn thấy địa chỉ + "Chỉ đường"; dừng gửi khi nhiệm vụ đóng / rời trang.
- [x] Giao diện Shop / NV: bản đồ + thời điểm + trạng thái cũ / chưa có; tự làm mới; dừng khi kết thúc.
- [x] Xóa điểm cũ hơn 30 ngày; `EXPLAIN` điểm gần nhất theo nhiệm vụ dùng index.
- [ ] Frontend: Vitest pass, build, audit, ảnh chụp 1440/390 (giả lập vị trí), thử trình duyệt theo `manual-test.md`.
