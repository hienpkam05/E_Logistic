# Spec 001 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

File này liệt kê **mọi bảng, trường, ràng buộc, enum và migration phát sinh trong spec 001**. Khi code lệch khỏi file này, sửa file này trong cùng thay đổi.

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Bảng mới | `accounts_user` | Thay User mặc định của Django |
| Bảng mới | `notifications_notification` | Thông báo nội bộ |
| Enum mới (không tạo bảng) | `UserRole`, `ShipmentStatus`, `HolderType`, `ShipmentAction`, `TaskType`, `TaskStatus`, `TaskAction`, `NotificationKind`, `ErrorCode` | Nguồn duy nhất cho giá trị |
| Hằng số mới | `MAX_DELIVERY_ATTEMPTS`, `COD_MAX_VND`, tiền tố mã… | Xem cuối file |
| Migration | `accounts/0001_initial`, `notifications/0001_initial` | Hai migration đầu tiên của dự án |

---

## User

App `accounts` · Bảng `accounts_user` · Kế thừa `AbstractUser` · `AUTH_USER_MODEL = "accounts.User"`

| Trường | Kiểu | Null | Mặc định | Ràng buộc / ghi chú | Nguồn |
|---|---|---|---|---|---|
| `id` | BigAutoField | | | PK | |
| `username` | CharField(150) | | | Unique (kế thừa). Tên đăng nhập | UC01.1 |
| `password` | CharField(128) | | | Băm (kế thừa). Không bao giờ trả qua API | UC01.1 BR1 |
| `full_name` | CharField(150) | | | Bắt buộc. Với Shop là tên Shop | UC02.1 |
| `phone` | CharField(10) | | | **Unique**. Validator `PHONE_REGEX` + `CheckConstraint` `accounts_user_phone_format` (regex ở mức DB) | UC02.2, 06.2 |
| `role` | CharField(10) | | | **Bắt buộc**, choices `UserRole`. `CheckConstraint` `accounts_user_role_valid`: `role IN ('SHOP','ADMIN','SHIPPER')` | Phân quyền mục 1 |
| `address` | CharField(255) | | `""` | Địa chỉ liên hệ (không dùng làm địa chỉ lấy hàng) | UC02.2 |
| `must_change_password` | BooleanField | | `False` | Bật khi Nhân viên đặt mật khẩu tạm | D4 |
| `email` | EmailField | | `""` | Kế thừa, không dùng cho nghiệp vụ | |
| `is_active` | BooleanField | | `True` | Kế thừa. `False` = tài khoản bị khóa | UC06.4 |
| `is_staff` | BooleanField | | `False` | Kế thừa. Chỉ cho phép vào Django admin — **không phải** vai trò nghiệp vụ | |
| `is_superuser` | BooleanField | | `False` | Kế thừa | |
| `last_login` | DateTimeField | ✔ | | Kế thừa | |
| `date_joined` | DateTimeField | | now | Kế thừa. Thời điểm tạo | |
| `updated_at` | DateTimeField | | auto_now | Mới | |
| ~~`first_name`~~ | | | | **Bỏ** (đặt `= None`) | |
| ~~`last_name`~~ | | | | **Bỏ** (đặt `= None`) | |

Index: unique `username`, unique `phone`; index thường `accounts_user_role_idx` (`role`).

Ràng buộc trong DB (đã kiểm tra sau migrate): `accounts_user_pkey`, `accounts_user_username_key`, `accounts_user_phone_key`, `accounts_user_role_valid`, `accounts_user_phone_format`.

`REQUIRED_FIELDS = ["full_name", "phone"]` — lệnh `createsuperuser` hỏi thêm hai trường này.

Hành vi:
- `UserManager.create_user(username, password, *, role, full_name, phone, **extra)` — thiếu `role` → `ValueError`.
- `UserManager.create_superuser(...)` — gán `role=ADMIN`, `is_staff=True`, `is_superuser=True`.
- Property: `is_shop`, `is_admin_role`, `is_shipper`.

---

## Notification

App `notifications` · Bảng `notifications_notification`

| Trường | Kiểu | Null | Mặc định | Ràng buộc / ghi chú |
|---|---|---|---|---|
| `id` | BigAutoField | | | PK |
| `recipient` | FK → User | | | `on_delete=CASCADE`, `related_name="notifications"`, `db_index=False` (index ghép bên dưới đã bắt đầu bằng `recipient`; User không bị xóa cứng nên CASCADE không xảy ra trong nghiệp vụ) |
| `kind` | CharField(40) | | | Choices `NotificationKind` |
| `title` | CharField(200) | | | |
| `body` | TextField | | `""` | |
| `payload` | JSONField | | `{}` | Liên kết đối tượng, vd `{"shipment_id": 12}`. Không chứa dữ liệu nhạy cảm |
| `created_at` | DateTimeField | | auto_now_add | |
| `read_at` | DateTimeField | ✔ | `NULL` | `NULL` = chưa đọc |

Index: ~~`notif_recipient_read_idx` `(recipient, read_at, -created_at)`~~ — **đã thay ở spec 002** bằng `notif_recipient_created_idx` và `notif_recipient_unread_idx` (partial), xem [spec 002 models.md](../002-xac-thuc/models.md#index). Không có index riêng cho `recipient_id`.
Ràng buộc trong DB (đã kiểm tra sau migrate): `notifications_notification_pkey`, khóa ngoại `recipient_id → accounts_user`.
Sắp xếp mặc định: `-created_at`, `-id`. Property `is_read`.

Service `notify(recipients, kind, title, body="", payload=None)` (`notifications/services.py`):
- Nhận một User hoặc danh sách; bỏ trùng và `None`; một bản ghi mỗi người nhận (`bulk_create`).
- `kind` ngoài `NotificationKind` → `ValueError`.
- **Gọi ngoài `transaction.atomic()` → `RuntimeError`**, để thông báo luôn rollback cùng nghiệp vụ.
- Mỗi bản ghi có bản sao `payload` riêng.

Django admin: chỉ xem (không thêm/sửa/xóa).

---

## Enum

Giá trị lưu DB là mã tiếng Anh; nhãn tiếng Việt chỉ để hiển thị. Đầy đủ bảng chuyển trạng thái xem [spec.md mục 3.4](spec.md#34-enum-nghiệp-vụ-và-bảng-chuyển-trạng-thái).

| Enum | File | Giá trị |
|---|---|---|
| `UserRole` | `accounts/constants.py` | `SHOP`, `ADMIN`, `SHIPPER` |
| `ShipmentStatus` | `shipments/constants.py` | 17 giá trị: `PENDING_APPROVAL`, `CANCELLED`, `REJECTED`, `AWAITING_PICKUP`, `PICKUP_ASSIGNED`, `PICKED_UP`, `PICKUP_FAILED`, `PICKUP_ABANDONED`, `AT_HUB`, `OUT_FOR_DELIVERY`, `DELIVERED`, `DELIVERY_FAILED`, `AWAITING_REDELIVERY`, `AWAITING_RETURN`, `RETURNING`, `AWAITING_SHOP_PICKUP`, `RETURNED_TO_SHOP` |
| `HolderType` | `shipments/constants.py` | `SHOP`, `SHIPPER`, `HUB`, `RECIPIENT` |
| `ShipmentAction` | `shipments/constants.py` | 18 hành động trong bảng chuyển trạng thái vận đơn |
| `TaskType` | `dispatch/constants.py` | `PICKUP`, `DELIVERY`, `RETURN` |
| `TaskStatus` | `dispatch/constants.py` | `ACTIVE`, `PENDING_SWAP_HANDOVER`, `SUCCEEDED`, `FAILED`, `REPLACED` |
| `TaskAction` | `dispatch/constants.py` | `TASK_SUCCEED`, `TASK_FAIL`, `TASK_REPLACE`, `TASK_START_SWAP`, `TASK_CONFIRM_SWAP` |
| `NotificationKind` | `notifications/constants.py` | `REQUEST_APPROVED`, `REQUEST_REJECTED`, `TASK_ASSIGNED`, `TASK_REPLACED`, `PICKED_UP`, `PICKUP_FAILED`, `PICKUP_ABANDONED`, `DELIVERED`, `DELIVERY_FAILED`, `RETURN_DECIDED`, `RETURN_AT_HUB`, `RETURN_COMPLETED`, `ACCOUNT_LOCKED_TASKS` |
| `ErrorCode` | `core/errors.py` | `VALIDATION_ERROR`, `NOT_AUTHENTICATED`, `PERMISSION_DENIED`, `NOT_FOUND`, `INVALID_TRANSITION`, `CONFLICT`, `LIMIT_REACHED`, `REQUEST_ERROR`, `SERVER_ERROR` (nhãn = thông điệp mặc định tiếng Việt) |

Thêm giá trị enum ở spec sau: sửa đúng file trên và ghi vào `models.md` của spec đó. Đổi hoặc xóa giá trị đã lưu DB cần migration dữ liệu.

## Hằng số

| Hằng số | File | Giá trị | Quyết định |
|---|---|---|---|
| `PHONE_REGEX` | `accounts/constants.py` | `^0\d{9}$` | |
| `MAX_DELIVERY_ATTEMPTS` | `dispatch/constants.py` | `3` | Đặc tả mục 1 |
| `COD_MAX_VND` | `shipments/constants.py` | `50_000_000` | D3 — chờ chốt |
| `REQUEST_CODE_PREFIX`, `REQUEST_CODE_DIGITS` | `shipments/constants.py` | `"YC"`, `8` | D2 — chờ chốt |
| `TRACKING_CODE_PREFIX`, `TRACKING_CODE_DATE_FORMAT`, `TRACKING_CODE_RANDOM_LENGTH` | `shipments/constants.py` | `"HTT"`, `"%y%m%d"`, `5` | D2 — chờ chốt |
| `TRACKING_CODE_ALPHABET` | `shipments/constants.py` | `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (bỏ I, O, 0, 1) | D2 |
| `INITIAL_SHIPMENT_STATUS`, `TERMINAL_SHIPMENT_STATUSES` | `shipments/constants.py` | `PENDING_APPROVAL`; `CANCELLED`, `REJECTED`, `PICKUP_ABANDONED`, `DELIVERED`, `RETURNED_TO_SHOP` | |
| `INITIAL_TASK_STATUS`, `TERMINAL_TASK_STATUSES` | `dispatch/constants.py` | `ACTIVE`; `SUCCEEDED`, `FAILED`, `REPLACED` | |
| `OPEN_TASK_STATUSES` | `dispatch/constants.py` | `ACTIVE`, `PENDING_SWAP_HANDOVER` — dùng cho ràng buộc "một nhiệm vụ mở mỗi vận đơn" (spec 006) | |
| `SHIPMENT_TRANSITIONS`, `TASK_TRANSITIONS` | `shipments/constants.py`, `dispatch/constants.py` | Bảng `action → Transition(sources, target, roles)` | spec.md mục 3.4 |

## Migration

| Migration | Nội dung | Ghi chú |
|---|---|---|
| `accounts/0001_initial` | Tạo `accounts_user` | **Phải là migration đầu tiên áp dụng lên DB** |
| `notifications/0001_initial` | Tạo `notifications_notification` | Phụ thuộc `accounts/0001_initial` |

Bảng tạo ở spec sau (`Shipment`, `ShipmentEvent`, `Task`, `TaskResult`, `Handover`, `LocationPing`) chỉ được thiết kế ở [spec.md mục 6](spec.md#6-thiết-kế-tham-chiếu-cho-spec-sau-chưa-tạo-bảng), chưa có migration trong spec này.

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 20/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 4: tạo `notifications/0001_initial` và áp dụng lên DB. Bỏ index thừa trên `recipient_id` (`db_index=False`) — rút migration bản đầu (bảng trống, chỉ DB local) và tạo lại |
| 21/11/2026 | Phase 3: tạo enum + bảng chuyển trạng thái vận đơn/nhiệm vụ (không có migration); thêm hằng số trạng thái đầu/kết thúc/mở và chi tiết định dạng mã |
| 21/11/2026 | Phase 1: tạo `accounts/0001_initial` và áp dụng lên DB. Thêm `CheckConstraint` định dạng `phone` ở mức DB; ghi tên index/ràng buộc thực tế |
