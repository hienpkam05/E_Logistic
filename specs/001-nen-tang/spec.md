# Spec 001 — Nền tảng và mô hình dữ liệu

Trạng thái: **Đã triển khai (21/11/2026)** — còn 2 việc phía người dùng ở mục 5 (tạo superuser, xóa `frontend/dist/` cũ). Quyết định D2, D3 vẫn theo đề xuất (chỉ là hằng số, đổi được). Ngày lập: 20/11/2026.

Tài liệu kèm theo: [tasks.md](tasks.md) (công việc theo phase) · [models.md](models.md) (bảng, trường, enum, migration) · [api.md](api.md) (endpoint mới/sửa, quy ước API chung).

Nguồn: [Đặc tả 42 UC](../../docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md) (mục 1–2), [Phân quyền](../../docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md) (mục 1, 5), [Checklist](../../docs/HTT_EXPRESS_Checklist_chuc_nang.md) (mục 3, 4), [Kiến trúc](../../docs/architecture.md).

## 1. Mục tiêu và phạm vi

Spec này không triển khai UC nào. Nó dựng phần mọi spec sau dùng chung, để không spec nào tự định nghĩa lại vai trò, trạng thái, mã lỗi hay cách gọi API:

1. Custom User và ba vai trò — **bắt buộc trước lần `migrate` đầu tiên**.
2. Nguồn duy nhất cho mọi enum (vai trò, trạng thái vận đơn, trạng thái/loại nhiệm vụ, hành động, nơi giữ hàng) và bảng chuyển trạng thái.
3. Hằng số nghiệp vụ, định dạng lỗi API, quy ước chống xử lý trùng và đồng thời.
4. Model và service thông báo nội bộ.
5. Endpoint trả enum cho frontend, để frontend không chép lại nhãn trạng thái.
6. Nền frontend: API client, store enum, formatter, badge trạng thái, cấu hình proxy không hardcode.
7. Thiết kế tham chiếu cho các model sẽ tạo ở spec sau (mục 6) — **chỉ thiết kế, chưa tạo bảng**.

**Ngoài phạm vi:** API đăng nhập/đăng xuất, mọi API nghiệp vụ, model `Shipment`, `Task`, `Handover`, lịch sử vận chuyển, GPS, màn hình nghiệp vụ, guard router theo vai trò (spec 002).

## 2. Quyết định cần chốt

Đặc tả chưa quy định các điểm dưới. Spec dùng phương án **Đề xuất** cho tới khi nhóm chốt khác; chỉ cần sửa hằng số/dữ liệu ở đúng một chỗ.

| # | Vấn đề | Đề xuất | Nơi định nghĩa |
|---|---|---|---|
| D1 | Kiểm tra "địa chỉ Hà Nội" | Địa chỉ gồm `phường/xã` (chọn từ danh sách) + `địa chỉ chi tiết` (tự nhập). Danh sách đơn vị hành chính Hà Nội hiện hành (mô hình 2 cấp từ 07/2025) lưu ở **file dữ liệu**, nhóm lấy từ nguồn chính thức; không viết danh sách trong code. Kiểm tra = mã phường/xã có trong danh sách | `backend/apps/shipments/data/hanoi_wards.json` (spec 004) |
| D2 | Định dạng mã | Mã yêu cầu: `YC` + 8 chữ số theo ID (`YC00000123`), sinh khi tạo. Mã vận đơn: `HTT` + `yyMMdd` + 5 ký tự ngẫu nhiên A–Z/2–9 bỏ ký tự dễ nhầm (`HTT261120K7Q2M`), sinh khi duyệt, unique + thử lại khi trùng | Hằng số tiền tố/độ dài trong `shipments/constants.py` |
| D3 | Thông tin kiện hàng | Bắt buộc: mô tả, số kiện (≥ 1). Tùy chọn: khối lượng (gram, > 0). COD là số nguyên VND, 0 ≤ COD ≤ `COD_MAX_VND` (đề xuất 50.000.000) | `shipments/constants.py` |
| D4 | Quên mật khẩu | Người dùng liên hệ Nhân viên; Nhân viên xác minh **họ tên + số điện thoại đã đăng ký** (ngoài hệ thống), đặt mật khẩu tạm và bật `must_change_password`. Lần đăng nhập sau bắt buộc đổi mật khẩu | Trường trên User (spec này), luồng ở spec 002/003 |
| D5 | Bàn giao có sai lệch | Không thêm trạng thái vận đơn. Ghi `discrepancy_note` trên bản ghi bàn giao, giữ nguyên trạng thái, Nhân viên xử lý rồi xác nhận lại | Model `Handover` (mục 6) |
| D6 | Phiên bản Python | `venv/` đang là Python 3.14, README ghi 3.12/3.13. Đề xuất: dùng 3.13 cho ổn định, hoặc giữ 3.14 nếu `pip install -r requirements.txt` và `manage.py check` chạy được, rồi sửa README cho khớp | README, `venv/` |

## 3. Backend

### 3.1. Custom User — `apps/accounts`

`accounts/constants.py`:

```python
class UserRole(models.TextChoices):
    SHOP = "SHOP", "Shop"
    ADMIN = "ADMIN", "Nhân viên/Admin"
    SHIPPER = "SHIPPER", "Shipper"

PHONE_REGEX = r"^0\d{9}$"   # số di động VN 10 chữ số
```

`accounts/models.py` — `User(AbstractUser)`:

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `username` | kế thừa | Tên đăng nhập, unique |
| `full_name` | `CharField(150)` | Họ tên; với Shop là tên Shop. Bỏ `first_name`, `last_name` (đặt `= None`) |
| `phone` | `CharField(10)`, unique | Validator `PHONE_REGEX` |
| `role` | `CharField(choices=UserRole)` | Bắt buộc. `CheckConstraint` giới hạn trong choices |
| `address` | `CharField(255)`, blank | Địa chỉ liên hệ; địa chỉ lấy hàng chi tiết thuộc đơn |
| `must_change_password` | `BooleanField(default=False)` | Quyết định D4 |
| `is_active` | kế thừa | `False` = bị khóa |
| `email` | kế thừa, blank | Không dùng cho nghiệp vụ |
| `updated_at` | `DateTimeField(auto_now=True)` | `date_joined` kế thừa là thời điểm tạo |

- `UserManager.create_superuser` gán `role=ADMIN`; `create_user` bắt buộc truyền `role`.
- Property tiện dụng: `is_shop`, `is_admin_role`, `is_shipper` — so sánh với `UserRole`, không so sánh chuỗi.
- `settings.AUTH_USER_MODEL = "accounts.User"`; đăng ký `UserAdmin` tùy biến trong `accounts/admin.py`.
- Migration `accounts/0001_initial` là migration đầu tiên của dự án.

`accounts/permissions.py` — `HasRole`: permission DRF nhận danh sách `UserRole`, kiểm tra đăng nhập + `is_active` + vai trò. Kiểm tra sở hữu/phân công đặt trong permission của từng app, không đặt ở đây.

### 3.2. Lỗi API thống nhất — `apps/core`

`core/errors.py`:

```python
class ErrorCode(models.TextChoices):
    VALIDATION_ERROR = "VALIDATION_ERROR"        # 400
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"      # 401
    PERMISSION_DENIED = "PERMISSION_DENIED"      # 403
    NOT_FOUND = "NOT_FOUND"                      # 404
    INVALID_TRANSITION = "INVALID_TRANSITION"    # 409 trạng thái hiện tại không cho phép hành động
    CONFLICT = "CONFLICT"                        # 409 dữ liệu vừa bị người khác thay đổi
    LIMIT_REACHED = "LIMIT_REACHED"              # 409 vượt giới hạn nghiệp vụ (vd 3 lần giao)
    SERVER_ERROR = "SERVER_ERROR"                # 500

class BusinessError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, fields=None, status=None): ...
```

- `core/exception_handler.py` đăng ký trong `REST_FRAMEWORK["EXCEPTION_HANDLER"]`. Mọi lỗi (DRF `ValidationError`, `NotAuthenticated`, `PermissionDenied`, `Http404`, `BusinessError`) trả về **một định dạng**:

```json
{ "error": { "code": "INVALID_TRANSITION", "message": "Yêu cầu không còn ở trạng thái Chờ xác nhận.", "fields": {} } }
```

- `fields` chỉ có khi lỗi theo trường: `{"phone": ["Số điện thoại đã tồn tại."]}`.
- Không đưa stack trace hay chi tiết nội bộ vào `message`. Lỗi 404 cho bản ghi không thuộc quyền xem phải giống hệt 404 bản ghi không tồn tại (không lộ sự tồn tại).

### 3.3. Phân trang — `core/pagination.py`

`StandardPagination(PageNumberPagination)`: `page_size = 20`, `page_size_query_param = "page_size"`, `max_page_size = 100`. Thay `DEFAULT_PAGINATION_CLASS` trong settings.

### 3.4. Enum nghiệp vụ và bảng chuyển trạng thái

Mỗi enum định nghĩa **một lần** trong `constants.py` của app sở hữu. Model ở spec sau import từ đây. Giá trị lưu DB là mã tiếng Anh, nhãn tiếng Việt khớp tên trạng thái trong checklist.

**`shipments/constants.py`**

`ShipmentStatus`:

| Mã | Nhãn | Kết thúc? |
|---|---|---|
| `PENDING_APPROVAL` | Chờ xác nhận | |
| `CANCELLED` | Đã hủy | ✔ |
| `REJECTED` | Bị từ chối | ✔ |
| `AWAITING_PICKUP` | Chờ lấy hàng | |
| `PICKUP_ASSIGNED` | Đã phân công lấy hàng | |
| `PICKED_UP` | Đã lấy hàng | |
| `PICKUP_FAILED` | Lấy hàng thất bại | |
| `PICKUP_ABANDONED` | Kết thúc do không lấy được hàng | ✔ |
| `AT_HUB` | Đã nhập điểm tập kết | |
| `OUT_FOR_DELIVERY` | Đang giao hàng | |
| `DELIVERED` | Đã giao hàng | ✔ |
| `DELIVERY_FAILED` | Giao hàng thất bại | |
| `AWAITING_REDELIVERY` | Chờ giao lại | |
| `AWAITING_RETURN` | Chờ xử lý hoàn | |
| `RETURNING` | Đang hoàn | |
| `AWAITING_SHOP_PICKUP` | Chờ Shop đến lấy | |
| `RETURNED_TO_SHOP` | Đã hoàn về Shop | ✔ |

`HolderType` (ai/nơi nào đang giữ hàng): `SHOP`, `SHIPPER`, `HUB` (điểm tập kết), `RECIPIENT` (đã giao người nhận).

`ShipmentAction` và bảng `SHIPMENT_TRANSITIONS` (khai báo dạng dữ liệu, không if/else):

| Hành động | Từ | Sang | Vai trò | UC | Điều kiện thêm (kiểm tra trong service) |
|---|---|---|---|---|---|
| `CREATE_REQUEST` | — | `PENDING_APPROVAL` | SHOP | 05.2 | |
| `CANCEL_REQUEST` | `PENDING_APPROVAL` | `CANCELLED` | SHOP | 05.5 | Chủ sở hữu |
| `REJECT_REQUEST` | `PENDING_APPROVAL` | `REJECTED` | ADMIN | 05.8 | Lý do bắt buộc |
| `APPROVE_REQUEST` | `PENDING_APPROVAL` | `AWAITING_PICKUP` | ADMIN | 05.6 | Sinh mã vận đơn |
| `ASSIGN_PICKUP` | `AWAITING_PICKUP` | `PICKUP_ASSIGNED` | ADMIN | 06.5 | Shipper hoạt động; không có nhiệm vụ lấy đang mở |
| `CONFIRM_PICKUP` | `PICKUP_ASSIGNED` | `PICKED_UP` | SHIPPER | 04.2 | Người phụ trách nhiệm vụ còn hiệu lực |
| `FAIL_PICKUP` | `PICKUP_ASSIGNED` | `PICKUP_FAILED` | SHIPPER | 04.3 | Lý do bắt buộc |
| `RETRY_PICKUP` | `PICKUP_FAILED` | `AWAITING_PICKUP` | ADMIN | 04.13 | Lý do bắt buộc |
| `ABANDON_PICKUP` | `PICKUP_FAILED` | `PICKUP_ABANDONED` | ADMIN | 04.13 | Lý do bắt buộc |
| `RECEIVE_AT_HUB` | `PICKED_UP` | `AT_HUB` | ADMIN | 04.10 | |
| `ASSIGN_DELIVERY` | `AT_HUB`, `AWAITING_REDELIVERY` | `OUT_FOR_DELIVERY` | ADMIN | 06.6 | Số lần đã giao < `MAX_DELIVERY_ATTEMPTS`; điều kiện bàn giao |
| `CONFIRM_DELIVERY` | `OUT_FOR_DELIVERY` | `DELIVERED` | SHIPPER | 04.5, 04.7 | COD thực thu = phải thu; tăng số lần giao |
| `FAIL_DELIVERY` | `OUT_FOR_DELIVERY` | `DELIVERY_FAILED` | SHIPPER | 04.6 | Lý do bắt buộc; tăng số lần giao |
| `DECIDE_REDELIVERY` | `DELIVERY_FAILED` | `AWAITING_REDELIVERY` | ADMIN | 04.12 | Số lần đã giao < `MAX_DELIVERY_ATTEMPTS`, nếu không → `LIMIT_REACHED` |
| `DECIDE_RETURN` | `DELIVERY_FAILED` | `AWAITING_RETURN` | ADMIN | 04.12 | Lý do bắt buộc |
| `ASSIGN_RETURN` | `AWAITING_RETURN` | `RETURNING` | ADMIN | 06.7 | |
| `RECEIVE_RETURN` | `RETURNING`, `AWAITING_RETURN` | `AWAITING_SHOP_PICKUP` | ADMIN | 04.9, 06.7 A1.2 | Từ `AWAITING_RETURN` chỉ khi hàng đã ở `HUB` |
| `CONFIRM_SHOP_RECEIVED` | `AWAITING_SHOP_PICKUP` | `RETURNED_TO_SHOP` | ADMIN | 04.11 | |

- Sửa yêu cầu (UC05.1) không đổi trạng thái — chỉ cho phép khi `PENDING_APPROVAL`, không nằm trong bảng.
- Đổi Shipper (UC06.8) **không đổi trạng thái vận đơn**; chỉ đổi trạng thái nhiệm vụ (bảng dưới).
- Trạng thái kết thúc không có hành động đi ra.

**`dispatch/constants.py`**

```python
MAX_DELIVERY_ATTEMPTS = 3

class TaskType(models.TextChoices):
    PICKUP = "PICKUP", "Lấy hàng"
    DELIVERY = "DELIVERY", "Giao hàng"
    RETURN = "RETURN", "Hoàn hàng"
```

`TaskStatus` và `TASK_TRANSITIONS`:

| Mã | Nhãn | Kết thúc? |
|---|---|---|
| `ACTIVE` | Đang thực hiện | |
| `PENDING_SWAP_HANDOVER` | Chờ bàn giao đổi Shipper | |
| `SUCCEEDED` | Hoàn tất | ✔ |
| `FAILED` | Thất bại | ✔ |
| `REPLACED` | Đã thay thế | ✔ |

| Hành động | Từ | Sang | Vai trò | Ghi chú |
|---|---|---|---|---|
| `TASK_SUCCEED` | `ACTIVE` | `SUCCEEDED` | SHIPPER (lấy/giao); ADMIN (hoàn — xác nhận tiếp nhận UC04.9) | |
| `TASK_FAIL` | `ACTIVE` | `FAILED` | SHIPPER | Chỉ loại PICKUP, DELIVERY |
| `TASK_REPLACE` | `ACTIVE` | `REPLACED` | ADMIN | Người cũ chưa giữ hàng (UC06.8) |
| `TASK_START_SWAP` | `ACTIVE` | `PENDING_SWAP_HANDOVER` | ADMIN | Người cũ đang giữ hàng |
| `TASK_CONFIRM_SWAP` | `PENDING_SWAP_HANDOVER` | `REPLACED` | ADMIN | Sau khi nhận hàng tại điểm tập kết |

Việc Shipper "ghi nhận bàn giao" (hoàn hàng, đổi Shipper) **không đổi trạng thái nhiệm vụ**, chỉ ghi `handover_reported_at` (mục 6). Nhiệm vụ `FAILED` không bao giờ chuyển sang `REPLACED` (UC06.8 A2).

### 3.5. Helper chuyển trạng thái — `core/transitions.py`

Dùng chung cho hai bảng trên (đây là nhu cầu dùng chung cụ thể, không phải base class tổng quát):

```python
@dataclass(frozen=True)
class Transition:
    sources: frozenset[str]     # rỗng = hành động khởi tạo
    target: str
    roles: frozenset[str]

def resolve_transition(table, action, current_status, role) -> Transition:
    """Trả Transition hoặc raise BusinessError(PERMISSION_DENIED / INVALID_TRANSITION)."""
```

- Chỉ kiểm tra vai trò + trạng thái nguồn (vai trò kiểm tra trước, để không tiết lộ trạng thái cho người sai quyền). Sở hữu, phân công, giới hạn lần giao, COD là điều kiện trong service của từng spec.
- `allowed_actions(table, status, role)` trả danh sách hành động khả dụng theo bảng — dùng để API chi tiết trả về các nút thao tác được phép (UC05.7 bước 5); service vẫn kiểm tra đầy đủ khi thực hiện.
- Service luôn gọi helper này; không view nào tự gán `status = ...`.

### 3.6. Quy ước giao dịch, đồng thời, chống trùng

Áp dụng cho mọi service thay đổi dữ liệu ở spec sau:

1. Bọc trong `transaction.atomic()`; khóa bản ghi chính bằng `select_for_update()` trước khi đọc trạng thái.
2. Đổi trạng thái + ghi lịch sử + ghi COD/bàn giao + tạo thông báo trong **cùng** transaction.
3. **Gửi lại** (UC "Quy tắc chung" — mất kết nối rồi gửi lại): nếu bản ghi đã ở trạng thái đích **và** sự kiện cuối cùng là đúng hành động đó do đúng người đó thực hiện trên đúng nhiệm vụ → trả 200 với dữ liệu hiện tại, không ghi thêm gì. Trường hợp khác → `INVALID_TRANSITION`/`CONFLICT`.
4. Ràng buộc DB làm lớp chặn cuối: unique mã vận đơn, unique "một nhiệm vụ đang mở mỗi đơn" (partial unique index), unique số thứ tự lần giao theo đơn.

### 3.7. Thông báo nội bộ — `apps/notifications`

Model `Notification`: `recipient` (FK User), `kind` (`NotificationKind`), `title` (`CharField(200)`), `body` (`TextField`), `payload` (`JSONField`, ví dụ `{"shipment_id": 12}`), `created_at`, `read_at` (null = chưa đọc). Index `(recipient, read_at, -created_at)`.

`NotificationKind` (trong `notifications/constants.py`): `REQUEST_APPROVED`, `REQUEST_REJECTED`, `TASK_ASSIGNED`, `TASK_REPLACED`, `PICKED_UP`, `PICKUP_FAILED`, `PICKUP_ABANDONED`, `DELIVERED`, `DELIVERY_FAILED`, `RETURN_DECIDED`, `RETURN_AT_HUB`, `RETURN_COMPLETED`, `ACCOUNT_LOCKED_TASKS` — nhãn tiếng Việt kèm theo. Spec sau thêm loại mới vào đây, không tự đặt chuỗi.

`notifications/services.py`: `notify(recipients, kind, title, body, payload=None)` — tạo bản ghi bằng `bulk_create`; **phải** được gọi bên trong transaction của nghiệp vụ (hàm tự kiểm tra, gọi ngoài transaction → `RuntimeError`). Không gửi email/SMS. API danh sách / đánh dấu đã đọc thuộc spec 002.

### 3.8. Endpoint enum — `GET /api/v1/meta/choices/`

Trong `apps/core`, `AllowAny` (không chứa dữ liệu nhạy cảm). Trả:

```json
{
  "user_roles": [{"value": "SHOP", "label": "Shop"}, ...],
  "shipment_statuses": [{"value": "PENDING_APPROVAL", "label": "Chờ xác nhận", "terminal": false}, ...],
  "shipment_actions": [...],
  "task_types": [...],
  "task_statuses": [...],
  "task_actions": [...],
  "holder_types": [...],
  "notification_kinds": [...],
  "limits": {"max_delivery_attempts": 3, "cod_max_vnd": 50000000}
}
```

Sinh tự động từ các `TextChoices` và hằng số — không viết tay danh sách trong view.

### 3.9. Cấu hình

- `settings.py`: thêm `AUTH_USER_MODEL`, `EXCEPTION_HANDLER`, `DEFAULT_PAGINATION_CLASS`; `CSRF_TRUSTED_ORIGINS` đọc từ env `DJANGO_CSRF_TRUSTED_ORIGINS` (danh sách phân tách bằng dấu phẩy, mặc định rỗng).
- Cập nhật `backend/.env.example` với biến mới.
- Các app chưa có model không cần migration rỗng.

## 4. Frontend

| File | Nội dung |
|---|---|
| `vite.config.js` | Proxy `/api` đọc đích từ `VITE_PROXY_TARGET` bằng `loadEnv` (mặc định `http://127.0.0.1:8000`); thêm biến vào `frontend/.env.example` |
| `src/services/http.js` | API client duy nhất: base URL `import.meta.env.VITE_API_BASE_URL`, `credentials: 'same-origin'`, gửi header `X-CSRFToken` từ cookie `csrftoken` cho method không an toàn, parse JSON, chuẩn hóa lỗi thành `ApiError { status, code, message, fields }` theo định dạng mục 3.2. Lỗi mạng → `code: 'NETWORK_ERROR'`. Dùng `fetch`, không thêm thư viện |
| `src/services/metaService.js` | `getChoices()` gọi `/meta/choices/` |
| `src/stores/meta.js` | Pinia store tải enum **một lần**, getter `label(group, value)`, `isTerminal(status)`, `limits` |
| `src/utils/format.js` | `formatVnd(number)`, `formatDateTime(iso)` theo `Asia/Ho_Chi_Minh`, `formatPhone` |
| `src/utils/statusTones.js` | Map **mã trạng thái → tone màu** (`neutral`, `info`, `warning`, `success`, `danger`). Chỉ chứa màu; nhãn lấy từ store |
| `src/components/common/StatusBadge.vue` | Props `group`, `value`; nhãn từ store, màu từ `statusTones`; mã lạ hiển thị chính mã đó với tone `neutral` |
| `src/assets/styles/main.css` | Thêm biến màu tone vào `:root`; giữ style hiện có |

`App.vue` gọi tải enum khi khởi động; lỗi tải hiển thị thông báo, không chặn trang giới thiệu.

## 5. Tiêu chí nghiệm thu

- [x] `pip install -r requirements.txt` và `python backend/manage.py check` chạy sạch bằng interpreter đã chốt ở D6. *(Python 3.14.2)*
- [x] `makemigrations` sinh đúng `accounts/0001_initial`; `migrate` chạy được trên PostgreSQL local (compose). `makemigrations --check` sau đó không phát hiện thay đổi. *(cùng `notifications/0001_initial`)*
- [ ] `createsuperuser` tạo tài khoản `role=ADMIN`; đăng nhập Django admin xem/sửa được User; không có trường `first_name`/`last_name`. *(Test tự động đã đạt: superuser nhận `ADMIN`, trang admin list/add/change render, thêm User qua admin. **Chờ người dùng tự tạo superuser và mở `/admin/` bằng tay** — DB hiện 0 superuser.)*
- [x] Tạo User với `role` ngoài 3 giá trị bị DB từ chối; `phone` trùng hoặc sai định dạng bị từ chối. *(ràng buộc ở mức DB)*
- [x] `GET /api/v1/meta/choices/` trả đủ các nhóm ở mục 3.8, nhãn khớp bảng trạng thái checklist. *(9 nhóm, gồm thêm `task_actions`)*
- [x] Gọi một endpoint cần đăng nhập khi chưa đăng nhập trả `401` với `{"error": {"code": "NOT_AUTHENTICATED", ...}}`; route không tồn tại dưới `/api/v1/` trả JSON `NOT_FOUND`.
- [ ] `npm run build` thành công; trang chủ chạy, `StatusBadge` hiển thị đúng nhãn tiếng Việt từ API. *(Build thành công khi xuất ra thư mục khác; `npm run dev` chạy, trang chủ 200; `StatusBadge` đúng nhãn + tông qua kiểm tra Vite SSR. **`npm run build` vào `frontend/dist/` bị chặn**: thư mục cũ không cho xóa file (quyền Windows) — người dùng xóa `frontend/dist/` bằng quyền Administrator rồi chạy lại.)*
- [x] Không còn chuỗi trạng thái/vai trò viết trực tiếp ngoài các file `constants.py`, `statusTones.js`. *(Rà bằng grep: chỉ còn trong `constants.py` và test.)*

**Ghi nhận khi nghiệm thu (ngoài tiêu chí):**

- `manage.py check --deploy` báo 5 cảnh báo bảo mật (HSTS, SSL redirect, cookie secure ×2, `DEBUG=True`) — đúng với môi trường local; xử lý khi có spec triển khai.
- `APP_TIME_ZONE` ở `frontend/src/utils/format.js` lặp giá trị `TIME_ZONE` backend (có comment chỉ nguồn).
- Chưa có test frontend tự động trong repo — cân nhắc Vitest từ spec 002.
- Spec 002 cần endpoint cấp cookie CSRF trước khi POST đăng nhập.

## 6. Thiết kế tham chiếu cho spec sau (chưa tạo bảng)

Để spec 004–011 dùng chung một mô hình, không tự thiết kế lại:

| Model (app) | Trường chính | Spec tạo |
|---|---|---|
| `Shipment` (`shipments`) | `request_code` (unique), `tracking_code` (unique, null tới khi duyệt), `shop` (FK User), thông tin người gửi/nhận, `pickup_ward`/`pickup_address`, `delivery_ward`/`delivery_address`, `package_description`, `package_count`, `weight_grams` (null), `cod_amount`, `status`, `holder_type`, `holder_shipper` (FK null), `delivery_attempts` (mặc định 0), `version`/`updated_at` | 004 |
| `ShipmentEvent` (`shipments`) | `shipment`, `action` (`ShipmentAction`), `from_status`, `to_status`, `actor`, `reason`, `task` (FK null), `created_at`. Chỉ thêm, không sửa/xóa | 004 |
| `Task` (`dispatch`) | `shipment`, `type`, `status`, `shipper`, `assigned_by`, `assigned_at`, `closed_at`, `replaced_by` (FK self null), `handover_reported_at`, `needs_attention`, `attempt_no` (chỉ DELIVERY). Partial unique: một task mở mỗi shipment | 006 |
| `TaskResult` (`dispatch`) | `task` (one-to-one), `outcome` (thành công/thất bại), `reason`, `cod_expected`, `cod_collected`, `recorded_by`, `recorded_at` | 006–007 |
| `Handover` (`dispatch`) | `shipment`, `task` (null), `kind` (nhập điểm tập kết / hoàn về điểm tập kết / đổi Shipper / Shop nhận hàng hoàn), `from_party`, `received_by`, `received_at`, `discrepancy_note` | 006, mở rộng ở 008–009 |
| `LocationPing` (`tracking`) | `task`, `shipper`, `lat`, `lng`, `recorded_at` (thiết bị), `received_at` | 011 |

Số lần giao lưu trên `Shipment.delivery_attempts` và đối chiếu với `Task.attempt_no`; chỉ tăng khi ghi kết quả cuối của nhiệm vụ giao.

## 7. Test bắt buộc

- `core`: helper chuyển trạng thái — vai trò sai → `PERMISSION_DENIED`, trạng thái nguồn sai → `INVALID_TRANSITION`; kiểm tra **toàn bộ bảng**: mọi `source`/`target` thuộc enum, trạng thái kết thúc không có hành động đi ra, mọi trạng thái không kết thúc đều có ít nhất một hành động đi ra.
- `core`: exception handler trả đúng định dạng cho `ValidationError`, `BusinessError`, 401, 404.
- `core`: `/meta/choices/` không cần đăng nhập, khớp enum.
- `accounts`: ràng buộc `role`, `phone`; `create_superuser` gán `ADMIN`; `HasRole` từ chối tài khoản `is_active=False`.
- Chạy test trên PostgreSQL (`python backend/manage.py test`), không dùng SQLite.

## 8. Lộ trình các spec sau

Xem [specs/README.md](../README.md).
