# Spec 004 — Yêu cầu gửi hàng của Shop

Trạng thái: **Đã chốt — sẵn sàng triển khai** (D1–D7 theo đề xuất, chốt 21/11/2026; D1 tạm dùng phường demo). Ngày lập: 21/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md)

Nguồn: [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md) UC05.1–05.5, mục 2 · [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md) mục 2.1, 3 (UC05.1–05.5), 5 (quy tắc 2, 5, 6, 7, 8), 6 · [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md) UC05.1–05.5, mục 3 (dữ liệu đầu vào), mục 4 · Nền: [spec 001](../001-nen-tang/spec.md) (enum, bảng trạng thái, thiết kế `Shipment`), [spec 002](../002-xac-thuc/spec.md) (chụp thông tin người gửi/nhận).

## 1. Mục tiêu và phạm vi

Shop gửi yêu cầu vận chuyển trong Hà Nội, theo dõi danh sách/chi tiết, sửa hoặc hủy khi còn **Chờ xác nhận**. Đây là spec đầu tiên có dữ liệu đơn hàng: tạo bảng `Shipment`, lịch sử `ShipmentEvent` và danh mục phường/xã dùng chung cho mọi spec sau.

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC05.2 | Tạo yêu cầu gửi hàng | Toàn bộ, gồm A1 (Hủy/rời form không tạo gì), E1 (thiếu, ngoài Hà Nội, COD âm) |
| UC05.3 | Danh sách vận đơn của Shop | Toàn bộ: chỉ đơn của mình, lọc trạng thái, tìm kiếm, phân biệt chờ duyệt/đã duyệt |
| UC05.4 | Chi tiết vận đơn của Shop | Thông tin, trạng thái, lịch sử, nút Sửa/Hủy theo trạng thái. Phần "phân công được công bố", "theo dõi vận chuyển" để trống — có ở spec 006/010/011 |
| UC05.1 | Chỉnh sửa yêu cầu | Toàn bộ, gồm E1 (vừa được duyệt / dữ liệu sai — không ghi đè) |
| UC05.5 | Hủy yêu cầu | Toàn bộ, gồm A1 (Không hủy), E1 (đã duyệt/từ chối/hủy) |

**Ngoài phạm vi:** Nhân viên duyệt/từ chối, sinh mã vận đơn, danh sách toàn hệ thống (spec 005); phân công, giao nhận (spec 006+); tra cứu theo mã cho cả Nhân viên (spec 010); tính phí, thanh toán (BR3 — không làm).

## 2. Quyết định cần chốt

**Đã chốt 21/11/2026: cả 7 điểm theo đề xuất.** D1: chưa có danh sách phường/xã chính thức → **tạm dùng phường demo** `[Demo] …`; khi có file CSV chính thức chỉ cần chạy `load_wards`, không sửa code (phường demo bị đánh dấu ngừng dùng nếu không có trong file).

| # | Vấn đề | Phương án |
|---|---|---|
| D1 | **Kiểm tra địa chỉ Hà Nội** (spec 001 D1) | Bảng **`Ward`** (mã, tên, đang dùng) trong DB; địa chỉ lấy/giao = **chọn phường/xã** + **địa chỉ chi tiết** tự nhập. Danh sách nạp bằng lệnh `load_wards` từ **file CSV chính thức do nhóm cung cấp** (Hà Nội đã bỏ cấp quận/huyện từ 07/2025). **Chưa có CSV:** `seed_demo --wards` tạo vài phường **ghi rõ là dữ liệu giả** (`[Demo] Phường A`…) để chạy thử; không tự bịa tên phường thật |
| D2 | Định dạng mã (spec 001 D2) | Mã yêu cầu `YC` + 8 chữ số theo id (`YC00000123`), sinh lúc tạo. Mã vận đơn sinh ở spec 005 |
| D3 | Kiện hàng, COD (spec 001 D3) | Bắt buộc: mô tả (≤ 255 ký tự), số kiện (1–99). Tùy chọn: khối lượng (gram, 1–100 000). COD số nguyên VND, 0 ≤ COD ≤ 50 000 000; 0 = không thu hộ. Ghi chú cho Shipper tùy chọn (≤ 500 ký tự) |
| D4 | Người gửi | Form **điền sẵn** họ tên, SĐT, địa chỉ từ hồ sơ Shop; Shop sửa được trên từng đơn. Đơn lưu **bản chụp** — sửa hồ sơ sau này không đổi đơn cũ (UC02.2 BR2) |
| D5 | Sửa yêu cầu (UC05.1) | Sửa được mọi trường nội dung (người gửi/nhận, địa chỉ, kiện hàng, COD, ghi chú); **không** đổi Shop, mã, trạng thái. Mỗi lần lưu có thay đổi ghi lịch sử với giá trị trước/sau |
| D6 | Hủy yêu cầu (UC05.5) | Lý do **không bắt buộc** (ghi vào lịch sử nếu có) |
| D7 | Danh sách Shop | Mặc định hiện mọi trạng thái, mới nhất trước; lọc theo trạng thái; tìm theo mã yêu cầu, mã vận đơn, tên hoặc SĐT người nhận |

## 3. Backend

### 3.1. Bảng chuyển trạng thái — thêm `UPDATE_REQUEST`

Checklist mục 4 có dòng "Sửa yêu cầu: Chờ xác nhận → Chờ xác nhận, Shop sở hữu" mà spec 001 đã bỏ ra. Thêm `ShipmentAction.UPDATE_REQUEST = transition([PENDING_APPROVAL], PENDING_APPROVAL, [SHOP])` — vòng về chính nó — để sửa cũng đi qua `resolve_transition` (kiểm vai trò + trạng thái) như mọi hành động. Test so khớp checklist bổ sung dòng này → bảng khớp **đủ 100%** checklist.

### 3.2. Quyền và phạm vi dữ liệu

- Mọi endpoint của spec này: `HasRole.of(SHOP)` (Nhân viên dùng các endpoint này ở spec 005 — mở rộng queryset theo vai trò, **không** tạo API riêng).
- Queryset luôn `shop = request.user` (phân quyền quy tắc 2). Đơn của Shop khác hoặc không tồn tại → `404` giống hệt nhau.
- `shop`, `request_code`, `tracking_code`, `status`, `holder_*`, `delivery_attempts` **không nhận** từ client; trường lạ bị bỏ qua (BR2 của UC05.1, UC05.2).

### 3.3. Service — `shipments/services.py`

| Hàm | Việc làm |
|---|---|
| `create_request(shop, data)` | `resolve_transition(CREATE_REQUEST, None, SHOP)`; tạo `Shipment` (`status=PENDING_APPROVAL`, `holder_type=SHOP`), sinh `request_code` từ id trong **cùng transaction**; ghi `ShipmentEvent(CREATE_REQUEST, from=None, to=PENDING_APPROVAL)` |
| `update_request(shop, pk, data, expected_updated_at)` | `select_for_update` đơn của Shop → `resolve_transition(UPDATE_REQUEST, status, SHOP)` (đã duyệt/hủy/từ chối → `409 INVALID_TRANSITION` "Yêu cầu không còn ở trạng thái Chờ xác nhận…" — UC05.1 E1) → `updated_at` khác → `409 CONFLICT`. Không đổi gì → không ghi lịch sử. Có đổi → ghi `UPDATE_REQUEST` với `changes` trước/sau |
| `cancel_request(shop, pk, reason="")` | `select_for_update` → đã `CANCELLED` bởi chính Shop → trả hiện tại (gửi lại, spec 001 mục 3.6); trạng thái khác `PENDING_APPROVAL` → `409 INVALID_TRANSITION` (UC05.5 E1); hợp lệ → `CANCELLED` + lịch sử `CANCEL_REQUEST` |

- Kiểm tra trạng thái **sau khi khóa bản ghi**, nên Shop sửa/hủy cùng lúc Nhân viên duyệt (spec 005 cũng khóa bản ghi) thì chỉ một bên thắng, bên kia nhận `409` — không ghi đè (UC05.1 bước 6, UC05.5 bước 5).
- Địa chỉ: `pickup_ward`, `delivery_ward` phải là `Ward` đang dùng; ward không tồn tại/ngừng dùng → `400` trường tương ứng "Địa chỉ phải thuộc Hà Nội (chọn phường/xã trong danh sách)."

### 3.4. Danh mục phường/xã

- Bảng `Ward` (`code` unique, `name`, `is_active`). Không có API sửa trong ứng dụng; quản trị qua lệnh `load_wards` và Django admin.
- `load_wards <file.csv>`: cột `code,name`; thêm mới/cập nhật tên; phường không còn trong file → `is_active=False` (không xóa — đơn cũ vẫn tham chiếu). Chạy lại an toàn.
- `GET /api/v1/shipments/wards/`: danh sách phường đang dùng cho form (mọi vai trò đã đăng nhập, không phân trang — vài trăm dòng).

### 3.5. Danh sách và chi tiết

- Danh sách: lọc `status` (một hoặc nhiều), `q` (mã yêu cầu, mã vận đơn, tên/SĐT người nhận); sắp xếp mới nhất trước; phân trang chuẩn. Trả bản rút gọn (mã, người nhận, phường giao, COD, trạng thái, thời gian).
- Chi tiết: đủ thông tin + `allowed_actions` (từ `allowed_actions(SHIPMENT_TRANSITIONS, status, SHOP)` — giao diện hiện nút Sửa/Hủy đúng trạng thái, UC05.4 bước 5).
- Lịch sử: `GET …/events/`, mới nhất trước, có người thực hiện, lý do, thay đổi.
- Index theo truy vấn thật (`shop`, `-created_at`) — kiểm tra bằng `EXPLAIN` như spec 002–003.

## 4. Frontend

| Route | View | Mô tả |
|---|---|---|
| `/shop/shipments` | `views/shop/ShipmentListView.vue` | Bảng đơn: mã (mã vận đơn nếu có, không thì mã yêu cầu + nhãn "Chờ duyệt"), người nhận, phường giao, COD, trạng thái (`StatusBadge`), thời gian; lọc trạng thái, tìm; URL giữ bộ lọc; trống → nút "Tạo yêu cầu" |
| `/shop/shipments/new` | `views/shop/ShipmentCreateView.vue` | Form 4 nhóm: Người gửi (điền sẵn từ hồ sơ), Người nhận, Kiện hàng, Thu hộ; Hủy không tạo gì; thành công → trang chi tiết + thông báo "Đã gửi yêu cầu YC…" |
| `/shop/shipments/:id` | `views/shop/ShipmentDetailView.vue` | Chi tiết + lịch sử; Sửa (cùng form, gửi `updated_at`) và Hủy (hộp xác nhận, lý do tùy chọn) chỉ hiện khi `allowed_actions` cho phép; `409` → thông báo trạng thái mới + Tải lại |

- **Dùng lại** form giữa tạo và sửa: `components/shipments/ShipmentForm.vue`. `components/common/WardSelect.vue` (ô chọn phường/xã có lọc theo chữ gõ) dùng cho cả địa chỉ lấy và giao — spec sau dùng lại.
- Menu Shop (`ROLE_MENU` trong `router/roles.js`): "Vận đơn của tôi", "Tạo yêu cầu gửi hàng".
- Tiền hiển thị qua `formatVnd`, trạng thái qua `StatusBadge` + `statusTones` (đã có).

## 5. Tiêu chí nghiệm thu

Checklist UC05.1–05.5, mục 3 (dữ liệu đầu vào) và tình huống phân quyền mục 6. **12/13 đạt** (bằng chứng: test backend `apps/shipments/tests/`, nhật ký [tasks.md](tasks.md)); còn thử trình duyệt.

- [x] Tạo yêu cầu: lưu đủ thông tin, `request_code` dạng `YC` + 8 số, trạng thái Chờ xác nhận, **chưa có mã vận đơn**; lịch sử có dòng tạo.
- [x] Thiếu trường bắt buộc, SĐT sai, phường/xã không thuộc danh sách, COD âm hoặc quá trần, số kiện/khối lượng ngoài giới hạn → `400` đúng trường; không tạo gì.
- [x] Gửi `shop`/`status`/`tracking_code` của người khác khi tạo hoặc sửa → bị bỏ qua; đơn luôn thuộc Shop đang đăng nhập (phân quyền mục 6).
- [x] Shop A không xem/sửa/hủy được đơn Shop B (kể cả đổi id trên URL) → `404`, không lộ dữ liệu.
- [x] Nhân viên/Shipper gọi các API này → `403`.
- [x] Danh sách chỉ đơn của mình; lọc trạng thái, tìm theo mã/người nhận đúng; phân biệt chờ duyệt (mã yêu cầu) và đã duyệt (mã vận đơn).
- [x] Sửa khi Chờ xác nhận: lưu, ghi lịch sử trước/sau; sửa khi đã duyệt/hủy/từ chối → `409`, dữ liệu giữ nguyên; bản cũ (`updated_at` cũ) → `409 CONFLICT`.
- [x] Hủy khi Chờ xác nhận → Đã hủy, không xóa bản ghi, có lịch sử; hủy lặp → trả hiện tại; hủy khi đã duyệt → `409`.
- [x] Sửa/hủy cùng lúc với một thao tác đổi trạng thái khác → chỉ một bên thành công, không ghi đè (test 2 luồng như spec 003).
- [x] Sửa hồ sơ Shop sau khi tạo đơn → thông tin người gửi trên đơn cũ không đổi.
- [x] Danh sách/chi tiết không N+1; `EXPLAIN` không phải `Sort` toàn bộ đơn của Shop.
- [x] `load_wards` chạy lại an toàn; phường bị bỏ khỏi file → ngừng dùng, đơn cũ vẫn hiển thị đúng tên.
- [ ] Frontend: test Vitest pass; build; thử trình duyệt theo `manual-test.md`. → Vitest 184 + build ✔; **còn thử trình duyệt** (32 bước).

## 6. Ghi chú cho spec sau

- **Spec 005:** mở rộng queryset danh sách/chi tiết cho `ADMIN` (toàn hệ thống); `APPROVE_REQUEST` sinh `tracking_code` + thông báo Shop; khóa bản ghi khi duyệt để không đua với sửa/hủy của Shop.
- **Spec 006+:** `holder_type`, `holder_shipper`, `delivery_attempts` đã có cột; `ShipmentEvent.task` thêm khi có bảng `Task`.
- **Spec 010:** tra cứu theo mã cho Shop/Nhân viên dùng lại queryset theo vai trò của spec này.
