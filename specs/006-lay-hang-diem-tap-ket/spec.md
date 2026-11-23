# Spec 006 — Lấy hàng và nhập điểm tập kết

Trạng thái: **Đã triển khai (22/11/2026)** — chờ người dùng thử trình duyệt ([manual-test.md](manual-test.md)). D1–D10 theo đề xuất, chốt 22/11/2026. Ngày lập: 22/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md) · [manual-test.md](manual-test.md)

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC06.5, UC04.1–04.3, UC04.10, UC04.13.
- [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md): mục 2.3 (Shipper), 3, 5 (quy tắc 2, 4, 5, 6, 8), 6.
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): các UC trên, mục 4 (bảng trạng thái), thông báo, đồng thời, thao tác lặp, kịch bản "Lấy thất bại".
- Nền:
  - [spec 001](../001-nen-tang/spec.md): mục 3 (bảng trạng thái vận đơn + nhiệm vụ, quy ước đồng thời/gửi lại), mục 6 (thiết kế `Task`, `TaskResult`, `Handover`).
  - [spec 003](../003-quan-ly-tai-khoan/spec.md): khóa Shipper còn nhiệm vụ mở.
  - [spec 005](../005-duyet-van-don/spec.md): màn Nhân viên, `allowed_actions`, mục 6 "Ghi chú cho spec sau".

## 1. Mục tiêu và phạm vi

Đưa vận đơn đã duyệt đi qua bước **lấy hàng** tới **điểm tập kết**. Đây là spec đầu tiên có nghiệp vụ cho **Shipper** và có bảng **nhiệm vụ** (`Task`); spec 007–009 dùng lại toàn bộ khung này.

```
Chờ lấy hàng ──phân công (NV)──► Đã phân công lấy hàng ──Shipper lấy được──► Đã lấy hàng ──NV nhận tại điểm tập kết──► Đã nhập điểm tập kết
      ▲                                    │                                                                          (spec 007 giao tiếp)
      │                                    └──Shipper lấy thất bại──► Lấy hàng thất bại ──NV: lấy lại──┘
      │                                                                     └──NV: kết thúc──► Kết thúc do không lấy được hàng
      └───────────────────────────────── (lấy lại) ─────────────────────────┘
```

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC06.5 | Phân công Shipper lấy hàng | Toàn bộ:<br>- chỉ đơn Chờ lấy hàng;<br>- chỉ Shipper hoạt động;<br>- không tạo nhiệm vụ lấy trùng;<br>- thông báo Shipper;<br>- A1 không có Shipper phù hợp; E1 Shipper vừa bị khóa / đơn đã được phân công. |
| UC04.1 | Xem nhiệm vụ lấy hàng | Toàn bộ:<br>- Shipper chỉ thấy nhiệm vụ của mình;<br>- A1 danh sách trống + tải lại;<br>- E1 nhiệm vụ đã chuyển người khác. |
| UC04.2 | Xác nhận lấy hàng thành công | Toàn bộ:<br>- hộp xác nhận;<br>- ghi người giữ hàng;<br>- thông báo Shop;<br>- BR2 gửi lại không ghi trùng. |
| UC04.3 | Cập nhật lấy hàng thất bại | Toàn bộ:<br>- lý do bắt buộc + ghi chú;<br>- thông báo Nhân viên và Shop;<br>- A1 hủy biểu mẫu. |
| UC04.10 | Xác nhận nhập điểm tập kết | Toàn bộ:<br>- ghi người giao/nhận, thời gian;<br>- hàng ở điểm tập kết;<br>- E1 đã tiếp nhận / ghi sai lệch.<br>Không quản lý kho (BR2). |
| UC04.13 | Xử lý lấy hàng thất bại | Toàn bộ:<br>- Lấy lại → Chờ lấy hàng (phân công lại qua UC06.5);<br>- Kết thúc → Kết thúc do không lấy được hàng;<br>- lý do bắt buộc, thông báo Shop. |

**Bổ sung đã treo từ spec 003:** khóa Shipper đang có nhiệm vụ mở → đánh dấu nhiệm vụ cần chú ý và báo Nhân viên (D9). Việc **thay người** thuộc UC06.8 (spec 009).

**Ngoài phạm vi:**
- Phân công giao, giao hàng, COD, giao lại: spec 007.
- Hoàn hàng: spec 008.
- Đổi Shipper khi đang có nhiệm vụ mở: spec 009.
- GPS / bản đồ: spec 011.
- Ảnh chụp, chữ ký khi lấy hàng: không có trong đặc tả.

## 2. Quyết định cần chốt

**Đã chốt 22/11/2026: cả 10 điểm theo đề xuất**, D4 dùng đúng danh sách 6 lý do bên dưới.

Kiểm tra khi chốt:
- Hành động `ASSIGN_PICKUP`, `CONFIRM_PICKUP`, `FAIL_PICKUP`, `RETRY_PICKUP`, `ABANDON_PICKUP`, `RECEIVE_AT_HUB` đã có trong `SHIPMENT_TRANSITIONS`; `TASK_TRANSITIONS` đã có.
- D9: spec 003 đã chuẩn bị `register_account_locked_hook` (chạy trong transaction khóa tài khoản). `dispatch` đăng ký hook ở `AppConfig.ready()`, nên `accounts` không phải import `dispatch` (không phụ thuộc vòng). Khóa tài khoản đã `select_for_update` dòng user → phân công cũng khóa dòng user để hai việc không chạy chồng.
- App `dispatch` đã có trong `INSTALLED_APPS` và URL `/api/v1/dispatch/`.

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **Mô hình dữ liệu** | Làm đúng thiết kế spec 001 mục 6, không thiết kế lại:<br>- `Task` (nhiệm vụ của một Shipper trên một đơn);<br>- `TaskResult` (kết quả cuối, một-một với Task);<br>- `Handover` (bàn giao hàng tại điểm tập kết).<br>`ShipmentEvent` thêm `task` (FK null). **Ràng buộc DB:** mỗi đơn tối đa **một nhiệm vụ đang mở** (partial unique index) — lớp chặn cuối cho "không phân công trùng". |
| D2 | **API** | Hành động trên **đơn** của Nhân viên đặt cạnh duyệt/từ chối, cùng khuôn (`updated_at`, `409`):<br>`/shipments/{id}/assign-pickup/`, `receive-at-hub/`, `retry-pickup/`, `abandon-pickup/`.<br>Phía **Shipper** làm việc theo **nhiệm vụ**:<br>`/tasks/` (của mình), `/tasks/{id}/`, `/tasks/{id}/confirm-pickup/`, `/tasks/{id}/fail-pickup/`.<br>Shipper **không** dùng API vận đơn. |
| D3 | **Shipper thấy gì** (UC04.1, quyền tối thiểu) | Chỉ nhiệm vụ được giao cho mình (đang mở và đã đóng, mới nhất trước).<br>Chi tiết nhiệm vụ lấy gồm:<br>- mã vận đơn;<br>- Shop + người gửi (tên, SĐT);<br>- địa chỉ lấy;<br>- mô tả hàng, số kiện, khối lượng; ghi chú.<br>**Không** hiện người nhận, địa chỉ giao, COD — chưa cần khi đi lấy (sẽ hiện ở nhiệm vụ giao spec 007).<br>Nhiệm vụ đã chuyển người khác → `404` như không tồn tại. |
| D4 | **Lý do lấy thất bại** (UC04.3 "chọn hoặc nhập") | Danh mục cố định (enum, nhãn từ `/meta/choices/`):<br>- Shop vắng mặt / không liên lạc được;<br>- Hàng chưa sẵn sàng;<br>- Sai địa chỉ lấy;<br>- Shop không muốn gửi nữa;<br>- Hàng không đúng mô tả;<br>- **Khác**.<br>Ghi chú tùy chọn, **bắt buộc khi chọn Khác**, ≤ 500 ký tự. |
| D5 | **Xác nhận lấy được hàng** (UC04.2) | Hộp xác nhận nêu mã, Shop, số kiện, mô tả hàng: "Tôi đã nhận đủ hàng". Không ảnh/chữ ký.<br>Sau khi xác nhận:<br>- `holder_type = SHIPPER`, `holder_shipper` = người lấy;<br>- nhiệm vụ lấy `SUCCEEDED`. |
| D6 | **Nhập điểm tập kết** (UC04.10) | Nhân viên bấm "Xác nhận tiếp nhận" trên đơn Đã lấy hàng.<br>- Ghi `Handover` gồm: người giao (Shipper đang giữ), người nhận, thời gian, **ghi chú sai lệch tùy chọn** (E1.2).<br>- `holder_type = HUB`, xóa `holder_shipper`.<br>- Một điểm tập kết duy nhất; không kho/kệ/tồn (BR2). |
| D7 | **Lấy lại / kết thúc** (UC04.13) | Lý do bắt buộc (1–500 ký tự).<br>- **Lấy lại** → Chờ lấy hàng; nút "Phân công lấy hàng" hiện lại ngay để Nhân viên chọn Shipper (có thể chọn người cũ); lịch sử lần trước giữ nguyên.<br>- **Kết thúc** → trạng thái kết thúc, có hộp xác nhận (A1.2), không tạo nhiệm vụ mới. |
| D8 | **Thông báo** | Mọi thông báo kèm `payload.shipment_id` (+ `task_id` cho Shipper):<br>- Phân công → **Shipper** (`TASK_ASSIGNED`).<br>- Lấy được → **Shop** (`PICKED_UP`).<br>- Lấy thất bại → **Shop** và **mọi Nhân viên đang hoạt động** (`PICKUP_FAILED`, UC04.3 bước 7).<br>- Lấy lại → **Shop** (loại mới `PICKUP_RETRY`).<br>- Kết thúc → **Shop** (`PICKUP_ABANDONED`).<br>Nhập điểm tập kết không gửi thông báo (đặc tả không yêu cầu); Shop thấy qua trạng thái/lịch sử. |
| D9 | **Khóa Shipper còn nhiệm vụ mở** (treo từ spec 003) | Khi khóa: nhiệm vụ mở của người đó bật `needs_attention`, gửi `ACCOUNT_LOCKED_TASKS` cho mọi Nhân viên đang hoạt động; danh sách/chi tiết Nhân viên hiện cảnh báo.<br>Nhiệm vụ **không** tự đóng (thay người ở spec 009).<br>Phân công cho Shipper đã khóa → `409` (UC06.5 E1). |
| D10 | **Màn Nhân viên** | Danh sách vận đơn thêm tab hàng việc, mỗi tab cũ nhất trước:<br>**Chờ xác nhận · Chờ phân công lấy · Lấy thất bại · Chờ nhập điểm tập kết · Tất cả**.<br>Hộp phân công liệt kê Shipper đang hoạt động kèm **số nhiệm vụ đang mở** của từng người (để chia việc), tìm theo tên/SĐT.<br>Thẻ "Điều phối" hiện Shipper phụ trách, người đang giữ hàng, lịch sử nhiệm vụ thật. |

## 3. Backend

### 3.1. Model (`dispatch`)

Chi tiết trường: [models.md](models.md).
- `Task`: `shipment`, `type`, `status`, `shipper`, `assigned_by`, `assigned_at`, `closed_at`, `replaced_by` (để spec 009), `handover_reported_at` (spec 008–009), `needs_attention`, `attempt_no` (spec 007).
- `TaskResult`: `task` (một-một), `outcome`, `reason_code`, `note`, `recorded_by`, `recorded_at`; cột COD để spec 007.
- `Handover`: `shipment`, `task` (null), `kind` (`HUB_INTAKE` ở spec này), `from_shipper`, `received_by`, `received_at`, `discrepancy_note`.
- `ShipmentEvent.task` FK null: mốc lịch sử gắn đúng nhiệm vụ.

### 3.2. Service (`dispatch/services.py`)

Mọi thao tác theo quy ước spec 001 mục 3.6:
1. Khóa **đơn** trước, rồi tới **nhiệm vụ**. Thứ tự cố định để tránh deadlock.
2. Kiểm trạng thái bằng `SHIPMENT_TRANSITIONS` / `TASK_TRANSITIONS`.
3. Kiểm `updated_at` (thao tác của Nhân viên).
4. Ghi đơn + nhiệm vụ + kết quả/bàn giao + lịch sử + thông báo trong **một transaction**.

| Hàm | Việc làm |
|---|---|
| `assign_pickup(staff, shipment_id, shipper_id, expected_updated_at)` | 1. Shipper phải `SHIPPER` và đang hoạt động (khóa dòng user — chặn đua với khóa tài khoản).<br>2. `ASSIGN_PICKUP`: tạo `Task(PICKUP, ACTIVE)`; đơn `PICKUP_ASSIGNED`.<br>3. Lịch sử + thông báo Shipper.<br>Đơn đã có nhiệm vụ mở → `409` (partial unique là lớp chặn cuối). |
| `confirm_pickup(shipper, task_id)` | 1. Nhiệm vụ phải của Shipper, `PICKUP`, `ACTIVE`; gửi lại khi đã `SUCCEEDED` bởi chính người đó → trả hiện tại (UC04.2 BR2).<br>2. `TASK_SUCCEED` + `CONFIRM_PICKUP`: đơn `PICKED_UP`, `holder = SHIPPER`.<br>3. `TaskResult(SUCCEEDED)` + thông báo Shop. |
| `fail_pickup(shipper, task_id, reason_code, note)` | `TASK_FAIL` + `FAIL_PICKUP`: đơn `PICKUP_FAILED`, `TaskResult(FAILED, lý do)`, thông báo Shop + Nhân viên. Holder **giữ** `SHOP` (BR2: chưa nhận hàng). |
| `receive_at_hub(staff, shipment_id, discrepancy_note, expected_updated_at)` | `RECEIVE_AT_HUB`: `Handover(HUB_INTAKE)`, đơn `AT_HUB`, `holder = HUB`. Đã `AT_HUB` → trả hiện tại (E1.1). |
| `retry_pickup` / `abandon_pickup(staff, shipment_id, reason, expected_updated_at)` | `RETRY_PICKUP` → `AWAITING_PICKUP` (+ `PICKUP_RETRY` cho Shop); `ABANDON_PICKUP` → `PICKUP_ABANDONED` (+ `PICKUP_ABANDONED`). Lý do vào lịch sử. |
| `flag_open_tasks_of_locked_shipper(shipper, actor)` | Gọi từ `lock_account` (spec 003) trong cùng transaction: bật `needs_attention`, báo Nhân viên (D9). |

### 3.3. Phạm vi dữ liệu và quyền

- `shipments_visible_to`: **thêm nhánh SHIPPER** = đơn có nhiệm vụ được giao cho mình. Dùng cho lịch sử / spec sau; Shipper vẫn **không** có quyền gọi API vận đơn (D2).
- `tasks_visible_to(user)`: SHIPPER → `Task.shipper = user`; ADMIN → mọi nhiệm vụ (đọc ở chi tiết đơn). Nhiệm vụ ngoài phạm vi → `404`.
- Hành động Nhân viên: `HasRole.of(ADMIN)`. Hành động Shipper: `HasRole.of(SHIPPER)`, kiểm thêm "người phụ trách".
- Chi tiết vận đơn cho Nhân viên thêm `tasks` (lịch sử nhiệm vụ: loại, Shipper, trạng thái, thời gian, kết quả) và `holder_shipper`.
- Nhân viên chọn Shipper qua `GET /dispatch/shippers/`: Shipper hoạt động kèm `open_task_count`, một truy vấn có `annotate`.

## 4. Frontend

| Route | View | Vai trò | Mô tả |
|---|---|---|---|
| `/shipper/tasks` | `views/shipper/TaskListView.vue` | SHIPPER | Nhiệm vụ lấy hàng của tôi:<br>- tab Đang làm / Đã xong;<br>- thẻ dễ bấm trên điện thoại (Shipper dùng chủ yếu ở điện thoại);<br>- trống → "Chưa có nhiệm vụ" + Tải lại. |
| `/shipper/tasks/:id` | `views/shipper/TaskDetailView.vue` | SHIPPER | Thông tin lấy hàng (D3), nút gọi điện SĐT người gửi (`tel:`), "Đã lấy hàng" (hộp xác nhận), "Lấy hàng thất bại" (lý do + ghi chú). Nhiệm vụ đã đóng / đã chuyển → chỉ xem / 404. |
| `/staff/shipments` | (sửa) | ADMIN | Thêm tab hàng việc (D10). |
| `/staff/shipments/:id` | (sửa) | ADMIN | Nút theo `allowed_actions`:<br>- "Phân công lấy hàng" (hộp chọn Shipper);<br>- "Xác nhận tiếp nhận" (ghi chú sai lệch);<br>- "Lấy lại" / "Kết thúc" (lý do).<br>Thẻ Điều phối thật; cảnh báo `needs_attention`. |

- Menu Shipper: "Nhiệm vụ lấy hàng". Trang chủ Shipper: ô "N nhiệm vụ đang làm".
- Dùng lại: `ConfirmDialog`, `ShipmentInfoCards`, `ShipmentEventList`, `usePagedList`, khuôn [design-system](../../docs/design-system.md).
- Mã hành động mới vào `shipmentActions.js` (test đối chiếu backend). Mã trạng thái nhiệm vụ đã có ở `statusTones.js` (`task_statuses`).

## 5. Tiêu chí nghiệm thu

**11/12 đạt** — bằng chứng: `apps/dispatch/tests/` (56 test, gồm 5 test 2 luồng thật), đột biến, `EXPLAIN`, smoke; xem nhật ký [tasks.md](tasks.md).

- [x] Phân công: chỉ đơn Chờ lấy hàng, chỉ Shipper hoạt động; đơn đã có nhiệm vụ mở → `409`; Shipper bị khóa → `409`; Shipper nhận thông báo; mọi bước trong một transaction.
- [x] Hai Nhân viên phân công cùng lúc cùng đơn → **một** nhiệm vụ (test 2 luồng + partial unique).
- [x] Shipper chỉ thấy nhiệm vụ của mình; nhiệm vụ người khác / đã chuyển → `404`; không gọi được API vận đơn, API của Nhân viên.
- [x] Chi tiết nhiệm vụ lấy **không** lộ người nhận, địa chỉ giao, COD (D3).
- [x] Lấy được: đơn Đã lấy hàng, Shipper giữ hàng, nhiệm vụ hoàn tất, Shop nhận thông báo; gửi lại không ghi trùng; nhiệm vụ đã đóng → `409`.
- [x] Lấy thất bại: lý do bắt buộc (Khác → ghi chú bắt buộc); đơn Lấy hàng thất bại; hàng vẫn ở Shop; Shop + Nhân viên nhận thông báo.
- [x] Nhập điểm tập kết: chỉ từ Đã lấy hàng; ghi người giao/nhận/thời gian/sai lệch; hàng ở điểm tập kết; làm lại → trả hiện tại, không ghi trùng.
- [x] Lấy lại: Chờ lấy hàng, phân công được lần nữa, lịch sử lần trước còn; Kết thúc: trạng thái kết thúc, không tạo nhiệm vụ; cả hai bắt buộc lý do, báo Shop.
- [x] Shipper xác nhận lấy cùng lúc Nhân viên thao tác khác trên đơn → không ghi đè (test 2 luồng).
- [x] Khóa Shipper còn nhiệm vụ mở → nhiệm vụ `needs_attention`, Nhân viên được báo; nhiệm vụ không mất.
- [x] Bảng chuyển trạng thái đơn + nhiệm vụ vẫn khớp checklist; không N+1; `EXPLAIN` danh sách nhiệm vụ của Shipper, tab hàng việc.
- [ ] Frontend: Vitest pass, build, ảnh chụp 1440/390 (màn Shipper ưu tiên điện thoại), thử trình duyệt theo `manual-test.md`. → Vitest 262 + build ✔, ảnh chụp 1440/390, 1 lượt bấm thật end-to-end; **còn người dùng thử** ([manual-test.md](manual-test.md), 41 bước).

## 6. Ghi chú cho spec sau

- **Spec 007:**
  - `ASSIGN_DELIVERY` tạo `Task(DELIVERY)` dùng lại `Task`/`TaskResult` (thêm cột COD), danh sách nhiệm vụ Shipper thêm tab Giao hàng.
  - Chi tiết nhiệm vụ giao mới hiện người nhận / COD.
- **Spec 008:** `Handover.kind` thêm loại hoàn về điểm tập kết / Shop nhận hàng hoàn.
- **Spec 009:** `TASK_REPLACE`, `TASK_START_SWAP` dùng `replaced_by`, `handover_reported_at`; xử lý nhiệm vụ `needs_attention`.
  - **Việc treo từ spec 003 (chưa làm ở 006):** hộp khóa Shipper nêu **số nhiệm vụ đang mở** (UC06.4 bước 2). Cần thêm dữ liệu cho API tài khoản mà `accounts` vẫn không import `dispatch` (vd: dispatch cung cấp số liệu qua hook / endpoint riêng). Gỡ `needs_attention` khi đã đổi Shipper.
