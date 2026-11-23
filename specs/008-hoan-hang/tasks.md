# Spec 008 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi".

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung (bài học 004–007):
- Docker DB đang chạy. **Không tắt server người dùng** (8000 / 5173); cần server thì bật 8010 / 5180 và tắt đúng tác vụ của mình.
- Smoke gửi `Origin`/`Referer`; script chụp: `MSYS_NO_PATHCONV=1`, tham số tách bằng `|`.
- Dữ liệu thử phải dọn; script rollback / `EXPLAIN` chạy bằng `manage.py shell -c "exec(...)"` (không nạp qua stdin) và **kiểm dòng "sequence giữ nguyên"**.
- Thêm giá trị enum → migration đổi `choices`; đột biến ràng buộc DB sửa **file migration**.
- Script đột biến dùng `sys.executable` và **chạy mốc chưa đột biến phải pass** trước.
- Hàm tiện ích trong lớp test không trùng tên method `TestCase`.

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D10 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt); đặc biệt D5 (NV tiếp nhận được khi Shipper chưa báo; nút ghi sai lệch), D6 (thông tin điểm tập kết từ `.env`), D7 (tên người nhận + ô tích), D10 (gộp tab Nhân viên theo giai đoạn). → Cả 10 điểm theo đề xuất; D5/D6/D10 hỏi riêng, đều chọn đề xuất.

Xong khi: mục 2 ghi rõ phương án đã chốt; models.md / api.md bỏ chữ "bản nháp".

---

## Phase 1 — Backend: model, migration, cấu hình

- [x] **1.1** `HandoverKind` +2, `ShipmentAction.REPORT_RETURN_ISSUE` / `REPORT_RETURN_HANDOVER` + dòng bảng, `NotificationKind.RETURN_HANDOVER_REPORTED`; hằng số thông điệp / tiêu đề.
- [x] **1.2** `Handover.receiver_name` + CHECK; `verbose_name` `received_by`.
- [x] **1.3** `settings.HUB` từ `.env` (+ `.env.example`); `/meta/choices/` nhóm `hub`.
- [x] **1.4** Migration; `migrate` local.
- [x] **1.5** Test: CHECK `receiver_name`; bảng chuyển trạng thái khớp checklist; `/meta/choices/` nhóm mới.

  → 6 test ở `dispatch/tests/test_return_models.py`; `test_transitions_table` thêm 2 dòng + 1 test vai trò ở Đang hoàn; `test_choices` thêm nhóm `hub`.

Xong khi: test pass; `makemigrations --check` sạch; đột biến trên migration bị bắt.

---

## Phase 2 — Backend: Nhân viên

- [x] **2.1** Bảng điều kiện `shipments/rules.py`: `ASSIGN_RETURN` cần hàng ở Shipper; `RECEIVE_RETURN` từ Chờ xử lý hoàn cần hàng ở điểm tập kết.
- [x] **2.2** Service `assign_return`, `receive_return`, `report_return_issue`, `confirm_shop_received` (dùng lại helper 006–007).
- [x] **2.3** 4 endpoint; chi tiết đơn `tasks[].handover_reported_at`, `return_result`.
- [x] **2.4** Test: từng hành động (thành công, sai trạng thái, `updated_at` cũ, gửi lại, quyền); A1.2 tiếp nhận thẳng; chỉ người giữ hàng; thông báo đúng người; 2 luồng (2 NV cùng tiếp nhận).

  → 18 test ở `dispatch/tests/test_staff_return.py` (gồm 2 test 2 luồng thật: 2 NV cùng tiếp nhận; 2 NV cùng xác nhận Shop nhận).

Xong khi: test pass; đột biến (bỏ điều kiện nơi giữ hàng, bỏ đóng nhiệm vụ, bỏ ô tích, bỏ khóa) bị bắt.

---

## Phase 3 — Backend: Shipper

- [x] **3.1** `TASK_SHIPMENT_VIEWS[RETURN]` (D8, `return_reason`); `handover_reported_at` trong nhiệm vụ; `allowed_actions` nhiệm vụ hoàn.
- [x] **3.2** Service + endpoint `report_return_handover` (thứ tự khóa đơn → nhiệm vụ; báo NV).
- [x] **3.3** Test: chỉ nhiệm vụ của mình; gửi lại; nhiệm vụ đóng → `409`; không lộ người nhận/COD; 2 luồng (Shipper báo vs NV tiếp nhận); `EXPLAIN` tab Hoàn hàng (nhiều trạng thái).
- [x] **3.4** Smoke toàn luồng checklist "Hoàn hàng" qua API; dọn dữ liệu.

  → 14 test ở `dispatch/tests/test_shipper_return.py` (gồm 2 test song song thật + 1 test thứ tự khóa); smoke **17/17**.

Xong khi: test pass; `EXPLAIN` ghi nhật ký.

---

## Phase 4 — Frontend: nền

- [x] **4.1** Service (`assignReturn`, `receiveReturn`, `reportReturnIssue`, `confirmShopReceived`, `reportReturnHandover`).
- [x] **4.2** `SHIPMENT_ACTION` +5, `TASK_TYPE.RETURN`; `meta.hub`; test đối chiếu backend.
- [x] **4.3** Component dùng lại / mới nếu cần (thẻ điểm tập kết).

  → `components/dispatch/HubCard.vue` (thẻ điểm tập kết từ `meta.hub`, có slot cho nội dung riêng mỗi màn); `meta.hub`; test: `HubCard.spec.js` (3), service (+2), store (+1).

Xong khi: test pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** Shipper: chi tiết hoàn (`TYPE_VIEW[RETURN]`), báo bàn giao, trang chủ ô thứ 3.
- [x] **5.2** Nhân viên: tab gộp theo giai đoạn + chip con; 3 nút/hộp mới; Điều phối nhiệm vụ hoàn.
- [x] **5.3** Shop: ô đến nhận tại điểm tập kết, thẻ "Kết quả hoàn".
- [x] **5.4** Vitest; ảnh 1440 + 390; bấm thật toàn luồng hoàn.

  → Ảnh 1440px: tab Hoàn hàng + chip, hộp phân công hoàn, hộp tiếp nhận (cảnh báo chưa báo), hộp Shop nhận, đơn Đã hoàn về Shop; Shop: thẻ đến nhận + kết quả hoàn. Ảnh 390px: trang chủ 3 ô, danh sách hoàn, chi tiết, hộp xác nhận, trạng thái chờ NV. Bấm thật 12/12.

Xong khi: test pass; build; 0 cảnh báo Vue.

---

## Phase 6 — Nghiệm thu

- [x] **6.1** `check`, `makemigrations --check`, backend xuôi + ngược; Vitest, audit, build. → `check` sạch, không migration mới, backend **476/476** xuôi + ngược, Vitest **310/310** (0 `[Vue warn]`), audit production 0, build OK (thư mục tạm).
- [x] **6.2** Rà hardcode. → Frontend sạch (không mã viết thẳng ngoài file cho phép, không hex, không `maxlength` số — giới hạn tên người nhận lấy từ `limits`). Backend: thông điệp / tiêu đề ở `constants.py`; giá trị demo điểm tập kết chỉ là mặc định trong `settings.HUB`, cấu hình thật qua `.env`.
- [ ] **6.3** `manual-test.md` + người dùng thử trình duyệt. → [manual-test.md](manual-test.md) sẵn sàng (37 bước, 9 nhóm; dùng lại đơn 3, 4 cuối kịch bản spec 007 nếu đã thử; đối chiếu từng "Mong đợi" với code). **Chờ người dùng.**
- [x] **6.4** Đánh dấu tiêu chí; `specs/README.md`, README gốc; ghi chú cho spec 009. → 11/12 tiêu chí `[x]`; README gốc có cách cấu hình điểm tập kết; spec.md mục 6 thêm 3 điểm cho spec 009 + 1 điểm giao diện (lý do hoàn ở màn NV).

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 22/11/2026 | — | Lập spec, chờ chốt D1–D10. Đối chiếu code: 3 hành động hoàn đã có trong bảng trạng thái (NV đã nhận `ASSIGN_RETURN`/`RECEIVE_RETURN` trong `allowed_actions` nhưng chưa có nút); `TaskType.RETURN`, `handover_reported_at`, 2 loại thông báo hoàn đã có; **chưa có thông tin điểm tập kết** ở đâu cả (D6). |
| 22/11/2026 | 0 | **Xong.** Người dùng chốt D1–D10 theo đề xuất (D5 tiếp nhận được khi Shipper chưa báo + cảnh báo; D6 điểm tập kết trong `.env`; D10 gộp tab theo giai đoạn + chip con). Kiểm giả định: `load_dotenv` + `.env.example` có sẵn; `TASK_SUCCEED` cho ADMIN; `RECEIVE_RETURN` nhận cả Đang hoàn lẫn Chờ xử lý hoàn; API danh sách nhận nhiều `status`. Làm rõ: tập trạng thái của từng tab giai đoạn (giữ nguyên các trạng thái NV cần xử lý + 3 trạng thái hoàn), khóa URL mới, cần đo `EXPLAIN` cho lọc nhiều trạng thái. |
| 22/11/2026 | 1 | **Xong.** `HandoverKind` +`RETURN_INTAKE`, `SHOP_PICKUP`; `Handover.receiver_name` + CHECK (có ⇔ Shop nhận, `isnull` tường minh); `received_by` đổi nhãn "nhân viên ghi nhận"; `ShipmentAction.REPORT_RETURN_HANDOVER` (SHIPPER) / `REPORT_RETURN_ISSUE` (ADMIN), cả hai Đang hoàn → Đang hoàn; `NotificationKind.RETURN_HANDOVER_REPORTED`; thông điệp / tiêu đề / động từ chặn cho 4 thao tác NV; `settings.HUB` (tên, địa chỉ, SĐT từ `.env`, có giá trị demo; **không sửa `.env` của người dùng**, chỉ `.env.example`), `/meta/choices/` nhóm `hub`. 3 migration áp dụng local (0 dòng bàn giao trước khi tạo lại CHECK).<br>- Test bảng "khớp checklist" thêm 2 cạnh tự lặp Đang hoàn — không có trong bảng mục 4 của checklist, ghi rõ nguồn UC04.9 và tiền lệ "Sửa yêu cầu" (spec 004).<br>- Backend **444/444** (437 + 7), xuôi + ngược; Vitest 292/292 (test đọc `constants.py` backend vẫn khớp).<br>- **Đột biến 7/7 bị bắt** (có mốc): 3 trên file migration (bỏ `isnull`, cho tên rỗng, loại khác có tên), 3 trên bảng trạng thái (Shipper ghi sai lệch, NV báo bàn giao thay, báo bàn giao ngoài Đang hoàn), 1 bỏ `hub`. |
| 22/11/2026 | 2 | **Xong.** `assign_return` (chỉ khi hàng ở Shipper, chỉ người đang giữ, báo Shipper kèm địa chỉ điểm tập kết), `receive_return` (đóng nhiệm vụ hoàn — NV ghi kết quả; bàn giao `RETURN_INTAKE`; hàng về điểm tập kết; báo Shop kèm địa chỉ + SĐT; tiếp nhận thẳng khi hàng đã ở điểm tập kết — A1.2), `report_return_issue` (chỉ ghi lịch sử + tăng phiên bản đơn, nhiệm vụ vẫn mở), `confirm_shop_received` (bàn giao `SHOP_PICKUP` + tên người nhận; hàng về Shop; báo Shop). Bảng điều kiện `shipments/rules.py` thêm `goods_with_shipper` / `return_receivable` + `guard_allows` dùng chung cho nút và service.<br>- `HOLDER_ONLY_MESSAGE` đổi chữ "giao bằng người khác" → "dùng người khác" để dùng chung cho giao lại lẫn hoàn.<br>- Gửi lại của "ghi sai lệch": không thể dùng cách cũ (trạng thái đích + mốc cuối cùng loại) vì hành động tự lặp — mọi lần ghi sau đều bị coi là gửi lại; chuyển sang so **cùng người + cùng ghi chú** với mốc cuối.<br>- Backend **462/462** (444 + 18), xuôi + ngược; không migration mới. Sắp xếp lại khối import `dispatch/services.py` (1 dòng do tôi chèn sai chỗ, 2 dòng `shipments.constants` tách đôi có từ trước).<br>- **Đột biến 14/15 bị bắt** (có mốc). Sống: bỏ lọc loại bàn giao khi lấy `return_result` — **tương đương** (khi Đã hoàn về Shop, bàn giao mới nhất luôn là Shop nhận); giữ điều kiện để rõ ý định. |
| 22/11/2026 | 3 | **Xong — backend spec 008 hoàn tất.** Nhiệm vụ hoàn cho Shipper: `TASK_SHIPMENT_VIEWS[RETURN]` (mã, Shop, kiện hàng; chi tiết thêm khối lượng, ghi chú, lý do hoàn); không người nhận / COD / SĐT. `report_return_handover`: ghi `handover_reported_at` + mốc `REPORT_RETURN_HANDOVER` + báo mọi NV; nhiệm vụ mở, đơn Đang hoàn; không tăng phiên bản đơn (NV đang mở hộp tiếp nhận không bị 409). `TASK_ONE_TIME_ACTIONS` bỏ nút đã làm.<br>- Backend **476/476** (462 + 14), xuôi + ngược; không migration mới.<br>- **Đột biến (có mốc): 7/10 → 9/10.** Sống lần đầu: (1) bỏ chặn nhiệm vụ đã đóng — bảng trạng thái đang chặn thay, nhưng spec 009 sẽ có nhiệm vụ hoàn bị thay người (đã đóng) khi đơn vẫn Đang hoàn → thêm test mô phỏng; (2) lý do hoàn lấy nhầm mốc khác — thêm test có ghi sai lệch sau quyết định hoàn. Còn sống: bỏ chặn loại nhiệm vụ — **tương đương** (đơn Đang hoàn chỉ có một nhiệm vụ mở và là nhiệm vụ hoàn; nhiệm vụ khác đều đã đóng).<br>- **`EXPLAIN` 30.000 đơn / 30.900 nhiệm vụ** (rollback, chạy bằng `exec`, "sequence giữ nguyên: True"): tab Hoàn hàng 3 trạng thái cũ nhất trước — Index Scan ngược `ship_created_idx` + lọc (bỏ 186 dòng), 0,13 ms; chip một trạng thái — `ship_status_created_idx`, 0,07 ms; nhiệm vụ hoàn của Shipper — Bitmap `task_shipper_assigned_idx` + Sort 25 dòng, 0,95 ms → **không thêm index**.<br>- Smoke API 17/17 trên Django 8010: toàn kịch bản checklist "Hoàn hàng" (kèm ghi sai lệch, bấm lại, Shop không tự xác nhận, đủ thông báo Shop/NV, đủ mốc lịch sử). Dọn 1 đơn + 3 nhiệm vụ / 3 kết quả / 3 bàn giao / 14 thông báo, sequence về như cũ; đã tắt đúng tác vụ server 8010.<br>- **Ghi cho Phase 5:** màn Shipper hiện chưa biết loại RETURN (rơi về khung lấy hàng) — chưa gặp vì NV chưa có nút phân công hoàn trên giao diện. |
| 23/11/2026 | 4 | **Xong.** `shipmentService` +4 (`assignReturn`, `receiveReturn`, `reportReturnIssue`, `confirmShopReceived` — luôn gửi `verified: true`, màn hình chỉ gọi sau khi NV tích), `taskService.reportReturnHandover`; `SHIPMENT_ACTION` +5, `TASK_TYPE.RETURN`, `HOLDER_TYPE.HUB` (test đối chiếu backend có sẵn tự kiểm mã mới); `meta.hub`; `HubCard`. Chip "Hoàn hàng" ở danh sách Shipper tự có nhờ `TASK_TYPE` (cập nhật 1 test + dữ liệu mẫu `task_types`).<br>- **Sửa lệch quy ước do tôi ở spec 007:** test `CodInput` + chế độ người giữ hàng của `ShipperPicker` từng nằm chung `components/__tests__/DispatchInputs.spec.js`, trong khi dự án đặt test theo thư mục (`components/dispatch/__tests__/ShipperPicker.spec.js` đã có) → tách thành `CodInput.spec.js` + gộp 2 test vào `ShipperPicker.spec.js`; helper `mountWithModel` chuyển vào `src/test-utils.js` dùng chung. Tổng số test giữ nguyên (đã đối chiếu 292 trước khi thêm test mới).<br>- Vitest **298/298** (292 + 6), 0 `[Vue warn]`; build OK (thư mục tạm).<br>- **Đột biến 10/10 bị bắt** (có mốc), gồm cả đột biến helper dùng chung (bỏ giá trị phát lúc dựng → test COD đơn không thu bắt).<br>- **Ghi cho Phase 5:** chip "Hoàn hàng" đã hiện nhưng thẻ / chi tiết nhiệm vụ hoàn chưa có khung riêng (đang rơi về khung lấy hàng) — chưa gặp vì NV chưa có nút phân công hoàn trên giao diện. |
| 23/11/2026 | 5 | **Xong — frontend spec 008 hoàn tất.** Shipper: `TYPE_VIEW[RETURN]` (một thao tác "Đã đưa hàng về điểm tập kết"), thẻ `HubCard` "Đưa hàng về" + lý do hoàn, dòng "đã báo — chờ NV xác nhận" (A1); thẻ danh sách hoàn (Shop, "Về <điểm tập kết>", cờ chờ xác nhận); trang chủ ô thứ 3, gỡ "Sắp có: hoàn hàng". Nhân viên: **tab gộp theo giai đoạn** (Chờ xác nhận · Lấy · Giao · Hoàn · Tất cả; nhãn giai đoạn = nhãn loại nhiệm vụ từ meta) + chip trạng thái con (chip không tính là "bộ lọc"; trạng thái ngoài giai đoạn trên URL bị bỏ); 4 nút/hộp (phân công hoàn chỉ người giữ, tiếp nhận + cảnh báo khi Shipper chưa báo + "Có sai lệch, chưa nhận?", ghi sai lệch dùng chung hộp lý do, Shop nhận điền sẵn tên Shop + ô tích); Điều phối hiện thời điểm Shipper báo. Shop: thẻ "Đến nhận hàng hoàn tại" khi Chờ Shop đến lấy; `ShipmentInfoCards` thẻ "Kết quả hoàn".<br>- Backend: `limits.handover_receiver_name_max_length` (không viết 100 ở frontend).<br>- Vitest **310/310**, 0 `[Vue warn]`, build OK. **Đột biến 16/16** (có mốc).<br>- Một lần chạy Vitest có 1 test `accountService` (spec 003, không liên quan) ghi thời gian 966.738 ms rồi lỗi — chạy lại riêng 4/4 trong 3 giây, cả bộ 299/299 → sự cố nhất thời của máy (treo/ngủ), không phải lỗi code.<br>- **Test bắt thiếu sót dữ liệu mẫu:** `limits` mẫu thiếu giới hạn tên người nhận → bổ sung cho khớp backend.<br>- **Lỗi do tôi, đã sửa:** tiến trình Vite cổng 5180 của tôi từ spec 007 **vẫn chạy** dù đã báo là đã tắt — `TaskStop` chỉ dừng lớp `npx`, tiến trình `node` con còn sống (lộ ra khi Vite mới báo cổng bận mà seed qua 5180 vẫn chạy). Kiểm dòng lệnh / cổng / thời điểm tạo xác nhận là của tôi → dừng theo PID; từ giờ chạy Vite bằng `node …/vite.js` và **kiểm cổng trống sau khi tắt** (đã kiểm: 8010, 5180 trống, không tiến trình sót). Ghi bộ nhớ.<br>- **Lượt bấm thật 12/12** (lần đầu 10/12: script của tôi đọc chữ trước khi trang tải xong — sửa bằng cách đợi phần tử khác báo trang đã tải rồi mới kiểm, chạy lại trên đơn khác). Dọn 6 đơn + 18 nhiệm vụ / 16 kết quả / 13 bàn giao / 73 thông báo; sequence về như cũ. |
| 23/11/2026 | 6 | Nghiệm thu: backend 476/476 xuôi + ngược, Vitest 310/310, 0 `[Vue warn]`, audit 0, build OK (máy chạy chậm hơn thường — backend 234 giây lần xuôi — nhưng đều pass). Rà hardcode sạch. **11/12 tiêu chí đạt**; còn thử trình duyệt theo `manual-test.md` (37 bước). Ghi lại việc có từ trước không thuộc spec này: lịch sử của Shop hiện tên người thực hiện từng mốc (spec 004–005), 16 cảnh báo Vue Router (spec 003), 404 `favicon.ico`. Không bật/tắt server người dùng; đã kiểm 8010 / 5180 trống. |
