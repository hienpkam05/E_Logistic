# Spec 006 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi".

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung:
- Docker DB đang chạy. **Không tắt server người dùng**; cần server thì bật cổng riêng và tắt đúng tác vụ của mình.
- Smoke test gửi `Origin`/`Referer`.
- Dữ liệu thử phải dọn; script đo `EXPLAIN` phải **đặt lại sequence** sau khi rollback (bài học spec 005).

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D10 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt). → Cả 10 điểm theo đề xuất; D4 dùng danh sách 6 lý do.

Xong khi: mục 2 ghi rõ phương án đã chốt.

---

## Phase 1 — Backend: model, migration, danh mục

- [x] **1.1** Enum `PickupFailReason`, `HandoverKind`; `NotificationKind.PICKUP_RETRY`; đăng ký `/meta/choices/`; hằng số (độ dài, thông điệp).
- [x] **1.2** Model `Task`, `TaskResult`, `Handover`; `ShipmentEvent.task`; partial unique + CHECK; admin chỉ xem.
- [x] **1.3** Migration theo thứ tự `shipments 0002 → dispatch 0001 → shipments 0003`; kiểm không có index FK thừa; `migrate` DB local.
- [x] **1.4** Test:
  - ràng buộc DB (2 nhiệm vụ mở cùng đơn bị chặn; `closed_at` ⇔ kết thúc; kết quả thứ 2 bị chặn);
  - bảng chuyển trạng thái đơn + nhiệm vụ vẫn khớp checklist;
  - `/meta/choices/` có nhóm mới.

  → 11 test ở `dispatch/tests/test_models.py`. Index chỉ đúng 3 cái dự định (2 ghép cho Task + FK `handover.shipment`), các FK không truy vấn để `db_index=False`.

Xong khi: test pass; `makemigrations --check` sạch.

---

## Phase 2 — Backend: Nhân viên phân công, nhập điểm tập kết, xử lý lấy thất bại

- [x] **2.1** Service `assign_pickup`, `receive_at_hub`, `retry_pickup`, `abandon_pickup` (khóa đơn → nhiệm vụ / user; kiểm bảng; `updated_at`; thông báo).
- [x] **2.2** `GET /dispatch/shippers/` (`open_task_count` bằng `annotate`, một truy vấn); 4 endpoint hành động trên đơn.
- [x] **2.3** Chi tiết đơn cho Nhân viên: `holder_shipper`, `tasks` (không N+1); Shop không nhận `tasks`.
- [x] **2.4** Hook khóa tài khoản (spec 003): `needs_attention` + `ACCOUNT_LOCKED_TASKS` (D9).
- [x] **2.5** Test:
  - từng hành động: thành công, sai trạng thái, `updated_at` cũ, gửi lại;
  - Shipper bị khóa / không phải Shipper;
  - quyền;
  - test 2 luồng: 2 NV cùng phân công → 1 nhiệm vụ; phân công vs khóa Shipper.

  → 23 test ở `dispatch/tests/test_staff_pickup.py` (gồm 3 test 2 luồng).

Xong khi: test pass; đột biến (bỏ khóa, bỏ partial unique, bỏ kiểm Shipper hoạt động) bị bắt.

---

## Phase 3 — Backend: Shipper

- [x] **3.1** `tasks_visible_to`; `shipments_visible_to` thêm nhánh SHIPPER.
- [x] **3.2** `GET /dispatch/tasks/`, `GET /dispatch/tasks/{id}/` (D3: không lộ người nhận/COD), `confirm-pickup/`, `fail-pickup/`.
- [x] **3.3** Service `confirm_pickup`, `fail_pickup` (khóa đơn → nhiệm vụ; người phụ trách; gửi lại; `TaskResult`; holder; thông báo).
- [x] **3.4** Test:
  - Shipper khác / nhiệm vụ đã đóng → 404 / 409;
  - lý do OTHER cần ghi chú;
  - holder đúng;
  - thông báo đúng người;
  - test 2 luồng: Shipper xác nhận vs NV xử lý đơn;
  - không N+1;
  - `EXPLAIN` danh sách nhiệm vụ của Shipper.
- [x] **3.5** Smoke end-to-end bằng API: duyệt → phân công → lấy được → nhập điểm tập kết; nhánh lấy thất bại → lấy lại → phân công lại → kết thúc; dọn dữ liệu + đặt lại sequence.

  → 18 test ở `dispatch/tests/test_shipper_pickup.py` (gồm 2 test song song). Smoke 13/13 trên Django riêng cổng 8010.

Xong khi: test pass; `EXPLAIN` ghi vào nhật ký.

---

## Phase 4 — Frontend: nền

- [x] **4.1** `taskService` (tasks, confirmPickup, failPickup); `shipmentService` thêm 4 hành động + `dispatchService.shippers`.
- [x] **4.2** `SHIPMENT_ACTION` thêm mã mới; `TASK_ACTION` nếu cần (test đối chiếu backend).
- [x] **4.3** Route `/shipper/tasks`, `/shipper/tasks/:id` (`ROLES.SHIPPER`), menu Shipper; `ROLE_SHIPMENT_DETAIL` / liên kết thông báo cho Shipper mở nhiệm vụ.
  → `notificationLinkFor(role, payload)` trong `roles.js`: Shipper mở theo `task_id`, vai trò khác theo `shipment_id`; màn Thông báo dùng hàm này. 2 view Shipper tạm (Phase 5 thay).
- [x] **4.4** Component dùng lại: `ShipperPicker.vue` (danh sách Shipper + số nhiệm vụ mở, tìm), `TaskStatusBadge` dùng `StatusBadge` nhóm `task_statuses`.
  → `ShipperPicker`: tìm chỉ gọi API khi ngừng gõ (250 ms), chặn kết quả cũ, "Đang rảnh" / "N nhiệm vụ đang mở", trống → hướng dẫn UC06.5 A1. **Không tạo `TaskStatusBadge`** — `StatusBadge` đã nhận `group="task_statuses"` (màu ở `statusTones.js`), thêm component là thừa.
- [x] **4.5** Test service/component; **test router thật** cho route mới (bài học spec 005).

Xong khi: test pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** `TaskListView` (Shipper): tab Đang làm / Đã xong, thẻ dễ bấm trên điện thoại, trống / lỗi / tải lại.
- [x] **5.2** `TaskDetailView` (Shipper):
  - thông tin lấy hàng, gọi điện;
  - "Đã lấy hàng" (hộp xác nhận), "Lấy hàng thất bại" (lý do + ghi chú, Khác bắt buộc ghi chú);
  - `409` / `404` → tải lại / báo đã chuyển.
- [x] **5.3** Màn Nhân viên:
  - tab hàng việc;
  - nút Phân công (hộp `ShipperPicker`), Xác nhận tiếp nhận, Lấy lại / Kết thúc;
  - thẻ Điều phối thật; cảnh báo `needs_attention`.
- [x] **5.4** Trang chủ Shipper: ô "N nhiệm vụ đang làm".
- [x] **5.5** Test Vitest; ảnh chụp 1440px + **390px** (màn Shipper); một lượt bấm thật end-to-end NV phân công → Shipper lấy → NV nhận.

  → Ảnh chụp 1440px (danh sách tab hàng việc, hộp phân công, hộp tiếp nhận, đơn lấy thất bại) + **390px** (trang chủ, danh sách, chi tiết có thanh thao tác dính đáy, hộp lý do). Lượt bấm thật: NV phân công → Shipper (điện thoại) "Đã lấy hàng" → NV xác nhận tiếp nhận kèm ghi chú sai lệch.

Xong khi: test pass; build; 0 cảnh báo Vue.

---

## Phase 6 — Nghiệm thu

- [x] **6.1** `check`, `makemigrations --check`, toàn bộ test backend; `npm run test`, audit, build. → `check` sạch, không migration mới, backend 376/376 (**xuôi + ngược** thứ tự), Vitest 262/262 (0 cảnh báo Vue), audit production 0, build OK.
- [x] **6.2** Rà hardcode. → Sửa 2 chỗ backend: `"Shipper khác"` viết thẳng ở nhánh DB chặn trùng → `ALREADY_ASSIGNED_UNKNOWN_NAME`; mẫu ghép "lý do — ghi chú" bằng f-string → `FAIL_REASON_WITH_NOTE`. Frontend sạch (mã chỉ ở file cho phép, không hex, không `maxlength` số). Tên route trong view giữ theo quy ước dự án (đã có test router thật).
- [ ] **6.3** `manual-test.md` (3 cửa sổ: Shop / NV / Shipper) + người dùng thử trình duyệt. → [manual-test.md](manual-test.md) sẵn sàng (41 bước, 9 nhóm; Shipper mở cỡ điện thoại; nhóm H khóa rồi mở khóa `demo_shipper`). **Chờ người dùng.**
- [x] **6.4** Đánh dấu tiêu chí; cập nhật `specs/README.md`, README gốc, spec 003 (hook khóa Shipper), `api.md`/`models.md` nếu lệch. → 11/12 tiêu chí `[x]`; spec 003 ghi rõ phần đã làm. **Phát hiện việc treo chưa làm:** spec 003 hứa spec 006 thêm số nhiệm vụ đang mở vào hộp khóa Shipper (UC06.4 bước 2) — chưa làm, đã ghi chuyển spec 009 (spec.md mục 6 + spec 003).

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 22/11/2026 | — | Lập spec, chờ chốt D1–D10. Người dùng đề nghị làm 007; đã giải thích 007 cần nền của 006, người dùng chọn làm 006 trước |
| 22/11/2026 | 0 | **Xong.** Người dùng chốt D1–D10 theo đề xuất, D4 dùng danh sách 6 lý do. Kiểm giả định: hành động lấy hàng đã có trong bảng trạng thái; hook khóa tài khoản đã có sẵn từ spec 003 (D9 không tạo phụ thuộc vòng); app `dispatch` đã đăng ký app/URL. |
| 22/11/2026 | 1 | **Xong.** Enum `PickupFailReason` (6 lý do), `HandoverKind`, `NotificationKind.PICKUP_RETRY`, nhóm `pickup_fail_reasons`/`handover_kinds` ở `/meta/choices/`; model `Task`/`TaskResult`/`Handover` + `ShipmentEvent.task`; admin chỉ xem. Migration đúng thứ tự `shipments 0002 → dispatch 0001 → shipments 0003`, đã áp dụng DB local. Backend 333/333.<br>- **Đột biến trên file migration** (DB test dựng từ migration, không từ model): gỡ 7 ràng buộc, **6 bị bắt**. Sống sót `taskresult_outcome_valid` → phân tích: **thừa thật** vì CHECK "lý do khớp kết quả" đã chỉ cho 2 cặp hợp lệ → bỏ, lùi migration local (DB chưa có dòng nào, đã kiểm) rồi sinh lại.<br>- **Sót do tôi, đã sửa:** thêm `PICKUP_RETRY` làm đổi `choices` cột `notifications.kind` → `makemigrations --check` báo thiếu → thêm `notifications/0003` (SQL rỗng). Ghi lại vào models.md: thêm giá trị enum luôn cần migration loại này. |
| 22/11/2026 | 2 | **Xong.** Phân công lấy (kèm danh sách Shipper có số nhiệm vụ mở, 1 truy vấn), nhập điểm tập kết (ghi `Handover`, hàng về điểm tập kết), lấy lại / kết thúc (lý do bắt buộc, báo Shop), hook khóa Shipper (D9). Chi tiết đơn của Nhân viên có `tasks`, `holder_shipper` (prefetch, không N+1); Shop **không nhận** 2 trường này.<br>- **Dùng lại, không chép:** hàm kiểm của duyệt/từ chối (spec 005) đổi thành `check_staff_action` nhận mẫu thông điệp; `lock_visible`, `detail_response` thành hàm dùng chung; serializer thao tác kế thừa `ApproveShipmentSerializer` (updated_at bắt buộc). Hook đăng ký ở `dispatch/apps.py` → `accounts` không import `dispatch`.<br>- Backend 357/357, **chạy cả thứ tự đảo ngược** cũng pass; không migration mới.<br>- **Đột biến 13/13 bị bắt** sau khi sửa 1 test yếu: "không xếp ít việc trước" ban đầu sống vì người bận cũng đứng sau theo bảng chữ cái → đổi dữ liệu test để thứ tự theo tên và theo số việc khác nhau.<br>- **Lỗi thật do test spec 003 của tôi, đã sửa:** 2 test thay danh sách hook khóa tài khoản rồi `clear()` → xóa luôn hook thật của spec 006 cho test chạy sau (chạy riêng `dispatch` thì pass, chạy cả bộ thì 2 test fail). Sửa: lưu và trả lại danh sách; thêm test canh hook thật còn đăng ký.<br>- Khác: hằng số động từ ban đầu viết qua hàm "import muộn" thừa (không có vòng import) → import thẳng; cách chống đăng ký hook trùng qua `__globals__` → cho `register_account_locked_hook` tự bỏ qua khi trùng. |
| 22/11/2026 | 3 | **Xong — backend spec 006 hoàn tất.** Shipper xem nhiệm vụ của mình (không lộ người nhận/địa chỉ giao/COD), 'Đã lấy hàng' (Shipper giữ hàng, báo Shop), 'Lấy thất bại' (lý do theo danh mục, Khác bắt buộc ghi chú, hàng vẫn ở Shop, báo Shop + mọi NV). `allowed_actions` của nhiệm vụ tính từ bảng trạng thái và chỉ khi nhiệm vụ còn mở. `shipments_visible_to` nhánh SHIPPER dùng subquery (JOIN+DISTINCT không khóa dòng được).<br>- Backend 376/376, **xuôi và ngược thứ tự** đều pass; không migration mới.<br>- **Lỗi nghiêm trọng do tôi, đã sửa:** lớp test có hàm tiện ích tên `fail()` → **che `TestCase.fail`**, mà `assertEqual` dùng `self.fail()` để báo lỗi → mọi assert sai trong `test_shipper_pickup.py` lặng lẽ pass (lần đột biến đầu 4/10 sống, trong đó có 2 cái chắc chắn phải bị bắt). Lần ra bằng cách cô lập: đột biến có chạy (in debug) nhưng `assertEqual(['a'], ['b'])` cũng không báo. Sửa: đổi tên `post_fail`; **thêm test canh `core/tests/test_test_hygiene.py`** quét mọi lớp test, cấm che method có sẵn của TestCase (đã thử: bắt được lỗi cũ); quét toàn repo: không còn chỗ nào.<br>- Sau khi sửa: **đột biến 10/10 bị bắt** (2 cái cần thêm test: `.count()` không sinh FOR UPDATE nên phải lấy dòng thật; thêm test chặn thao tác lấy hàng trên nhiệm vụ GIAO cho spec 007).<br>- Thêm test: sau lấy lại + phân công lại, **nhiệm vụ cũ không còn nút** (đơn lại ở Đã phân công lấy).<br>- **`EXPLAIN` 31.500 nhiệm vụ** (rollback, sequence giữ nguyên ✔): tab Tất cả / Đã xong Index Scan `task_shipper_assigned_idx`, không Sort, 0,3 ms; tab Đang làm dùng partial unique + Sort ~36 dòng, 1,8 ms — số nhiệm vụ mở của một Shipper luôn nhỏ → **không thêm index**.<br>- Serializer: bỏ `__init__` gán choices + import muộn thừa. Lúc đầu tôi nói `required=False` + `default` làm DRF báo lỗi — **nói sai**, chỉ `required=True` + `default` mới lỗi; sửa chỉ là làm gọn.<br>- Script gỡ lỗi rollback của tôi làm id đơn nhảy (đơn smoke là 11, 12) → sau khi dọn đặt lại sequence đơn = 9 (mã tiếp theo `YC00000010`), user/phường về max id, task/kết quả/bàn giao về 1. Đã tắt đúng tác vụ server 8010 của tôi. |
| 22/11/2026 | 4 | **Xong.** `taskService`, `dispatchService`, `shipmentService` thêm 4 thao tác điều phối; `SHIPMENT_ACTION` thêm 6 mã (test đối chiếu backend pass); route + menu Shipper; `notificationLinkFor`; `ShipperPicker`.<br>- Vitest 243/243, 0 cảnh báo Vue, build OK; backend 376/376.<br>- **Đột biến 9/9 bị bắt**, gồm route `:id(\d+)` mất dấu `\` (lỗi thật của spec 005) — bắt được nhờ test router thật. Đột biến này qua Bash không áp được (Bash ăn ký tự thoát) → chạy bằng script Python riêng, đã kiểm file được khôi phục.<br>- Sau bài học `fail()` ở Phase 3: xác nhận bằng `--reporter=verbose` rằng 2 test trong `describe` async (`notificationLinkFor`) **thực sự chạy**. |
| 22/11/2026 | 5 | **Xong — frontend spec 006 hoàn tất.** Shipper: danh sách nhiệm vụ (thẻ, Đang làm / Đã xong), chi tiết (gọi điện, "Đã lấy hàng", "Lấy hàng thất bại" chọn lý do — Khác bắt buộc ghi chú), trang chủ ô nhiệm vụ đang làm. Nhân viên: tab hàng việc (nhãn từ backend), nút thao tác khai báo dạng bảng theo `allowed_actions`, hộp phân công (`ShipperPicker` chỉ tải khi mở), xác nhận tiếp nhận, lấy lại / kết thúc dùng chung hộp lý do, thẻ Điều phối thật + cảnh báo Shipper bị khóa.<br>- **Dùng lại:** `HighlightTile` (trang chủ NV + Shipper, bỏ CSS trùng), `DispatchCard`, `StatusBadge group=task_statuses` (không tạo component mới). Backend: `limits.task_note_max_length`, `handover_note_max_length` để frontend không viết 500.<br>- Vitest 262/262, 0 cảnh báo Vue, build OK; backend 376/376; không migration mới. **Đột biến 13/13 bị bắt.** Test mới đếm khớp tổng (22 = 16 cũ + 6 mới) — xác nhận thực sự chạy.<br>- **Hardcode tự bắt được, đã sửa:** viết `OTHER_REASON = 'OTHER'` trong màn hình → chuyển `PICKUP_FAIL_REASON` vào `shipmentActions.js` + test đối chiếu `PickupFailReason` backend.<br>- **Thiếu sót thật do ảnh chụp phát hiện, đã sửa:** lịch sử không hiện **phân công cho ai** / người giữ hàng / ghi chú sai lệch (backend có ghi `changes.shipper|holder|discrepancy_note` nhưng `ShipmentEventList` thiếu nhãn) → thêm nhãn + test; lượt bấm thật xác nhận hiện đủ.<br>- Dữ liệu chụp (đơn 10–14) đã xóa kèm nhiệm vụ / kết quả / bàn giao / thông báo; sequence đặt lại (mã tiếp theo `YC00000010`). Đã tắt đúng 2 tác vụ server 8010/5180 của tôi. |
| 22/11/2026 | 6 | Nghiệm thu: backend 376/376 xuôi + ngược, Vitest 262/262, audit 0, build OK. Rà hardcode sửa 2 chỗ backend (tên dự phòng "Shipper khác", mẫu ghép lý do). **11/12 tiêu chí đạt**; còn thử trình duyệt theo `manual-test.md` (41 bước). Đối chiếu từng "Mong đợi" trong kịch bản với code (tiêu đề thông báo, nhãn tab, hành vi khi khóa). Đọc lại spec 003 thì thấy **một việc đã hứa cho spec 006 mà chưa làm** (số nhiệm vụ mở trong hộp khóa Shipper — UC06.4 bước 2) → ghi chuyển spec 009, không làm vội ở bước nghiệm thu. Không bật/tắt server người dùng. |
