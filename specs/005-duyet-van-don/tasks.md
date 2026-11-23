# Spec 005 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Backend (1–3) và nền frontend (4) làm song song được.

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung:
- Docker DB đang chạy.
- **Không tắt server người dùng.**
- Smoke test gửi `Origin`/`Referer` như trình duyệt.
- Dữ liệu thử tạo ra phải dọn sau khi xong.

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D8 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt). → Cả 8 điểm theo đề xuất; Duyệt có hộp xác nhận.

Xong khi: mục 2 ghi rõ phương án đã chốt.

---

## Phase 1 — Backend: nền

- [x] **1.1** Hằng số:
  - thông điệp `409` (theo nhãn trạng thái hiện tại);
  - mẫu tiêu đề/nội dung thông báo;
  - `TRACKING_CODE_MAX_ATTEMPTS`.

  → Thêm `TRACKING_CODE_REGEX` (dựng từ tiền tố/bảng chữ/độ dài, test dùng lại), `REJECT_REASON_REQUIRED_MESSAGE`.
- [x] **1.2** `generate_tracking_code(now)`: giờ Việt Nam, `secrets`, bảng chữ đã có. Test:
  - định dạng;
  - ngày theo giờ VN quanh nửa đêm UTC;
  - không có ký tự dễ nhầm.

  → Thêm test vừa cột DB (14/20 ký tự), 300 mã gần như không trùng, regex loại mã sai.
- [x] **1.3** `shipments_visible_to`: nhánh ADMIN. Test phạm vi cho đủ 3 vai trò. → View vẫn `IsShop` tới Phase 2, nên Nhân viên **chưa** gọi được API.
- [x] **1.4** Serializer:
  - `shop` lồng (rút gọn + chi tiết);
  - `rejection_reason`;
  - `allowed_actions` theo vai trò người xem.

  → `allowed_actions` đã tính theo vai trò từ spec 004, chỉ thêm test cho Nhân viên. `ShipmentShopSerializer` kế thừa `EventActorSerializer` + `phone` (không chép). `rejection_reason` chỉ truy vấn khi `REJECTED`; đơn còn Chờ xác nhận thì không lộ lý do cũ. Danh sách/chi tiết thêm `select_related("shop")`.

Xong khi: test pass; `makemigrations --check` sạch (hoặc migration index được ghi vào models.md).

---

## Phase 2 — Backend: danh sách, chi tiết cho Nhân viên

- [x] **2.1** Quyền đọc `HasRole.of(SHOP, ADMIN)` cho danh sách, chi tiết, lịch sử; tạo/sửa/hủy giữ SHOP. → `CanViewShipments` + `ShopOnlyForWrites` (đọc thì 2 vai trò, ghi chỉ Shop) trên cùng view; test chặn mật khẩu tạm vẫn nhận ra.
- [x] **2.2** Query param:
  - `created_from`/`created_to` (giờ VN, `from > to` → `400`);
  - `ordering` (2 giá trị);
  - `q` tìm theo Shop khi là Nhân viên.
- [x] **2.3** Test:
  - Nhân viên thấy đơn mọi Shop, Shop vẫn bị giới hạn, Shipper `403`;
  - lọc ngày ở biên;
  - `ordering` sai → `400`;
  - tìm theo Shop;
  - số truy vấn không đổi theo số dòng;
  - `EXPLAIN` mặc định / tab Chờ xác nhận / lọc ngày.

  → 13 test ở `test_staff_list.py`. **`EXPLAIN` phát hiện danh sách mặc định của Nhân viên quét toàn bảng** → migration `0002_staff_list_indexes` (xem nhật ký).

Xong khi: test pass; `EXPLAIN` ghi vào nhật ký.

---

## Phase 3 — Backend: duyệt, từ chối

- [x] **3.1** `approve_request`, `reject_request` theo spec mục 3.2 (khóa → đã xong thì trả hiện tại → transition → `updated_at` → ghi), thông báo trong cùng transaction.
- [x] **3.2** View + URL `approve/`, `reject/` (`HasRole.of(ADMIN)`, `404` trước lỗi dữ liệu).
- [x] **3.3** Test chức năng:
  - duyệt: mã, trạng thái, lịch sử, 1 thông báo;
  - duyệt lặp → cùng mã, không ghi thêm;
  - từ chối: lý do bắt buộc/trim/giới hạn, không mã, `rejection_reason`;
  - đã hủy/đã từ chối/đã duyệt → `409` đúng thông điệp;
  - `updated_at` cũ → `CONFLICT`;
  - Shop/Shipper `403`;
  - trùng mã 5 lần → `500`, không lưu gì (mock bộ sinh).
- [x] **3.4** Test đồng thời 2 luồng thật:
  - 2 Nhân viên cùng duyệt → 1 mã;
  - duyệt vs Shop hủy;
  - duyệt vs Shop sửa;
  - duyệt vs từ chối.
- [x] **3.5** Smoke qua Vite (có `Origin`) với `demo_shop` + `demo_nhanvien`; dọn dữ liệu thử. → Vite/Django của người dùng đang tắt nên smoke trên **Django riêng cổng 8010** (có `Origin`), 12/12; đã tắt đúng tác vụ đó và dọn dữ liệu.

Xong khi: test pass; đột biến (bỏ khóa, bỏ kiểm tra đã duyệt) bị test bắt.

---

## Phase 4 — Frontend: nền

- [x] **4.1** `shipmentService`:
  - `approve(id, updatedAt)`, `reject(id, reason, updatedAt)`;
  - `list` nhận `createdFrom`, `createdTo`, `ordering`.
- [x] **4.2** `SHIPMENT_ACTION` thêm `APPROVE_REQUEST`, `REJECT_REQUEST`.
- [x] **4.3** Tách `ShipmentInfoCards.vue`, `ShipmentEventList.vue` từ màn chi tiết Shop. Màn Shop dùng lại, test cũ vẫn pass.
  → 15 test cũ màn Shop pass **không sửa dòng nào**; file 305 → 210 dòng.
  - `ShipmentInfoCards`: prop `showShop` thêm thẻ Shop; slot cho thẻ riêng ("Điều phối" ở Phase 5).
  - `ShipmentEventList`: tự tải + phân trang, `reload()` qua `defineExpose`, thêm chặn phản hồi cũ khi đổi đơn, nhãn `tracking_code` = "Mã vận đơn" cho mốc duyệt.
- [x] **4.4** Route `staff-shipments`, `staff-shipment-detail` (`meta.roles: [ROLES.ADMIN]`); menu "Quản lý vận đơn". → 2 view tạm (Phase 5 thay); menu đứng đầu nhóm Nhân viên, icon `clipboard`.
- [x] **4.5** Test Vitest cho service và 2 component tách.

Xong khi: test pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** `StaffShipmentListView.vue`:
  - tab Chờ xác nhận (cũ nhất trước) / Tất cả;
  - lọc trạng thái, khoảng ngày, tìm;
  - cột Shop;
  - URL giữ bộ lọc; trống/lỗi.
- [x] **5.2** `StaffShipmentDetailView.vue`:
  - thẻ thông tin + Shop + Điều phối "Chưa phát sinh";
  - Duyệt (xác nhận), Từ chối (lý do bắt buộc);
  - `409` → "Tải bản mới nhất".
- [x] **5.3** Phía Shop: khung lý do khi Bị từ chối. Màn Thông báo: "Xem vận đơn" theo vai trò.
- [x] **5.4** Trang chủ Nhân viên: ô "N yêu cầu chờ duyệt".
- [x] **5.5** Test Vitest cho các màn; kiểm tra giao diện 1440px / 390px bằng ảnh chụp.

  → Ảnh chụp 1440px/390px trên Django 8010 + Vite 5180 riêng: trang chủ, danh sách, chi tiết, hộp duyệt/từ chối, đơn đã duyệt, Shop thấy lý do, thông báo có "Xem vận đơn". Lượt bấm thật end-to-end: Nhân viên duyệt qua giao diện → Shop mở thông báo → đúng màn chi tiết.

Xong khi: test pass; build; 0 cảnh báo Vue.

---

## Phase 6 — Nghiệm thu

- [x] **6.1** `check`, `makemigrations --check`, toàn bộ test backend; `npm run test`, build. → `check` sạch, không migration mới, backend 323/323, Vitest 230/230 (0 cảnh báo Vue), audit production 0, build OK.
- [x] **6.2** Rà hardcode (mã hành động chỉ ở `shipmentActions.js`; không màu hex trong component). → Sửa 2 chỗ:
  - Thông điệp thiếu `updated_at` viết thẳng ở view (có từ spec 004) và **không nhất quán**: PATCH có câu riêng, duyệt/từ chối dùng câu mặc định DRF → `MISSING_VERSION_MESSAGE` dùng chung 3 API + test.
  - Giá trị `ordering` (`'created_at'`) viết thẳng ở màn danh sách → `SHIPMENT_ORDERING` trong `shipmentActions.js` + test đối chiếu `SHIPMENT_LIST_ORDERINGS` backend.
  - Không còn mã cứng ngoài file cho phép, không màu hex, không URL cứng.
- [ ] **6.3** `manual-test.md` + người dùng thử trình duyệt (luồng Shop tạo → Nhân viên duyệt/từ chối → Shop thấy kết quả). → [manual-test.md](manual-test.md) sẵn sàng (31 bước, 7 nhóm, 2 cửa sổ Shop/NV). **Chờ người dùng.**
- [x] **6.4** Đánh dấu tiêu chí; cập nhật `specs/README.md`, README gốc, `api.md`/`models.md` nếu lệch. Bỏ bước giả lập duyệt khỏi manual-test spec 004 (nay duyệt được thật). → 10/11 tiêu chí `[x]`; nhóm F manual-test spec 004 nay duyệt bằng màn hình thật (mã vận đơn không còn ghi cứng `HTTTHU01`).

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 21/11/2026 | — | Lập spec, chờ chốt D1–D8 |
| 21/11/2026 | 0 | **Xong.** Người dùng chốt D1–D8 theo đề xuất, Duyệt có hộp xác nhận. Kiểm tra lại giả định: `HasRole.of` nhận nhiều vai trò; múi giờ đúng. **Sửa 1 chỗ tôi viết sai** ở models.md: index trạng thái thật là `(status, -created_at)`, không có `-id` → Phase 2 phải kiểm `EXPLAIN` trước khi kết luận không cần index mới. |
| 21/11/2026 | 1 | **Xong.** Mã vận đơn, phạm vi Nhân viên, serializer `shop`/`rejection_reason`. Backend 289/289 pass (+9 test ở `test_staff_foundation.py`); `makemigrations --check` sạch (không migration). **Đột biến 7/7 bị bắt** (bỏ nhánh ADMIN, Shipper thấy hết, ngày theo UTC, phần ngẫu nhiên cố định, lộ lý do khi chưa từ chối, lấy lý do cũ nhất, N+1 theo shop). Cập nhật `DETAIL_FIELDS`/`SUMMARY_FIELDS` trong test spec 004: thay đổi API có chủ đích (`shop`, `rejection_reason`), đã ghi ở api.md. Không bật/tắt server. |
| 22/11/2026 | 2–3 | **Xong — backend spec 005 hoàn tất.**<br>- **Database:** Docker Desktop lỗi engine 500 (đã khởi động lại theo phép người dùng; `wsl --shutdown` bị chặn). Sau đó engine tự hồi phục → `docker compose up -d db`; container được tạo lại nhưng **dữ liệu còn nguyên** (6 tài khoản, 5 phường, migration đủ).<br>- **Test:** 34 test mới (13 `test_staff_list.py`, 21 `test_staff_decisions.py`, gồm 6 test 2 luồng thật) pass ngay lần đầu; toàn bộ backend 323/323. Sửa test spec 004 `test_staff_and_shipper_forbidden` → `test_shipper_forbidden`: spec 005 cố ý mở quyền xem cho Nhân viên (D1).<br>- **Đột biến 16/17 bị bắt.** Sống sót: đổi quyền view duyệt sang cho cả Shop. Lý do: lớp chặn thứ hai ở service (bảng trạng thái kiểm vai trò) vẫn trả 403. Đây là chặn 2 lớp có chủ đích, không phải lỗ hổng.<br>- **`EXPLAIN` 30.000 đơn (rollback):** danh sách mặc định của Nhân viên **Seq Scan toàn bảng + Sort, 64 ms** (spec 004 không gặp vì Shop luôn lọc `shop`). → Migration **`0002_staff_list_indexes`**: thêm `ship_created_idx (-created_at, -id)`; `ship_status_created_idx` thêm `-id`. Sau đó cả 3 truy vấn (mặc định / tab Chờ xác nhận / lọc 7 ngày) đều Index Scan, **không Sort** (10 ms / 0,23 ms / 0,57 ms). Lần đo đầu lọc ngày ra kế hoạch lạ do thống kê bảng user cũ → thêm `ANALYZE accounts_user` rồi đo lại.<br>- **Smoke** 12/12 trên Django riêng cổng 8010: tab chờ cũ nhất trước; bản cũ 409; duyệt ra `HTT261122…`; duyệt lại cùng mã; Shop gọi duyệt 403; Shop hủy đơn đã duyệt 409; lý do trống 400; từ chối + Shop thấy lý do; 2 thông báo đúng loại; Nhân viên tạo đơn 403.<br>- **Tác dụng phụ do tôi gây ra, đã sửa:** script `EXPLAIN` rollback dữ liệu nhưng PostgreSQL **không rollback sequence** → id đơn nhảy lên 90010. Sau khi dọn (bảng trống) đặt lại `setval(..., 9)` → mã tiếp theo vẫn `YC00000010` như manual-test spec 004. Sequence bảng user cũng nhảy (vô hại, không đặt lại). Lần sau script đo phải đặt lại sequence. |
| 22/11/2026 | 4 | **Xong.** Service `approve`/`reject` + tham số lọc ngày/sắp xếp; `SHIPMENT_ACTION` thêm 2 mã (test đối chiếu backend pass); tách 2 component dùng chung; route + menu Nhân viên.<br>- Vitest 200/200, 0 cảnh báo Vue; build OK; backend 323/323. **Đột biến 8/8 bị bắt.**<br>- Ghi nhận: build nay xử lý 1.811 module (Vite quét từng file icon của Lucide) → build ~37 s, nhưng **bundle chính vẫn 142 kB** (tree-shaking đúng).<br>- Lại gặp lỗi Bash phân tích heredoc dài → chuyển sang tạo file bằng công cụ ghi file. |
| 22/11/2026 | 5 | **Xong — spec 005 hoàn tất phần code.** Danh sách Nhân viên (2 tab, lọc ngày, tìm theo Shop), chi tiết (duyệt có hộp xác nhận, từ chối bắt buộc lý do, 409 → tải bản mới), Shop thấy lý do từ chối, thông báo "Xem vận đơn" theo vai trò, trang chủ Nhân viên ô "N yêu cầu chờ duyệt".<br>- **Backend bổ sung** (UC05.7 bước 4): chi tiết trả `holder_type`, `delivery_attempts`; `limits.reject_reason_max_length`.<br>- **Dùng lại:** `composables/usePagedList` (tải + chặn phản hồi cũ) cho danh sách Nhân viên và chuyển danh sách Shop sang dùng (9 test cũ pass); `shipmentRouteFor(role, id)` trong `roles.js`; mã `PENDING_APPROVAL` đặt trong `statusTones.js` (đúng quy tắc chỗ chứa mã trạng thái) + test bắt buộc là mã thật.<br>- Vitest 229/229, 0 cảnh báo Vue, build OK; backend 323/323; không migration mới. **Đột biến 13/13 bị bắt.**<br>- **Lỗi thật do ảnh chụp phát hiện, đã sửa:** route `/staff/shipments/:id` viết `':id(\d+)'` trong chuỗi JS (Phase 4) → mất dấu `\`, chỉ khớp chữ "d" nên mở chi tiết ra 404. Unit test không bắt được vì dùng bộ route giả → **thêm `router/__tests__/routes.spec.js` chạy trên router thật**; đã thử khôi phục lỗi cũ thì test fail.<br>- Lỗi giao diện ảnh chụp phát hiện, đã sửa: ô ngày trên điện thoại lệch, nhãn xuống dòng.<br>- Lỗi trong test của tôi, đã sửa: 2 dòng thừa vô nghĩa trong test "Bỏ lọc"; cách viết `find(k => k === ...)` vòng vo cho hằng số trạng thái.<br>- Dữ liệu ảnh chụp (đơn 10–13) đã xóa cùng lịch sử/thông báo; đặt lại sequence → mã tiếp theo vẫn `YC00000010`. Đã tắt đúng 2 tác vụ server của tôi. |
| 22/11/2026 | 6 | Nghiệm thu: backend 323/323, Vitest 230/230, audit 0, build OK. Rà hardcode tìm ra 2 chỗ và đã sửa (thông điệp thiếu `updated_at` không nhất quán giữa sửa và duyệt/từ chối; giá trị `ordering` viết thẳng). Hằng `ordering` ban đầu đặt ở `shipmentService.js` nhưng test màn hình mock cả module → chuyển sang `shipmentActions.js`. **10/11 tiêu chí đạt**; còn thử trình duyệt theo `manual-test.md` (31 bước). Tự rà kịch bản, sửa 2 chỗ viết sai (bước D7 không tái tạo được "duyệt lại"; bảng dữ liệu thiếu SĐT người nhận). Không bật/tắt server người dùng. |
