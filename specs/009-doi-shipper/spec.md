# Spec 009 — Đổi Shipper / phân công lại

Trạng thái: **Đã triển khai; nghiệm thu chức năng tự động đạt. Chưa chốt toàn bộ: người dùng chưa tự thử và audit dev còn mở.**
D1–D11 đã chốt theo đề xuất ngày 23/11/2026. Ngày lập: 23/11/2026.
Kết quả chi tiết: [acceptance.md](acceptance.md) · [Kịch bản người dùng thử](manual-test.md).

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md)

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC06.8; UC06.4 bước 2 (việc treo từ spec 003); UC06.6 A2, UC06.7 A1.1.
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): UC06.8, mục "Quy tắc bàn giao khi đổi Shipper" (6 điểm), kịch bản "Đổi Shipper chưa giữ hàng", "Đổi Shipper đã giữ hàng", "Ba lần giao" (đổi Shipper không đặt lại bộ đếm).
- Nền:
  - [spec 001](../001-nen-tang/spec.md): `TASK_REPLACE`, `TASK_START_SWAP`, `TASK_CONFIRM_SWAP` (đã có trong `TASK_TRANSITIONS`), `Task.replaced_by`, `handover_reported_at`.
  - [spec 003](../003-quan-ly-tai-khoan/spec.md): khóa Shipper — **chưa làm** số nhiệm vụ đang mở trong hộp khóa (UC06.4 bước 2).
  - [spec 006](../006-lay-hang-diem-tap-ket/spec.md) D9 `needs_attention`; [spec 007](../007-giao-hang-cod/spec.md) D7 (giao lại chỉ người đang giữ, `holder_locked`), CHECK `attempt_no`; [spec 008](../008-hoan-hang/spec.md) A1.2 (tiếp nhận thẳng khi hàng ở điểm tập kết), mục 6.

## 1. Mục tiêu và phạm vi

Thay người làm nhiệm vụ chưa xong mà **không mất lịch sử** và **không bỏ qua bàn giao kiện hàng**; gỡ các chỗ "kẹt" đã treo từ spec 003, 006, 007, 008.

```
Nhiệm vụ LẤY đang mở (Shipper chưa nhận hàng) ──Đổi Shipper──► cũ: Đã thay thế · mới: nhiệm vụ lấy (ngay)

Nhiệm vụ GIAO đang mở (Shipper đang giữ hàng) ──Đổi Shipper (người mới = dự kiến)──► cũ: Chờ bàn giao đổi Shipper
        │                                                                                 │ Shipper cũ báo đã đưa về (tùy chọn)
        │                                                                                 │ NV ghi sai lệch (giữ chờ)
        │                                                                                 ▼
        │                                                     NV xác nhận nhận hàng ──► cũ: Đã thay thế · mới: nhiệm vụ giao
        │                                                                                    (cùng lần giao — không thêm lượt)
Không có nhiệm vụ mở nhưng hàng ở Shipper (Chờ giao lại / Chờ xử lý hoàn) ──NV nhận hàng về điểm tập kết──► hàng ở điểm tập kết
        → giao lại bằng bất kỳ ai (UC06.6) / tiếp nhận hoàn thẳng (UC06.7 A1.2)
```

| UC / việc | Phần làm trong spec này |
|---|---|
| UC06.8 bước 1–7 | Đổi Shipper khi **người cũ chưa nhận hàng** (nhiệm vụ lấy đang mở): thay ngay trong một lần xử lý, lý do bắt buộc, báo người cũ + người mới. |
| UC06.8 A1 | Người cũ **đang giữ hàng** (nhiệm vụ giao đang mở): Chờ bàn giao đổi Shipper; người mới chỉ là dự kiến; người cũ chỉ xem + báo đã đưa về; NV xác nhận nhận thực tế → tạo nhiệm vụ thay thế đúng tiến trình. |
| UC06.8 A1.6 | Nhiệm vụ **hoàn**: người cũ đưa hàng về điểm tập kết chính là hoàn tất → dùng "Tiếp nhận hàng hoàn" (spec 008), không đổi người (D3). |
| UC06.8 A2 | Nhiệm vụ đã thất bại: không đổi thành Đã thay thế — dùng UC04.12 / UC04.13 rồi phân công đợt mới (đã có ở 006–007). |
| UC06.8 E1 | Sai lệch → ghi chú, giữ chờ; người cũ bị khóa → NV xác nhận thay; người mới bị khóa → chọn người khác trước khi tạo nhiệm vụ. |
| UC06.6 A2, UC06.7 A1.1 (treo từ 007 D7, 008) | **Nhận hàng về điểm tập kết** khi không có nhiệm vụ mở mà hàng còn ở Shipper → sau đó giao lại bằng người khác / tiếp nhận hoàn thẳng. |
| UC06.4 bước 2 (treo từ spec 003) | Hộp khóa Shipper liệt kê **nhiệm vụ đang mở** của người đó. |
| Spec 006 D9 (treo) | Cảnh báo `needs_attention` hết khi đã đổi người (nhiệm vụ cũ đóng, nhiệm vụ mới sạch). |

**Ngoài phạm vi:** chia sẻ vị trí khi bàn giao (UC06.8 A1.3 "chia sẻ vị trí") → spec 011.

## 2. Quyết định cần chốt

**Đã chốt 23/11/2026: cả 11 điểm theo đề xuất** — hỏi riêng và xác nhận D2 (ký hiệu `KEEP`), D3 (nhiệm vụ hoàn không đổi người), D4 (không có "hủy đổi", chỉ đổi người dự kiến).

**Làm rõ khi chốt:**
- D2 — `resolve_transition` trả `Transition` với `target` **đã thay `KEEP` bằng trạng thái hiện tại**: code ngoài bảng (nhiều service gán `shipment.status = rule.target`) không bao giờ thấy `KEEP` → không thể ghi nhầm trạng thái. `allowed_actions` coi `KEEP` hợp lệ ở mọi trạng thái nguồn. Có test canh.
- D4 — UC06.8 bước 3: người thay thế phải **khác** người cũ, kể cả khi đổi người dự kiến. Đã bắt đầu đổi người thì không quay về người cũ; muốn người cũ giao tiếp chỉ có cách phân công đợt sau (sau khi việc đổi đã xong).

Kiểm tra khi chốt (đối chiếu code 23/11/2026):
- `TASK_TRANSITIONS` đã có `TASK_REPLACE` (ACTIVE → REPLACED), `TASK_START_SWAP` (ACTIVE → PENDING_SWAP_HANDOVER), `TASK_CONFIRM_SWAP` (PENDING → REPLACED); `OPEN_TASK_STATUSES` gồm cả PENDING (partial unique vẫn đúng: một nhiệm vụ mở mỗi đơn).
- `Task.replaced_by` (FK self), `handover_reported_at` có sẵn; `NotificationKind.TASK_REPLACED` có sẵn.
- Bảng `SHIPMENT_TRANSITIONS` + bộ kiểm `TransitionTableChecks` bắt mỗi hành động có **đúng một trạng thái đích** — thao tác "giữ nguyên trạng thái" cho **nhiều** trạng thái nguồn không khai báo được (D2).
- Nhiệm vụ giao: Shipper giữ hàng ngay từ lúc phân công (spec 007 D6) → đổi người khi giao luôn đi nhánh A1.
- CHECK `task_attempt_matches_type` (spec 007) bắt nhiệm vụ giao có `attempt_no` 1..3 → nhiệm vụ thay thế chép `attempt_no` cũ.
- `tasks_visible_to(shipper)` lọc theo `Task.shipper` → người dự kiến **tự nhiên chưa thấy** nhiệm vụ chờ (A1.2); người cũ vẫn thấy nhiệm vụ đã thay thế trong "Đã xong".
- `confirm_delivery` / `fail_delivery` đã đi qua `TASK_TRANSITIONS` (chỉ từ `ACTIVE`) → người cũ gọi API trực tiếp khi đang chờ cũng bị chặn; chỉ cần sửa `allowed_actions` để **nút** khớp.

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **Mô hình dữ liệu** | Không bảng mới:<br>- `Task.swap_candidate` (FK User, null) — người mới **dự kiến** trong lúc Chờ bàn giao (A1.2); CHECK chỉ có khi `PENDING_SWAP_HANDOVER`.<br>- Nhiệm vụ cũ `replaced_by` → nhiệm vụ mới.<br>- `HandoverKind.REASSIGN_INTAKE` "Nhận hàng về để đổi Shipper" (dùng cho xác nhận bàn giao đổi người và cho "nhận hàng về điểm tập kết").<br>- `NotificationKind` + `SWAP_HANDOVER_REQUIRED` (báo người cũ đưa hàng về), `SWAP_HANDOVER_REPORTED` (người cũ báo đã đưa về). |
| D2 | **Thao tác giữ nguyên trạng thái trên nhiều trạng thái nguồn** | Thêm ký hiệu `KEEP` cho bảng: `transition([A, B], KEEP, roles)` = "ở nguyên trạng thái hiện tại". `TransitionTableChecks` hiểu `KEEP` (đích hợp lệ = chính nguồn). Dùng cho 5 hành động mới (D9). Dòng cũ (`UPDATE_REQUEST`, `REPORT_RETURN_*`) giữ nguyên — không bắt buộc đổi. |
| D2b | *Phương án khác cho D2* | Mỗi trạng thái nguồn một hành động riêng (vd `RECALL_FOR_REDELIVERY`, `RECALL_FOR_RETURN`) — không đổi bộ kiểm nhưng nhân đôi mã, nhãn, nút. **Không đề xuất.** |
| D3 | **Loại nhiệm vụ nào được đổi** | - **Lấy** đang mở (người cũ chưa nhận hàng) → **thay ngay** (UC06.8 bước 4–7).<br>- **Giao** đang mở (người cũ đang giữ hàng) → **luôn chờ bàn giao** (A1).<br>- **Hoàn** đang mở → **không đổi người**: người cũ đưa hàng về điểm tập kết là hoàn tất; NV dùng "Tiếp nhận hàng hoàn" (spec 008, làm được cả khi người cũ bị khóa — A1.6, E1.2).<br>- Nhiệm vụ đã thất bại → không đổi (A2). |
| D4 | **Chờ bàn giao đổi Shipper** (A1) | - Nhiệm vụ cũ `PENDING_SWAP_HANDOVER`, lưu người dự kiến + lý do; đơn **vẫn Đang giao hàng**.<br>- Người cũ **mất** "Giao thành công / Giao thất bại / COD" (BR2); chỉ còn xem + **"Đã đưa hàng về điểm tập kết"** (ghi `handover_reported_at`, báo NV).<br>- Người dự kiến **chưa thấy** nhiệm vụ (A1.2).<br>- NV đổi được **người dự kiến** khi còn chờ (gọi lại "Đổi Shipper"); **không có "hủy đổi"** (đặc tả không có; tránh trả quyền COD cho người cũ). |
| D5 | **NV xác nhận nhận hàng bàn giao** (A1.4–A1.5, E1) | Hộp nêu người cũ, người dự kiến, kiện hàng, đã báo chưa:<br>- ô **"Shipper mới đã nhận hàng tại điểm tập kết"** bắt buộc (như spec 007 D6);<br>- ghi chú sai lệch tùy chọn;<br>- xác nhận → `Handover(REASSIGN_INTAKE)` (người giao = người cũ), nhiệm vụ cũ `REPLACED` + `replaced_by`, nhiệm vụ giao mới cho người dự kiến **cùng `attempt_no`**, hàng ở người mới; báo người cũ (`TASK_REPLACED`) + người mới (`TASK_ASSIGNED`).<br>- Người dự kiến không còn hoạt động lúc xác nhận → `409`, **không ghi gì**, NV chọn người khác rồi xác nhận lại (E1.3).<br>- **"Ghi sai lệch, chưa nhận"** (E1.1): ghi lịch sử, giữ chờ.<br>- Người cũ bị khóa: NV xác nhận bình thường (E1.2). |
| D6 | **Nhận hàng về điểm tập kết** (UC06.6 A2, UC06.7 A1.1 — treo 007/008) | Đơn **Chờ giao lại** hoặc **Chờ xử lý hoàn**, không có nhiệm vụ mở, hàng ở Shipper X → nút "Nhận hàng về điểm tập kết" (ghi chú sai lệch tùy chọn) → `Handover(REASSIGN_INTAKE)`, hàng ở điểm tập kết, **không gửi thông báo theo D10**. Sau đó: giao lại bằng **bất kỳ** Shipper (spec 007 đã cho khi hàng không ở Shipper); hoàn → "Tiếp nhận hàng hoàn" thẳng (spec 008 A1.2). Gỡ luôn cảnh báo `holder_locked`. |
| D7 | **Số lần giao, COD** (BR checklist điểm 6) | Đổi người **không** tăng / đặt lại `delivery_attempts`, không ghi `TaskResult` cho nhiệm vụ bị thay; nhiệm vụ mới mang đúng `attempt_no` cũ. Đơn đã giao / đã hoàn tất không có nút đổi (BR1). |
| D8 | **Nhiệm vụ đang mở trong hộp khóa Shipper** (UC06.4 bước 2 — treo spec 003) | `GET /dispatch/shippers/{id}/open-tasks/` (NV): mã đơn, loại, trạng thái, `needs_attention`. Hộp "Khóa tài khoản" của Shipper gọi API này và hiện danh sách + dòng "Sau khi khóa, cần đổi Shipper cho các nhiệm vụ này". `accounts` vẫn **không** import `dispatch` (frontend gọi thẳng API điều phối). |
| D9 | **API** | NV trên đơn (cùng khuôn `updated_at`, `409`):<br>- `swap-shipper/` (`shipper_id`, `reason`) — tự đi nhánh thay ngay / chờ bàn giao theo loại nhiệm vụ; khi đang chờ thì đổi người dự kiến;<br>- `confirm-swap-handover/` (`handed_over`, `discrepancy_note`);<br>- `report-swap-issue/` (`reason`);<br>- `recall-to-hub/` (`discrepancy_note`).<br>Shipper: `tasks/{id}/report-swap-handover/`. Hành động mới trong bảng (D2): `SWAP_SHIPPER` (Đã phân công lấy, Đang giao → KEEP), `CONFIRM_SWAP_HANDOVER`, `REPORT_SWAP_ISSUE` (Đang giao → KEEP, ADMIN), `REPORT_SWAP_HANDOVER` (Đang giao → KEEP, SHIPPER), `RECALL_TO_HUB` (Chờ giao lại, Chờ xử lý hoàn → KEEP, ADMIN). Điều kiện theo nhiệm vụ / nơi giữ hàng vào `shipments/rules.py`; điều kiện theo **trạng thái nhiệm vụ** (vd người cũ đang chờ thì không còn "Giao thành công") vào bảng phía nhiệm vụ. |
| D10 | **Thông báo** | - Thay ngay: người cũ `TASK_REPLACED`, người mới `TASK_ASSIGNED`.<br>- Bắt đầu chờ: người cũ `SWAP_HANDOVER_REQUIRED` ("Đưa hàng về điểm tập kết để bàn giao" + địa chỉ). Người dự kiến **chưa** được báo.<br>- Người cũ báo đã đưa về: mọi NV `SWAP_HANDOVER_REPORTED`.<br>- Xác nhận bàn giao: người cũ `TASK_REPLACED`, người mới `TASK_ASSIGNED`.<br>- Nhận hàng về điểm tập kết: **không báo** ai (không có nhiệm vụ nào bị thay; hàng đã thực tế về điểm tập kết, NV ghi nhận).<br>Shop không nhận thông báo đổi người (việc nội bộ; Shop thấy trạng thái không đổi). |
| D11 | **Màn hình** | **NV (chi tiết đơn):** nút **"Đổi Shipper"** khi có nhiệm vụ lấy/giao đang mở — hộp nêu người cũ, tình trạng giữ hàng, `ShipperPicker` **loại người cũ**, lý do bắt buộc, ghi rõ nhánh (thay ngay / chờ bàn giao). Khi chờ: dải cảnh báo "Chờ bàn giao đổi Shipper — dự kiến: X", nút "Xác nhận nhận hàng bàn giao", "Ghi sai lệch", "Đổi Shipper" (đổi người dự kiến). Nút **"Nhận hàng về điểm tập kết"** (D6). Thẻ Điều phối: nhiệm vụ "Đã thay thế → <người mới>", "Chờ bàn giao". Cảnh báo `needs_attention` / `holder_locked` kèm nút xử lý.<br>**Shipper cũ:** nhiệm vụ chờ bàn giao có dải "Nhiệm vụ đang chờ bàn giao đổi Shipper — đưa hàng về điểm tập kết" + nút "Đã đưa hàng về điểm tập kết"; nhiệm vụ đã thay thế ở tab Đã xong, không nút.<br>**Hộp khóa Shipper:** danh sách nhiệm vụ đang mở (D8). |

## 3. Backend

### 3.1. Model / bảng

Chi tiết: [models.md](models.md).
- `Task.swap_candidate` + CHECK; `HandoverKind.REASSIGN_INTAKE`; `NotificationKind` +2; `ShipmentAction` +5; `core/transitions.KEEP` + cập nhật `TransitionTableChecks` (D2).
- Bảng điều kiện theo trạng thái nhiệm vụ cho hành động Shipper (D4, D9): `CONFIRM_DELIVERY`, `FAIL_DELIVERY` chỉ khi nhiệm vụ `ACTIVE`; `REPORT_SWAP_HANDOVER` chỉ khi `PENDING_SWAP_HANDOVER`.

### 3.2. Service (`dispatch/services.py`)

Khuôn 006–008: khóa đơn → user / nhiệm vụ; "đã xong" → trạng thái → `updated_at`; một transaction; dùng lại `_lock_available_shipper`, `_create_task`, `_holder_value`, `_open_task`, `_close_task`, `_lock_own_task`, `_require_guard`.

| Hàm | Việc làm |
|---|---|
| `swap_shipper(staff, shipment_id, shipper_id, reason, expected_updated_at)` | Nhiệm vụ mở phải là lấy/giao; người mới ≠ người cũ, hoạt động (khóa dòng user).<br>- Lấy `ACTIVE` → `TASK_REPLACE`, nhiệm vụ lấy mới, `replaced_by`; báo cũ + mới.<br>- Giao `ACTIVE` → `TASK_START_SWAP`, `swap_candidate`; báo người cũ.<br>- Giao `PENDING_SWAP_HANDOVER` → đổi `swap_candidate`.<br>Gửi lại cùng người → trả hiện tại. |
| `confirm_swap_handover(staff, shipment_id, discrepancy_note, expected_updated_at)` | Nhiệm vụ `PENDING`; khóa dòng `swap_candidate`, còn hoạt động (khác → `409`, không ghi gì); `Handover(REASSIGN_INTAKE)`; `TASK_CONFIRM_SWAP` + `replaced_by`; nhiệm vụ giao mới cùng `attempt_no`; hàng ở người mới; báo cũ + mới. |
| `report_swap_issue(staff, shipment_id, reason, expected_updated_at)` | Chỉ ghi lịch sử + tăng phiên bản đơn (như spec 008); gửi lại cùng ghi chú → trả hiện tại. |
| `report_swap_handover(shipper, task_id)` | Nhiệm vụ của mình, `PENDING`; ghi `handover_reported_at`; báo NV; gửi lại → trả hiện tại. |
| `recall_to_hub(staff, shipment_id, discrepancy_note, expected_updated_at)` | Không nhiệm vụ mở, hàng ở Shipper (bảng điều kiện); `Handover(REASSIGN_INTAKE)`; hàng ở điểm tập kết; không đổi trạng thái đơn. |

### 3.3. Hiển thị

- NV: `tasks[].swap_candidate`, `tasks[].replaced_by` (id nhiệm vụ mới + tên người mới).
- Shipper: nhiệm vụ `PENDING_SWAP_HANDOVER` → `allowed_actions` = `REPORT_SWAP_HANDOVER` (chưa báo) / `[]`; vẫn thấy thông tin để mang hàng về; `REPLACED` → chỉ xem, ẩn SĐT (đã đóng — spec 007 D3).
- `GET /dispatch/shippers/{id}/open-tasks/` (D8).

## 4. Frontend

Nền Phase 4 đã có:
- `shipmentService.swapShipper(id, shipperId, reason, updatedAt)`, `confirmSwapHandover(id, discrepancyNote, updatedAt)`,
  `reportSwapIssue(id, reason, updatedAt)`, `recallToHub(id, discrepancyNote, updatedAt)`.
- `taskService.reportSwapHandover(id)` và `dispatchService.openTasks(shipperId)`.
- `SHIPMENT_ACTION` đủ 5 mã mới; `TASK_STATUS` trong `utils/statusTones.js` gồm `ACTIVE`,
  `PENDING_SWAP_HANDOVER`, `REPLACED`. Nhãn vẫn lấy từ meta, có test đối chiếu enum backend.
- `ShipperPicker.exclude`: `Number | null`, mặc định `null`, là ID người cũ. Lọc trên mọi kết quả API/tìm kiếm;
  lựa chọn bị loại được đặt lại `null` khi dựng hoặc khi prop đổi. Nếu `holder` trùng `exclude` thì không có
  người hợp lệ để chọn, không tự tải người khác thay người đang giữ hàng. Bỏ `exclude` sẽ hiện lại lựa chọn.
- Các hàm xác nhận bàn giao gửi `handed_over: true` theo khuôn phân công giao hiện có; màn hình Phase 5 chỉ
  gọi sau khi Nhân viên đã tích xác nhận nhận hàng thực tế.

Màn hình Phase 5 đã triển khai (test và ảnh tại [tasks.md](tasks.md#phase-5--frontend-màn-hình)):

| Chỗ | Thay đổi |
|---|---|
| `StaffShipmentDetailView` | `ACTION_BUTTONS` + Đổi Shipper, Xác nhận nhận hàng bàn giao, Ghi sai lệch (bàn giao), Nhận hàng về điểm tập kết; hộp dùng lại `ShipperPicker` (thêm prop **`exclude`** — loại người cũ), hộp lý do, ô tích bàn giao. |
| `DispatchCard` | Dải "Chờ bàn giao đổi Shipper — dự kiến X"; nhiệm vụ "Đã thay thế → <người mới>"; cảnh báo `needs_attention` / `holder_locked` gợi ý nút xử lý. |
| `TaskDetailView` (Shipper) | Nhiệm vụ chờ bàn giao: dải cảnh báo + nút "Đã đưa hàng về điểm tập kết" (`HubCard`); nhãn trạng thái từ meta. |
| `AccountDetailView` (hộp khóa Shipper) | Danh sách nhiệm vụ đang mở (D8). |

## 5. Tiêu chí nghiệm thu

- [x] Đổi Shipper nhiệm vụ lấy (chưa nhận hàng): một lần xử lý; cũ Đã thay thế + `replaced_by`; mới nhận nhiệm vụ; người cũ mất quyền ngay (`409` khi bấm "Đã lấy hàng"); lý do bắt buộc; báo đúng người.
- [x] Đổi Shipper nhiệm vụ giao (đang giữ hàng): Chờ bàn giao; người mới chưa thấy nhiệm vụ; người cũ không giao / thất bại / ghi COD được, chỉ báo đã đưa về; đổi người dự kiến được.
- [x] Xác nhận bàn giao: lưu người giao / nhận / thời gian / sai lệch; nhiệm vụ mới đúng loại, **cùng lần giao**; `delivery_attempts` không đổi; người dự kiến bị khóa → `409`, không ghi gì; người cũ bị khóa vẫn xác nhận được.
- [x] Ghi sai lệch: giữ chờ bàn giao, chưa cấp quyền người mới.
- [x] Nhiệm vụ hoàn / đã thất bại / đơn đã kết thúc: không có "Đổi Shipper" (D3, A2, BR1).
- [x] Nhận hàng về điểm tập kết: hàng ở điểm tập kết; sau đó giao lại bằng người khác được; hoàn tiếp nhận thẳng được; cảnh báo `holder_locked` hết.
- [x] Hộp khóa Shipper liệt kê nhiệm vụ đang mở; sau khi đổi người, cảnh báo `needs_attention` không còn trên đơn.
- [x] Bảng `KEEP`: bộ kiểm bảng vẫn chặt (đột biến: `KEEP` sai nguồn, hành động thừa).
- [x] Đồng thời (2 luồng thật): Shipper cũ "Giao thành công" đúng lúc NV đổi người → chỉ một bên thắng, không ghi COD sau khi đã chờ bàn giao; 2 NV cùng xác nhận bàn giao → 1 nhiệm vụ mới.
- [x] Bảng chuyển trạng thái nhiệm vụ / vận đơn khớp checklist; không N+1; `EXPLAIN` nhiệm vụ mở theo Shipper (hộp khóa).
- [x] Kịch bản checklist "Đổi Shipper chưa giữ hàng" + "Đổi Shipper đã giữ hàng" + "Ba lần giao (đổi Shipper không đặt lại bộ đếm)" — smoke API + bấm thật.
- [ ] Frontend: Vitest pass, build, ảnh chụp 1440/390, thử trình duyệt theo `manual-test.md`.

  → Tự động đã đạt Vitest 326/326, build cache, 10 ảnh và 3 luồng Chrome thật trên test DB;
  phần người dùng tự thử còn chờ (đã xác nhận "Chưa tự thử"). Chi tiết nguồn bằng chứng tại acceptance.md.

## 6. Ghi chú cho spec sau

- **Spec 011:** UC06.8 A1.3 "chia sẻ vị trí phục vụ bàn giao" của Shipper cũ khi chờ bàn giao.
