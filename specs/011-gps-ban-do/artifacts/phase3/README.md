# Spec 011 Phase 3 — 24/11/2026

Đã hoàn thành nền frontend: Leaflet 1.9.4, trackingService, useLocationSharing và LiveLocationMap.
Chưa gắn vào màn nghiệp vụ Shipper/Shop/NV; đó là Phase 4. Không thay backend/schema, không migrate/purge DB.

| Kiểm chứng | Kết quả |
|---|---|
| Test mới | 36: 19 chia sẻ GPS, 16 map, 1 service |
| [Toàn Vitest](vitest.txt) | 373/373, 47 file, 21,90 s |
| Map cuối sau chỉnh câu lỗi tile | 16/16 |
| [Build ứng dụng](build.txt) | 1.833 module, 2,98 s |
| [Build fixture + Chrome](browser.txt) | 38 module, 1,41 s; 0 Vue warning / 0 page error |
| [Audit trước](audit-before.json) / [sau](audit-all.json) | Đều 7 mục dev: 5 moderate, 2 critical |
| [Audit production](audit-production.json) | 0 phát hiện |

Package/lockfile chỉ thêm Leaflet 1.9.4, không nâng major thư viện khác. npm audit không có mục Leaflet mới;
7 mục dev cũ thuộc graph Vitest/@vue/test-utils đã ghi ở spec 009–010, không ghi audit đầy đủ là sạch.
[Skill dự án](../../../../.agents/skills/htt-express-code/SKILL.md) yêu cầu giữ phiên bản/package manager hiện có;
không nâng major Vitest trong phase nền GPS. Vitest toàn bộ vẫn có warning fixture AccountCreateView/navActive cũ,
browser fixture thực tế không có Vue warning/page error.

Build app xuất vào `frontend/node_modules/.cache/spec011-phase3-build` để tránh `dist` bị khóa/quyền như các spec trước.
Vì Phase 4 mới import các khối vào màn hình, có thêm build fixture nhập trực tiếp component/composable và Leaflet;
build app thành công riêng chưa đủ chứng minh các module chưa được dùng đã được bundle.
Fixture build tại `frontend/node_modules/.cache/spec011-phase3-fixture-build`.

## Phạm vi đã kiểm

- Không tự bật GPS; kiểm phiên/role/task trước yêu cầu vị trí. Dùng timestamp của thiết bị, kiểm freshness/sai số,
  nhịp gửi từ metadata; không queue offline/không gửi lại mẫu bị bỏ. Đứng yên vẫn kiểm task theo nhịp metadata.
- Từ chối/thu hồi quyền, GPS lỗi, mạng lỗi, API 401/403/404/409; đóng/đổi task/logout/unmount dừng watcher/timer,
  abort request; callback/response cũ không bật lại phiên mới hoặc ghi vào task mới.
- Map không tạo điểm giả khi rỗng; task/đơn thay đổi bỏ marker cũ. Poll không chồng request;
  clock vẫn đánh dấu cũ nếu API đang treo. Mất quyền/đóng task xóa tọa độ và dừng tự gọi lại.
- Có tọa độ/thời điểm/sai số, nhãn stale, lỗi API/tile và retry; attribution hiển thị cả control map và nguồn dưới map.
  Màu marker dùng token; tile URL/attribution qua config, referrer policy gửi origin, không bulk/prefetch/offline tiles.
- Teardown gỡ map, ResizeObserver, timer, visibility/permission/offline listeners. Tab ẩn hoặc active=false dừng đọc;
  hiện lại tải dữ liệu mới. Server fixture 5180 được dừng và kiểm cổng trống sau chạy.

## Bằng chứng Chrome

Chrome thực thi **Leaflet và Geolocation API thật**; tọa độ do Playwright giả lập.
API trả fixture, tile là ô lưới fixture được chặn tại browser, không tải tile OSM hoặc dùng GPS thiết bị thật.
Flow API/PostgreSQL end-to-end thuộc Phase 4, không tuyên bố đã kiểm ở đây.

| Trạng thái | 1440 | 390 |
|---|---|---|
| Điểm mới | [Desktop](map-fresh-1440.png) | [Mobile](map-fresh-390.png) |
| Điểm cũ | [Desktop](map-stale-1440.png) | [Mobile](map-stale-390.png) |
| Tile lỗi, giữ tọa độ/nguồn | [Desktop](map-tile-error-1440.png) | [Mobile](map-tile-error-390.png) |

Không tràn ngang. Đã xem ảnh điểm mới 390 và tile lỗi 1440; chỉnh câu báo lỗi không còn nói tọa độ “bên dưới”
khi tọa độ nằm trên map, chạy lại 16 test map và toàn browser fixture trên code cuối.
Lượt fixture đầu mô phỏng tile lỗi trúng tile đã cache trong Chrome; đổi vùng tọa độ fixture để kiểm đúng request lỗi.
Không sửa logic map để ép test lỗi cache thành công.

Chạy từ gốc repo (Chrome và cache Playwright theo công cụ spec 009, cổng 5180 trống):

```powershell
cd frontend
npm.cmd run test
npm.cmd run build -- --outDir node_modules/.cache/spec011-phase3-build --emptyOutDir false
npm.cmd audit --json
npm.cmd audit --omit=dev --json
cd ..
node specs/011-gps-ban-do/tools/check_phase3_browser.cjs
```

Harness gốc ở `tools/phase3-harness.html`, chỉ được copy vào node_modules/.cache khi chạy công cụ;
không thêm route/demo vào ứng dụng chính. Nguồn tích hợp: [Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html),
[OSM tile policy](https://operations.osmfoundation.org/policies/tiles/), [W3C Geolocation](https://www.w3.org/TR/geolocation/).
Các nguồn chỉ dùng để kiểm cách tích hợp API/tile; ngưỡng nghiệp vụ lấy từ spec/metadata backend.
