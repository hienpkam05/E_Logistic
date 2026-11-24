# Spec 011 Phase 2 — 24/11/2026

GET `/api/v1/shipments/{id}/location/` và command `purge_location_pings` đã triển khai.
Không sửa schema, không tạo migration mới. Migration Phase 1 trên DB đang dùng vẫn `[ ] 0001_initial`;
không chạy purge hoặc migrate trên DB đó trong lượt này.

| Kiểm chứng | Kết quả |
|---|---|
| Django check | Không có lỗi |
| makemigrations --check --dry-run | No changes detected |
| 15 test Phase 2 (11 đọc GPS, 4 purge) | 15/15, 0,741 s |
| [Backend xuôi](backend-forward.txt) | 585/585, 52,835 s |
| [Backend đảo thứ tự](backend-reverse.txt) | 585/585, 58,132 s |
| [Mutation quyền đọc/retention](mutations.txt) | Mốc 35/35 GPS, bắt 6/6 |

Các đột biến: bỏ scope Shop, đọc task đóng, lấy điểm task khác, đánh stale sớm ở đúng 300 giây,
purge theo recorded_at thay vì received_at, xóa cả điểm đúng biên retention. Runner chạy trong process con,
không sửa source server; không tính lỗi hạ tầng là bắt được mutation.

Test kiểm quyền Shop/NV/Shipper, không phiên/tài khoản khóa/mật khẩu tạm, body 404 đơn ngoài quyền bằng
đơn không tồn tại; task đóng/chờ bàn giao/thay người; thứ tự thời điểm đo + id; số JSON, accuracy null,
thời điểm nhận/đo, biên stale 300 giây; không đổi dữ liệu nghiệp vụ; số query không tăng khi có thêm 1.000 điểm.
Purge kiểm biên strict 30 ngày, đồng hồ máy chủ thay cho thiết bị, override ngày, dữ liệu sai và chạy lại không xóa thêm.

## EXPLAIN

[Kế hoạch và kết quả rollback](explain-location.txt): 20.000 điểm task mở + 20.000 điểm task cũ.
`latest_points` và subquery GPS trong `current_task_location` đều dùng **location_task_latest_idx**;
execution time lần đo này lần lượt **0,035 ms** / **0,101 ms**. Không dùng số fixture làm cam kết production.
Task chỉ có 2 hàng nên PostgreSQL chọn seq scan cho bảng task; dữ liệu GPS lớn dùng index đã có, không thêm index.

Runner tạo/chọn **test DB** bằng Django runner, sau đó mới sinh fixture ID âm trong transaction.
Fixture rollback sạch, so sánh count/sequence trước-sau giữ nguyên. Không ép planner, ANALYZE hoặc migrate DB đang dùng.
Không chạy đồng thời script này với suite khác vì dùng chung test DB.

```powershell
.\venv\Scripts\python.exe backend/manage.py test apps.tracking.tests.test_location_read apps.tracking.tests.test_purge --keepdb --noinput
.\venv\Scripts\python.exe backend/manage.py shell -c "exec(open('specs/011-gps-ban-do/tools/explain_location.py', encoding='utf-8').read())"
.\venv\Scripts\python.exe specs/011-gps-ban-do/tools/check_phase2_mutations.py
```

Log PowerShell có thể gắn NativeCommandError cho stderr thông thường; kết luận theo exit code và OK/FAILED.
Purge cần được người vận hành lên lịch riêng; Phase 3–4 frontend/bản đồ vẫn chưa triển khai.
