# Spec 004 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Backend (1–3) và nền frontend (4) làm song song được.

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung: Docker DB đang chạy. **Không tắt server người dùng**; smoke test gửi `Origin`/`Referer` như trình duyệt.

---

## Phase 0 — Chốt quyết định, dữ liệu phường/xã

- [x] **0.1** Chốt D1–D7 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt). → Cả 7 điểm theo đề xuất.
- [x] **0.2** D1: nhận file CSV phường/xã Hà Nội chính thức (cột `code,name`) đặt vào `docs/data/`, **hoặc** xác nhận tạm dùng phường demo giả. → **Tạm dùng phường demo** (dự án chưa có file danh sách; đã kiểm tra). Việc còn treo: nhóm bổ sung CSV chính thức rồi chạy `load_wards`.

Xong khi: mục 2 ghi rõ phương án; biết nguồn dữ liệu phường/xã.

---

## Phase 1 — Backend: model, migration, danh mục

- [x] **1.1** `ShipmentAction.UPDATE_REQUEST` + dòng `SHIPMENT_TRANSITIONS`; cập nhật test so khớp checklist (thêm dòng Sửa yêu cầu); hằng số mới. → Bảng chuyển trạng thái khớp **đủ** checklist mục 4.
- [x] **1.2** Model `Ward`, `Shipment`, `ShipmentEvent` theo [models.md](models.md); `CheckConstraint` (trạng thái, số kiện, COD); admin (event chỉ đọc). → Thêm ràng buộc DB cho khối lượng, 2 SĐT, dạng mã yêu cầu, `holder_type`. Admin: vận đơn + lịch sử **chỉ xem** (đổi trạng thái phải qua service); phường sửa được, không xóa.
- [x] **1.3** Migration `shipments/0001_initial`; xem lại không có index FK thừa; `migrate` DB local.
- [x] **1.4** Lệnh `load_wards <csv>` (thêm/cập nhật/ngừng dùng, chạy lại an toàn); `seed_demo --wards` tạo phường demo giả có tiền tố `[Demo]`. → Thêm `--dry-run`; chấp nhận BOM Excel; lỗi một dòng thì không ghi gì; báo rõ file không phải UTF-8. Đã nạp 5 phường `DEMO-01…05` lên DB local.
- [x] **1.5** Test: ràng buộc DB (COD âm/quá trần, số kiện 0, trạng thái lạ), `request_code`, `load_wards` (lặp, ngừng dùng, file sai cột), `PROTECT` (không xóa phường/Shop đang có đơn), bảng chuyển trạng thái khớp checklist đủ dòng.
  → 21 test (`test_models.py`, `test_load_wards.py`, bảng chuyển trạng thái, `seed_demo --wards` + thay bằng danh sách thật). Tổng backend 242.

Xong khi: test pass; toàn bộ test spec 001–003 vẫn pass.

---

## Phase 2 — Backend: tạo, danh sách, chi tiết, phường/xã

- [x] **2.1** `services.create_request` (transition + bản chụp + `request_code` + lịch sử trong một transaction).
- [x] **2.2** Serializer tạo/rút gọn/chi tiết (ward theo mã, `allowed_actions`), query serializer danh sách. → `ActiveWardField` chỉ nhận phường đang dùng, lỗi "Địa chỉ phải thuộc Hà Nội…" ngay ở trường.
- [x] **2.3** View + URL: `wards/`, `shipments/` (GET, POST), `shipments/{id}/` (GET); `HasRole.of(SHOP)`; queryset theo Shop. → Phạm vi dữ liệu gom vào **một hàm** `shipments_visible_to(user)` (`permissions.py`) — spec 005 mở rộng tại đây.
- [x] **2.4** Test: tạo hợp lệ/sai từng trường, phường ngừng dùng, trường cấm bị bỏ qua, Shop A–B `404`, Nhân viên/Shipper `403`, lọc/tìm/phân trang, không N+1, `EXPLAIN` danh sách.
  → `test_api_create_list.py` 21 test. `EXPLAIN`: danh sách và lọc trạng thái đều `Index Scan using ship_shop_created_idx`, không `Sort`.

Xong khi: test pass.

---

## Phase 3 — Backend: sửa, hủy, lịch sử

- [x] **3.1** `services.update_request` (khóa bản ghi, transition, `updated_at`, `changes` trước/sau), `services.cancel_request` (idempotent). → Kiểm trạng thái trước `updated_at` (thông điệp "không còn Chờ xác nhận" rõ hơn); phường ghi lịch sử cả mã + tên.
- [x] **3.2** View + URL: `PATCH {id}/`, `{id}/cancel/`, `{id}/events/`.
- [x] **3.3** Test: sửa khi chờ/đã hủy/đã duyệt (đặt trạng thái trực tiếp trong test), `409` bản cũ, không đổi gì thì không ghi lịch sử, hủy lặp, **2 luồng song song** (sửa vs đổi trạng thái) chỉ một bên thắng, sửa hồ sơ Shop không đổi đơn cũ, lịch sử đúng thứ tự + người thực hiện.
  → `test_api_update_cancel.py` 17 test, gồm 2 test **2 luồng thật** (luồng "duyệt" giữ khóa, Shop phải đợi rồi nhận `409`). Kiểm tra đột biến bỏ `select_for_update` → cả hai fail với `'ok'` (Shop sửa/hủy được đơn đã duyệt — hủy còn đè trạng thái thành Đã hủy).
- [x] **3.4** Smoke test trên server đang chạy (có `Origin`), dữ liệu thử dọn sau khi xong. → 7/7 qua Vite; đã xóa đơn thử + 3 dòng lịch sử.

Xong khi: test pass; smoke đạt.

---

## Phase 4 — Frontend: nền

- [x] **4.1** `services/shipmentService.js`; store/cách tải danh mục phường (một lần mỗi phiên). → `stores/wards.js`.
- [x] **4.2** `components/common/WardSelect.vue` (lọc theo chữ gõ), `components/shipments/ShipmentForm.vue` (dùng cho tạo + sửa). → `WardSelect` lọc **không dấu** ("hoan kiem" ra "Hoàn Kiếm", cả đ/Đ), giữ phường đang chọn khi lọc. Giới hạn số kiện/khối lượng/COD lấy từ `/meta/choices/` — backend thêm `package_count_min/max`, `weight_grams_max` vào `limits` (không chép số sang frontend).
- [x] **4.3** Route `/shop/shipments`, `/shop/shipments/new`, `/shop/shipments/:id` (`meta.roles: [ROLES.SHOP]`); menu Shop trong `ROLE_MENU`. → 3 view tạm (Phase 5 thay).
- [x] **4.4** Test Vitest cho service, `WardSelect`, `ShipmentForm`. → + store wards; tổng 151 test, 0 cảnh báo Vue.

Xong khi: test pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** `ShipmentListView.vue` (mã yêu cầu/vận đơn, lọc, tìm, URL, trống → Tạo yêu cầu, lỗi → Tải lại). → Trạng thái/từ khóa/trang trên URL; đổi lọc về trang 1; trống có lọc → "Bỏ lọc", không lọc → "Tạo yêu cầu đầu tiên"; chặn phản hồi cũ về muộn.
- [x] **5.2** `ShipmentCreateView.vue` (điền sẵn người gửi từ hồ sơ, Hủy, lỗi trường, thành công → chi tiết). → Thành công sang chi tiết `?created=1` (thông báo đã gửi); không tải được phường → "Tải lại"; danh mục phường rỗng → cảnh báo.
- [x] **5.3** `ShipmentDetailView.vue` (thông tin, lịch sử, Sửa/Hủy theo `allowed_actions`, `409` → báo trạng thái mới + Tải lại). → Mã hành động gom ở `utils/shipmentActions.js` (test đối chiếu `ShipmentAction` backend). `409 CONFLICT`/`INVALID_TRANSITION` → "Tải bản mới nhất"; nếu hết được sửa thì thoát chế độ sửa. Hủy bị `409` → tải lại, nút xác nhận bị khóa.
- [x] **5.4** Test Vitest cho 3 màn hình. → 8 + 6 + 14 test màn hình, 2 test `shipmentActions`; `mountView` thêm tùy chọn `beforeMount` (chuẩn bị store trước khi mount).

Xong khi: test pass; build.

---

## Phase 6 — Nghiệm thu

- [x] **6.1** `check`, `makemigrations --check`, toàn bộ test backend; `npm run test`, build. → `check` sạch, không migration mới, backend 280/280, Vitest 184/184 (0 cảnh báo Vue), audit production 0, build 91 module (vào scratchpad — `dist/` vẫn bị chặn quyền). Smoke qua Vite có `Origin` 7/7 trên server người dùng; đã xóa đơn thử.
- [x] **6.2** Rà hardcode. → Không còn mã trạng thái/hành động viết thẳng ngoài `constants.py` (backend) và `roles.js`/`statusTones.js`/`http.js`/`shipmentActions.js` (frontend); không URL/host cứng. **Sửa 3 chỗ:** độ dài từ khóa `100` lặp ở 2 serializer + 2 màn hình → `SEARCH_QUERY_MAX_LENGTH` (`core/constants.py`) + `limits.search_query_max_length`; `ShipmentEvent.reason` viết `500` → `EVENT_REASON_MAX_LENGTH`; ô lý do hủy không giới hạn và lỗi lý do chỉ hiện chung chung → `maxlength` từ `limits.cancel_reason_max_length` + lỗi hiện dưới ô. Độ rộng cột model (150/10/20/30) giữ theo quy ước Django như các app trước.
- [ ] **6.3** `manual-test.md` + người dùng thử trình duyệt. → [manual-test.md](manual-test.md) sẵn sàng (32 bước, 7 nhóm; nhóm F giả lập "vừa được duyệt" bằng lệnh vì màn hình duyệt thuộc spec 005). **Chờ người dùng.**
- [x] **6.4** Đánh dấu tiêu chí; cập nhật `specs/README.md`, README gốc, spec 001 (bảng trạng thái có `UPDATE_REQUEST`), `api.md`/`models.md` nếu lệch. → 12/13 tiêu chí `[x]` (còn thử trình duyệt); spec 001 thêm dòng `UPDATE_REQUEST` vào bảng + ghi chú `limits` mở rộng; api.md/models.md ghi 2 giới hạn và hằng số mới.

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 21/11/2026 | 0 | **Xong.** Người dùng chốt D1–D7 theo đề xuất; D1 tạm dùng phường demo `[Demo]` vì dự án chưa có danh sách phường/xã chính thức (đã tìm trong repo: không có CSV/Excel nào). Thiết kế bảng `Ward` + `load_wards` giữ nguyên để thay bằng dữ liệu thật mà không sửa code. |
| 21/11/2026 | 1 | **Xong.** 3 bảng + `UPDATE_REQUEST` + `load_wards` + `seed_demo --wards`. 242 test backend, 136 Vitest pass. Test chạy trên DB test trước, rồi `migrate` DB local; kiểm tra index: không có index FK thừa (`shop`, `shipment` để `db_index=False`), 11 ràng buộc CHECK. 1 test của tôi viết sai (cp1258 không mã hóa được "ờ" dựng sẵn) — đổi sang ghi byte UTF-8 sai trực tiếp. Nạp phường demo bằng `seed_demo --wards --output` (giữ mật khẩu `hien12345` của 6 tài khoản — đã kiểm tra). Ghi nhận: Django tự tạo index `_like` cho cột mã unique — không dùng cho tìm "chứa chuỗi", để lại vì lượng ghi nhỏ. |
| 21/11/2026 | 2 | **Xong.** API phường/xã, tạo, danh sách, chi tiết. 263 test pass (sửa 1 test spec 001 dùng `/api/v1/shipments/123/` làm "đường dẫn không tồn tại" — nay là route thật). `EXPLAIN` không `Sort`. Smoke **qua proxy Vite có `Origin`/`Referer`** (bài học lỗi đăng nhập) với `demo_shop`/`demo_nhanvien` 9/9: tạo `YC00000001` chưa có mã vận đơn, phường sai + COD âm `400`, gửi `shop`/`status` lạ bị bỏ qua, tìm, Nhân viên `403` (spec 005 mới mở), `DELETE` `405`. Đã xóa 2 đơn thử + lịch sử (DB còn 0 đơn; mã yêu cầu tiếp theo sẽ là `YC00000003` vì id không quay lại — chỉ là thẩm mỹ). |
| 21/11/2026 | 3 | **Xong — backend spec 004 hoàn tất.** Sửa/hủy/lịch sử. 280 test pass. Chống ghi đè chứng minh bằng test 2 luồng + đột biến. Smoke qua Vite có `Origin` với `demo_shop` 7/7: sửa COD + phường (gửi `status` lạ bị bỏ qua), bản cũ `409 CONFLICT`, hủy → `allowed_actions: []`, hủy lặp `200`, sửa sau hủy `409 INVALID_TRANSITION`, lịch sử 3 dòng đúng thứ tự. DB về 0 đơn. Không bật/tắt server. |
| 21/11/2026 | 4 | **Xong.** Service, store phường, `WardSelect`, `ShipmentForm`, 3 route + menu Shop. 151 Vitest + 280 backend pass; build 79 module. **Lỗi thật (cảnh báo Vue):** `<input type="number">` được Vue tự đổi sang Number nhưng `FormField` chỉ nhận String → sửa `FormField` nhận `[String, Number]` (ảnh hưởng mọi form có ô số). 1 lỗi test của tôi (lấy nhầm ô lọc thay vì ô chọn phường). Không bật/tắt server. |
| 21/11/2026 | 5 | **Xong — frontend spec 004 hoàn tất.** 3 màn hình Shop: danh sách, tạo, chi tiết (sửa/hủy/lịch sử). `API_ERROR` thêm `INVALID_TRANSITION`. 181 Vitest (0 cảnh báo Vue) + 280 backend pass; build OK; `makemigrations --check` không đổi. **Đột biến 8/8 bị test bắt** (bỏ chặn phản hồi cũ, không gửi lọc, không gửi `updated_at`, luôn cho sửa, không thoát sửa sau 409, không khóa nút hủy sau 409, không báo đã gửi, không điền sẵn người gửi). **Phát hiện khi viết test:** hủy bị 409 xong tải lại thì hộp xác nhận vẫn mở với nút "Hủy yêu cầu" bấm được → khóa nút khi `allowed_actions` không còn `CANCEL_REQUEST`. 1 lỗi test của tôi: hộp `<dialog>` đóng vẫn nằm trong DOM nên tìm nhầm nút cùng tên. Không bật/tắt server. |
| 21/11/2026 | 6 | Nghiệm thu: backend 280/280, Vitest 184/184, audit 0, build OK, smoke qua Vite 7/7 (DB về 0 đơn). Rà hardcode tìm ra 3 chỗ và đã sửa (độ dài từ khóa lặp 4 nơi, `500` ở `ShipmentEvent.reason`, ô lý do hủy không giới hạn + lỗi không chỉ đúng ô) — 3 đột biến kiểm tra test mới đều bị bắt; sửa kéo theo màn hình danh sách tài khoản (spec 003) dùng cùng giới hạn. **12/13 tiêu chí đạt**; còn thử trình duyệt theo `manual-test.md` (32 bước). Không bật/tắt server. |
