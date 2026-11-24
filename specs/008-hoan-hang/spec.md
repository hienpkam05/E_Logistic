# Spec 008 — Hoàn hàng

Trạng thái: **Đã triển khai (23/11/2026)** — chờ người dùng thử trình duyệt ([manual-test.md](manual-test.md)). D1–D10 theo đề xuất, chốt 22/11/2026. Ngày lập: 22/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md) · [manual-test.md](manual-test.md)

Nguồn:
- [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md): UC06.7, UC04.8, UC04.9, UC04.11.
- [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md): các UC trên, mục 4 (bảng trạng thái — dòng "Tiếp nhận hàng hoàn đã ở điểm tập kết"), thông báo, thao tác lặp, kịch bản "Hoàn hàng".
- Nền:
  - [spec 001](../001-nen-tang/spec.md): mục 3 (`ASSIGN_RETURN`, `RECEIVE_RETURN`, `CONFIRM_SHOP_RECEIVED`; `TASK_SUCCEED` cho RETURN do **Nhân viên**; Shipper báo bàn giao chỉ ghi `handover_reported_at`), mục 6 (`Handover` nhiều loại).
  - [spec 006](../006-lay-hang-diem-tap-ket/spec.md): `Task`, `Handover`, nhập điểm tập kết.
  - [spec 007](../007-giao-hang-cod/spec.md): quyết định hoàn, D7 (chỉ Shipper đang giữ hàng), mục 6 "Ghi chú cho spec 008".

## 1. Mục tiêu và phạm vi

Đưa đơn đã quyết định hoàn về **điểm tập kết** rồi trả cho **Shop** — kết thúc luồng hoàn (cột mốc kịch bản "Hoàn hàng" của checklist).

```
Chờ xử lý hoàn ──phân công hoàn (NV)──► Đang hoàn ──Shipper báo đã bàn giao──► (vẫn Đang hoàn, chờ NV)
      │                                    │                                         │
      │                                    └──NV ghi sai lệch (chưa nhận) ◄──────────┤
      │                                                                              ▼
      └──(hàng đã ở điểm tập kết — A1.2)──► NV tiếp nhận hàng hoàn ──────────► Chờ Shop đến lấy ──NV xác nhận Shop đã nhận──► Đã hoàn về Shop
```

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC06.7 | Phân công Shipper hoàn hàng | Toàn bộ trừ A1.1 (đổi người khi người cũ còn giữ hàng → spec 009):<br>- chỉ từ Chờ xử lý hoàn;<br>- hàng đang ở Shipper X → chỉ phân công X (như spec 007 D7);<br>- A1.2 hàng đã ở điểm tập kết → tiếp nhận thẳng, **không tạo chuyến hoàn thừa** (A1.3);<br>- E1 chưa có quyết định / Shipper bị khóa;<br>- BR1 không đặt Đã hoàn về Shop khi phân công. |
| UC04.8 | Xem nhiệm vụ hoàn hàng | Toàn bộ: mã đơn, tình trạng hàng, điểm tập kết, trạng thái nhiệm vụ; A1 trống; E1 không còn thuộc mình → 404. |
| UC04.9 | Bàn giao hàng hoàn | Toàn bộ:<br>- Shipper báo đã bàn giao (A1: đơn vẫn Đang hoàn);<br>- Nhân viên xác nhận tiếp nhận → Chờ Shop đến lấy, đóng nhiệm vụ, báo Shop;<br>- E1 ghi sai lệch, chưa nhận;<br>- BR1 Shipper không tự xác nhận. |
| UC04.11 | Xác nhận Shop nhận hàng hoàn | Toàn bộ: kiểm người nhận thuộc Shop, lưu người bàn giao / người nhận / thời gian → Đã hoàn về Shop, báo Shop; A1 chưa đến → giữ nguyên; E1 đã hoàn tất → không ghi thêm. |

**Ngoài phạm vi:**
- Đổi Shipper khi đang giữ hàng hoàn (UC06.7 A1.1, UC06.8): spec 009.
- Phí hoàn, đối soát: không có trong đặc tả.
- Nhiều điểm tập kết / kho / kệ: không có (một điểm tập kết duy nhất — spec 006 D6).

## 2. Quyết định cần chốt

**Đã chốt 22/11/2026: cả 10 điểm theo đề xuất** — hỏi riêng và xác nhận D5 (NV tiếp nhận được khi Shipper chưa báo, kèm cảnh báo; có "Ghi sai lệch, chưa nhận"), D6 (điểm tập kết trong `.env`), D10 (gộp tab theo giai đoạn + chip con).

**Làm rõ khi chốt:**
- D10 — tab giai đoạn gồm các trạng thái **Nhân viên cần xử lý** (giữ nguyên tập trạng thái của các tab hiện có, thêm 3 trạng thái hoàn):
  - Lấy hàng: Chờ lấy hàng · Lấy hàng thất bại · Đã lấy hàng;
  - Giao hàng: Đã nhập điểm tập kết · Chờ giao lại · Giao hàng thất bại;
  - Hoàn hàng: Chờ xử lý hoàn · Đang hoàn · Chờ Shop đến lấy.
  Trạng thái chỉ chờ Shipper (Đã phân công lấy, Đang giao) xem ở tab Tất cả như hiện nay. URL đổi khóa tab (`?tab=pickup|delivery|return&status=`) — link cũ dạng `?tab=hub` rơi về tab mặc định (đã có quy tắc "tab lạ").
- Lọc nhiều trạng thái + cũ nhất trước có thể không dùng thẳng được index `(status, -created_at, -id)` → đo `EXPLAIN` ở Phase 3 trước khi quyết định có thêm index.

Kiểm tra khi chốt (đối chiếu code 22/11/2026):
- `ASSIGN_RETURN` (`AWAITING_RETURN → RETURNING`), `RECEIVE_RETURN` (`RETURNING`, `AWAITING_RETURN → AWAITING_SHOP_PICKUP`), `CONFIRM_SHOP_RECEIVED` (`→ RETURNED_TO_SHOP`) đã có trong `SHIPMENT_TRANSITIONS`; chi tiết đơn của NV ở Chờ xử lý hoàn **đã trả** `ASSIGN_RETURN`, `RECEIVE_RETURN` (chưa có nút).
- `TaskType.RETURN`, `Task.handover_reported_at`, `NotificationKind.RETURN_AT_HUB`, `RETURN_COMPLETED` đã có.
- Chưa có thông tin điểm tập kết (tên, địa chỉ) ở đâu cả — cần cho UC04.8 bước 3 và Shop biết nơi đến lấy (D6).
- Các bảng cần thêm RETURN (spec 007 ghi sẵn): `TASK_SHIPMENT_VIEWS` (backend), `TYPE_VIEW`, `TASK_TYPE` (frontend).
- `settings.py` đã đọc `.env` bằng `load_dotenv`, có `.env.example` → D6 chỉ thêm biến. `TASK_SUCCEED` đã cho ADMIN (dùng cho RETURN). API danh sách đã nhận nhiều `status` (D10 không đổi backend).

| # | Vấn đề | Đề xuất |
|---|---|---|
| D1 | **Mô hình dữ liệu** | Không bảng mới:<br>- `Task(type=RETURN)`; Shipper báo bàn giao ghi `handover_reported_at` (nhiệm vụ vẫn `ACTIVE` — spec 001).<br>- `Handover` thêm 2 loại: `RETURN_INTAKE` (điểm tập kết nhận hàng hoàn), `SHOP_PICKUP` (Shop nhận lại hàng).<br>- `Handover` thêm `receiver_name` (tên người nhận phía Shop — chỉ `SHOP_PICKUP`, CHECK). `received_by` vẫn là **Nhân viên ghi nhận**.<br>- Kết quả nhiệm vụ hoàn: `TaskResult(SUCCEEDED)` do **Nhân viên** ghi khi tiếp nhận (UC04.9 bước 6 "đóng nhiệm vụ hoàn"). |
| D2 | **API** | Cùng khuôn 006–007:<br>- NV trên đơn: `assign-return/`, `receive-return/`, `report-return-issue/`, `confirm-shop-received/`.<br>- Shipper trên nhiệm vụ: `report-return-handover/`. |
| D3 | **Phân công hoàn** (UC06.7) | - Hàng ở Shipper X (trường hợp thường, sau giao thất bại) → chỉ phân công **X** (dùng lại `ShipperPicker holder`). Người khác → `409` (spec 009).<br>- **Không** cần ô "đã nhận hàng" (X đang giữ sẵn).<br>- X bị khóa → chặn + cảnh báo (như spec 007 D7).<br>- Hàng **đã ở điểm tập kết** (A1.2 — xảy ra sau đổi Shipper ở spec 009): ẩn "Phân công hoàn", hiện thẳng **"Tiếp nhận hàng hoàn"**. Quy tắc này vào bảng điều kiện `shipments/rules.py` (`ASSIGN_RETURN` cần hàng ở Shipper; `RECEIVE_RETURN` từ Chờ xử lý hoàn cần hàng ở điểm tập kết). |
| D4 | **Shipper báo bàn giao** (UC04.9 bước 1–3, A1) | Nút **"Đã đưa hàng về điểm tập kết"** (hộp xác nhận nêu mã, số kiện) → ghi `handover_reported_at`, báo **mọi Nhân viên** (loại mới `RETURN_HANDOVER_REPORTED`). Đơn **vẫn Đang hoàn**; nhiệm vụ hiện "Đã báo bàn giao lúc … — chờ Nhân viên xác nhận". Gửi lại → trả hiện tại. Shipper **không** có nút xác nhận tiếp nhận (BR1). |
| D5 | **Nhân viên tiếp nhận hàng hoàn** (UC04.9 bước 4–7, E1) | Hộp "Tiếp nhận hàng hoàn" nêu mã, số kiện, mô tả, Shipper giao, **đã báo bàn giao chưa**:<br>- **Xác nhận tiếp nhận** → `Handover(RETURN_INTAKE)` (ghi chú sai lệch tùy chọn), nhiệm vụ `SUCCEEDED`, đơn Chờ Shop đến lấy, hàng ở điểm tập kết, báo Shop `RETURN_AT_HUB`.<br>- Được xác nhận cả khi Shipper **chưa** báo (Shipper quên / bị khóa — checklist mục đổi Shipper điểm 3); hộp hiện cảnh báo.<br>- **Ghi sai lệch, chưa nhận** (E1) → hành động mới `REPORT_RETURN_ISSUE` (Đang hoàn → Đang hoàn), ghi chú bắt buộc vào lịch sử; nhiệm vụ vẫn mở. |
| D6 | **Thông tin điểm tập kết** (UC04.8 bước 3; Shop biết nơi lấy) | Cấu hình trong `settings` đọc từ `.env`: `HUB_NAME`, `HUB_ADDRESS`, `HUB_PHONE` (có giá trị demo). Trả trong `/meta/choices/` nhóm `hub`. Hiện ở nhiệm vụ hoàn (Shipper) và đơn Chờ Shop đến lấy (Shop). |
| D7 | **Shop nhận lại hàng** (UC04.11) | Hộp "Xác nhận Shop đã nhận hàng hoàn":<br>- **Tên người nhận** bắt buộc (điền sẵn tên Shop, sửa được nếu người đại diện);<br>- ô tích bắt buộc **"Đã kiểm tra người nhận thuộc Shop / được Shop ủy quyền"** (bước 3);<br>- ghi chú tùy chọn.<br>→ `Handover(SHOP_PICKUP)`, đơn Đã hoàn về Shop, hàng ở Shop, báo Shop `RETURN_COMPLETED`. Gửi lại → trả hiện tại. Shop **không** tự bấm (BR1). |
| D8 | **Shipper thấy gì ở nhiệm vụ hoàn** (UC04.8) | Mã vận đơn, tên Shop, kiện hàng (mô tả, số kiện, khối lượng), **lý do hoàn** (lý do quyết định hoàn), **điểm tập kết** (D6). **Không** hiện người nhận / COD / SĐT người gửi (không cần để đưa về điểm tập kết). |
| D9 | **Thông báo** | - Phân công hoàn → **Shipper** (`TASK_ASSIGNED`, tiêu đề "Nhiệm vụ hoàn hàng mới").<br>- Shipper báo bàn giao → **mọi NV đang hoạt động** (`RETURN_HANDOVER_REPORTED` — mới).<br>- Tiếp nhận → **Shop** (`RETURN_AT_HUB`, kèm địa chỉ điểm tập kết).<br>- Shop đã nhận → **Shop** (`RETURN_COMPLETED`).<br>Phân công hoàn **không** báo Shop (đặc tả chỉ yêu cầu báo Shipper; Shop đã nhận `RETURN_DECIDED` ở spec 007). |
| D10 | **Màn hình** | **Shipper:** chip "Hoàn hàng" tự có khi thêm `TASK_TYPE.RETURN`; chi tiết hoàn theo `TYPE_VIEW`; trang chủ thêm ô "nhiệm vụ hoàn hàng đang làm"; gỡ "Sắp có: Nhiệm vụ hoàn hàng".<br>**Nhân viên:** hiện đã 7 tab hàng việc, thêm 3 nữa sẽ quá dài → **gộp tab theo giai đoạn**: Chờ xác nhận · **Lấy hàng** · **Giao hàng** · **Hoàn hàng** · Tất cả; mỗi tab giai đoạn có hàng chip trạng thái con (mặc định gồm mọi trạng thái của giai đoạn, cũ nhất trước). API danh sách đã nhận nhiều `status` — không đổi backend.<br>**Shop:** đơn Chờ Shop đến lấy có ô "Hàng hoàn đang ở điểm tập kết — đến nhận tại …"; Đã hoàn về Shop có thẻ "Kết quả hoàn" (thời gian, người nhận). |

## 3. Backend

### 3.1. Model / cấu hình

Chi tiết: [models.md](models.md).
- `HandoverKind` + `RETURN_INTAKE`, `SHOP_PICKUP`; `Handover.receiver_name` + CHECK (có ⇔ `SHOP_PICKUP`).
- `ShipmentAction.REPORT_RETURN_ISSUE` (`RETURNING → RETURNING`, ADMIN) và `REPORT_RETURN_HANDOVER` (`RETURNING → RETURNING`, SHIPPER) — hai thao tác không đổi trạng thái nhưng cần mốc lịch sử, đi qua bảng như `UPDATE_REQUEST` (spec 004).
- `NotificationKind.RETURN_HANDOVER_REPORTED`.
- `settings.HUB` (tên, địa chỉ, SĐT) từ `.env`; `/meta/choices/` nhóm `hub`.
- Migration đổi `choices` (SQL rỗng) cho `handover.kind`, `shipmentevent.action`, `notification.kind`; cột `receiver_name`.

### 3.2. Service (`dispatch/services.py`)

Khuôn spec 006–007: khóa đơn → user / nhiệm vụ; "đã xong" → trạng thái → `updated_at`; một transaction; dùng lại `_resend_of_assignment`, `_lock_available_shipper`, `_create_task`, `_holder_value`, `_staff_decision`/`check_staff_action`, `_lock_own_task`.

| Hàm | Việc làm |
|---|---|
| `assign_return(staff, shipment_id, shipper_id, expected_updated_at)` | `ASSIGN_RETURN` + điều kiện bảng (hàng ở Shipper); chỉ người đang giữ (D3); Shipper hoạt động; `Task(RETURN)`; đơn Đang hoàn; báo Shipper. |
| `report_return_handover(shipper, task_id)` | Nhiệm vụ RETURN của mình, `ACTIVE`; đã báo → trả hiện tại; ghi `handover_reported_at`; lịch sử (không đổi trạng thái); báo NV. |
| `receive_return(staff, shipment_id, discrepancy_note, expected_updated_at)` | `RECEIVE_RETURN` + điều kiện bảng. Có nhiệm vụ hoàn mở → `TASK_SUCCEED` + `TaskResult` (NV ghi); `Handover(RETURN_INTAKE)`; đơn Chờ Shop đến lấy, hàng ở điểm tập kết; báo Shop. Gửi lại → trả hiện tại. |
| `report_return_issue(staff, shipment_id, note, expected_updated_at)` | `REPORT_RETURN_ISSUE`: chỉ ghi lịch sử (ghi chú bắt buộc); không đổi trạng thái, nhiệm vụ vẫn mở. |
| `confirm_shop_received(staff, shipment_id, receiver_name, note, expected_updated_at)` | `CONFIRM_SHOP_RECEIVED`; `Handover(SHOP_PICKUP)`; đơn Đã hoàn về Shop, hàng ở Shop; báo Shop. Gửi lại → trả hiện tại. |

### 3.3. Hiển thị

- Shipper: `TASK_SHIPMENT_VIEWS[RETURN]` = `ReturnShipmentBrief/DetailSerializer` (D8, kèm `return_reason`); `allowed_actions` của nhiệm vụ hoàn lấy từ bảng như mọi loại (`REPORT_RETURN_HANDOVER` cho SHIPPER ở Đang hoàn), **bỏ đi khi đã báo** (`handover_reported_at` có giá trị).
- NV: `tasks[].handover_reported_at`; Shop + NV: `return_result` = `{received_at, receiver_name}` khi Đã hoàn về Shop (cùng cách `delivery`).

## 4. Frontend

| Route / chỗ | Thay đổi |
|---|---|
| `TaskListView`, `TaskDetailView` (Shipper) | `TASK_TYPE.RETURN` → chip "Hoàn hàng"; `TYPE_VIEW[RETURN]`: thẻ "Đưa về điểm tập kết" (tên, địa chỉ, SĐT điểm tập kết), lý do hoàn, nút "Đã đưa hàng về điểm tập kết"; sau khi báo: dòng chờ NV xác nhận. |
| `ShipperHomeView` | Ô thứ 3 "nhiệm vụ hoàn hàng đang làm"; gỡ "Sắp có: Nhiệm vụ hoàn hàng". |
| `StaffShipmentListView` | Gộp tab theo giai đoạn + chip trạng thái con (D10). |
| `StaffShipmentDetailView` | `ACTION_BUTTONS` + Phân công hoàn (`ShipperPicker holder`), Tiếp nhận hàng hoàn (ghi chú sai lệch + nút "Ghi sai lệch, chưa nhận"), Xác nhận Shop đã nhận (tên người nhận, ô tích). Điều phối: nhiệm vụ hoàn + "đã báo bàn giao lúc …". |
| `ShipmentInfoCards`, chi tiết Shop | Ô "đến nhận tại điểm tập kết"; thẻ "Kết quả hoàn". |

Mã mới vào `shipmentActions.js` (`SHIPMENT_ACTION` +5, `TASK_TYPE.RETURN`) + test đối chiếu backend; thông tin điểm tập kết lấy từ `meta.hub`.

## 5. Tiêu chí nghiệm thu

**11/12 đạt** — bằng chứng: `apps/dispatch/tests/test_return_models.py`, `test_staff_return.py`, `test_shipper_return.py` (38 test, gồm 4 test song song thật + 1 test thứ tự khóa), đột biến có mốc (backend 7/7, 14/15, 9/10 — 2 tương đương; frontend 10/10, 16/16), `EXPLAIN`, smoke 17/17; xem nhật ký [tasks.md](tasks.md).

- [x] Phân công hoàn chỉ từ Chờ xử lý hoàn, chỉ Shipper đang giữ hàng, Shipper hoạt động, không hai nhiệm vụ mở; không đặt Đã hoàn về Shop; báo Shipper.
- [x] Hàng đã ở điểm tập kết khi Chờ xử lý hoàn → không phân công được, tiếp nhận thẳng được (không chuyến hoàn thừa).
- [x] Shipper chỉ thấy nhiệm vụ hoàn của mình (khác → `404`); thấy điểm tập kết, lý do hoàn; không thấy người nhận / COD.
- [x] Shipper báo bàn giao: đơn vẫn Đang hoàn, nhiệm vụ vẫn mở, NV được báo; gửi lại không ghi trùng; Shipper không xác nhận thay NV.
- [x] NV tiếp nhận: ghi người giao / nhận / thời gian / sai lệch; nhiệm vụ đóng; Chờ Shop đến lấy; hàng ở điểm tập kết; báo Shop; gửi lại không ghi trùng.
- [x] NV ghi sai lệch chưa nhận: ghi chú bắt buộc, trạng thái và nhiệm vụ giữ nguyên.
- [x] Xác nhận Shop nhận: tên người nhận + ô tích bắt buộc; Đã hoàn về Shop; hàng ở Shop; báo Shop; gửi lại không ghi trùng; Shop không gọi được.
- [x] Ràng buộc DB `receiver_name` ⇔ `SHOP_PICKUP` (đột biến trên migration).
- [x] Đồng thời (2 luồng thật): 2 NV cùng tiếp nhận → 1 bàn giao; tiếp nhận vs Shipper báo bàn giao.
- [x] Bảng chuyển trạng thái khớp checklist (thêm `REPORT_RETURN_ISSUE`, `REPORT_RETURN_HANDOVER`); không N+1; `EXPLAIN` tab Hoàn hàng (nhiều trạng thái).
- [x] Toàn luồng checklist "Hoàn hàng": giao thất bại → quyết định hoàn → phân công hoàn → Shipper bàn giao → NV nhận → Chờ Shop đến lấy → NV xác nhận Shop nhận → Đã hoàn về Shop (smoke API + bấm thật).
- [ ] Frontend: Vitest pass, build, ảnh chụp 1440/390, thử trình duyệt theo `manual-test.md`. → Vitest 310 + build ✔, ảnh chụp 1440/390, lượt bấm thật 12/12; **còn người dùng thử** ([manual-test.md](manual-test.md), 37 bước).

## 6. Ghi chú cho spec sau

- **Spec 009 đã xử lý (23/11/2026):** Chờ xử lý hoàn, không nhiệm vụ mở mà hàng ở Shipper → NV nhận về điểm tập kết,
  hàng ở `HUB`, tiếp nhận hoàn thẳng (A1.2), không tạo chuyến hoàn thừa; hết `holder_locked`.
  - D3 spec 009 **không đổi người trên nhiệm vụ hoàn đang mở**: dùng Tiếp nhận hàng hoàn, kể cả người cũ bị khóa/chưa báo.
    Test nhiệm vụ hoàn `REPLACED` là chặn dữ liệu bất thường, không phải một nhánh đổi người hợp lệ.
  - Helper báo đưa hàng về dùng chung với báo bàn giao đổi người; khóa đơn → người ghi → nhiệm vụ,
    kiểm lại tài khoản sau khi chờ khóa, tránh deadlock với khóa tài khoản. Không đổi hợp đồng API báo hoàn.
- **Giao diện:** chi tiết đơn của NV chưa có trường "lý do hoàn" riêng — hộp phân công hoàn chỉ dẫn sang mục Lịch sử. Nếu cần, thêm `return_reason` cho NV như phía Shipper (một truy vấn).

**Việc có từ trước, không thuộc spec này (ghi lại khi nghiệm thu):** lịch sử vận đơn của Shop hiện tên Nhân viên / Shipper thực hiện từng mốc (từ spec 004–005); 16 cảnh báo Vue Router trong test màn tài khoản (spec 003); 404 `favicon.ico`.
