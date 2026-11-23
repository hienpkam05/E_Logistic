# Spec 007 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi".

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung (bài học 004–006):
- Docker DB đang chạy. **Không tắt server người dùng** (8000 / 5173); cần server thì bật cổng riêng (8010 / 5180) và tắt đúng tác vụ của mình.
- Smoke test gửi `Origin`/`Referer`.
- Dữ liệu thử phải dọn; script rollback / `EXPLAIN` phải **đặt lại sequence**.
- Thêm giá trị enum → kiểm `makemigrations --check` (cần migration đổi `choices`).
- Đột biến ràng buộc DB → sửa **file migration**; đột biến khóa dòng → không dùng `.count()`.
- Hàm tiện ích trong lớp test không trùng tên method `TestCase` (có test canh).

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D11 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt); đặc biệt D3 (ẩn SĐT khi nhiệm vụ đã đóng — sửa cả nhiệm vụ lấy), D4 (danh sách lý do), D5 (Shipper tự gõ COD), D7 (giao lại chỉ Shipper đang giữ hàng). → Cả 11 điểm theo đề xuất; D3/D5/D7 hỏi riêng, đều chọn đề xuất.

Xong khi: mục 2 ghi rõ phương án đã chốt; models.md / api.md bỏ chữ "bản nháp".

---

## Phase 1 — Backend: model, migration, danh mục

- [x] **1.1** Enum `DeliveryFailReason`; `NotificationKind.OUT_FOR_DELIVERY`, `REDELIVERY_SCHEDULED`; nhóm `delivery_fail_reasons` ở `/meta/choices/`; hằng số thông điệp / tiêu đề.
- [x] **1.2** `TaskResult.cod_expected`, `cod_collected`, `reason_code` mở rộng `choices`; 2 CHECK COD; `Shipment` CHECK `delivery_attempts ≤ 3`.
- [x] **1.3** Migration `dispatch 0002`, `shipments 0004`, `notifications 0004`; `migrate` DB local.
- [x] **1.4** Test:
  - CHECK COD (lệch, chỉ một cột, COD trên kết quả thất bại) + CHECK số lần;
  - mã `PickupFailReason` và `DeliveryFailReason` không trùng;
  - `/meta/choices/` có nhóm mới; bảng chuyển trạng thái vẫn khớp checklist.

  → 15 test ở `dispatch/tests/test_delivery_models.py`; `test_choices` thêm nhóm mới. Bảng chuyển trạng thái không đổi (test cũ vẫn pass).

Xong khi: test pass; `makemigrations --check` sạch; đột biến trên migration (gỡ từng CHECK) bị bắt.

---

## Phase 2 — Backend: Nhân viên phân công giao, giao lại, hoàn

- [x] **2.1** Service `assign_delivery` (dùng lại kiểm Shipper / khóa user của `assign_pickup` — tách hàm chung, không chép), `decide_redelivery`, `decide_return`.
- [x] **2.2** Bảng điều kiện phụ cho `allowed_actions` (ẩn giao lại / phân công giao khi đủ 3 lần — D8).
- [x] **2.3** 3 endpoint trên đơn; serializer kế thừa khuôn `_versioned()`; `handed_over` bắt buộc đúng.
- [x] **2.4** Chi tiết đơn NV: `tasks[].attempt_no`, `result.cod_*`, cảnh báo Shipper giữ hàng đã bị khóa (D7); Shop: `delivery` (không N+1).
- [x] **2.5** Test:
  - từng hành động: thành công, sai trạng thái, `updated_at` cũ, gửi lại, quyền;
  - không tăng số lần khi phân công; `attempt_no` đúng ở lần 1, 2, 3;
  - D7: giao lại chỉ người đang giữ; D8: đủ 3 lần → `LIMIT_REACHED`, `allowed_actions` chỉ còn hoàn;
  - thông báo đúng người;
  - 2 luồng: 2 NV cùng phân công giao → 1 nhiệm vụ.

  → 24 test ở `dispatch/tests/test_staff_delivery.py` (gồm 2 test 2 luồng thật: 2 NV cùng phân công giao; giao lại vs hoàn cùng lúc).

Xong khi: test pass; đột biến (bỏ kiểm số lần, bỏ kiểm người giữ, bỏ khóa user, tăng lần khi phân công) bị bắt.

---

## Phase 3 — Backend: Shipper giao hàng

- [x] **3.1** `GET /dispatch/tasks/` đổi mặc định `type` thành tất cả (sửa test spec 006 đang giả định mặc định PICKUP); chi tiết chọn serializer theo loại; `DeliveryShipmentDetailSerializer` (D3); ẩn SĐT khi nhiệm vụ đã đóng (cả nhiệm vụ lấy — cập nhật test spec 006).
- [x] **3.2** Service `confirm_delivery` (so COD, thông điệp chênh lệch, `delivery_attempts = attempt_no`, holder `RECIPIENT`), `fail_delivery` (lý do theo nhóm giao, holder giữ Shipper). Dùng lại `_lock_own_…`, `_already_recorded`, `_close_task`.
- [x] **3.3** 2 endpoint Shipper.
- [x] **3.4** Test:
  - COD khớp / thiếu / thừa / 0 / âm / quá lớn; lệch → **không có dòng nào được ghi**;
  - gửi lại không cộng tiền, không tăng lần; thành công rồi gửi thất bại → `409`;
  - lý do lấy hàng gửi vào `fail-delivery` → `400`; thao tác giao trên nhiệm vụ LẤY → `409`;
  - Shipper khác → `404`; không N+1;
  - 2 luồng: 2 lần xác nhận song song → 1 kết quả; Shipper xác nhận vs NV thao tác khác.
  - `EXPLAIN` danh sách nhiệm vụ lọc `type` (dữ liệu lớn, rollback + đặt lại sequence).
- [x] **3.5** Smoke API end-to-end: … → nhập điểm tập kết → phân công giao → thất bại ×2 (giao lại) → thành công có COD; nhánh thất bại lần 3 → chỉ còn hoàn → hoàn. Dọn dữ liệu.

  → 21 test ở `dispatch/tests/test_shipper_delivery.py` (gồm 2 test song song thật + 1 test thứ tự khóa); smoke **19/19** trên Django riêng cổng 8010.

Xong khi: test pass; `EXPLAIN` ghi vào nhật ký.

---

## Phase 4 — Frontend: nền

- [x] **4.1** `taskService` (confirmDelivery, failDelivery, list `type`); `shipmentService` (assignDelivery, decideRedelivery, decideReturn).
- [x] **4.2** `shipmentActions.js`: `SHIPMENT_ACTION` thêm mã, `DELIVERY_FAIL_REASON`, `TASK_TYPE` (test đối chiếu backend).
- [x] **4.3** Menu Shipper "Nhiệm vụ"; liên kết thông báo loại mới (`notificationLinkFor`).
- [x] **4.4** Component dùng lại / mới: `ShipperPicker` nhận chế độ khóa người giữ (D7); ô COD (`CodInput` hoặc dùng `FormField`, nhận số tiền phải thu, báo thiếu / thừa ngay khi gõ).
- [x] **4.5** Test service/component; test router thật nếu đổi route.

  → Không đổi route (chỉ đổi nhãn menu) nên không cần thêm test router. `CodInput.vue` (component riêng thay vì `FormField`: cần ô số có dấu chấm ngăn cách + so sánh trực tiếp với phải thu); `ShipperPicker` prop `holder`. Test mới: `components/__tests__/DispatchInputs.spec.js` (7), service (+2), hằng số đối chiếu backend (+2 qua `it.each`), `formatNumber` (+1).

Xong khi: test pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** `TaskListView`: bộ lọc loại, thẻ giao (người nhận, COD, lần N/3).
- [x] **5.2** `TaskDetailView`: khối giao (gọi người nhận, COD nổi bật), "Giao thành công" (hộp COD), "Giao thất bại" (lý do + ghi chú), nút "Chưa thu đủ? Ghi giao thất bại"; nhiệm vụ đã đóng ẩn SĐT.
- [x] **5.3** Màn Nhân viên: 3 tab mới; nút Phân công giao (ô "Shipper đã nhận hàng"), Giao lại / Hoàn (dùng lại hộp lý do); thẻ Điều phối lần N/3 + các lần giao + COD; cảnh báo Shipper giữ hàng bị khóa.
- [x] **5.4** Shop: khối "Đã giao" (thời gian, COD đã thu). Trang chủ Shipper tách ô lấy / giao.
- [x] **5.5** Vitest; ảnh chụp 1440 + **390px**; một lượt bấm thật NV phân công giao → Shipper giao thành công có COD → Shop thấy COD đã thu.

  → Ảnh 1440px: tab Giao thất bại, đơn thất bại lần 1 / 3/3 (chỉ còn hoàn), hộp phân công giao, hộp giao lại, đơn Đã giao (NV + Shop). Ảnh 390px: trang chủ Shipper 2 ô, danh sách lọc loại, chi tiết giao, hộp COD. Lượt bấm thật 9/9 bước.

Xong khi: test pass; build; 0 cảnh báo Vue.

---

## Phase 6 — Nghiệm thu

- [x] **6.1** `check`, `makemigrations --check`, toàn bộ test backend (xuôi + ngược); `npm run test`, audit, build. → `check` sạch, không migration mới, backend **437/437** xuôi + ngược, Vitest **292/292** (0 `[Vue warn]`), audit production 0, build OK (thư mục tạm — `frontend/dist` vẫn lỗi quyền xóa).
- [x] **6.2** Rà hardcode (mã chỉ ở file cho phép, không số `3` / `500` viết thẳng ở frontend). → Frontend: 1 chỗ `holder_type === 'SHIPPER'` trong màn NV → `HOLDER_TYPE` ở `shipmentActions.js` + test đối chiếu `HolderType` (đột biến bị bắt). Không hex, không `maxlength` số, số lần lấy từ `limits`. Backend: thông điệp đều ở `constants.py`, ký hiệu tiền ở `core/formatting.py`.
- [ ] **6.3** `manual-test.md` (Shop / NV / Shipper điện thoại) + người dùng thử trình duyệt. → [manual-test.md](manual-test.md) sẵn sàng (41 bước, 9 nhóm; đối chiếu từng "Mong đợi" với code: tiêu đề thông báo, nhãn tab, chữ báo thiếu/thừa). **Chờ người dùng.**
- [x] **6.4** Đánh dấu tiêu chí; cập nhật `specs/README.md` (**cột mốc demo "giao thành công"**), README gốc, `api.md` / `models.md` nếu lệch; ghi chú cho spec 008–009. → 11/12 tiêu chí `[x]`; specs/README ghi đạt cột mốc demo; README gốc; spec.md mục 6 thêm chỗ cần mở rộng cho RETURN (008) và ràng buộc `attempt_no` khi thay người (009).

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 22/11/2026 | — | Lập spec, chờ chốt D1–D11. Đối chiếu code: 5 hành động giao đã có trong bảng trạng thái; `delivery_attempts`, `attempt_no`, `HolderType.RECIPIENT`, `LIMIT_REACHED`, 3 loại thông báo giao đã có; `reason_code` cần mở rộng. |
| 22/11/2026 | 0 | **Xong.** Người dùng chốt D1–D11 theo đề xuất (D3 ẩn SĐT cả hai loại nhiệm vụ, D5 tự gõ COD, D7 giao lại chỉ Shipper đang giữ). Kiểm lại code khi chốt, **bản nháp sai 2 chỗ, đã sửa:** (1) `type` ở danh sách nhiệm vụ đã có từ spec 006 (mặc định PICKUP) — chỉ đổi mặc định, không phải thêm mới; (2) mã `WRONG_ADDRESS` đã thuộc lý do lấy hàng → lý do giao dùng `ADDRESS_NOT_FOUND`, chỉ `OTHER` dùng chung (cùng nhãn). `TASK_SUCCEED`/`TASK_FAIL` đã áp dụng cho mọi loại nhiệm vụ, không cần sửa bảng. |
| 22/11/2026 | 1 | **Xong.** `DeliveryFailReason` (6 lý do), `FAIL_REASONS_BY_TASK_TYPE`, `TASK_RESULT_REASON_CHOICES` (hợp 2 nhóm, bỏ mã trùng); `NotificationKind.OUT_FOR_DELIVERY`, `REDELIVERY_SCHEDULED`; nhóm `delivery_fail_reasons` ở `/meta/choices/`; thông điệp + tiêu đề thông báo + động từ chặn cho 3 thao tác NV. `TaskResult.cod_expected/cod_collected` + CHECK cặp + CHECK "chỉ thành công, thực thu = phải thu"; `Shipment` CHECK ≤ 3 lần; CHECK `attempt_no` siết thành "GIAO bắt buộc 1..3". 3 migration đã áp dụng local (DB 0 nhiệm vụ / 0 kết quả / 0 đơn vượt 3 lần — kiểm trước khi thêm CHECK).<br>- Backend **391/391** (376 + 15), xuôi + ngược; `makemigrations --check` sạch; Vitest 262/262 (test frontend đối chiếu `constants.py` backend vẫn khớp).<br>- **Lỗi do tôi, test bắt được ngay:** CHECK `attempt_no` viết `type=DELIVERY AND 1 ≤ attempt_no ≤ 3` — khi `attempt_no` NULL biểu thức ra NULL, PostgreSQL coi là đạt → nhiệm vụ GIAO thiếu số lần vẫn lọt. Sửa: thêm `attempt_no IS NOT NULL`; lùi migration local (chưa có dữ liệu) rồi sinh lại. Ghi bài học vào models.md.<br>- **Đột biến trên file migration 8/8 bị bắt** (*lần chạy đầu vô giá trị — xem nhật ký Phase 2; đã chạy lại đúng, vẫn 8/8*) (bỏ `IS NOT NULL`, nới 1..3 hai đầu, loại khác có `attempt_no`, bỏ CHECK cặp COD, cho thu một phần `≤`, COD trên kết quả thất bại, nới số lần của đơn); file đã khôi phục.<br>- Lệch nhỏ so với models.md bản chốt, đã cập nhật: chuyển `MAX_DELIVERY_ATTEMPTS` sang `shipments/constants.py` (ràng buộc trên `Shipment`, tránh `shipments` phụ thuộc `dispatch`); thay CHECK `attempt_no` thay vì giữ nguyên. |
| 22/11/2026 | 2 | **Xong.** `assign_delivery` (lần N = số lần đã giao + 1, không tăng số lần; Shipper giữ hàng; D7 giao lại chỉ người đang giữ; báo Shipper + Shop), `decide_redelivery` (còn lượt), `decide_return` (hoàn sớm được); 3 endpoint; `handed_over` bắt buộc `true` ở serializer. Chi tiết đơn: `holder_locked` (NV), `delivery` (mọi vai trò), `tasks[].attempt_no`, `result.cod_*`; `allowed_actions` lọc theo số lần qua **`shipments/rules.py`** (bảng điều kiện phụ, không `if` trong serializer).<br>- **Dùng lại, không chép:** tách `_resend_of_assignment`, `_lock_available_shipper`, `_create_task` từ `assign_pickup`; `_pickup_decision` → `_staff_decision` (đích lấy từ bảng trạng thái thay vì dict viết tay, có `guard`); `PickupDecisionSerializer` → `StaffDecisionSerializer`; hàm `race()` chép y hệt ở test spec 005 và 006 → `core/tests/race.py` (`RaceMixin`), 3 nơi dùng chung.<br>- Backend **415/415** (391 + 24), xuôi + ngược; không migration mới. Test cũ đổi 1 chỗ: tập trường chi tiết đơn có thêm `delivery`.<br>- **Lỗi nghiêm trọng trong công cụ kiểm của tôi, đã sửa:** script đột biến gọi `subprocess.run(["python", ...])` — trên máy này `python` trong subprocess trỏ sang **Python hệ thống (Django 4.2)**, không phải venv (Django 5.2) → bộ test lỗi ngay khi dựng (`CheckConstraint(condition=...)`), mọi đột biến đều "bị bắt" giả. Ảnh hưởng: kết quả 8/8 ở Phase 1 và lần đầu 14/14 ở Phase 2 **không có giá trị**. Lộ ra vì tôi nghi một đột biến lẽ ra phải sống (test Shop chỉ có 1 lần giao) mà lại "bị bắt" → xem lỗi thật thì là `TypeError`. Sửa: dùng `sys.executable` + **bắt buộc chạy mốc trên code chưa đột biến phải pass** trước khi tính. Kiểm lại: đột biến spec 006 chạy trực tiếp trong Bash (venv) nên không bị ảnh hưởng.<br>- **Chạy lại đúng:** Phase 1 **8/8** (thật); Phase 2 **13/14** — sống đúng cái tôi nghi (`delivery` lấy nhầm kết quả thất bại cũ). Thêm test "thất bại lần 1, giao được lần 2 → Shop thấy lần 2" → **14/14**.<br>- 1 test tôi viết sai kỳ vọng: đòi `allowed_actions` rỗng ở Chờ xử lý hoàn, nhưng bảng đã khai sẵn `ASSIGN_RETURN`/`RECEIVE_RETURN` của spec 008 (frontend chỉ vẽ nút có trong bảng nút) → sửa test kiểm trạng thái. Bỏ 1 assert vô nghĩa (`created_at > now()`). |
| 22/11/2026 | 3 | **Xong — backend spec 007 hoàn tất.** `confirm_delivery` (COD = phải thu, báo rõ thiếu/thừa bằng `format_vnd` cùng dạng frontend; kết quả + COD + số lần + người nhận giữ hàng trong một transaction; gửi lại không cộng tiền/lần), `fail_delivery` (lý do nhóm giao, số lần = lần của nhiệm vụ, hàng vẫn ở Shipper, báo Shop + mọi NV). Danh sách nhiệm vụ mặc định mọi loại; khối `shipment` chọn theo loại qua bảng `TASK_SHIPMENT_VIEWS`; ẩn SĐT khi nhiệm vụ đã đóng ở cả hai loại (D3).<br>- **Dùng lại:** `_resolve_pickup` → `_resolve_own_task` (tham số loại), `_close_task` nhận COD, `_reason_text` theo `FAIL_REASONS_BY_TASK_TYPE`; view Shipper dùng khuôn `_ShipperTaskAction` (4 thao tác); `FailDeliverySerializer` kế thừa `FailPickupSerializer`; `run_parallel` chuyển vào `RaceMixin` (test spec 006 dùng chung).<br>- Backend **437/437** (415 + 21 + 1 `format_vnd`), xuôi + ngược; không migration mới.<br>- **Đột biến (có mốc chưa đột biến phải pass): 15/17 → 17/17.** Sống lần đầu: (1) bỏ khóa dòng đơn, chỉ giữ khóa nhiệm vụ — chưa có thao tác NV nào ghi đơn Đang giao nên không hành vi nào phân biệt được; thêm test kiểm **thứ tự khóa trong SQL** (đơn → nhiệm vụ, quy ước chống deadlock cho spec 009). Bản đầu của test này sai — để lệnh phân công nằm trong vùng đo nên 2 khóa đầu là của NV; phát hiện khi in danh sách bảng bị khóa, đã sửa. (2) cho COD âm qua serializer — service vẫn chặn nhưng thông điệp vô nghĩa; siết test: số không hợp lệ bị từ chối trước bước so tiền.<br>- **`EXPLAIN` 46.500 nhiệm vụ trộn lấy + giao:** mặc định mọi loại / chỉ giao: Index Scan `task_shipper_assigned_idx` không Sort, 0,2–0,3 ms; giao đang làm: partial unique + Sort ~23 dòng, 1,4 ms; tab NV Giao thất bại: `ship_status_created_idx` quét ngược, 0,3–1,1 ms → **không thêm index**.<br>- **Lỗi do tôi, đã sửa:** chạy script `EXPLAIN` bằng cách nạp vào `manage.py shell` qua stdin → console tương tác hiểu sai khối lệnh, đoạn **đặt lại sequence báo SyntaxError và không chạy** (4 lần chạy đẩy sequence đơn lên 60009, nhiệm vụ 185926, user 178, phường 9). Dữ liệu vẫn rollback (0 đơn, 0 nhiệm vụ). Đối chiếu số dư (60009 = 9 + 4×15.000; 178 = 10 + 4×42) → đặt lại đúng giá trị gốc (đơn 9, nhiệm vụ 1, user 10, phường 5); chạy lại bằng `shell -c "exec(...)"` → script tự đặt lại, "sequence giữ nguyên: True".<br>- Smoke API 19/19 (giao có COD, thiếu COD bị từ chối nêu chênh lệch, bấm lại, ẩn SĐT, Shop thấy COD; 3 lần thất bại → chỉ còn hoàn → giao lại lần 4 `LIMIT_REACHED` → hoàn; Shop nhận đủ 5 loại thông báo). **Bước D7 (Shipper khác) không chạy được** vì DB demo chỉ có 1 Shipper hoạt động — đã có test tự động. Dọn 2 đơn + nhiệm vụ/kết quả/bàn giao/thông báo, sequence về như cũ; đã tắt đúng tác vụ server 8010 của tôi.<br>- **Hồi quy frontend do D3, sửa luôn:** chi tiết nhiệm vụ LẤY đã đóng sẽ hiện nút gọi `tel:null` (backend giờ trả `sender_phone: null`) — ảnh hưởng kịch bản thử spec 006 đang chờ → ẩn SĐT + nút gọi khi null, thêm test (đột biến bỏ `v-if` bị bắt). Vitest 263/263; build OK (ra thư mục tạm — `frontend/dist` vẫn lỗi quyền xóa, việc treo phía người dùng). Còn lại cho Phase 5: danh sách Shipper không gửi `type` nên sẽ thấy cả nhiệm vụ giao dưới dạng thẻ lấy hàng — hiện chưa tạo được nhiệm vụ giao từ giao diện nên chưa gặp. |
| 22/11/2026 | 4 | **Xong.** `taskService.confirmDelivery/failDelivery`, `shipmentService.assignDelivery` (luôn gửi `handed_over: true` — màn hình chỉ gọi sau khi NV tích), `decideRedelivery`, `decideReturn`; `SHIPMENT_ACTION` +5 mã, `DELIVERY_FAIL_REASON` (`OTHER`, `COD_NOT_READY`), `TASK_TYPE` — test đọc thẳng `dispatch/constants.py` (gộp 3 kiểm tra bằng `it.each`); menu Shipper "Nhiệm vụ lấy hàng" → "Nhiệm vụ"; `formatNumber` (số không ký hiệu cho ô tiền).<br>- **`CodInput`** (D5): COD phải thu chữ to, ô để trống bắt Shipper tự gõ, chỉ nhận chữ số, hiển thị `350.000`, chặn theo `limits.cod_max_vnd`, báo Khớp / Thiếu / Thừa ngay khi gõ, đơn không COD không có ô và giá trị 0; `matches` cho màn cha. **`ShipperPicker holder`** (D7): chỉ người đang giữ hàng, chọn sẵn, không gọi API, có giải thích đổi Shipper.<br>- `notificationLinkFor` không cần sửa: thông báo phân công giao đã có `task_id` (Shipper), các loại khác có `shipment_id`.<br>- Vitest **275/275** (263 + 12), **0 `[Vue warn]`**; build OK (thư mục tạm); audit production 0. 16 cảnh báo **Vue Router** trong output là **có từ trước** (test màn tài khoản spec 003 dùng `onBeforeRouteLeave` khi mount không có `<RouterView>`, và `navActive`) — không do phase này, chưa sửa.<br>- **Đột biến 14/14 bị bắt** (có mốc chưa đột biến phải pass).<br>- 2 test tôi viết sai lúc đầu (component phát `update:modelValue` ngay khi dựng, trước khi biến `wrapper` được gán) → viết helper `mountWithModel` giữ giá trị phát sớm. Test trang chủ Shipper tìm chữ "Nhiệm vụ lấy hàng" ở menu → đổi sang kiểm liên kết menu trỏ `/shipper/tasks`.<br>- **Ghi cho Phase 5:** trang chủ Shipper còn mục "Sắp có: Nhiệm vụ giao hàng, ghi nhận COD" — phải gỡ khi làm màn giao; tiêu đề màn danh sách / nút quay lại vẫn ghi "Nhiệm vụ lấy hàng". |
| 22/11/2026 | 5 | **Xong — frontend spec 007 hoàn tất.** Shipper: danh sách lọc loại (Tất cả / Lấy / Giao trên URL, giữ khi đổi tab), thẻ giao (người nhận, địa chỉ, COD, lần N/3); chi tiết theo bảng `TYPE_VIEW` (không if/else rải rác): giao có gọi người nhận, COD chữ to, "Giao thành công" dùng `CodInput` (chỉ bấm được khi khớp), "Chưa thu đủ? Ghi giao thất bại" mở hộp thất bại chọn sẵn lý do chưa đủ tiền COD, lỗi lệch COD từ backend hiện ngay ô COD; trang chủ 2 ô (giao, lấy), gỡ "Sắp có: giao hàng, COD". Nhân viên: +3 tab, nút Phân công giao (ô tích bàn giao, giao lại thì chỉ người đang giữ, người giữ bị khóa thì chặn + cảnh báo), Giao lại / Chuyển hoàn dùng chung hộp lý do, báo lý do lần thất bại gần nhất + "đủ 3 lần chỉ được hoàn"; Điều phối: số lần N/3, lần giao, lý do đúng nhóm, COD đã thu. Chung: thẻ "Kết quả giao" trong `ShipmentInfoCards` (Shop + NV); lịch sử có nhãn `attempt_no`, `delivery_attempts`, `cod_collected` (định dạng tiền).<br>- **Dùng lại:** `ShipperPicker holder`, `CodInput`, `REASON_DIALOGS`, `ACTION_BUTTONS`, `ShipmentInfoCards`, class `.checkbox` có sẵn (bỏ class mới tôi định thêm), `FAIL_REASON_GROUP` dùng ở 3 nơi.<br>- Vitest **291/291** (275 + 16), **0 `[Vue warn]`**, build OK (thư mục tạm); backend không đổi.<br>- **Đột biến 17/18 bị bắt** (có mốc). Sống: bỏ `holder_locked` khỏi điều kiện khóa nút phân công — **tương đương**, vì khi người giữ hàng bị khóa hộp không hiện danh sách + ô tích nên nút vẫn khóa; giữ làm lớp chặn dự phòng.<br>- **Tự bắt và sửa:** (1) comment `FAIL_REASON_GROUP` ghi "test đối chiếu" nhưng chưa có test → thêm test đọc `FAIL_REASONS_BY_TASK_TYPE` + tên nhóm ở `core/choices.py` (đột biến sai tên nhóm bị bắt); (2) viết `color: #fff` trong chip lọc → đổi `var(--brand-contrast)`; (3) script seed ảnh sót một dòng phân công giao đơn cần giữ ở điểm tập kết → sửa trước khi chạy; (4) script chụp tách tham số bằng `=` nên URL có query bị cắt, Git Bash đổi `/shop/...` thành đường dẫn Windows → bản `shot7.mjs` (tách `|`, ghi URL lỗi) + `MSYS_NO_PATHCONV=1`.<br>- **Ảnh chụp phát hiện lỗi trình bày, đã sửa:** chi tiết giao ghi "Shop Shop Demo Hoàn Kiếm · 0987…" — lặp chữ và dễ hiểu nhầm SĐT là của Shop (thực ra của người nhận) → SĐT đứng cạnh nút gọi người nhận, tên Shop chuyển vào thẻ Kiện hàng ("Hàng của Shop").<br>- **Lượt bấm thật 9/9** (Django 8010 + Vite 5180 riêng): NV chưa tích bàn giao → nút khóa; phân công giao lần 1; Shipper 390px gõ thiếu → "Thiếu 90.000 ₫" + nút khóa; gõ đúng → hiển thị `690.000`, giao thành công, đã thu COD, ẩn SĐT; Shop thấy Đã giao + COD 690.000 ₫. Cảnh báo trình duyệt: chỉ 401 (kiểm phiên trước đăng nhập) và 404 `favicon.ico` (dự án chưa có favicon — có từ trước).<br>- Dọn 6 đơn chụp + 14 nhiệm vụ / 13 kết quả / 6 bàn giao / 54 thông báo; sequence về như cũ (đơn 9, nhiệm vụ 1, user 10, phường 5); đã tắt đúng 2 tác vụ server 8010 / 5180 của tôi. |
| 22/11/2026 | 6 | Nghiệm thu: backend 437/437 xuôi + ngược, Vitest 292/292, 0 `[Vue warn]`, audit 0, build OK. **11/12 tiêu chí đạt**; còn thử trình duyệt theo `manual-test.md` (41 bước). Rà hardcode: sửa `'SHIPPER'` viết thẳng → `HOLDER_TYPE` + test đối chiếu.<br>- **Lỗi do tôi lúc thêm test, đã sửa:** script Python ghi file biến `\n` trong regex JS thành xuống dòng thật — test vẫn báo pass (chưa rõ vì sao trình biên dịch chấp nhận) → sửa, rồi **đột biến mã `HOLDER_TYPE` để chắc test thật sự kiểm** (bị bắt). Tên test `it.each` của Phase 4 in cả object (`có trong { OTHER: 'OTHER' }`) do `%s` thứ hai lấy nhầm tham số → đổi thứ tự tham số.<br>- Ghi rõ việc có từ trước không thuộc spec này: 16 cảnh báo Vue Router (test màn tài khoản spec 003, `navActive`), 404 `favicon.ico`. Không bật/tắt server người dùng. |
| 23/11/2026 | — | **Đính chính (phát hiện khi làm spec 008 Phase 5):** dòng Phase 5 ghi "đã tắt đúng 2 tác vụ server 8010 / 5180" là **chưa đúng** — tiến trình `node` của Vite 5180 còn sống sau `TaskStop` (chỉ lớp `npx` bị dừng). Đã dừng theo PID ngày 23/11/2026; xem nhật ký spec 008 Phase 5. |
