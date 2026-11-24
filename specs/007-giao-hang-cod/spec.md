# Spec 007 — Giao hàng, COD, giao lại

Trạng thái: **Đã triển khai (22/11/2026)** — chờ người dùng thử trình duyệt ([manual-test.md](manual-test.md)). D1–D11 theo đề xuất, chốt 22/11/2026. Ngày lập: 22/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md) · [manual-test.md](manual-test.md)

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC06.6, UC04.4–04.7, UC04.12.
- [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md): mục 2.3 (Shipper), 3, 5, 6.
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): các UC trên, mục 4 (bảng trạng thái), COD, giới hạn 3 lần giao, thông báo, đồng thời, thao tác lặp.
- Nền:
  - [spec 001](../001-nen-tang/spec.md): mục 3 (bảng trạng thái, `MAX_DELIVERY_ATTEMPTS = 3`, quy ước đồng thời/gửi lại), mục 6 (`TaskResult.cod_expected` / `cod_collected`, số lần giao).
  - [spec 006](../006-lay-hang-diem-tap-ket/spec.md): toàn bộ khung `Task` / `TaskResult`, màn Shipper, hộp phân công, `check_staff_action`; mục 6 "Ghi chú cho spec 007".

## 1. Mục tiêu và phạm vi

Đưa đơn từ **điểm tập kết** tới **người nhận**, ghi **COD** đúng một lần cùng kết quả giao, và xử lý **giao thất bại** (giao lại tối đa 3 lần hoặc chuyển hoàn). Sau spec này đạt **cột mốc demo "giao thành công"** (specs/README).

```
Đã nhập điểm tập kết ──phân công giao (NV)──► Đang giao hàng ──Shipper giao được + COD khớp──► Đã giao hàng
          ▲                                     │
          │                                     └──Shipper giao thất bại (lần +1)──► Giao hàng thất bại
          │                                                                       ├──NV: giao lại (lần < 3)──► Chờ giao lại ──phân công giao──┐
          │                                                                       └──NV: hoàn (bất kỳ lần nào; lần 3 thì bắt buộc)──► Chờ xử lý hoàn (spec 008)
          └──────────────────────────────────────────────────── (Chờ giao lại cũng phân công được) ──────────────────────┘
```

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC06.6 | Phân công Shipper giao hàng | Toàn bộ trừ A2:<br>- lần đầu chỉ từ Đã nhập điểm tập kết (BR1); giao lại chỉ từ Chờ giao lại, số lần < 3;<br>- chỉ Shipper hoạt động; không hai nhiệm vụ mở;<br>- không tăng số lần khi phân công;<br>- thông báo Shipper + Shop;<br>- A1 giao lại bằng Shipper cũ còn giữ hàng; E1 các điều kiện chưa đạt.<br>**A2** (đổi Shipper khi người cũ còn giữ hàng) → spec 009 (UC06.8), xem D7. |
| UC04.4 | Xem nhiệm vụ giao hàng | Toàn bộ: người nhận, địa chỉ, COD, số lần đã giao; A1 trống; E1 đã thu hồi → không còn khả dụng; BR2 thông tin liên hệ chỉ dùng cho nhiệm vụ (D3). |
| UC04.5 | Xác nhận giao thành công | Toàn bộ: COD thực thu = phải thu; ghi kết quả + COD + thời gian + số lần trong **một transaction**; Đã giao hàng; báo Shop; A1 không COD; E1 lệch → không lưu gì; BR2 gửi lại không cộng tiền/lần. "Dừng chia sẻ vị trí" (bước 7) → spec 011. |
| UC04.6 | Cập nhật giao thất bại | Toàn bộ: lý do bắt buộc; tăng số lần **đúng một lần**; đóng nhiệm vụ; Giao hàng thất bại; Shipper vẫn giữ hàng; báo Nhân viên + Shop; A1 lần 3 → chỉ được hoàn; E1 gửi lại không tăng trùng. |
| UC04.7 | Ghi nhận COD | Là một phần của UC04.5 (BR3): VND, không âm, bằng phải thu; không thu một phần, đối soát, nộp tiền (BR1); không sửa số phải thu (BR2). |
| UC04.12 | Quyết định giao lại / hoàn | Toàn bộ: Giao lại (số lần < 3) → Chờ giao lại; Hoàn (sớm hoặc bắt buộc ở lần 3) → Chờ xử lý hoàn; lý do bắt buộc; E1 giao lại khi đủ 3 lần → từ chối. **Phân công hoàn** (UC06.7) → spec 008. |

**Ngoài phạm vi:**
- Phân công hoàn, nhận hàng hoàn, Shop nhận lại: spec 008.
- Đổi Shipper khi đang giữ hàng (UC06.6 A2, UC06.8): spec 009.
- Chia sẻ vị trí / bản đồ: spec 011.
- Đối soát COD, Shipper nộp tiền, trả tiền Shop, doanh thu (UC04.7 BR1–BR2): không có trong đặc tả.
- Ảnh chụp / chữ ký người nhận: không có trong đặc tả.

## 2. Quyết định cần chốt

**Đã chốt 22/11/2026: cả 11 điểm theo đề xuất** — hỏi riêng và xác nhận D3 (ẩn SĐT ở **cả hai** loại nhiệm vụ), D5 (Shipper tự gõ COD, ô để trống), D7 (giao lại chỉ Shipper đang giữ hàng; đổi người ở spec 009).

Kiểm tra khi chốt (đối chiếu code 22/11/2026):
- `ASSIGN_DELIVERY`, `CONFIRM_DELIVERY`, `FAIL_DELIVERY`, `DECIDE_REDELIVERY`, `DECIDE_RETURN` đã có trong `SHIPMENT_TRANSITIONS`; `TASK_SUCCEED` / `TASK_FAIL` đã nhận loại DELIVERY.
- `Shipment.delivery_attempts`, `Task.attempt_no` (CHECK chỉ DELIVERY), `MAX_DELIVERY_ATTEMPTS = 3`, `HolderType.RECIPIENT`, `ErrorCode.LIMIT_REACHED`, `NotificationKind.DELIVERED / DELIVERY_FAILED / RETURN_DECIDED` đã có.
- `TaskResult.reason_code` hiện chỉ nhận `PickupFailReason` → cần mở rộng (D1, D4).
- Spec 006 đã có test chặn thao tác **lấy hàng** trên nhiệm vụ GIAO — giữ nguyên, thêm chiều ngược lại.
- **Lệch so với bản nháp, đã sửa khi chốt:**
  - `GET /dispatch/tasks/` **đã có** `type` từ spec 006 (mặc định `PICKUP`) → spec này chỉ **đổi mặc định thành tất cả**, không thêm tham số.
  - `PickupFailReason` đã dùng mã `WRONG_ADDRESS` → lý do giao dùng `ADDRESS_NOT_FOUND` (tránh một mã hai nhãn). `OTHER` dùng chung vì cùng nhãn "Khác".

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **Mô hình dữ liệu** | Dùng lại `Task(type=DELIVERY)` và `TaskResult`, không tạo bảng mới:<br>- `TaskResult` thêm `cod_expected`, `cod_collected` (VND, null với nhiệm vụ lấy và giao thất bại).<br>- CHECK DB: hai cột cùng null hoặc cùng có; có thì `outcome = SUCCEEDED` **và** `cod_collected = cod_expected` (lớp chặn cuối cho "không thu một phần").<br>- `reason_code` nhận lý do lấy **hoặc** giao (D4); serializer kiểm đúng nhóm theo loại nhiệm vụ.<br>- `Shipment` thêm CHECK `delivery_attempts ≤ 3`.<br>- **Số lần:** phân công ghi `Task.attempt_no = delivery_attempts + 1` (chưa tăng — UC06.6); ghi kết quả (thành công hoặc thất bại) đặt `delivery_attempts = attempt_no` → gửi lại không bao giờ tăng trùng. |
| D2 | **API** | Cùng khuôn spec 006:<br>- Nhân viên trên **đơn**: `/shipments/{id}/assign-delivery/`, `decide-redelivery/`, `decide-return/` (gửi `updated_at`, `409`).<br>- Shipper trên **nhiệm vụ**: `/dispatch/tasks/{id}/confirm-delivery/`, `fail-delivery/`.<br>- `GET /dispatch/tasks/`: `type` (đã có) đổi mặc định thành tất cả. |
| D3 | **Shipper thấy gì ở nhiệm vụ giao** (UC04.4, BR2) | Mã vận đơn; **người nhận** (tên, SĐT), địa chỉ giao; **COD phải thu**; mô tả hàng, số kiện, khối lượng; ghi chú; tên Shop; **lần giao N/3**.<br>**Không** hiện SĐT người gửi / địa chỉ lấy (không cần khi giao).<br>**Nhiệm vụ đã đóng: ẩn SĐT người nhận** (BR2 — chỉ dùng khi đang làm nhiệm vụ). Áp dụng luôn cho nhiệm vụ lấy (ẩn SĐT người gửi khi đã đóng) để hai loại cùng quy tắc — thay đổi nhỏ so với spec 006. |
| D4 | **Lý do giao thất bại** (UC04.6 bước 3) | Danh mục cố định `DeliveryFailReason` (nhãn từ `/meta/choices/`):<br>- Không liên hệ được người nhận;<br>- Người nhận hẹn giao lại;<br>- Người nhận từ chối nhận;<br>- Người nhận chưa đủ tiền COD;<br>- Sai / không tìm thấy địa chỉ;<br>- **Khác**.<br>Ghi chú tùy chọn, **bắt buộc khi Khác**, ≤ 500 ký tự (dùng lại `task_note_max_length`). |
| D5 | **Nhập COD** (UC04.5 bước 3, UC04.7) | - Đơn có COD: hộp "Giao thành công" hiện **COD phải thu thật to**; Shipper **phải tự gõ** số thực thu (ô để trống, không điền sẵn) để buộc đếm tiền. Lệch → `400`, `fields.cod_collected` nói rõ **thiếu / thừa bao nhiêu** (E1.1); không lưu gì.<br>- Đơn không COD (A1): không có ô nhập, hộp ghi "Đơn không thu COD", gửi lên 0.<br>- Hộp xác nhận nêu mã, tên người nhận, số tiền: "Người nhận đã nhận hàng".<br>- Nút phụ "Chưa thu đủ? Ghi giao thất bại" mở hộp thất bại chọn sẵn lý do "chưa đủ tiền COD" (E1.3). |
| D6 | **Người giữ hàng** | - Phân công giao: Nhân viên giao hàng cho Shipper tại điểm tập kết → hộp phân công có ô **"Shipper đã nhận hàng"** bắt buộc tích (UC06.6 bước 3–4); sau đó `holder = SHIPPER` (người được giao). Không tạo `Handover` (bảng đó ghi hàng **vào** điểm tập kết).<br>- Giao thành công → `holder = RECIPIENT`.<br>- Giao thất bại → **giữ** `SHIPPER` (UC04.6 bước 7). |
| D7 | **Giao lại và đổi Shipper** (UC06.6 A1/A2) | Chờ giao lại mà hàng đang ở Shipper X:<br>- chỉ phân công được **chính X** (A1) — hộp phân công chọn sẵn X, khóa chọn người khác;<br>- chọn người khác → `409` "Hàng đang ở {X}. Muốn đổi người cần bàn giao về điểm tập kết (đổi Shipper)" — làm ở spec 009.<br>X bị khóa → đơn chờ spec 009 (đã có cảnh báo `needs_attention` từ spec 006 cho nhiệm vụ mở; đơn Chờ giao lại không còn nhiệm vụ mở → **thêm** cảnh báo "Shipper giữ hàng đã bị khóa" trên chi tiết đơn). |
| D8 | **Giới hạn 3 lần** (BR1 các UC) | - Lần thất bại thứ 3: `allowed_actions` của Nhân viên chỉ còn **Hoàn**; màn hình ghi "Đã giao 3/3 lần — chỉ được hoàn" (UC04.6 A1).<br>- Giao lại / phân công khi đã 3 lần → `409 LIMIT_REACHED` (kiểm cả ở service dù bảng trạng thái đã chặn — phòng dữ liệu cũ).<br>- Lần thành công cũng tính lần (UC04.12 BR1). |
| D9 | **Quyết định giao lại / hoàn** (UC04.12) | Cả hai **lý do bắt buộc** (1–500 ký tự), hộp xác nhận; dùng lại hộp lý do của "Lấy lại / Kết thúc" spec 006.<br>Hộp hiện: lý do lần thất bại gần nhất, danh sách các lần giao (Shipper, kết quả, lý do, thời gian), số lần N/3, người đang giữ hàng (bước 2).<br>Hoàn sớm được ở mọi lần (A1.2); không tự tạo nhiệm vụ hoàn (BR2). |
| D10 | **Thông báo** (kèm `shipment_id`, + `task_id` cho Shipper) | - Phân công giao → **Shipper** (`TASK_ASSIGNED`) + **Shop** (loại mới `OUT_FOR_DELIVERY` "Đơn đang được giao").<br>- Giao thành công → **Shop** (`DELIVERED`, nêu COD đã thu nếu có).<br>- Giao thất bại → **Shop** + **mọi Nhân viên đang hoạt động** (`DELIVERY_FAILED`, nêu lần N/3).<br>- Giao lại → **Shop** (loại mới `REDELIVERY_SCHEDULED` "Sẽ giao lại").<br>- Hoàn → **Shop** (`RETURN_DECIDED`). |
| D11 | **Màn hình** | **Shipper:** menu "Nhiệm vụ lấy hàng" → **"Nhiệm vụ"**; danh sách thêm bộ lọc loại **Tất cả · Lấy hàng · Giao hàng** (thẻ có nhãn loại); chi tiết giao có nút gọi người nhận, COD nổi bật, "Giao thành công" / "Giao thất bại"; trang chủ tách ô "lấy" / "giao".<br>**Nhân viên:** thêm tab **Đã nhập điểm tập kết · Chờ giao lại · Giao thất bại** (mỗi tab một trạng thái, dùng `status` sẵn có — không đổi API danh sách); nút Phân công giao / Giao lại / Hoàn theo `allowed_actions`; thẻ Điều phối hiện "Lần giao N/3" và các lần giao kèm COD.<br>**Shop:** chi tiết đơn Đã giao hiện thời gian giao và **COD đã thu**. |

## 3. Backend

### 3.1. Model

Chi tiết: [models.md](models.md).
- `TaskResult`: thêm `cod_expected`, `cod_collected`; `reason_code` mở rộng nhóm; CHECK COD (D1).
- `Shipment`: CHECK `delivery_attempts BETWEEN 0 AND MAX_DELIVERY_ATTEMPTS`.
- Enum mới `DeliveryFailReason`; `NotificationKind` thêm `OUT_FOR_DELIVERY`, `REDELIVERY_SCHEDULED` (migration đổi `choices`, SQL rỗng — bài học spec 006).

### 3.2. Service (`dispatch/services.py`)

Theo quy ước spec 001 mục 3.6 như spec 006: khóa **đơn** → **user / nhiệm vụ**; kiểm "đã xong" (gửi lại) → trạng thái → `updated_at`; một transaction. Dùng lại `check_staff_action`, `_close_task`, `_already_recorded`, `notify`.

| Hàm | Việc làm |
|---|---|
| `assign_delivery(staff, shipment_id, shipper_id, expected_updated_at)` | 1. `ASSIGN_DELIVERY`; `delivery_attempts < 3` (khác → `LIMIT_REACHED`).<br>2. Shipper hoạt động (khóa dòng user — `_lock_available_shipper` dùng chung với `assign_pickup`). `handed_over = true` kiểm ở serializer.<br>3. Chờ giao lại + `holder = SHIPPER` → chỉ người đang giữ (D7).<br>4. Tạo `Task(DELIVERY, attempt_no = attempts + 1)`; đơn `OUT_FOR_DELIVERY`, `holder = SHIPPER`.<br>5. Lịch sử + thông báo Shipper, Shop. Partial unique vẫn là lớp chặn trùng cuối. |
| `confirm_delivery(shipper, task_id, cod_collected)` | 1. Nhiệm vụ của mình, `DELIVERY`, `ACTIVE`; đã `SUCCEEDED` → trả hiện tại, **không** kiểm lại tiền / tăng lần (BR2).<br>2. `cod_collected == shipment.cod_amount` (khác → `400` chỉ rõ chênh lệch).<br>3. `TaskResult(SUCCEEDED, cod_expected, cod_collected)`, `delivery_attempts = attempt_no`, đơn `DELIVERED`, `holder = RECIPIENT`, báo Shop. |
| `fail_delivery(shipper, task_id, reason_code, note)` | `TASK_FAIL` + `FAIL_DELIVERY`: `TaskResult(FAILED, lý do)`, `delivery_attempts = attempt_no`, đơn `DELIVERY_FAILED`, holder giữ Shipper, báo Shop + Nhân viên. Gửi lại khi đã `FAILED` → trả hiện tại. |
| `decide_redelivery(staff, shipment_id, reason, expected_updated_at)` | `DECIDE_REDELIVERY` khi `delivery_attempts < 3` (khác → `LIMIT_REACHED`); đơn `AWAITING_REDELIVERY`; báo Shop. |
| `decide_return(staff, shipment_id, reason, expected_updated_at)` | `DECIDE_RETURN` → `AWAITING_RETURN`; báo Shop (`RETURN_DECIDED`). |

`allowed_actions` của đơn (Nhân viên) cần lọc thêm theo số lần: `DECIDE_REDELIVERY` / `ASSIGN_DELIVERY` ẩn khi đã 3 lần (D8). Làm bằng **một bảng điều kiện phụ** cạnh `SHIPMENT_TRANSITIONS` (hành động → hàm kiểm), không viết `if` rải rác trong serializer. → Đã làm: `shipments/rules.py` (`SHIPMENT_ACTION_GUARDS`, `shipment_allowed_actions`, `has_delivery_attempts_left`) — dùng cho cả nút (chi tiết đơn, chi tiết nhiệm vụ) lẫn service.

### 3.3. Phạm vi dữ liệu và quyền

- Không đổi `shipments_visible_to` / `tasks_visible_to` (spec 006 đã có nhánh SHIPPER).
- Serializer chi tiết nhiệm vụ chọn theo loại: `PickupShipmentDetailSerializer` (đã có) / `DeliveryShipmentDetailSerializer` (mới, D3). Ẩn SĐT khi nhiệm vụ đã đóng ở **cả hai**.
- `TaskSummarySerializer` (chi tiết đơn của Nhân viên) thêm `attempt_no`; `TaskResultSerializer` thêm `cod_expected`, `cod_collected`.
- Chi tiết đơn của Nhân viên thêm `holder_locked` (Shipper đang giữ hàng đã bị khóa — D7).
- Chi tiết đơn thêm `delivery` = `{delivered_at, cod_collected, attempt_no}` khi Đã giao — **mọi vai trò** xem được đơn (Shop cần nhất; NV dùng luôn). Một truy vấn, chỉ khi Đã giao (cùng cách `rejection_reason`); không lộ Shipper/nhiệm vụ.

## 4. Frontend

| Route | View | Vai trò | Thay đổi |
|---|---|---|---|
| `/shipper/tasks` | `TaskListView.vue` (sửa) | SHIPPER | Bộ lọc loại (query `type`), nhãn loại trên thẻ, thẻ giao hiện người nhận + COD + lần N/3. |
| `/shipper/tasks/:id` | `TaskDetailView.vue` (sửa) | SHIPPER | Khối thông tin theo loại; giao: gọi người nhận, COD nổi bật, "Giao thành công" (hộp COD), "Giao thất bại" (lý do + ghi chú). Tách 2 khối thao tác thành component con nếu file quá dài. |
| `/staff/shipments` | (sửa) | ADMIN | 3 tab mới (D11). |
| `/staff/shipments/:id` | (sửa) | ADMIN | Thêm vào bảng `ACTION_BUTTONS`: Phân công giao (dùng lại `ShipperPicker` + ô "đã nhận hàng"; giao lại thì khóa người giữ), Giao lại / Hoàn (dùng lại `REASON_DIALOGS`). Thẻ Điều phối: lần N/3, các lần giao, COD. |
| `/shop/shipments/:id` | (sửa) | SHOP | Khối "Đã giao": thời gian, COD đã thu. |

- Mã mới vào `shipmentActions.js` (`SHIPMENT_ACTION`, `DELIVERY_FAIL_REASON`, `TASK_TYPE` nếu cần) kèm test đối chiếu backend.
- Component mới `components/dispatch/CodInput.vue` (D5); `ShipperPicker` thêm prop `holder` (D7). `utils/format.js` thêm `formatNumber`.
- COD hiển thị bằng `formatVnd` sẵn có; giới hạn từ `meta.limits`.
- Ảnh chụp 390px cho màn Shipper là bắt buộc (dùng chủ yếu trên điện thoại).

## 5. Tiêu chí nghiệm thu

**11/12 đạt** — bằng chứng: `apps/dispatch/tests/test_delivery_models.py`, `test_staff_delivery.py`, `test_shipper_delivery.py` (60 test, gồm 4 test song song thật + 1 test thứ tự khóa), đột biến có mốc (backend 8/8, 14/14, 17/17; frontend 14/14, 17/18 — 1 tương đương), `EXPLAIN`, smoke 19/19; xem nhật ký [tasks.md](tasks.md).

- [x] Phân công giao: lần đầu chỉ từ Đã nhập điểm tập kết; giao lại chỉ từ Chờ giao lại khi < 3 lần; Shipper hoạt động; không hai nhiệm vụ mở; **không tăng số lần**; Shipper giữ hàng; báo Shipper + Shop.
- [x] Giao lại khi hàng ở Shipper X → chỉ phân công X; người khác → `409` (D7).
- [x] Shipper thấy người nhận / địa chỉ / COD / lần N/3 ở nhiệm vụ giao của mình; nhiệm vụ người khác → `404`; nhiệm vụ đã đóng ẩn SĐT (D3).
- [x] Giao thành công: COD khớp → Đã giao, người nhận giữ hàng, số lần = lần của nhiệm vụ, `TaskResult` có COD, báo Shop — **một transaction**; COD lệch → `400` nêu chênh lệch, **không ghi gì**; không COD → 0.
- [x] CHECK DB chặn kết quả có COD lệch / COD trên kết quả thất bại (đột biến trên migration).
- [x] Giao thất bại: lý do bắt buộc (Khác → ghi chú); số lần +1 đúng một lần; Shipper vẫn giữ hàng; báo Shop + Nhân viên.
- [x] Gửi lại (thành công / thất bại) → trả hiện tại, **không cộng tiền, không tăng lần**; kết quả ngược loại trên nhiệm vụ đã đóng → `409`.
- [x] Lần 3 thất bại → chỉ còn Hoàn; giao lại / phân công → `LIMIT_REACHED`; lần thành công cũng tính.
- [x] Giao lại / Hoàn: lý do bắt buộc, lịch sử giữ đủ các lần, báo Shop; hoàn sớm được.
- [x] Đồng thời (test 2 luồng thật): 2 NV cùng phân công giao → 1 nhiệm vụ; Shipper xác nhận giao vs NV thao tác khác; 2 lần gửi xác nhận song song → 1 kết quả, số lần +1.
- [x] Bảng chuyển trạng thái vẫn khớp checklist; không N+1; `EXPLAIN` danh sách nhiệm vụ lọc `type`, tab Nhân viên mới.
- [ ] Frontend: Vitest pass, build, ảnh chụp 1440/390, một lượt bấm thật NV phân công giao → Shipper giao thành công có COD; thử trình duyệt theo `manual-test.md`. → Vitest 292 + build ✔, ảnh chụp 1440/390, lượt bấm thật 9/9; **còn người dùng thử** ([manual-test.md](manual-test.md), 41 bước).

## 6. Ghi chú cho spec sau

- **Spec 008:** `ASSIGN_RETURN` từ Chờ xử lý hoàn — hàng có thể còn ở Shipper (giao thất bại) hoặc ở điểm tập kết; `RECEIVE_RETURN` thêm `HandoverKind`. Nhiệm vụ loại RETURN dùng lại khung nhiệm vụ / màn Shipper của 006–007.
  - Chỗ cần thêm loại RETURN (đã khai dạng bảng): backend `TASK_SHIPMENT_VIEWS` (serializer Shipper), `FAIL_REASONS_BY_TASK_TYPE` (RETURN không thất bại — giữ nguyên); frontend `TYPE_VIEW` (`TaskDetailView`), `TASK_TYPE`, chip lọc danh sách tự thêm theo `TASK_TYPE`.
  - Chờ xử lý hoàn hiện đã trả `allowed_actions` = `ASSIGN_RETURN`, `RECEIVE_RETURN` (bảng trạng thái có sẵn) nhưng màn NV chưa có nút — thêm vào `ACTION_BUTTONS`.
- **Spec 009:** UC06.6 A2 — đổi Shipper khi người cũ còn giữ hàng (bàn giao về điểm tập kết, rồi mới phân công người mới); `attempt_no` của nhiệm vụ thay thế **giữ nguyên** (đổi người không cấp thêm lượt, UC04.6 BR1, UC06.6 BR2). Gỡ cảnh báo "Shipper giữ hàng đã bị khóa" (D7).
  - **Đã xử lý 23/11/2026:** đổi nhiệm vụ giao qua trạng thái Chờ bàn giao; người cũ mất giao/thất bại/COD;
    Nhân viên nhận thực tế rồi mới tạo nhiệm vụ cùng `attempt_no`. Khi Chờ giao lại mà không còn nhiệm vụ mở,
    dùng Nhận hàng về điểm tập kết, sau đó phân công người khác; hết `holder_locked`.
    Đã bấm thật đổi người ở lần 3, thất bại thứ 3 không có giao lại/lần 4; chỉ chuyển hoàn.
  - CHECK `task_attempt_matches_type` bắt nhiệm vụ GIAO luôn có `attempt_no` 1..3 → nhiệm vụ thay thế phải chép `attempt_no` của nhiệm vụ cũ.
  - Đổi Shipper trên đơn Đang giao: khóa ĐƠN trước NHIỆM VỤ (đã có test kiểm thứ tự khóa phía Shipper).
- **Spec 011:** dừng chia sẻ vị trí khi nhiệm vụ giao đóng (UC04.5 bước 7).

**Việc có từ trước, không thuộc spec này (ghi lại khi nghiệm thu):** 16 cảnh báo Vue Router trong output test màn tài khoản (spec 003: `onBeforeRouteLeave` khi mount không có `<RouterView>`) và `navActive`; trình duyệt báo 404 `favicon.ico` (dự án chưa có favicon).
