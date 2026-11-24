# Spec 011 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Điều kiện chung như [spec 009 tasks.md](../009-doi-shipper/tasks.md#phase-0--chốt-quyết-định). **Làm sau spec 009** (nhiệm vụ chờ bàn giao — BR3).

```
Phase 0 ─► Phase 1 (model + API gửi) ─► Phase 2 (API xem + dọn dữ liệu) ─┐
                         └──────► Phase 3 (frontend nền: composable, Leaflet) ─┼─► Phase 4 (màn hình) ─► Phase 5 (nghiệm thu)
```

---

## Phase 0 — Chốt quyết định

- [ ] **0.1** Chốt D1–D10; đặc biệt D1 (giữ 30 ngày), D3 (ngưỡng điểm cũ / nhịp gửi), D6 (Leaflet + nền OSM), D7 (chỉ đường bằng Google Maps, không gọi dịch vụ định tuyến), app `tracking`.

- [x] **0.2** Đối chiếu UC03.3–03.5, quyền GPS và đầu vào spec 009; kiểm code hiện có, các điểm tái sử dụng và khác biệt cần chốt.
- [x] **0.3** Làm rõ thiết kế đề xuất đồng bộ trong spec/model/API: đồng hồ thiết bị/máy chủ, replay/nhịp gửi, ràng buộc/index, metadata, dừng chia sẻ và giới hạn bản đồ ngoài ứng dụng.

Đã rà soát ngày 23/11/2026:

- App `tracking` đã cài trong Django và có khung, chỉ mở rộng; `OPEN_TASK_STATUSES` và unique một task mở/đơn đã có.
- Người cũ chờ bàn giao tiếp tục gửi cho task cũ; swap_candidate chưa có quyền. Đổi người không tái dùng điểm task cũ.
- Nhịp 15 giây theo giờ nhận máy chủ, timestamp đo dùng đúng `position.timestamp`; không queue offline hoặc đóng dấu mới cho tọa độ cũ.
- Retention dùng `received_at`, thêm index dọn; độ chính xác có phần lẻ; GET trả cả thời điểm đo/nhận và không lộ danh tính Shipper.
- D7 là điều chỉnh so với tuyến nhúng trong UC03.4, đã gửi câu hỏi lựa chọn cùng nhóm ngưỡng/quyền/lưu dữ liệu.
  **Chưa có câu trả lời thì 0.1 vẫn mở**, không ghi rằng người dùng đã chốt. Các con số và lựa chọn map hiện là đề xuất.
- Nguồn kỹ thuật chính thức và điều kiện tích hợp đã ghi ở [spec.md](spec.md#cơ-sở-kỹ-thuật-đã-kiểm-tra-ngày-23112026).

Xong khi: người dùng chọn các phương án ảnh hưởng dữ liệu/quyền và D7; phản ánh lựa chọn vào spec/model/API,
ghi ngày/cơ sở quyết định rồi mới đánh dấu 0.1. Không cần viết code GPS hoặc chạy migration trong Phase 0.

**Cập nhật khi bắt đầu Phase 1:** sau câu hỏi trên, người dùng yêu cầu làm Phase 1. Thực hiện phần lưu/gửi
theo phương án đã trình bày; giữ 0.1 mở để không ghi giả xác nhận riêng D1–D10. D7 chưa chốt, không chặn API gửi GPS.

## Phase 1 — Backend: lưu vị trí

- [x] **1.1** Mở rộng app `tracking` đã có, `LocationPing` + CHECK + index; hằng số; `limits` ở `/meta/choices/`.
- [x] **1.2** `POST /dispatch/tasks/{id}/locations/` (đúng Shipper, nhiệm vụ mở kể cả chờ bàn giao, điểm cũ / tương lai / dày).
- [x] **1.3** Test + đột biến (bỏ kiểm người gửi, bỏ kiểm nhiệm vụ mở, bỏ ngưỡng thời gian).

  → Thêm **20 test GPS**, cập nhật hợp đồng test metadata (7 khóa mới). GPS + metadata **30/30**;
  toàn backend **570/570 xuôi (52,781 s)** và **570/570 ngược (53,462 s)** trên PostgreSQL.
  Mốc mutation **20/20**, **7/7 đột biến bị bắt**. Lượt đầu target permission chưa tác động tới alias helper đã import,
  runner báo survived; đã sửa target sang hàm service thực sự được dùng và chạy lại đủ bộ đạt 7/7, không sửa source server.
  `check` sạch, `makemigrations --check --dry-run` không có thay đổi. Migration mới đã review, chỉ áp tại test DB;
  `showmigrations tracking` trên DB đang dùng vẫn `[ ] 0001_initial`.
  [Bằng chứng và lệnh chạy](artifacts/phase1/README.md).

```powershell
.\venv\Scripts\python.exe backend/manage.py test apps.tracking.tests apps.core.tests.test_choices --keepdb --noinput
.\venv\Scripts\python.exe specs/011-gps-ban-do/tools/check_phase1_mutations.py
```

Xong khi: test PostgreSQL đạt cả biên thời gian/accuracy, replay/đồng thời, task chờ bàn giao, Shipper bị khóa,
task đóng/đổi người; đột biến bị bắt. `check` và kiểm migration đạt, chưa tự migrate DB dùng chung.

## Phase 2 — Backend: xem vị trí, dọn dữ liệu

- [x] **2.1** `GET /shipments/{id}/location/` (điểm gần nhất, `stale`, chỉ khi nhiệm vụ mở, phạm vi Shop).
- [x] **2.2** Lệnh `purge_location_pings`.
- [x] **2.3** Test; `EXPLAIN` điểm gần nhất (nhiều điểm, rollback + `exec`).

  → GET dùng scope đơn hiện có và một SQL task mở + correlated subquery điểm mới nhất, trả số JSON/thời gian/stale,
  không danh tính Shipper/hành trình. Task mới sau thay người không nhận điểm task cũ; task đóng trả null.
  Purge theo received_at, mặc định 30 ngày, giữ đúng biên; chỉ nhận --days nguyên dương và kiểm overflow.

  → **15 test mới** (11 đọc, 4 purge) đạt; toàn backend **585/585 xuôi (52,835 s)** và **585/585 ngược (58,132 s)**.
  Mutation mốc **35/35 GPS**, **6/6 đột biến bị bắt**: scope, task mở, task của điểm, stale boundary,
  đồng hồ retention và biên xóa. Query count không tăng khi thêm 1.000 điểm; check/migration drift sạch.

  → EXPLAIN trên **40.000 điểm trong PostgreSQL test DB** dùng location_task_latest_idx cho cả điểm gần nhất và
  subquery GET; lần đo 0,035/0,101 ms. Fixture ID âm rollback sạch, sequence giữ nguyên; không ép planner/thống kê.
  Không migrate/purge DB đang dùng, không có schema mới; DB đó vẫn chưa áp migration Phase 1.
  [Bằng chứng và lệnh chạy](artifacts/phase2/README.md).

Xong khi: test quyền và body 404 giống nhau đạt; GET không trả điểm nhiệm vụ cũ sau thay người/đóng,
không N+1; kế hoạch truy vấn dùng index; purge chỉ xóa điểm quá hạn theo received_at, không xóa task/đơn.

## Phase 3 — Frontend nền

- [x] **3.1** `leaflet` (audit), `trackingService`, `useLocationSharing` (giả lập `navigator.geolocation` trong test), `LiveLocationMap`.

  → Thêm đúng dependency `leaflet` **1.9.4**, không đổi major/package khác; CSS bundle tại component, tile URL/attribution
  qua config/env tập trung. `trackingService` dùng client session/CSRF chung, hỗ trợ AbortSignal;
  `taskService.get` thêm options tương thích để kiểm nhiệm vụ và hủy request.

  → `useLocationSharing(taskId, { taskStatus })`: chỉ start chủ động, xác minh task trước khi xin GPS;
  Permissions API + callback bắt từ chối/thu hồi, không queue offline/không đóng dấu mới cho tọa độ cũ.
  Kiểm freshness/accuracy và nhịp theo metadata; task health check kể cả đứng yên; dừng/abort/dọn watch/timer
  khi logout bắt đầu, đổi task, đóng task, unmount, API 401/403/404/409; response cũ không bật lại phiên mới.

  → `LiveLocationMap(shipmentId, active)`: polling không chồng request, dừng khi ẩn tab/active=false/đóng task/mất quyền;
  xóa marker cũ khi đổi task/đơn. Clock độc lập vẫn đánh stale nếu API đang treo. Có trạng thái rỗng/cũ/lỗi API/tile,
  retry, tọa độ/thời điểm và attribution; không đặt điểm/tuyến giả. Gỡ map/observer/timer/handler khi unmount.

  → **36 test mới** (19 composable, 16 map, 1 service); toàn frontend **373/373 / 47 file, 21,90 s**.
  Component map cuối kiểm lại 16/16 sau chỉnh câu báo lỗi tile. Build app **1.833 module / 2,98 s**;
  build fixture nhập trực tiếp các module Phase 3 **38 module / 1,41 s** (app chưa dùng chúng tới Phase 4).
  Chrome + Leaflet/geolocation thật, API/tile fixture: **0 Vue warning / 0 page error**, 6 ảnh 1440/390,
  không tràn ngang; server 5180 đã dừng. Đây là kiểm component, flow API/PostgreSQL thật để Phase 4.

  → Audit trước/sau: **7 mục dev cũ** (5 moderate, 2 critical), **production 0**, không mục Leaflet mới.
  Không ghi audit đầy đủ là sạch, không nâng major Vitest trong phase này. [Bằng chứng](artifacts/phase3/README.md).

Xong khi: Vitest kiểm quyền bị từ chối/thu hồi, GPS lỗi/mạng lỗi, dừng watcher/timer và response cũ;
không gửi lại timestamp cũ như mới. Map có trạng thái rỗng/cũ/lỗi, teardown sạch, attribution hiện và build đạt.

## Phase 4 — Màn hình

- [x] **4.1** Shipper: nút bật chia sẻ + giải thích + trạng thái; "Chỉ đường" ở thẻ điểm đến (lấy / giao / hoàn).
- [x] **4.2** Shop / NV: khối "Theo dõi vị trí" ở chi tiết đơn khi có nhiệm vụ mở.
- [x] **4.3** Vitest; ảnh 1440 + 390 với giả lập vị trí; bấm thật (Shipper bật chia sẻ → Shop thấy điểm).

  → TaskDetailView dùng LocationSharingCard, giữ GPS tùy chọn không chặn nghiệp vụ; hướng đi theo taskDestination,
  chờ bàn giao/hoàn về hub. Link Google Maps chỉ có api=1 và destination địa chỉ, không cần GPS để tạo link;
  không gửi tên/SĐT/COD/mã đơn/vị trí hiện tại. D7 thực hiện theo phương án đã đề xuất và yêu cầu làm Phase 4,
  không ghi giả đã có lựa chọn riêng D1–D10 hoặc tuyến nhúng.

  → Callback onTask từ health check cập nhật trạng thái/điểm đến của view; task đóng bỏ khối chia sẻ.
  Shop/NV dùng onlyWhenOpen, slot tiêu đề; mutation đổi updated_at làm mới khối GPS kể cả polling cũ đã dừng.
  Load chi tiết ba view có request counter để response cũ không ghi đè route mới.

  → **11 test tích hợp mới**, tổng **384/384 Vitest / 48 file (28,49 s)**. Build app đã chứa Leaflet/GPS
  **1.846 module / 6,10 s** tại cache riêng tránh dist khóa/quyền. Không đổi dependency/backend contract.
  Browser app thật + session/CSRF/PostgreSQL **1/1 (73,316 s)**: bật GPS → lưu điểm → Shop/NV xem;
  task đóng dừng/hide; pending handover về hub; thay người tạo task chưa có điểm rồi nhận GPS người mới;
  chặn Shop khác. **0 Vue warning / 0 page error**, 10 ảnh 1440/390 không tràn ngang.
  GPS/tile giả lập; toàn API nghiệp vụ thật. Kiểm URL Maps, không gọi dịch vụ bên ngoài.
  [Bằng chứng](artifacts/phase4/README.md) · [Hướng dẫn thử tay](manual-test.md).

  → Server test 8010/5180 đã dừng, Django dọn fixture; DB đang dùng vẫn chưa áp tracking.0001_initial.
  Phase 5 (toàn bộ nghiệm thu + người dùng tự thử) chưa đánh dấu hoàn tất.

Xong khi: flow thật trên PostgreSQL test DB đạt; kiểm điểm đến cả lấy/giao/hoàn/chờ bàn giao,
đổi người và đóng task không lộ GPS cũ, không tự bật chia sẻ; 0 Vue warning/page error ở browser, không tràn ngang.

## Phase 5 — Nghiệm thu

- [ ] **5.1** Kiểm toàn bộ; rà hardcode; `manual-test.md` (cách giả lập vị trí, hạn chế HTTPS); README (lưu 30 ngày, cấu hình nền bản đồ).

Xong khi: check/backend xuôi-ngược/Vitest/build/audit có bằng chứng, báo rõ audit còn mở nếu có;
README hướng dẫn lịch purge và provider, người dùng tự thử theo manual-test. Không đánh dấu thay phần người dùng.

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 24/11/2026 | 4 | Xong gắn GPS vào màn Shipper/Shop/NV, DirectionsLink theo địa chỉ lấy/giao/hub và pending swap; callback health cập nhật view, task đóng dừng. D7 làm theo đề xuất/yêu cầu tiếp tục Phase 4, không giả xác nhận riêng hay tuyến nhúng. Chặn response cũ và làm mới map sau mutation cùng đơn. 11 test mới, tổng 384/384; build 1.846 module/6,10 s; browser/API/PostgreSQL test DB thật 1/1/73,316 s, 0 Vue warning/page error, 10 ảnh. Chỉ GPS/tile giả lập. Không đổi schema/dependency, không migrate DB dùng chung; server test dừng. Đã viết manual-test nhưng người dùng chưa tự thử; còn Phase 5. |
| 24/11/2026 | 3 | Xong nền frontend: Leaflet 1.9.4, trackingService/AbortSignal, composable chia sẻ chủ động theo metadata, map live polling + stale/tile/API error + teardown. 36 test mới, tổng 373/373; map cuối 16/16. Build app 1.833 module/2,98 s và fixture 38 module/1,41 s. Chrome thực thi Leaflet/geolocation thật với API/tile fixture đạt, 0 Vue warning/page error, 6 ảnh; server test dừng. Audit prod 0, dev giữ 7 mục cũ, không có finding Leaflet. Chưa gắn vào màn nghiệp vụ, chưa tuyên bố flow API thật của Phase 4; D7 còn mở. |
| 24/11/2026 | 2 | Xong GET vị trí theo scope Shop/NV và snapshot task/point, whitelist JSON số/thời gian/stale; task đóng/đổi người không lộ điểm cũ. Thêm command purge theo received_at, mặc định 30 ngày, override dương có kiểm biên/overflow; không tự cài lịch chạy. 15 test mới; 585 backend xuôi/ngược; mốc 35 GPS và 6/6 mutation. EXPLAIN 40.000 điểm trên test DB dùng index hiện có, rollback/count/sequence sạch. Không sửa schema, không migrate/purge DB dùng chung; frontend còn Phase 3–4. |
| 23/11/2026 | 1 | Xong phần lưu/gửi GPS theo yêu cầu tiếp tục Phase 1 sau câu hỏi Phase 0, không ghi giả xác nhận riêng D1–D10; D7 còn mở. LocationPing + 3 CHECK/2 index, migration 0001, constants, metadata và POST theo task. Dùng khóa đơn → user → task, kiểm active/trạng thái sau khóa, validate trước replay/throttle; không đổi dữ liệu giao nhận. 20 test mới; GPS+metadata 30/30; backend 570/570 xuôi và ngược; mutation mốc 20/20, 7/7 bị bắt sau sửa target alias ở runner. Check/migration drift sạch. Chưa migrate DB đang dùng, chưa làm Phase 2–4. |
| 23/11/2026 | 0 | Đã đối chiếu UC03.3–03.5/phân quyền/checklist/code; app tracking có khung, input spec 009 sẵn. Làm rõ hợp đồng đề xuất: khóa chống đua, replay/nhịp server, accuracy phần lẻ, index latest/retention, metadata, vòng đời chia sẻ và điểm đến chờ bàn giao. Kiểm tài liệu W3C/Google/OSM. D7 khác tuyến nhúng UC gốc, đã gửi câu hỏi chọn cùng các mức lưu/quyền/ngưỡng; chưa có xác nhận nên 0.1 còn mở. Không sửa code runtime, không tạo migration/cài thư viện. |
| 23/11/2026 | — | Lập spec, chờ chốt D1–D10. Chưa có dịch vụ bản đồ / tọa độ địa chỉ trong dự án → đề xuất Leaflet + OSM cho bản đồ, chỉ đường bằng mở Google Maps theo địa chỉ văn bản (không gọi dịch vụ định tuyến). Ghi rõ hạn chế: Geolocation chỉ chạy trên HTTPS / `localhost`. |
