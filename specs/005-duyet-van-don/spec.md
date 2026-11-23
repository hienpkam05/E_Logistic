# Spec 005 — Duyệt và quản lý vận đơn (Nhân viên)

Trạng thái: **Đã triển khai (22/11/2026)** — chờ người dùng thử trình duyệt ([manual-test.md](manual-test.md)). D1–D8 theo đề xuất, chốt 21/11/2026. Ngày lập: 21/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md) · [manual-test.md](manual-test.md)

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC05.6–05.9.
- [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md): mục 2.2, 3 (UC05.6–05.9), 5 (quy tắc 1, 2, 5, 6, 8), 6.
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): UC05.6–05.9, thông báo nội bộ, xử lý đồng thời, thao tác lặp, mục 4 (Duyệt / Từ chối).
- Nền:
  - [spec 001](../001-nen-tang/spec.md): D2 định dạng mã vận đơn; `APPROVE_REQUEST`, `REJECT_REQUEST` đã có trong bảng trạng thái.
  - [spec 004](../004-yeu-cau-gui-hang/spec.md): `Shipment`, `ShipmentEvent`, `shipments_visible_to`, mục 6 "Ghi chú cho spec sau".
  - [docs/design-system.md](../../docs/design-system.md): khuôn giao diện.

## 1. Mục tiêu và phạm vi

Nhân viên/Admin xem toàn bộ yêu cầu và vận đơn, **duyệt** yêu cầu Chờ xác nhận để sinh mã vận đơn chính thức (đơn sang **Chờ lấy hàng**), hoặc **từ chối** có lý do. Shop nhận thông báo kết quả. Sau spec này luồng vận đơn đi tiếp được tới bước phân công lấy hàng (spec 006).

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC05.9 | Danh sách vận đơn của Nhân viên | Toàn bộ:<br>- toàn hệ thống;<br>- tìm theo mã / người nhận / Shop;<br>- lọc trạng thái, khoảng ngày tạo;<br>- phân biệt yêu cầu chờ duyệt và vận đơn chính thức;<br>- A1 không có kết quả, E1 lọc sai / lỗi tải. |
| UC05.7 | Chi tiết vận đơn của Nhân viên | Thông tin Shop, người gửi/nhận, kiện hàng, COD, trạng thái, người giữ hàng, số lần giao, lịch sử; nút theo `allowed_actions`.<br>"Shipper phụ trách", "kết quả giao" hiện nhãn **Chưa phát sinh** (A1.2). Dữ liệu thật có từ spec 006–007. |
| UC05.6 | Xác nhận (duyệt) | Toàn bộ:<br>- sinh mã vận đơn, Chờ lấy hàng, lịch sử, thông báo Shop;<br>- E1: Shop vừa sửa/hủy, hoặc đã duyệt;<br>- BR1–BR2: không sinh mã thứ hai. |
| UC05.8 | Từ chối | Toàn bộ:<br>- lý do bắt buộc, Bị từ chối, thông báo Shop, không sinh mã;<br>- A1: đóng hộp không đổi gì;<br>- E1: lý do trống hoặc không còn Chờ xác nhận. |

**Bổ sung phía Shop:**
- Chi tiết đơn **Bị từ chối** hiện rõ lý do (UC05.8 mô tả "thông báo rõ lý do cho Shop").
- Thông báo duyệt/từ chối có liên kết mở thẳng vận đơn.

**Ngoài phạm vi:**
- Phân công lấy hàng (UC06.5) và mọi bước sau: spec 006+.
- Tra cứu nhanh theo mã ở mọi màn hình: spec 010.
- Sửa nội dung yêu cầu thay Shop: không có trong đặc tả. Nhân viên chỉ duyệt hoặc từ chối.

## 2. Quyết định cần chốt

**Đã chốt 21/11/2026: cả 8 điểm theo đề xuất.**
- Duyệt **có hộp xác nhận** trước khi sinh mã, đúng UC05.6 bước 4 "chọn Xác nhận và xác nhận thao tác"; duyệt không hoàn tác được.
- Kiểm tra khi chốt: `HasRole.of(*roles)` đã nhận nhiều vai trò (dùng được cho D1); `TIME_ZONE = Asia/Ho_Chi_Minh` (D4, D7).

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **API cho Nhân viên** | **Dùng chung** endpoint vận đơn của spec 004:<br>- `shipments_visible_to(user)` mở rộng: ADMIN thấy toàn hệ thống.<br>- Thêm 2 endpoint hành động `…/{id}/approve/`, `…/{id}/reject/`.<br>- Shop vẫn chỉ thấy đơn của mình; Shipper vẫn `403` (spec 006 mở).<br>- Sửa/hủy/tạo vẫn chỉ Shop. Bảng trạng thái chặn vai trò, Nhân viên gọi thì nhận `403`. |
| D2 | **Duyệt/từ chối trên dữ liệu cũ** (UC05.6 E1) | Gửi kèm `updated_at` của bản Nhân viên đang xem. Shop vừa sửa sau khi Nhân viên mở → `409 CONFLICT` "Yêu cầu vừa được Shop thay đổi…", Nhân viên tải lại để xem nội dung mới rồi mới quyết định. Thứ tự kiểm tra như spec 004: khóa bản ghi → trạng thái → `updated_at`. |
| D3 | **Gửi lại / hai người cùng duyệt** (BR1, BR2) | Đơn đã được duyệt (đã có mã vận đơn) mà nhận thêm lệnh duyệt → trả **200 kèm trạng thái hiện tại**, không sinh mã mới, không ghi lịch sử, không gửi thông báo lần hai. Tương tự từ chối lặp khi đã Bị từ chối. Trạng thái khác (Đã hủy, đã từ chối mà bấm duyệt…) → `409 INVALID_TRANSITION` với thông báo trạng thái hiện tại. |
| D4 | **Mã vận đơn** (spec 001 D2) | `HTT` + `yyMMdd` theo **giờ Việt Nam** ngày duyệt + 5 ký tự ngẫu nhiên từ bảng chữ đã bỏ I/O/0/1 (`HTT261121K7Q2M`). Sinh bằng `secrets`. Trùng (unique DB) → thử lại tối đa 5 lần trong savepoint. Vẫn trùng thì `500` và không lưu gì: xác suất cỡ 1/33 triệu mỗi lần, chỉ là lớp chặn. |
| D5 | **Lý do từ chối** | Bắt buộc, cắt khoảng trắng, 1–500 ký tự (`EVENT_REASON_MAX_LENGTH`):<br>- lưu ở lịch sử `REJECT_REQUEST`;<br>- chi tiết đơn trả `rejection_reason` (lấy từ mốc từ chối gần nhất, không thêm cột);<br>- thông báo cho Shop chứa lý do. |
| D6 | **Thông báo Shop** | Tạo trong cùng transaction với duyệt/từ chối (`notify()` đã có):<br>- Duyệt: `REQUEST_APPROVED`, "Yêu cầu YC… đã được duyệt", nội dung "Mã vận đơn HTT…".<br>- Từ chối: `REQUEST_REJECTED`, "Yêu cầu YC… bị từ chối", nội dung "Lý do: …".<br>- `payload = {"shipment_id": id}`. Màn Thông báo có nút "Xem vận đơn" mở đúng màn chi tiết theo vai trò. |
| D7 | **Danh sách Nhân viên** (UC05.9) | Hai tab:<br>- **Chờ xác nhận** (mặc định, **cũ nhất trước**, xử lý theo thứ tự đến);<br>- **Tất cả** (mới nhất trước).<br>Lọc theo trạng thái và khoảng ngày tạo (từ ngày – đến ngày, giờ Việt Nam). Tìm theo mã yêu cầu, mã vận đơn, tên/SĐT người nhận, **tên/tên đăng nhập/SĐT Shop**. Cột: mã, Shop, người nhận, giao đến, COD, trạng thái, ngày tạo. |
| D8 | **Trang chủ Nhân viên** | Thêm menu "Quản lý vận đơn" (thanh bên). Trang chủ có ô "N yêu cầu chờ duyệt", bấm vào mở tab Chờ xác nhận. Số lấy từ `count` của API danh sách, không thêm API riêng. |

## 3. Backend

### 3.1. Phạm vi dữ liệu và quyền

- `shipments_visible_to(user)`: SHOP → `shop=user`; **ADMIN → mọi đơn**; vai trò khác → rỗng.
- Danh sách, chi tiết, lịch sử: `HasRole.of(SHOP, ADMIN)`.
- `approve/`, `reject/`: `HasRole.of(ADMIN)`. Vai trò còn được kiểm tra lần nữa trong `resolve_transition`.
- Tạo, sửa, hủy: giữ `HasRole.of(SHOP)`.
- ADMIN thấy mọi đơn nên `404` chỉ xảy ra khi đơn thật sự không tồn tại.

### 3.2. Service — `shipments/services.py`

| Hàm | Việc làm |
|---|---|
| `approve_request(staff, pk, expected_updated_at)` | 1. `select_for_update` đơn.<br>2. Đã có `tracking_code` → trả hiện tại (D3).<br>3. `resolve_transition(APPROVE_REQUEST, status, ADMIN)`; không hợp lệ → `409` nêu trạng thái hiện tại.<br>4. `updated_at` khác → `409 CONFLICT`.<br>5. Sinh `tracking_code` (D4), `status=AWAITING_PICKUP`.<br>6. Ghi lịch sử `APPROVE_REQUEST` (`changes.tracking_code`) và `notify(shop, REQUEST_APPROVED…)`.<br>Tất cả trong **một transaction**: lỗi thì không có vận đơn dở dang (điều kiện sau UC05.6). |
| `reject_request(staff, pk, reason, expected_updated_at)` | Như trên:<br>- đã `REJECTED` → trả hiện tại;<br>- hợp lệ → `status=REJECTED`, lịch sử `REJECT_REQUEST` có `reason`, `notify(shop, REQUEST_REJECTED…)`, **không** sinh mã. |
| `generate_tracking_code(now)` | Hàm thuần, test được, dùng hằng số `TRACKING_CODE_*` đã có. |

- Đồng thời:
  - Shop sửa/hủy cùng lúc Nhân viên duyệt: cả hai khóa cùng dòng, bên sau thấy trạng thái mới → `409`.
  - Hai Nhân viên cùng duyệt: người sau nhận `200` với cùng mã, không có mã thứ hai.
  - Chứng minh bằng test 2 luồng thật như spec 003–004.
- `holder_type` giữ `SHOP`: hàng vẫn ở Shop tới khi Shipper lấy (spec 006).

### 3.3. Danh sách, chi tiết

- Query param mới:
  - `created_from`, `created_to`: ngày `YYYY-MM-DD`, tính theo `Asia/Ho_Chi_Minh`, gồm cả hai đầu. `from > to` → `400` đúng trường.
  - `ordering`: `created_at` hoặc `-created_at` (mặc định). Giá trị khác → `400`.
- `q` với ADMIN tìm thêm theo Shop: họ tên, tên đăng nhập, SĐT.
- Serializer:
  - Bản rút gọn và chi tiết thêm `shop: {id, username, full_name, phone}` (`select_related`, không N+1).
  - Chi tiết thêm `rejection_reason` (chỉ truy vấn khi `REJECTED`) và `allowed_actions` theo **vai trò người xem**.
- Kiểm tra index bằng `EXPLAIN` cho các truy vấn thật của Nhân viên: mặc định, tab Chờ xác nhận cũ nhất trước, lọc theo ngày. Chỉ thêm index khi kế hoạch thực thi cho thấy cần.

## 4. Frontend

| Route | View | Mô tả |
|---|---|---|
| `/staff/shipments` | `views/staff/StaffShipmentListView.vue` | Khuôn danh sách:<br>- tab Chờ xác nhận / Tất cả, lọc trạng thái, từ ngày – đến ngày, tìm;<br>- cột Shop;<br>- bộ lọc nằm trên URL. |
| `/staff/shipments/:id` | `views/staff/StaffShipmentDetailView.vue` | Khuôn chi tiết:<br>- thẻ Shop, Người gửi, Người nhận, Kiện hàng, Thu hộ, Điều phối ("Chưa phát sinh"), lịch sử;<br>- nút **Duyệt** (hộp xác nhận nêu mã yêu cầu, Shop, COD — đã chốt) và **Từ chối** (hộp có lý do bắt buộc) theo `allowed_actions`;<br>- `409` → cảnh báo + "Tải bản mới nhất". |

- **Dùng lại, không chép:** tách từ `shop/ShipmentDetailView.vue`:
  - `components/shipments/ShipmentInfoCards.vue`: các thẻ thông tin;
  - `components/shipments/ShipmentEventList.vue`: lịch sử có phân trang.

  Màn Shop và màn Nhân viên cùng dùng hai component này.
- `utils/shipmentActions.js` thêm `APPROVE_REQUEST`, `REJECT_REQUEST` (test đối chiếu backend đã có).
- Menu ADMIN thêm "Quản lý vận đơn" (`ROLE_MENU`). Trang chủ Nhân viên có ô "yêu cầu chờ duyệt" (D8).
- Màn Thông báo: thông báo có `payload.shipment_id` thì hiện "Xem vận đơn", mở route chi tiết theo vai trò.
- Chi tiết của Shop: đơn Bị từ chối hiện khung lý do.

## 5. Tiêu chí nghiệm thu

**10/11 đạt** — bằng chứng: `apps/shipments/tests/test_staff_*.py` (34 test, gồm 6 test 2 luồng thật), đột biến, `EXPLAIN`, smoke; xem nhật ký [tasks.md](tasks.md).

- [x] Nhân viên thấy yêu cầu/vận đơn của **mọi Shop**; Shop vẫn chỉ thấy của mình; Shipper `403`.
- [x] Danh sách Nhân viên: tab Chờ xác nhận cũ nhất trước; lọc trạng thái, khoảng ngày (sai → `400` đúng trường); tìm theo mã, người nhận, Shop; trống / lỗi tải có thông báo và cách thoát.
- [x] Chi tiết Nhân viên: đủ thông tin Shop, người gửi/nhận, kiện, COD, trạng thái, lịch sử; phần chưa phát sinh có nhãn rõ; **không** có nút đổi trạng thái tùy ý.
- [x] Duyệt: sinh mã đúng định dạng, duy nhất; Chờ lấy hàng; lịch sử có người duyệt; Shop nhận thông báo kèm mã.
- [x] Duyệt lặp / hai người cùng duyệt → **một** mã, **một** dòng lịch sử, **một** thông báo.
- [x] Shop sửa sau khi Nhân viên mở → duyệt bị `409 CONFLICT`, tải lại thấy nội dung mới; Shop hủy trước → `409` nêu Đã hủy.
- [x] Từ chối: lý do bắt buộc (trống → `400`); Bị từ chối, không có mã vận đơn; Shop thấy lý do ở chi tiết và thông báo.
- [x] Không duyệt/từ chối được đơn đã hủy, đã từ chối, đã duyệt (trừ lặp cùng hành động); Shop không gọi được `approve/`/`reject/` (`403`).
- [x] Mọi bước trong một transaction: lỗi sinh mã → không đổi trạng thái, không lịch sử, không thông báo.
- [x] Danh sách/chi tiết Nhân viên không N+1; `EXPLAIN` không `Sort` toàn bảng cho truy vấn mặc định và tab Chờ xác nhận.
- [ ] Frontend: Vitest pass, build, thử trình duyệt theo `manual-test.md`. → Vitest 229 + build ✔, ảnh chụp 1440/390 + 1 lượt bấm thật end-to-end; **còn người dùng thử** ([manual-test.md](manual-test.md), 31 bước).

## 6. Ghi chú cho spec sau

- **Spec 006:**
  - Phân công lấy hàng nhận đơn `AWAITING_PICKUP` (có `tracking_code`).
  - Thẻ "Điều phối" ở chi tiết Nhân viên sẽ hiện Shipper, nhiệm vụ thật.
  - `shipments_visible_to` thêm nhánh SHIPPER (đơn đang được giao cho mình).
- **Spec 010:** tra cứu theo mã dùng lại `q` và `shipments_visible_to`.
