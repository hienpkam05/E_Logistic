# Spec 010 — Tra cứu và lịch sử vận chuyển

Trạng thái: **Phase 1–2 đã triển khai; Phase 3 kiểm tra kỹ thuật đạt, chờ người dùng tự thử và xử lý/chấp nhận audit dev còn mở.** Ngày lập: 23/11/2026.
Thực hiện D1–D7 theo đề xuất và các điểm làm rõ dưới đây: sau câu hỏi Phase 0, người dùng yêu cầu
"làm phase 1 spec 10" và tiếp tục công việc. Đây là cơ sở tiến hành theo phương án đã trình bày,
không ghi là đã có câu trả lời riêng chốt cả 7 lựa chọn.

Tài liệu kèm theo: [tasks.md](tasks.md) · [api.md](api.md) · [models.md](models.md) (hằng số, không bảng/cột/migration mới).

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC03.1, UC03.2.
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): UC03.1 ("không có tra cứu công khai"), UC03.2 ("lịch sử được thêm mới, không sửa đè").
- Nền: [spec 004](../004-yeu-cau-gui-hang/spec.md) (danh sách + tìm của Shop), [spec 005](../005-duyet-van-don/spec.md) (danh sách + tìm của Nhân viên, `shipments_visible_to`), `ShipmentEvent` + `GET /shipments/{id}/events/` (spec 004–009), `ShipmentEventList`.

## 1. Mục tiêu và phạm vi

Phần lớn đã có từ spec 004–009; spec này **bù phần còn thiếu** cho đúng UC03.1–03.2, không làm lại:

| Đã có | Còn thiếu (làm ở spec này) |
|---|---|
| Danh sách đơn của Shop / NV có ô tìm **gần đúng** (mã, người nhận, Shop), đã giới hạn theo quyền | **Tra cứu theo đúng mã** (UC03.1): một trang riêng, nhập mã → kết quả tóm tắt + nút xem chi tiết / lịch sử; không tìm thấy (A1), mã rỗng (E1); **không lộ** đơn của Shop khác (BR1–BR2) |
| `GET /shipments/{id}/events/` — mới nhất trước, có người thực hiện, lý do, thay đổi; chỉ thêm mới (BR1) | **Phân biệt từng lần lấy / giao lại / thay Shipper** (UC03.2 bước 5, BR2): mỗi mốc mang nhãn "Lần giao N", "Lần lấy N", "Đổi Shipper"; thông báo **"Chưa phát sinh vận chuyển"** khi mới tạo / duyệt (A1) |
| Thời gian theo giờ Việt Nam ở mọi màn (`formatDateTime`) | — (đã đạt BR2 về múi giờ; có test) |

**Ngoài phạm vi:** tra cứu công khai không đăng nhập (BR2, checklist); vị trí / bản đồ (spec 011).

## 2. Quyết định cần chốt

### Rà soát đầu vào Phase 0 (23/11/2026)

Đã đối chiếu UC03.1–03.2, `shipments_visible_to`, serializer và component lịch sử hiện có:

- `ShipmentEventSerializer.actor` đang dùng serializer chung có `id`, `username`, `full_name`;
  UI chỉ hiện tên. D6 cần chốt giới hạn **cả payload API và giao diện**, không chỉ phần hiển thị.
- `Task.attempt_no` chỉ dành cho giao; nhiệm vụ lấy không có số lần đã lưu. D3 cần số thứ tự lấy
  tính trên toàn bộ nhiệm vụ lấy của đơn, ổn định theo `(assigned_at, id)`, không đếm trên một trang lịch sử.
  Nhiệm vụ giao thay thế từ spec 009 giữ `attempt_no` cũ, không được tăng số lần theo số Task.
- D4 phải xét toàn bộ lịch sử của đơn, không suy ra từ riêng trang đang xem; một trang chỉ có mốc tạo/duyệt
  chưa đủ kết luận đơn chưa phát sinh vận chuyển.
- `ShipmentSummarySerializer` chưa có `updated_at`. Kết quả lookup cần bổ sung trường này để đáp ứng D2;
  tái sử dụng serializer hiện có qua mở rộng riêng cho lookup, không cần đổi schema database.
- D1 nên chuẩn hóa bằng cắt khoảng trắng **đầu/cuối** rồi đổi chữ hoa, so sánh đúng mã;
  không tự xóa khoảng trắng giữa mã hay chuyển thành tìm gần đúng. D5 cần thêm `id` làm khóa phụ khi thời gian trùng.

Các điểm trên được dùng làm phương án triển khai khi người dùng yêu cầu tiếp tục Phase 1.
Làm rõ D3: `pickup_no` là số **đợt nhiệm vụ lấy** (kể cả bản ghi thay người), không phải bộ đếm lần giao;
giữ nguyên `attempt_no` của nhiệm vụ giao khi thay người. Backend tính số lấy toàn đơn, không sửa DB.

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **Tra cứu theo mã** (UC03.1 bước 3–5) | `GET /shipments/lookup/?code=…` — khớp **đúng** mã vận đơn **hoặc** mã yêu cầu, không phân biệt hoa thường, bỏ khoảng trắng. Chỉ tìm trong phạm vi được xem (`shipments_visible_to`): đơn Shop khác trả **404 giống hệt** mã không tồn tại (không lộ "có nhưng không phải của bạn" — BR2). Mã rỗng / quá dài → `400` (E1). |
| D2 | **Màn hình tra cứu** | Trang `/tracking` cho **Shop và Nhân viên** (Shipper không — UC03.1 tác nhân), mục menu "Tra cứu vận đơn". Một ô nhập mã + nút Tra cứu; kết quả: mã, trạng thái, Shop (NV), người nhận, ngày tạo, cập nhật gần nhất + nút **"Xem chi tiết"** (màn chi tiết sẵn có theo vai trò) và **"Lịch sử vận chuyển"** (cuộn tới khối lịch sử). Mã trên URL (`?code=`) để chia sẻ / quay lại. |
| D3 | **Phân biệt lần lấy / giao / đổi người** (UC03.2 bước 5, BR2) | API lịch sử trả thêm `task` = `{id, type, attempt_no}` cho mốc gắn nhiệm vụ (đã có `ShipmentEvent.task` từ spec 006). Giao diện: nhãn **"Lần giao N"** cho mốc nhiệm vụ giao; **"Lần lấy N"** đánh số theo thứ tự nhiệm vụ lấy của đơn; mốc đổi Shipper / bàn giao (spec 009) hiện nhãn **"Đổi Shipper"**. Không đổi dữ liệu đã lưu (BR1). |
| D4 | **Chưa phát sinh vận chuyển** (A1) | Khi lịch sử chỉ có tạo / sửa / hủy / duyệt / từ chối → dòng "Chưa phát sinh vận chuyển — mốc lấy hàng sẽ hiện khi Nhân viên phân công." |
| D5 | **Thứ tự** | Giữ **mới nhất trước** (như hiện nay — đọc trạng thái mới nhất ngay). Thêm nút chuyển "Cũ nhất trước" (đọc theo dòng thời gian — UC03.2 bước 4) bằng tham số `ordering`. |
| D6 | **Người xử lý trong lịch sử của Shop** | UC03.2 bước 4 yêu cầu hiện người xử lý cho cả Shop → **giữ** tên Nhân viên / Shipper như hiện nay; **không** hiện SĐT hay tài khoản nội bộ (hiện đã không hiện). Trả lời câu hỏi treo từ spec 008. |
| D7 | **Dữ liệu** | Không bảng / cột mới: tra cứu dùng 2 cột `unique` sẵn có (`tracking_code`, `request_code` — tìm đúng nên dùng được index; kiểm `EXPLAIN` với tìm không phân biệt hoa thường — nếu không dùng index thì chuẩn hóa mã về chữ hoa trước khi tìm, vì mã luôn được sinh chữ hoa). |

## 3. Backend

- `ShipmentLookupView` (`GET /shipments/lookup/`): `HasRole.of(SHOP, ADMIN)`; query serializer (`code` 1..`SEARCH_QUERY_MAX_LENGTH`);
  trim đầu/cuối rồi uppercase, giữ khoảng trắng giữa; trả `ShipmentLookupSerializer` kế thừa summary + `updated_at` hoặc cùng 404.
- `queries.lookup_shipments`: chọn cột unique theo prefix YC/HTT, scalar subquery tìm pk bằng index mã,
  truy vấn ngoài vẫn giới hạn `shipments_visible_to`. Không trả dữ liệu từ bước chưa lọc quyền.
- `ShipmentEventSerializer`: thêm `task` (`id`, `type`, `attempt_no`, `pickup_no`) — queryset `select_related("actor", "task")`;
  số đợt lấy tính một query toàn đơn, không N+1. Shop nhận actor `{id, full_name}`, NV giữ `{id,username,full_name}`.
- `GET …/events/?ordering=created_at|-created_at` mặc định mới nhất trước, thêm khóa phụ id cùng chiều;
  rỗng/giá trị lạ trả 400. Metadata phân trang thêm `has_transport_activity` xét toàn đơn.
- Không model/cột/index/migration mới. Hợp đồng chi tiết và ví dụ: [api.md](api.md).

## 4. Frontend

| Chỗ | Thay đổi |
|---|---|
| `views/common/TrackingView.vue` (mới) | Ô mã, kết quả tóm tắt, nút xem chi tiết / lịch sử; trạng thái ban đầu/loading/không thấy/lỗi; giữ mã để thử lại, query URL khôi phục khi quay lại; phản hồi cũ không đè mã mới. |
| `router` + `roles.js` | Route `/tracking` (Shop, NV), mục menu "Tra cứu vận đơn". |
| `ShipmentEventList` | Dùng `task.pickup_no`, `task.attempt_no`, action đổi người để gắn nhãn; `has_transport_activity` cho "Chưa phát sinh vận chuyển"; select đổi thứ tự, về trang 1. Link lịch sử tới `#shipment-history`, chờ tải rồi cuộn với khoảng trống topbar. |
| `shipmentService` | `lookup(code)`, `events(id, {page, ordering})`. |

## 5. Tiêu chí nghiệm thu

- [x] Tra cứu đúng mã vận đơn / mã yêu cầu (không phân biệt hoa thường, bỏ khoảng trắng đầu/cuối); Shop chỉ thấy đơn mình — đơn Shop khác và mã không tồn tại trả **cùng** `404`; Shipper không gọi được; mã rỗng → `400`.
- [x] Màn tra cứu: kết quả tóm tắt + nút chi tiết / lịch sử; không thấy (A1); lỗi mạng (E1) giữ mã đã nhập để thử lại.
- [x] Lịch sử: nhãn "Lần giao N", "Lần lấy N", "Đổi Shipper"; "Chưa phát sinh vận chuyển" khi mới tạo / duyệt; đổi thứ tự được; không N+1.
- [x] `EXPLAIN` tra cứu dùng index mã trên cột unique hiện có (PostgreSQL chọn index `_like` cho phép equality;
  không tuyên bố đó là index unique riêng). Cả hai vai trò/hai loại mã đã đo, không ép planner, không thêm index.
- [ ] Frontend: Vitest pass, build, ảnh chụp 1440/390, thử trình duyệt theo `manual-test.md`.

Kiểm tra tự động/frontend/build/ảnh đã đạt; tiêu chí cuối giữ mở cho phần người dùng tự thử.
Kết quả và giới hạn: [acceptance.md](acceptance.md) · [hướng dẫn thử](manual-test.md).

## 6. Ghi chú cho spec sau

**Đầu vào spec 009 đã triển khai/kiểm tự động (23/11/2026):** có 5 hành động đổi người/bàn giao/nhận về,
`ShipmentEvent.task` và `tasks[].replaced_by`/`swap_candidate` trên chi tiết NV. Không tạo TaskResult cho nhiệm vụ
bị thay; nhiệm vụ giao thay thế giữ `attempt_no`, nên không đánh số lần giao theo số bản ghi Task.
**Cập nhật Phase 1–2 spec 010:** API `/events/` đã trả metadata task/pickup_no, actor Shop không còn username;
NV vẫn giữ cấu trúc actor cũ. Frontend đã dùng `has_transport_activity` thay vì tự đoán từ trang đang xem,
`pickup_no` cho lần lấy và `attempt_no` cho lần giao; không đếm lại theo số bản ghi Task.

- **Spec 011:** nút "Theo dõi vị trí" đặt cạnh kết quả tra cứu / chi tiết đơn khi đơn đang có nhiệm vụ hoạt động.
