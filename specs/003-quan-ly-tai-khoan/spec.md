# Spec 003 — Quản lý tài khoản và Shipper

Trạng thái: **Đã triển khai (21/11/2026)** — 13/14 tiêu chí đạt bằng test tự động + smoke test; còn thử trên trình duyệt ([manual-test.md](manual-test.md)). D1–D7 theo đề xuất. Ngày lập: 21/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) · [models.md](models.md) · [api.md](api.md) · [manual-test.md](manual-test.md)

Nguồn: [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md) UC02.4, UC06.1–06.4, UC01.3 A1 · [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md) mục 3 (UC02.4, UC06.1–06.4), mục 4 (đặt lại mật khẩu người khác, tạo tài khoản Shop), mục 5 quy tắc 1, 4, 7, 8, 10 · [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md) UC02.4, UC06.1–06.4 · Nền: [spec 001](../001-nen-tang/spec.md), [spec 002](../002-xac-thuc/spec.md).

## 1. Mục tiêu và phạm vi

Nhân viên/Admin (`ADMIN`) quản lý tài khoản Shop, Shipper và Nhân viên trong ứng dụng: xem danh sách, thêm, sửa hồ sơ, khóa/mở khóa, đặt lại mật khẩu tạm sau khi xác minh — mọi thao tác có lịch sử người thực hiện. Đây là cách duy nhất tạo tài khoản Shop/Shipper (không tự đăng ký).

| UC | Tên | Phần làm trong spec này |
|---|---|---|
| UC02.4 | Quản lý tài khoản người dùng | Toàn bộ: danh sách theo vai trò/trạng thái, thêm (A1), sửa, khóa/mở khóa (A2), E1 trùng dữ liệu + Admin hoạt động cuối cùng |
| UC06.1 | Xem danh sách Shipper | Toàn bộ — cùng màn hình/API với UC02.4, lọc sẵn vai trò Shipper |
| UC06.2 | Thêm Shipper | Toàn bộ — cùng form tạo tài khoản, khóa sẵn vai trò Shipper |
| UC06.3 | Cập nhật thông tin Shipper | Toàn bộ, gồm E1 "tài khoản vừa thay đổi" (chống ghi đè) |
| UC06.4 | Khóa/mở khóa Shipper | Khóa, mở khóa, vô hiệu hóa phiên, chặn đăng nhập. **Phần nhiệm vụ đang mở** (bước 2, 6: hiển thị, đánh dấu cần xử lý) chỉ để sẵn điểm móc — bảng nhiệm vụ tạo ở **spec 006** |
| UC01.3 A1 | Nhân viên hỗ trợ khôi phục mật khẩu | Đặt lại mật khẩu tạm sau khi Nhân viên xác minh danh tính (phía người dùng đã làm ở spec 002) |

**Ngoài phạm vi:** xóa tài khoản (không có — BR1); tự đăng ký; OTP/email/SMS; phân công/chặn phân công (spec 006 kiểm tra `is_active` khi phân công); đổi Shipper khi bị khóa (spec 009).

## 2. Quyết định cần chốt

**Đã chốt 21/11/2026: cả 7 điểm theo đề xuất** (D1: quản lý cả 3 vai trò; D3: hệ thống sinh mật khẩu tạm, hiện một lần).

| # | Vấn đề | Phương án |
|---|---|---|
| D1 | Vai trò được quản lý | `ADMIN` tạo/sửa/khóa/đặt lại mật khẩu **cả ba vai trò** (Nhân viên và Admin là một vai trò — spec 001). Ngoại lệ: **không thao tác lên chính mình** (tự sửa qua Hồ sơ/Đổi mật khẩu của spec 002), để không tự khóa mình hay tự cấp mật khẩu tạm |
| D2 | Đổi vai trò | **Không đổi vai trò sau khi tạo** (UC06.3 BR1). Cần vai trò khác thì tạo tài khoản mới — tránh Shop có vận đơn bỗng thành Shipper |
| D3 | Mật khẩu khi tạo tài khoản | Hệ thống **sinh mật khẩu tạm ngẫu nhiên**, hiện **một lần duy nhất** cho Nhân viên để chuyển cho người dùng; tài khoản mới có `must_change_password = true` (đổi ngay lần đăng nhập đầu — luồng spec 002). Nhân viên không tự đặt mật khẩu cho người khác |
| D4 | Đặt lại mật khẩu (UC01.3 A1) | Như D3; Nhân viên phải đánh dấu **"Đã xác minh danh tính"** (họ tên + số điện thoại đã đăng ký, xác minh ngoài hệ thống) — hệ thống ghi nhận vào lịch sử. Mọi phiên cũ của tài khoản mất hiệu lực |
| D5 | Khóa tài khoản | Lý do **không bắt buộc** (ghi vào lịch sử nếu có). Phiên cũ mất hiệu lực ngay và **không sống lại khi mở khóa** (cơ chế `session_version`, mục 3.2) |
| D6 | Lịch sử tài khoản | Bảng `AccountEvent` chỉ thêm, không sửa/xóa: ai, lúc nào, hành động, trường nào đổi (giá trị trước/sau, **không bao giờ** có mật khẩu) |
| D7 | Tìm kiếm | Một ô tìm theo tên đăng nhập, họ tên, số điện thoại (chứa chuỗi, không phân biệt hoa thường). Tìm không dấu ("hoa an" ra "Hòa An") **chưa làm** — cần extension `unaccent` của PostgreSQL, để sau nếu cần |

## 3. Backend

### 3.1. Quyền

- Mọi endpoint quản lý: `HasRole.of(UserRole.ADMIN)` (đã kế thừa chặn mật khẩu tạm — spec 002). Shop/Shipper gọi → `403`.
- Thao tác lên chính mình (D1): `PATCH`, khóa, mở khóa, đặt lại mật khẩu → `403 PERMISSION_DENIED` với thông điệp "Dùng trang Thông tin cá nhân / Đổi mật khẩu để thay đổi tài khoản của chính bạn." Xem chi tiết chính mình vẫn được.
- Không có `DELETE` (BR1) → `405`.

### 3.2. Phiên khi khóa và mở khóa (`session_version`)

Vấn đề: Django đã từ chối phiên của tài khoản `is_active = false`, nhưng phiên vẫn nằm trong DB — **mở khóa thì cookie cũ dùng lại được ngay**, trái UC06.4 A1.3 ("Shipper đăng nhập lại").

Giải pháp: thêm `User.session_version` (số nguyên) và ghi đè `User.get_session_auth_hash()` để băm kèm `session_version`. Django đã kiểm tra hash này ở **mọi request** → tăng `session_version` là **mọi phiên cũ mất hiệu lực vĩnh viễn**, không cần quét bảng phiên.

| Sự kiện | `session_version` | Kết quả |
|---|---|---|
| Khóa | +1 | Phiên cũ hết hiệu lực; mở khóa sau đó cũng không dùng lại được |
| Đặt lại mật khẩu | (mật khẩu đổi → hash đổi) | Phiên cũ hết hiệu lực — đúng sẵn |
| Tự đổi mật khẩu (spec 002) | không đổi | `update_session_auth_hash` giữ phiên hiện tại như cũ |

Lưu ý triển khai: đổi công thức hash làm **tất cả phiên đang có mất hiệu lực một lần** khi deploy — mọi người đăng nhập lại.

### 3.3. Admin hoạt động cuối cùng (BR2)

- Không khóa được tài khoản `ADMIN` nếu sau khi khóa không còn `ADMIN` nào đang hoạt động → `409 LIMIT_REACHED` "Không thể khóa Nhân viên/Admin đang hoạt động cuối cùng."
- Chống hai Admin khóa nhau cùng lúc: trong transaction, `select_for_update()` **mọi** `ADMIN` đang hoạt động **theo thứ tự `id`** rồi mới khóa dòng mục tiêu và đếm. Khóa dòng mục tiêu trước sẽ gây deadlock; không khóa danh sách thì cả hai cùng thành công và mất hết Admin — cả hai đã được chứng minh bằng kiểm tra đột biến (Phase 3).
- Superuser Django (`is_superuser`) vẫn là `ADMIN`; không có quy tắc riêng.

### 3.4. Service — `accounts/services.py`

| Hàm | Việc làm |
|---|---|
| `create_account(actor, data)` | Tạo user (`role` từ form; UC06.2 luôn `SHIPPER`), sinh mật khẩu tạm, `must_change_password=True`; ghi `AccountEvent(CREATED)`; trả `(user, temp_password)` |
| `update_account(actor, user, data, expected_updated_at)` | Sửa `full_name`, `phone`, `address`. `updated_at` khác giá trị client đã tải → `409 CONFLICT` "Tài khoản vừa được người khác thay đổi. Vui lòng tải lại." (UC06.3 E1). Ghi `AccountEvent(UPDATED)` với các trường đổi (trước/sau) |
| `lock_account(actor, user, reason="")` | Kiểm tra D1, BR2; đã khóa → trả trạng thái hiện tại (idempotent, UC06.4 E1.1); `is_active=False`, `session_version += 1`; ghi `LOCKED`; gọi hook `account_locked` (spec 006 đăng ký: đánh dấu nhiệm vụ mở cần xử lý, thông báo `ACCOUNT_LOCKED_TASKS`) |
| `unlock_account(actor, user)` | Đã hoạt động → trả hiện tại; `is_active=True`; ghi `UNLOCKED`. Không khôi phục phiên cũ |
| `reset_password(actor, user, identity_verified)` | `identity_verified` phải `true` (D4); sinh mật khẩu tạm, `must_change_password=True`; ghi `PASSWORD_RESET` (chỉ ghi "đã xác minh", không ghi mật khẩu); trả mật khẩu tạm |

- Mọi hàm ghi trong `transaction.atomic()` + `select_for_update()` bản ghi user (spec 001 mục 3.6).
- Mật khẩu tạm: 12 ký tự từ `secrets`, bỏ ký tự dễ nhầm (`0 O 1 l I`), luôn qua `AUTH_PASSWORD_VALIDATORS`. Không lưu dạng rõ, không ghi log, không gửi trong thông báo — chỉ có trong **một** response.
- Trùng `username`/`phone` → `400 VALIDATION_ERROR` theo trường, thông điệp tiếng Việt; tranh chấp cùng lúc → `IntegrityError` đổi thành lỗi trường (như spec 002).

### 3.5. Danh sách

- Lọc: `role`, `is_active` (`true`/`false`), `q` (D7); sắp xếp mặc định `role`, `username`; phân trang chuẩn.
- Trả về đúng trường quản trị cần (mục api.md), **không** có mật khẩu, hash, phiên (UC06.1 BR1).
- Truy vấn không N+1; thêm index nếu `EXPLAIN` cho thấy cần (bảng nhỏ — kiểm tra ở Phase 2).

## 4. Frontend

| Route | View | Mô tả |
|---|---|---|
| `/staff/accounts` | `views/staff/AccountListView.vue` | Bảng tài khoản; tab vai trò (Tất cả/Shop/Shipper/Nhân viên), lọc trạng thái, ô tìm; bộ lọc + trang trên URL; nút "Thêm tài khoản" |
| `/staff/accounts/new` | `views/staff/AccountCreateView.vue` | Form tạo; `?role=SHIPPER` khóa sẵn vai trò (UC06.2); Hủy quay về danh sách (A1); thành công → hộp **mật khẩu tạm hiện một lần** kèm nút sao chép |
| `/staff/accounts/:id` | `views/staff/AccountDetailView.vue` | Hồ sơ + sửa (Lưu/Hủy, gửi `updated_at`), Khóa/Mở khóa (hộp xác nhận nêu ảnh hưởng — A2.1), Đặt lại mật khẩu (ô "Đã xác minh danh tính"), lịch sử thao tác |

- Menu Nhân viên (trang chủ + thanh trên): "Quản lý tài khoản" → `/staff/accounts`, "Quản lý Shipper" → `/staff/accounts?role=SHIPPER` — **cùng một màn hình**, không chép thành màn riêng.
- Component dùng chung mới: `components/common/PaginationBar.vue` (tách từ `NotificationsView` — nay có danh sách thứ hai), `components/common/ConfirmDialog.vue` (dùng `<dialog>`), `components/common/OneTimeSecret.vue` (hiện mật khẩu tạm + sao chép + cảnh báo chỉ hiện một lần).
- Nhãn vai trò lấy từ store meta; trạng thái Hoạt động/Bị khóa là nhãn cố định của màn hình này (không phải enum backend).
- Route `meta.roles: [ROLES.ADMIN]` — guard sẵn có.

## 5. Tiêu chí nghiệm thu

Checklist UC02.4, UC06.1–06.4 và tình huống phân quyền mục 6:

Bằng chứng: test backend (`test_session_version`, `test_management`, `test_management_actions`) + test Vitest + smoke test trên server đang chạy (nhật ký Phase 1–6 ở [tasks.md](tasks.md)).

- [x] Shop/Shipper gọi mọi API quản lý tài khoản → `403`; chưa đăng nhập → `401`. *(test_management, test_management_actions; smoke `demo_shop`)*
- [x] Danh sách lọc đúng theo vai trò, trạng thái, từ khóa; phân trang; không có mật khẩu/hash/phiên trong response. *(test_management; AccountListView.spec; smoke)*
- [x] Tạo tài khoản: trùng `username` hoặc `phone` → `400` đúng trường, **không** tạo tài khoản dở dang; thành công trả mật khẩu tạm **một lần**, tài khoản có `must_change_password = true`, đăng nhập lần đầu bị buộc đổi mật khẩu. *(test_management, kể cả tranh chấp `IntegrityError`; smoke)*
- [x] Tạo Shipper từ "Quản lý Shipper" luôn ra vai trò `SHIPPER` (UC06.2 BR1). *(AccountCreateView.spec — kể cả khi danh mục chưa tải)*
- [x] Sửa hồ sơ: không đổi được `role`, `username`, `is_active`; dữ liệu trùng/sai → `400`, không lưu gì; tải bản cũ rồi lưu sau khi người khác đã sửa → `409 CONFLICT`. *(test_management; AccountDetailView.spec; smoke)*
- [x] Khóa: tài khoản không đăng nhập được (lỗi chung như sai mật khẩu), phiên đang mở → `401` ngay request kế tiếp; **mở khóa không làm phiên cũ sống lại** — phải đăng nhập lại. *(test_session_version có test đối chứng; test_management_actions; smoke 10/10)*
- [x] Khóa/mở khóa lặp lại → trả trạng thái hiện tại, không ghi lịch sử trùng. *(test_management_actions)*
- [x] Không khóa được Admin hoạt động cuối cùng (`409`); hai Admin khóa nhau cùng lúc không làm hệ thống mất hết Admin. *(test 2 luồng song song thật 5/5 lần + kiểm tra đột biến)*
- [x] Không sửa/khóa/đặt lại mật khẩu chính mình qua chức năng quản lý (`403`). *(test_management, test_management_actions; AccountDetailView.spec ẩn thao tác)*
- [x] Đặt lại mật khẩu: thiếu xác nhận "đã xác minh" → `400`; thành công trả mật khẩu tạm một lần, phiên cũ của tài khoản đó → `401`, đăng nhập bằng mật khẩu tạm bị buộc đổi. *(test_management_actions; smoke)*
- [x] Mỗi thao tác tạo/sửa/khóa/mở khóa/đặt lại có một dòng lịch sử với người thực hiện và thời gian; lịch sử không chứa mật khẩu; không có API sửa/xóa lịch sử. *(test_management_actions; `events/` POST → 405; admin chỉ đọc)*
- [x] Không có API xóa tài khoản (`DELETE` → `405`). *(test_management; smoke)*
- [x] Mật khẩu tạm không xuất hiện trong log, thông báo, lịch sử, hay bất kỳ response nào khác ngoài response tạo/đặt lại. *(test_management, test_management_actions kiểm tra log + body danh sách/chi tiết/lịch sử)*
- [ ] Frontend: test Vitest pass; build; thử trình duyệt theo `manual-test.md`. *(Vitest 136/136 ✔; build ✔ khi xuất ra thư mục khác — `frontend/dist/` cũ vẫn khóa quyền xóa; **chờ người dùng thử theo [manual-test.md](manual-test.md)**.)*

## 6. Ghi chú cho spec sau

- **Spec 006:** khi phân công kiểm tra `shipper.is_active` + vai trò; đăng ký hook `account_locked` để đánh dấu `Task.needs_attention` và gửi `ACCOUNT_LOCKED_TASKS` cho Nhân viên; bổ sung số nhiệm vụ đang mở vào chi tiết tài khoản Shipper (UC06.4 bước 2).
  - **Cập nhật 22/11/2026 (spec 006 đã làm):** kiểm Shipper hoạt động khi phân công (khóa dòng user — không đua với khóa tài khoản); hook đăng ký ở `dispatch/apps.py`, `register_account_locked_hook` bỏ qua đăng ký trùng. **Chưa làm:** số nhiệm vụ đang mở trong hộp khóa (UC06.4 bước 2) → chuyển sang spec 009.
- **Spec 009:** Shipper bị khóa đang giữ hàng → Nhân viên ghi nhận bàn giao thay (UC06.4 BR2).
