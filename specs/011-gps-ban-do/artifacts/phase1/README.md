# Spec 011 Phase 1 — 23/11/2026

Đã triển khai LocationPing, constants/metadata và POST `/api/v1/dispatch/tasks/{id}/locations/`.
Không có API xem vị trí/purge/frontend trong Phase 1. Phần lưu/gửi làm theo phương án đã trình bày
và yêu cầu tiếp tục Phase 1; không coi đó là câu trả lời riêng chốt toàn bộ D1–D10.

| Kiểm chứng | Kết quả |
|---|---|
| Django check | Không có lỗi |
| makemigrations --check --dry-run | No changes detected |
| GPS + metadata | 30/30 |
| [Toàn backend xuôi](backend-forward.txt) | 570/570, 52,781 s |
| [Toàn backend đảo thứ tự](backend-reverse.txt) | 570/570, 53,462 s |
| [Đột biến](mutations.txt) | Mốc 20/20, 7/7 bị bắt |

20 test mới kiểm quyền/phiên/khóa user, 404 trước payload sai, task đóng/chờ bàn giao/đã thay,
tọa độ/accuracy/phần lẻ/null và DB CHECK, timezone/biên thời gian, replay/nhịp theo máy chủ,
không đổi Shipment/Task/Event/Notification/COD. Test giao dịch thật chạy hai request song song,
đua đóng task và khóa user, kiểm không deadlock.

Runner mutation dùng process riêng, không sửa file runtime; đích kiểm quyền nằm trong helper service
thay vì module permission vì helper đã import alias. Các biến thể còn lại bỏ kiểm task mở, cửa sổ thời gian,
nhịp, replay, thời điểm phân công, và kiểm active sau khóa. Không tính lỗi hạ tầng là bắt được mutation.

Migration đã được áp dụng khi chạy PostgreSQL **test DB**. DB người dùng chưa migrate:
`showmigrations tracking` vẫn `[ ] 0001_initial`. Khi chuẩn bị chạy chức năng trên DB local,
review migration rồi chạy theo quy trình của dự án; không reset dữ liệu.

Lệnh từ gốc repo, dùng venv hiện có, chạy tuần tự vì các suite dùng chung test DB:

```powershell
.\venv\Scripts\python.exe backend/manage.py check
.\venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe backend/manage.py test apps --keepdb --noinput
.\venv\Scripts\python.exe backend/manage.py test apps --reverse --keepdb --noinput
.\venv\Scripts\python.exe specs/011-gps-ban-do/tools/check_phase1_mutations.py
```

Log redirect PowerShell có thể gắn nhãn NativeCommandError cho stderr của test runner;
kết quả dựa trên exit code và tổng kết OK/FAILED, không dựa vào nhãn shell.
