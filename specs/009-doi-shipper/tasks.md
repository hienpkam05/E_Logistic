# Spec 009 — Danh sách công việc

Spec: [spec.md](spec.md) · Model: [models.md](models.md) · API: [api.md](api.md)

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi".

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┐
                └──────► Phase 4 ──────────┼─► Phase 5 ─► Phase 6
```

Điều kiện chung (bài học 004–008):
- Docker DB đang chạy. **Không tắt server người dùng** (8000 / 5173). Server của tôi: Django 8010, Vite 5180 **chạy bằng `node …/vite.js`** (không `npx`); tắt xong **kiểm cổng trống**.
- Smoke gửi `Origin`/`Referer`; script chụp: `MSYS_NO_PATHCONV=1`, tham số tách `|`; e2e đợi trang tải xong (phần tử khác) rồi mới kiểm.
- Script rollback / `EXPLAIN` chạy bằng `manage.py shell -c "exec(...)"`, kiểm dòng "sequence giữ nguyên".
- Thêm giá trị enum → migration đổi `choices`; CHECK viết `isnull` tường minh; đột biến ràng buộc DB sửa **file migration**.
- Script đột biến dùng `sys.executable`, **chạy mốc chưa đột biến phải pass** trước.
- Test component đặt đúng thư mục `components/<nhóm>/__tests__/`; hàm tiện ích test không trùng tên method `TestCase`.

---

## Phase 0 — Chốt quyết định

- [x] **0.1** Chốt D1–D11 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt); đặc biệt D2 (ký hiệu `KEEP` cho bảng), D3 (nhiệm vụ hoàn không đổi người), D4 (không có "hủy đổi"), D6 (nhận hàng về điểm tập kết). → Cả 11 điểm theo đề xuất; D2/D3/D4 hỏi riêng, đều chọn đề xuất.

Xong khi: mục 2 ghi rõ phương án đã chốt; models.md / api.md bỏ chữ "bản nháp".

---

## Phase 1 — Backend: model, bảng, migration

- [x] **1.1** `core/transitions.KEEP` + `resolve_transition` / `allowed_actions` hiểu `KEEP`; `TransitionTableChecks` cập nhật.
- [x] **1.2** `ShipmentAction` +5 + dòng bảng; `HandoverKind.REASSIGN_INTAKE`; `NotificationKind` +2; hằng số thông điệp / tiêu đề.
- [x] **1.3** `Task.swap_candidate` + CHECK; migration; `migrate` local.
- [x] **1.4** Test: `KEEP` (đích = nguồn, bộ kiểm còn chặt); CHECK `swap_candidate`; bảng khớp checklist.

  → Test: `core/tests/test_transitions.py` (+5 `KEEP`, +3 kiểm chính bộ kiểm bảng trên bảng cố ý sai), `dispatch/tests/test_swap_models.py` (9: CHECK, mã mới, điều kiện nút NV / Shipper). **Làm sớm từ Phase 2.1 + 3.1:** điều kiện nút (`shipments/rules.py`) và lọc nút theo trạng thái nhiệm vụ (`TASK_STATUS_FOR_ACTION`) — vì thêm 5 hành động vào bảng mà không có điều kiện thì mọi đơn đang giao sẽ hiện "Đổi Shipper", Shipper hiện "Đã đưa hàng về" sai.

Xong khi: test pass; `makemigrations --check` sạch; đột biến (migration + `KEEP`) bị bắt.

---

## Phase 2 — Backend: Nhân viên

- [x] **2.1** Điều kiện bảng `shipments/rules.py` (có nhiệm vụ lấy/giao mở; đang chờ bàn giao; hàng ở Shipper + không nhiệm vụ mở).
- [x] **2.2** Service `swap_shipper`, `confirm_swap_handover`, `report_swap_issue`, `recall_to_hub`.
- [x] **2.3** 4 endpoint; `GET /dispatch/shippers/{id}/open-tasks/`; chi tiết đơn `tasks[].swap_candidate`, `replaced_by`.
- [x] **2.4** Test: từng nhánh (lấy thay ngay, giao chờ, đổi dự kiến, xác nhận, sai lệch, nhận về); attempt giữ nguyên; người mới bị khóa lúc xác nhận; người cũ bị khóa; không đổi được nhiệm vụ hoàn / thất bại / đơn kết thúc; `needs_attention`, `holder_locked` hết; 2 luồng (2 NV cùng xác nhận).

  → `dispatch/tests/test_staff_swap.py`: **20 test** (17 API / giao dịch + 3 đồng thời). Backend **513/513** pass trên PostgreSQL; `check` sạch; `makemigrations --check --dry-run` không thay đổi. Script `tools/check_phase2_mutations.py`: mốc 20/20 pass, **13/13 đột biến bị bắt**; chạy trong tiến trình con, không sửa source server. API chi tiết không N+1 khi tăng số nhiệm vụ thay thế / người dự kiến.

Xong khi: test pass; đột biến bị bắt.

---

## Phase 3 — Backend: Shipper

- [x] **3.1** Bảng điều kiện theo trạng thái nhiệm vụ cho `allowed_actions` của Shipper (chờ bàn giao → mất giao/thất bại, có báo đã đưa về).
- [x] **3.2** Service + endpoint `report_swap_handover`.
- [x] **3.3** Test: người cũ không giao / thất bại / ghi COD được khi chờ (cả gọi API trực tiếp); người dự kiến chưa thấy nhiệm vụ; sau xác nhận người cũ chỉ xem, người mới thấy đúng lần giao; 2 luồng (Shipper cũ giao thành công vs NV đổi người); `EXPLAIN` nhiệm vụ mở theo Shipper.
- [x] **3.4** Smoke 3 kịch bản checklist (đổi chưa giữ hàng, đổi đã giữ hàng, ba lần giao + đổi người); dọn dữ liệu.

  → `dispatch/tests/test_shipper_swap.py`: **13 test** (8 API / giao dịch + 5 đồng thời), gồm cả hai thứ tự giao thành công ↔ đổi người, hai thiết bị cùng báo và báo ↔ xác nhận. `test_swap_smoke.py`: **3 smoke qua Django Client**, đăng nhập thật bằng API với session, CSRF, Origin/Referer; không chạy trình duyệt hay mở server riêng. Dữ liệu smoke nằm trong test DB, tự rollback. Backend **529/529** pass trên PostgreSQL (59,2 s); check sạch, không phát sinh migration.

  → `tools/explain_open_tasks.py`: fixture 20.000 nhiệm vụ, Shipper cần xem có 20 mở + 980 đã đóng. Không ép planner / không chạy ANALYZE thống kê. Lượt đầu dùng `Index Scan task_shipper_assigned_idx`, trả 20 dòng trong 0,206 ms; lượt cuối dùng `BitmapAnd` giữa `task_one_open_per_shipment` và `task_shipper_assigned_idx`, nối `shipments_shipment_pkey`, trả 20 dòng trong 0,546 ms. Đây là số đo fixture, không phải benchmark production. Cả hai lượt kiểm được **"Rollback sạch; sequence giữ nguyên."**; không thêm index.

```powershell
.\venv\Scripts\python.exe backend/manage.py test apps.dispatch.tests.test_shipper_swap apps.dispatch.tests.test_swap_smoke --keepdb --noinput
.\venv\Scripts\python.exe backend/manage.py shell -c "exec(open('specs/009-doi-shipper/tools/explain_open_tasks.py', encoding='utf-8').read())"
```

Xong khi: test pass; `EXPLAIN` ghi nhật ký.

---

## Phase 4 — Frontend: nền

- [x] **4.1** Service (`swapShipper`, `confirmSwapHandover`, `reportSwapIssue`, `recallToHub`, `reportSwapHandover`, `dispatchService.openTasks`).
- [x] **4.2** `SHIPMENT_ACTION` +5; trạng thái nhiệm vụ cần so sánh (`TASK_STATUS` nếu cần) — test đối chiếu backend.
- [x] **4.3** `ShipperPicker` prop `exclude`; test.

  → **319/319 Vitest** pass (43 file, 29,9 s), thêm 9 test; nhóm liên quan **39/39** pass.
  Test hợp đồng 6 hàm service, 5 mã hành động + `TASK_STATUS` đối chiếu backend; picker kiểm loại người cũ,
  xóa lựa chọn đã bị loại, đổi/bỏ prop, kết quả API đang chờ/tìm mới, danh sách rỗng và `holder` trùng `exclude`.
  **Build đạt** với `npm.cmd run build -- --outDir node_modules/.cache/spec009-phase4-build --emptyOutDir false`
  (1.831 module, 2,92 s). Lệnh build mặc định gặp `EPERM` khi Vite xóa `dist/assets/HomeView-DR9cXqZf.js`;
  dùng thư mục kiểm tra riêng được Git bỏ qua, không dừng server hay thay cấu hình Vite.
  Vitest còn warning Vue Router ở test AccountDetailView/AccountCreateView và navActive (file không đổi trong Phase 4);
  không có warning ở nhóm test ShipperPicker vừa thêm. Chưa triển khai các màn hình Phase 5.

Xong khi: test pass; build.

---

## Phase 5 — Frontend: màn hình

- [x] **5.1** NV: nút / hộp Đổi Shipper, Xác nhận nhận hàng bàn giao, Ghi sai lệch, Nhận hàng về điểm tập kết; Điều phối (chờ bàn giao, đã thay thế → người mới, cảnh báo kèm hướng xử lý).
- [x] **5.2** Shipper: nhiệm vụ chờ bàn giao (dải cảnh báo + nút báo đã đưa về).
- [x] **5.3** Hộp khóa Shipper: danh sách nhiệm vụ đang mở.
- [x] **5.4** Vitest; ảnh 1440 + 390; bấm thật 2 kịch bản đổi Shipper.

  → **326/326 Vitest** pass, 43 file, thêm 7 test cho đổi người/đổi dự kiến, xác nhận bắt buộc nhận hàng,
  409 chọn lại người, ghi sai lệch, nhận về, Shipper báo bàn giao và hộp khóa có lỗi tải/thử lại.
  AccountDetailView test dựng qua RouterView để đăng ký guard đúng (không còn warning ở nhóm này).
  Browser thật **Chrome headless + API thật/PostgreSQL test DB**: đổi nhiệm vụ lấy → người cũ chỉ xem, người mới
  bấm nhận hàng; đổi nhiệm vụ giao → người cũ báo về → NV xác nhận → người mới thấy lần 2, bộ đếm vẫn 1.
  Hộp khóa liệt kê đúng vận đơn đang mở. **0 Vue warning / 0 page error**, không tràn ngang.
  **8 ảnh 1440/390** đã xem và sửa: [bằng chứng](artifacts/phase5/README.md).
  Dùng LiveServer test riêng 8010 + Vite 5180; kết thúc đã kiểm cổng trống, Django dọn dữ liệu test DB.
  Build đạt (1.831 module, 29,64 s) tại `node_modules/.cache/spec009-phase5-build`, tránh `dist` EPERM như Phase 4.
  Vitest toàn bộ vẫn có warning fixture AccountCreateView / navActive không đổi trong Phase 5; browser thật không có.

```powershell
cd frontend
npm.cmd run test
npm.cmd run build -- --outDir node_modules/.cache/spec009-phase5-build --emptyOutDir false
cd ..
.\venv\Scripts\python.exe specs/009-doi-shipper/tools/run_browser_phase5.py
```

Xong khi: test pass; build; 0 cảnh báo Vue.

---

## Phase 6 — Nghiệm thu

- [x] **6.1** `check`, `makemigrations --check`, backend xuôi + ngược; Vitest, audit, build. **Đã chạy đầy đủ;
  audit còn phát hiện dev, không đánh dấu audit sạch.** Backend cuối 531/531 xuôi (70,269 s) và 531/531 `--reverse`
  (72,775 s); Vitest 326/326; build cache Phase 6 đạt (6,39 s). Audit production 0; full 7 (5 moderate, 2 critical).
- [x] **6.2** Rà hardcode. Các trường nghiệp vụ dùng enum/hằng chung, meta/formatter/service/http;
  không thấy ID/demo user, URL máy chủ, mã màu hex hoặc số lần giao viết trực tiếp trong logic màn hình mới.
- [ ] **6.3** `manual-test.md` + người dùng thử trình duyệt. **File đã viết**; người dùng trả lời
  **"Chưa tự thử"** ngày 23/11/2026. Browser tự động đã bấm đủ 3 luồng nhưng không đánh dấu thay người dùng.
- [x] **6.4** Đánh dấu tiêu chí; `specs/README.md`, README gốc; cập nhật spec 003 / 006 / 007 / 008 (việc treo đã xử lý); ghi chú cho spec 010–011.

**Chưa chốt nghiệm thu toàn bộ.** Chi tiết kết quả, hai lỗi đã sửa, audit còn mở và các bước để chốt:
[acceptance.md](acceptance.md). Browser nghiệm thu trên test DB đạt 3 luồng + hộp khóa,
0 Vue warning/page error, 10 ảnh 1440/390 tại [artifacts/phase6](artifacts/phase6/README.md).
Script đột biến Phase 2 chạy lại trên code cuối: mốc 20/20 và **13/13 bị bắt**.

Lỗi tìm trong Phase 6: báo bàn giao vs khóa tài khoản có thể deadlock/ghi sau khi khóa; sửa khóa
đơn → user người ghi → task và kiểm lại active. Thông báo TASK_REPLACED sau nhận dùng lý do đổi gần nhất,
không lấy ghi chú nhận hàng. Có 2 test đồng thời mới và assertion thông báo; 3 kiểm chứng thất bại trước sửa.
Không có migration/endpoint/trường mới. Dữ liệu browser ở test DB được dọn; cổng 8010/5180 đã trả lại.

```powershell
.\venv\Scripts\python.exe backend/manage.py check
.\venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe backend/manage.py test apps --keepdb --noinput
.\venv\Scripts\python.exe backend/manage.py test apps --reverse --keepdb --noinput
.\venv\Scripts\python.exe specs/009-doi-shipper/tools/check_phase2_mutations.py
$env:SPEC009_BROWSER_ARTIFACTS = 'phase6'
.\venv\Scripts\python.exe specs/009-doi-shipper/tools/run_browser_phase5.py
```

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 23/11/2026 | — | Lập spec, chờ chốt D1–D11. Đối chiếu code: 3 chuyển trạng thái nhiệm vụ đổi người đã có trong `TASK_TRANSITIONS`; `replaced_by`, `handover_reported_at`, `TASK_REPLACED` có sẵn; **bảng vận đơn chưa khai được thao tác "giữ nguyên trạng thái" cho nhiều trạng thái nguồn** (D2); nhiệm vụ giao luôn đang giữ hàng (spec 007 D6) → luôn nhánh chờ bàn giao. Gom 4 việc treo: hộp khóa (003), `needs_attention` (006), `holder_locked` / giao lại người khác (007), hoàn khi người cũ còn giữ (008). |
| 23/11/2026 | 0 | **Xong.** Người dùng chốt D1–D11 theo đề xuất (D2 `KEEP`, D3 hoàn không đổi người, D4 không có hủy). Kiểm giả định: người dự kiến chưa thấy nhiệm vụ nhờ `tasks_visible_to` lọc theo `shipper`; `confirm/fail_delivery` đã chặn khi không `ACTIVE`. **Làm rõ:** `KEEP` được thay bằng trạng thái thật ngay trong `resolve_transition` (nhiều service gán `status = rule.target` — không được thấy `KEEP`); người thay thế luôn khác người cũ (UC06.8 bước 3). Mô tả phương án D4 trong câu hỏi chốt tôi viết hơi rối ("chọn chính họ làm… không được") — ghi lại rõ ở spec.md mục 2. |
| 23/11/2026 | 1 | **Xong** (kèm 2.1, 3.1 làm sớm). `KEEP` trong `core/transitions.py`: `resolve_transition` trả `Transition` có đích thật (`dataclasses.replace`), `Transition.target_from`, `transition([], KEEP)` → `ValueError`; bộ kiểm bảng hiểu `KEEP` (đích hợp lệ = nguồn, KEEP không tạo cạnh mới). 5 hành động mới (`SWAP_SHIPPER`, `CONFIRM_SWAP_HANDOVER`, `REPORT_SWAP_ISSUE`, `REPORT_SWAP_HANDOVER`, `RECALL_TO_HUB`) + `REASSIGN_INTAKE` + 2 loại thông báo + `Task.swap_candidate` (CHECK `isnull` tường minh). 3 migration áp dụng local (0 dòng bàn giao, 0 nhiệm vụ trước khi tạo lại CHECK).<br>- **Docker Desktop không chạy** khi bắt đầu (lượt test đầu thất bại vì không nối được DB; có lẽ máy vừa ngủ / khởi động lại — giải thích cả việc máy chậm). Người dùng cho phép → mở Docker Desktop, bật lại container `db` cũ (dữ liệu còn: 6 tài khoản, 0 đơn).<br>- 4 test cũ đổi kỳ vọng **đúng thiết kế**: `HandoverKind` +1; đơn Đang giao có `SWAP_SHIPPER`; Chờ giao lại / Chờ xử lý hoàn khi hàng còn ở Shipper có `RECALL_TO_HUB`.<br>- Backend **493/493** xuôi + ngược (máy chậm: 169 s / 127 s); Vitest 310/310; không migration mới.<br>- **Đột biến (có mốc) 11/13.** Lần đầu sống thêm 2: (1) bỏ kiểm đích trong bộ kiểm bảng — test "bảng cố ý sai" của tôi chỉ kiểm "có lỗi", mà bảng đó còn hỏng kiểm tra khác → siết: kiểm **đúng tên** kiểm tra báo lỗi; khi siết lại tôi viết sai 2 chỗ (lỗi trong `subTest` mang tên `runTest` → lấy tên kiểm tra cha; kỳ vọng thiếu "không tới được kết thúc" — bộ kiểm đúng, tôi sai) — bước chạy mốc chặn đúng nên không ra kết quả giả; (2) đột biến "KEEP tạo cạnh tới mọi nơi" tôi viết là **tương đương** (KEEP luôn tự lặp) → thay bằng "không giải KEEP khi tính đường đi" (bị bắt). Còn sống 2 — **tương đương ở mức nút**: đổi được nhiệm vụ hoàn (đơn Đang hoàn không thuộc nguồn `SWAP_SHIPPER`), nhận về khi còn nhiệm vụ mở (Chờ giao lại / Chờ xử lý hoàn không bao giờ có nhiệm vụ mở) → kiểm lại ở service Phase 2. |
| 23/11/2026 | 2 | **Xong.** 4 service / POST Nhân viên + GET nhiệm vụ mở theo Shipper; prefetch người dự kiến / nhiệm vụ thay thế. Khóa đơn rồi cả người cũ và mới theo id trước nhiệm vụ; giữ helper khóa nhiệm vụ dùng chung như cũ. Thay ngay nhiệm vụ lấy; giao chờ bàn giao, giữ attempt_no, không ghi TaskResult / COD. Ghi sai lệch chỉ thêm lịch sử; nhận về không thông báo theo D10 (sửa câu D6 cho thống nhất). Gửi lại không ghi trùng; lỗi thông báo hoặc người mới bị khóa rollback toàn bộ. **20 test mới**, gồm 3 ca đồng thời; kiểm quyền, phiên bản, không N+1. Backend cuối **513/513**, 122.9 s (lượt trước 96.1 s); check và makemigrations sạch. Đột biến **13/13** sau mốc 20/20: guard loại nhiệm vụ / người giữ / chờ bàn giao, phiên bản, cùng người, người mới bị khóa, attempt_no, replaced_by, holder, thông báo, needs_attention, transaction, khóa đơn. Script dùng băm nhanh như manage.py test, không ghi source. Chưa làm Phase 3.2 trở đi hoặc frontend. |
| 23/11/2026 | 3 | **Xong.** POST report-swap-handover: chỉ người cũ trên nhiệm vụ giao chờ bàn giao; ghi thời điểm, lịch sử và báo mọi NV hoạt động trong một transaction. Dùng chung helper báo bàn giao với hoàn hàng, giữ hành vi báo hoàn. Gửi lại không trùng (kể cả sau khi đóng); không tăng phiên bản đơn, không đổi người giữ / attempt / COD. **13 test mới + 3 smoke API** (Django Client, CSRF + Origin/Referer, rollback test DB); kiểm hai thứ tự giao thành công vs đổi người, hai thiết bị báo, báo vs xác nhận; người cũ mất quyền/COD, người dự kiến chưa thấy, người mới thấy đúng lần giao. **529/529** backend pass trên PostgreSQL, 59,2 s; check sạch, không migration mới. EXPLAIN 20.000 nhiệm vụ dùng index có sẵn, 20 kết quả; lượt cuối BitmapAnd task_one_open_per_shipment + task_shipper_assigned_idx, 0,546 ms. Cả hai lượt đo rollback sạch, sequence giữ nguyên. Smoke từng gặp 429 vì 4 người dùng chung IP trong nhiều kịch bản; fixture đã dùng IP riêng cho mỗi người, giữ nguyên throttle. Chưa làm frontend Phase 4–5 hoặc nghiệm thu Phase 6. |
| 23/11/2026 | 4 | **Xong.** Thêm 6 hàm service qua http client chung; 5 SHIPMENT_ACTION và TASK_STATUS (ACTIVE / PENDING_SWAP_HANDOVER / REPLACED) đối chiếu backend. ShipperPicker.exclude là ID dạng Number hoặc null: lọc cả tìm kiếm, xóa lựa chọn bị loại, hỗ trợ đổi prop, không chọn holder bị loại hoặc tự giao cho người không giữ hàng. **9 test mới**, nhóm liên quan 39/39, toàn frontend **319/319** (43 file). Build mặc định bị EPERM khi dọn file HomeView trong dist; build sang node_modules/.cache/spec009-phase4-build đạt, 1.831 module / 2,92 s. Không thay cấu hình, không dừng server. Warning Vue Router nằm ở test AccountDetailView / AccountCreateView / navActive không sửa trong lượt này. Đã ghi rõ chữ ký service và prop trong spec; màn hình thuộc Phase 5. |
| 23/11/2026 | 5 | **Xong.** Giao diện NV có đổi người / đổi dự kiến (loại người cũ, lý do bắt buộc), xác nhận bàn giao bắt buộc tick nhận hàng, sai lệch và nhận về. DispatchCard hiện chờ bàn giao / người thay thế / cảnh báo kèm nút hợp quyền. Shipper chờ đổi chỉ thấy điểm tập kết và báo đã đưa về, không phần giao/COD; nhiệm vụ đã bị thay thế chỉ xem. Hộp khóa Shipper tải nhiệm vụ mở, có loading/lỗi/thử lại và chặn khóa khi chưa tải được. **326/326 Vitest** (7 test mới), build đạt ở cache Phase 5. Browser Chrome headless/API thật trên PostgreSQL test DB pass hai luồng, giữ attempt 2; 8 ảnh 1440/390 đã kiểm và sửa dải cảnh báo/chụp sau hiệu ứng. **0 Vue warning / 0 page error**, không tràn ngang. Server riêng 8010/5180 đã dừng, test DB được dọn; chưa làm nghiệm thu Phase 6. |
| 23/11/2026 | 6 | **Nghiệm thu chức năng tự động đạt; chưa chốt toàn bộ.** Đã tái hiện rồi sửa deadlock/nhận báo sau khóa khi báo bàn giao vs khóa tài khoản (khóa đơn → người ghi → task, kiểm lại active); sửa thông báo thay thế dùng lý do đổi, không dùng ghi chú nhận. Thêm 2 test đồng thời, assertion nội dung và cập nhật thứ tự khóa báo hoàn. **531/531 xuôi + 531/531 đảo thứ tự**, check/migration sạch; **326/326 Vitest**, build cache đạt; browser đủ 3 luồng + hộp khóa, 10 ảnh, 0 Vue warning/page error; 13/13 đột biến bị bắt lại sau mốc 20/20. Rà hardcode đạt. Audit production 0; full 7 mục dev (5 moderate, 2 critical), audit fix không force đổi 0 package, giữ major theo skill. Đã viết manual-test và báo cáo acceptance; người dùng trả lời Chưa tự thử nên 6.3 vẫn mở. Đã cập nhật README/specs/architecture, các việc treo 003/006/007/008 và đầu vào 010–011; không thêm migration/API. |
