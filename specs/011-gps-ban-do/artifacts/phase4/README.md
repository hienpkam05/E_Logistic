# Spec 011 Phase 4 — 24/11/2026

Đã gắn LocationSharingCard/DirectionsLink vào TaskDetailView và LiveLocationMap vào chi tiết Shop/NV.
Các API nghiệp vụ GPS/điều phối dùng backend thật qua session/CSRF và PostgreSQL **test DB**.
Không đổi schema/dependency/API contract, không migrate hoặc purge DB đang dùng.

| Kiểm chứng | Kết quả |
|---|---|
| Test tích hợp mới | 11/11 |
| [Toàn Vitest](vitest.txt) | 384/384, 48 file, 28,49 s |
| [Build app](build.txt) | 1.846 module, 6,10 s; gồm Leaflet/GPS thực tế trong app |
| [Chrome + API/PostgreSQL thật](browser.txt) | 1/1, 73,316 s; 0 Vue warning / 0 page error |
| Responsive | 10 ảnh 1440/390, không tràn ngang |

Build xuất `frontend/node_modules/.cache/spec011-phase4-build`, giữ cách tránh dist bị khóa/quyền đã biết.
Vitest toàn bộ còn warning fixture AccountCreateView/navActive cũ, browser thật không có Vue warning/page error.
Dependency không đổi so với Phase 3; [audit Phase 3](../phase3/README.md) production 0/dev còn 7 mục cũ.
Phase 5 mới chạy lại nghiệm thu toàn bộ/audit và nhận kết quả người dùng tự thử.

## Kịch bản thực tế đã đạt

- Đăng nhập UI thật; Shipper chưa bật không có POST GPS. Bật thì tọa độ giả lập Chrome gửi qua API được lưu,
  Shop/NV đúng đơn thấy điểm bằng Leaflet, thời điểm và sai số.
- Lấy/giao/hoàn có URL Maps đúng địa chỉ; chờ bàn giao health check cập nhật view về hub, bỏ UI giao/COD.
- Lấy thành công đóng task: khối chia sẻ dừng, Shop polling bỏ điểm cũ. Shop khác bị chặn; NV xem được đơn khác.
- Xác nhận đổi người đóng task cũ: old sharing dừng, URL chỉ đường cũ không còn; Shop thấy task mới chưa có điểm.
  Người mới bật thì Shop nhận tọa độ người mới; không tái dùng GPS người cũ. Tắt chia sẻ dừng watcher.
- 11 Vitest tích hợp kiểm giải thích/từ chối GPS vẫn có địa chỉ/chỉ đường và thao tác nghiệp vụ;
  chỉ gửi api=1/destination, encode ký tự; health update, task đóng, đóng map và reload sau mutation cùng đơn.
- Load chi tiết dùng request counter để phản hồi route trước không đè route mới. Mutation đổi updated_at
  làm mới map ngay cả khi polling trước đó đã dừng do chưa có task.

Chrome dùng geolocation giả lập, **chỉ tile** được thay bằng fixture ô lưới để không gọi OSM trong test.
Mọi API nghiệp vụ đều thật; không mô phỏng response GPS/điều phối. Google Maps chỉ kiểm URL tạo ra,
không điều hướng ra dịch vụ ngoài hoặc tuyên bố tuyến nhúng/định tuyến đã thành công.
D7 làm theo phương án đã trình bày và yêu cầu tiếp tục Phase 4; không ghi giả lựa chọn riêng D1–D10.

| Màn | 1440 | 390 |
|---|---|---|
| Shipper đang chia sẻ | [Desktop](shipper-sharing-1440.png) | [Mobile](shipper-sharing-390.png) |
| Shop nhận vị trí | [Desktop](shop-location-1440.png) | [Mobile](shop-location-390.png) |
| Nhân viên nhận vị trí | [Desktop](staff-location-1440.png) | [Mobile](staff-location-390.png) |
| Shipper chờ bàn giao | [Desktop](shipper-swap-1440.png) | [Mobile](shipper-swap-390.png) |
| Shop nhận GPS người mới | [Desktop](shop-new-shipper-1440.png) | [Mobile](shop-new-shipper-390.png) |

Đã xem ảnh Shipper chờ bàn giao 390 và Shop nhận vị trí 1440; thanh thao tác di động dính chân viewport,
cần cuộn khi nội dung dài. Ảnh cuối được cập nhật lại sau sửa reload GPS theo revision của đơn.
Server test 8010/5180 đã dừng, fixture được Django dọn; DB đang dùng vẫn `[ ] tracking.0001_initial`.

Chạy từ gốc repo, cần Chrome/cache Playwright như công cụ spec 009 và hai cổng trống:

```powershell
.\venv\Scripts\python.exe specs/011-gps-ban-do/tools/run_browser_phase4.py
cd frontend
npm.cmd run test
npm.cmd run build -- --outDir node_modules/.cache/spec011-phase4-build --emptyOutDir false
```

Không chạy browser runner cùng suite khác dùng test DB. Log PowerShell có thể gắn NativeCommandError cho stderr
thường; kết luận theo exit code và OK/FAILED. [Hướng dẫn người dùng tự thử](../../manual-test.md), chưa đánh dấu thay người dùng.
