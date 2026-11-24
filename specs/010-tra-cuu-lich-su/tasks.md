# Spec 010 — Danh sách công việc

Spec: [spec.md](spec.md) · API: [api.md](api.md) · Dữ liệu/hằng số: [models.md](models.md) (không migration).

Quy ước: `[ ]` chưa làm, `[x]` đã làm **và** đạt "Xong khi". Điều kiện chung như [spec 009 tasks.md](../009-doi-shipper/tasks.md#phase-0--chốt-quyết-định) (server riêng 8010/5180 chạy bằng `node`, kiểm cổng trống; mốc chưa đột biến; `exec` cho script; v.v.).

Spec nhỏ — 4 phase:

```
Phase 0 ─► Phase 1 (backend) ─► Phase 2 (frontend) ─► Phase 3 (nghiệm thu)
```

---

## Phase 0 — Chốt quyết định

- [ ] **0.1** Chốt D1–D7 ở [spec.md mục 2](spec.md#2-quyết-định-cần-chốt); đặc biệt D1 (đơn Shop khác trả cùng 404), D2 (trang riêng, Shipper không có), D6 (Shop thấy tên người xử lý).

  → Đã rà soát UC03.1–03.2 và code hiện tại; ghi các điểm cần làm rõ ở spec.md: actor còn username,
  số thứ tự lấy và trạng thái chưa vận chuyển phải tính toàn đơn, lookup cần `updated_at`, thứ tự cần khóa phụ `id`.
  Đã gửi người dùng câu hỏi chốt gộp D1–D7. Người dùng không chọn riêng mà yêu cầu làm Phase 1 rồi "tiếp tục";
  tiến hành theo đề xuất đã trình bày và ghi rõ cơ sở tại spec.md, không ghi là có xác nhận riêng đủ 7 lựa chọn.
  Checklist 0.1 giữ mở để không làm sai lịch sử chốt quyết định; không chặn phần code đã được yêu cầu.

Xong khi: mục 2 ghi phương án đã chốt.

---

## Phase 1 — Backend

- [x] **1.1** `GET /shipments/lookup/` (chuẩn hóa mã, phạm vi theo quyền, 404 không lộ); `EXPLAIN` dùng index mã trên cột unique hiện có.
- [x] **1.2** Lịch sử: `task` trong mỗi mốc (`select_related`), `ordering`.
- [x] **1.3** Test: đúng / sai hoa thường / khoảng trắng; mã yêu cầu; đơn Shop khác = không tồn tại (so sánh cả body); Shipper 403; mã rỗng; lịch sử có `task`, thứ tự, không N+1.

  → `shipments/tests/test_lookup_history.py`: **19 test mới**. Hồi quy trên code cuối **550/550 xuôi (55,029 s)**
  và **550/550 đảo thứ tự (57,717 s)**;
  cập nhật đúng 1 test hợp đồng cũ (`task` mới, actor Shop bỏ username). Django check sạch, không migration mới.
  `tools/check_phase1_mutations.py`: mốc 19/19, **9/9 đột biến bị bắt** (phạm vi, uppercase, trim, 404 khác,
  gần đúng, username, select_related, số lấy và cờ vận chuyển). Runner chạy process con, không sửa source server.

  → `tools/explain_lookup.py`: 20.000 đơn tạm, cả Shop/NV và mã YC/HTT. Scalar subquery là InitPlan chạy một lần
  theo index `shipments_shipment_tracking_code_…_like` / `shipments_shipment_request_code_…_like`;
  query ngoài vẫn lọc phạm vi. PostgreSQL dùng index equality có sẵn trên cột unique, không thêm index.
  Lượt kiểm đầu trên truy vấn cuối khoảng 0,073–1,562 ms, số đo fixture không phải benchmark production.
  [Plan cuối](artifacts/phase1/explain-lookup.txt) kiểm **"Rollback sạch; sequence giữ nguyên."**
  Không ép planner hoặc thay thống kê DB. Fixture dùng id âm và mã YC hợp lệ 8 số; không gọi nextval.

  → API đã ghi `updated_at` chỉ trên lookup; `task.pickup_no` theo toàn bộ đợt lấy (kể cả thay người),
  `attempt_no` giao giữ nguyên; `has_transport_activity` toàn đơn và actor theo vai trò. Phase 2 chưa làm.

```powershell
.\venv\Scripts\python.exe backend/manage.py test apps.shipments.tests.test_lookup_history --keepdb --noinput
.\venv\Scripts\python.exe specs/010-tra-cuu-lich-su/tools/check_phase1_mutations.py
.\venv\Scripts\python.exe backend/manage.py shell -c "exec(open('specs/010-tra-cuu-lich-su/tools/explain_lookup.py', encoding='utf-8').read())"
```

Xong khi: test pass; đột biến (bỏ lọc phạm vi, bỏ chuẩn hóa, lộ thông điệp khác) bị bắt.

---

## Phase 2 — Frontend

- [x] **2.1** `shipmentService.lookup`, `events(…, ordering)`; route `/tracking` + menu Shop / NV (test router thật).
- [x] **2.2** `TrackingView`; `ShipmentEventList` nhãn lần lấy / giao / đổi Shipper, "Chưa phát sinh vận chuyển", đổi thứ tự.
- [x] **2.3** Vitest; ảnh 1440 + 390; bấm thật tra cứu (Shop thấy đơn mình, không thấy đơn người khác).

  → **337/337 Vitest** pass, 44 file, thêm 11 test (6 trang tra cứu, 3 lịch sử, 1 router thật, 1 service).
  Router guard/menu kiểm đúng Shop/NV, chặn Shipper và người chưa đăng nhập. Lịch sử dùng số/cờ backend,
  đổi thứ tự tải về trang 1, reload giữ thứ tự; đổi đơn xóa mốc cũ; phản hồi cũ không đè đơn/mã mới.
  Lookup lưu mã query URL, hiển thị lỗi theo trường/404/mất mạng, thử lại cùng mã và route chi tiết theo vai trò.

  → Chrome headless + Django API/PostgreSQL **test DB thật** đạt: Shop tra HTT/YC, không thấy mã Shop khác,
  NV thấy đơn Shop khác, Shipper bị đưa về trang chủ; nhãn Lần lấy 1/Lần giao 2/Đổi Shipper, đổi thứ tự,
  cờ chưa phát sinh, URL restore, link hash cuộn không bị topbar che, mất mạng giữ mã và thử lại.
  **0 Vue warning / 0 page error** trên browser, 8 ảnh 1440/390 đã kiểm, không tràn ngang:
  [bằng chứng](artifacts/phase2/README.md). Lượt cuối browser 8,068 s.
  Server test 8010/5180 đã dừng và kiểm cổng trống, fixture test DB được dọn.

  → Build cuối đạt, 1.833 module, 4,84 s, outDir `node_modules/.cache/spec010-phase2-build` (giữ cách tránh
  `dist` bị EPERM từ spec 009). Hai component vừa chỉnh cuộn/validation kiểm lại **14/14** test pass.
  Toàn Vitest vẫn có warning fixture AccountCreateView/navActive không đổi trong Phase 2; browser thật không có.

```powershell
cd frontend
npm.cmd run test
npm.cmd run build -- --outDir node_modules/.cache/spec010-phase2-build --emptyOutDir false
cd ..
.\venv\Scripts\python.exe specs/010-tra-cuu-lich-su/tools/run_browser_phase2.py
```

Xong khi: test pass; build; 0 cảnh báo Vue.

---

## Phase 3 — Nghiệm thu

- [x] **3.1** `check`, backend xuôi + ngược; Vitest, audit, build; rà hardcode.
- [ ] **3.2** `manual-test.md` + người dùng thử trình duyệt.
- [x] **3.3** Đánh dấu tiêu chí; `specs/README.md`, README gốc.

  → [Báo cáo nghiệm thu](acceptance.md): check/migration sạch; **550/550 xuôi và 550/550 ngược** trên PostgreSQL,
  **337/337 Vitest**, build đạt. Audit production **0**; audit đầy đủ còn **7** mục dev (5 moderate, 2 critical),
  không ghi là audit sạch. Đã rà quyền, serializer, query và hardcode; không cần đổi logic ứng dụng ở Phase 3.
  Đã viết [manual-test.md](manual-test.md) và gửi câu hỏi cho người dùng; **3.2 giữ mở** tới khi có kết quả tự thử.
  Bằng chứng Chrome và ảnh lưu riêng ở [artifacts/phase3](artifacts/phase3/README.md).

  → Chrome **1/1 test / 8,987 s**, **0 Vue warning / 0 page error**, 8 ảnh 1440/390; cổng test 8010/5180 đã trống.
  Browser dùng fixture test DB riêng, Django dọn khi kết thúc. Không đánh dấu thay phần người dùng thử.

## Nhật ký

| Ngày | Phase | Ghi chú |
|---|---|---|
| 23/11/2026 | 3 | Kiểm tra kỹ thuật đạt: Django check/migration sạch; PostgreSQL 550/550 xuôi (56,421 s) và 550/550 ngược (77,548 s); Vitest 337/337 (44 file, 28,90 s); build 1.833 module (4,67 s) vào cache riêng. Chrome/API thật 1/1 (8,987 s), 0 Vue warning/page error, 8 ảnh; server test đã dừng. Rà quyền/query/serializer/hardcode không thấy lỗi mới. Audit production 0; đầy đủ còn 7 mục dev (2 critical), giữ major hiện có. Đã viết manual-test và gửi câu hỏi tự thử, chưa có xác nhận nên 3.2 còn mở. Cập nhật tiêu chí/README và acceptance; không tuyên bố nghiệm thu toàn bộ. |
| 23/11/2026 | — | Lập spec, chờ chốt D1–D7. Đối chiếu code: tìm **gần đúng** trong danh sách Shop / NV đã có và đã giới hạn theo quyền; API lịch sử + `ShipmentEvent.task` đã có → spec chỉ bù tra cứu đúng mã + phân biệt lần lấy / giao / đổi người. Viết khi spec 009 mới xong Phase 1 (không phụ thuộc 009 — chỉ nhãn "Đổi Shipper" dùng mã hành động của 009, đã có từ Phase 1). |
| 23/11/2026 | 1 | **Backend đã triển khai.** Lookup đúng YC/HTT, trim đầu/cuối + uppercase, không gần đúng; query ngoài lọc quyền, cùng body 404 ngoài Shop/không tồn tại. Lookup kế thừa summary + updated_at, không đổi list. Lịch sử thêm task/pickup_no tính toàn đơn, ordering+id, has_transport_activity toàn đơn; actor Shop chỉ id/full_name, NV giữ cấu trúc cũ. **19 test mới**, cập nhật 1 test cũ theo hợp đồng; mốc 19/19, **9/9 đột biến bị bắt**; check/migration sạch. Đo 20.000 đơn cho cả hai vai trò/mã; query OR ban đầu chọn index Shop rồi lọc nhiều dòng, đã dùng scalar subquery InitPlan tìm theo cột mã unique, query ngoài vẫn kiểm quyền. Plan lưu cuối dùng index mã _like có sẵn, 0,050–0,537 ms; không ép planner/thống kê, rollback sạch, sequence giữ nguyên. Lượt fixture đầu dùng mã YC dài quá, CHECK bắt đúng, đã sửa về 8 chữ số. Rà soát Phase 0 được dùng làm hướng triển khai theo yêu cầu làm Phase 1, không ghi giả xác nhận riêng D1–D7. Chưa làm frontend Phase 2. |
| 23/11/2026 | 2 | **Xong.** TrackingView + route/menu Shop/NV, service lookup/order; URL giữ mã, đúng link chi tiết/lịch sử theo vai trò, loading/404/lỗi mạng/thử lại, chống response cũ. Lịch sử lấy số lần và cờ toàn đơn backend, đổi thứ tự về trang 1, nhãn đổi người và người dự kiến; link hash cuộn sau tải, scroll margin theo topbar. **337/337 Vitest**, thêm 11 test; 14 test component chạy lại sau chỉnh validation/cuộn đều đạt. Build cuối **1.833 module / 4,84 s**, cache riêng tránh dist EPERM. Chrome/API thật trên PostgreSQL test DB đạt tra HTT/YC, Shop không thấy đơn khác, NV thấy, Shipper bị chặn; lịch sử/order/hash và retry mạng. **0 Vue warning/page error**, 8 ảnh 1440/390 đã kiểm, không tràn ngang; lượt cuối 8,068 s. Server 8010/5180 đã dừng, fixture được dọn. Chưa làm nghiệm thu Phase 3. |
