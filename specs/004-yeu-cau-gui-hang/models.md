# Spec 004 — Thay đổi dữ liệu

Spec: [spec.md](spec.md) · Công việc: [tasks.md](tasks.md) · API: [api.md](api.md)

## Tóm tắt

| Loại | Đối tượng | Thay đổi |
|---|---|---|
| Bảng mới | `shipments_ward` | Danh mục phường/xã Hà Nội (D1) |
| Bảng mới | `shipments_shipment` | Yêu cầu gửi hàng / vận đơn |
| Bảng mới | `shipments_shipmentevent` | Lịch sử vận chuyển, chỉ thêm |
| Enum | `ShipmentAction` | Thêm `UPDATE_REQUEST` (+ dòng trong `SHIPMENT_TRANSITIONS`) |
| Hằng số | `shipments/constants.py` | Giới hạn kiện hàng, độ dài trường |
| Migration | `shipments/0001_initial` | 3 bảng trên |
| Lệnh quản trị | `load_wards` | Nạp danh mục từ CSV |

## Ward

App `shipments` · Bảng `shipments_ward`

| Trường | Kiểu | Null | Mặc định | Ghi chú |
|---|---|---|---|---|
| `id` | BigAutoField | | | PK |
| `code` | CharField(20) | | | **Unique** — mã đơn vị hành chính chính thức |
| `name` | CharField(100) | | | Tên hiển thị, vd "Phường Hoàn Kiếm" |
| `is_active` | BooleanField | | `True` | `False` khi không còn trong file nạp gần nhất; không xóa |

Sắp xếp: `name`. Index: unique `code`.

## Shipment

App `shipments` · Bảng `shipments_shipment`

| Trường | Kiểu | Null | Mặc định | Ràng buộc / ghi chú | Nguồn |
|---|---|---|---|---|---|
| `id` | BigAutoField | | | PK | |
| `request_code` | CharField(12) | ✔ | | **Unique**. `YC` + 8 số theo id, gán ngay sau khi tạo trong cùng transaction (null chỉ trong khoảnh khắc đó) | D2, UC05.2 |
| `tracking_code` | CharField(20) | ✔ | | **Unique**. Sinh khi duyệt (spec 005) | UC05.6 |
| `shop` | FK → User | | | `PROTECT`. Lấy từ phiên, không từ client | BR2 |
| `status` | CharField(30) | | `PENDING_APPROVAL` | Choices `ShipmentStatus`; `CheckConstraint` trong choices | |
| `sender_name` | CharField(150) | | | Bản chụp lúc tạo/sửa | D4 |
| `sender_phone` | CharField(10) | | | `PHONE_REGEX` | |
| `pickup_ward` | FK → Ward | | | `PROTECT` | D1 |
| `pickup_address` | CharField(255) | | | Số nhà, đường… | |
| `receiver_name` | CharField(150) | | | | |
| `receiver_phone` | CharField(10) | | | `PHONE_REGEX` | |
| `delivery_ward` | FK → Ward | | | `PROTECT` | D1 |
| `delivery_address` | CharField(255) | | | | |
| `package_description` | CharField(255) | | | | D3 |
| `package_count` | PositiveSmallIntegerField | | `1` | `CheckConstraint` 1–99 | D3 |
| `weight_grams` | PositiveIntegerField | ✔ | | 1–100 000 | D3 |
| `cod_amount` | PositiveBigIntegerField | | `0` | `CheckConstraint` 0 ≤ x ≤ `COD_MAX_VND` | D3 |
| `note` | CharField(500) | | `""` | Ghi chú cho Shipper | D3 |
| `holder_type` | CharField(20) | | `SHOP` | Choices `HolderType` | spec 001 |
| `holder_shipper` | FK → User | ✔ | | `PROTECT`; dùng từ spec 006 | spec 001 |
| `delivery_attempts` | PositiveSmallIntegerField | | `0` | Dùng từ spec 007 | spec 001 |
| `created_at` | DateTimeField | | auto_now_add | | |
| `updated_at` | DateTimeField | | auto_now | Chống ghi đè khi sửa | UC05.1 E1 |

Index (kiểm tra lại bằng `EXPLAIN` ở Phase 2): `(shop, -created_at, -id)` cho danh sách Shop; `(status, -created_at)` dự phòng cho spec 005. FK `shop` `db_index=False` (index ghép đã bắt đầu bằng `shop`).

Ràng buộc CHECK thực tế trên DB (Phase 1): `ship_status_valid`, `ship_holder_type_valid`, `ship_package_count_range`, `ship_weight_range`, `ship_cod_max`, `ship_phones_format`, `ship_request_code_format` + 4 ràng buộc `>= 0` Django tự thêm cho cột số dương = 11. Django còn tự tạo index `_like` (`varchar_pattern_ops`) cho `request_code`, `tracking_code`, `ward.code` — chỉ phục vụ tìm theo tiền tố; giữ lại (lượng ghi nhỏ), có thể bỏ bằng cách đổi `unique=True` sang `UniqueConstraint` nếu cần.

Admin Django: vận đơn + lịch sử **chỉ xem** (đổi trạng thái chỉ qua service + bảng chuyển trạng thái).

## ShipmentEvent

App `shipments` · Bảng `shipments_shipmentevent` · **Chỉ thêm** — không API sửa/xóa; admin chỉ đọc.

| Trường | Kiểu | Null | Ghi chú |
|---|---|---|---|
| `id` | BigAutoField | | PK |
| `shipment` | FK → Shipment | | `PROTECT`, `db_index=False` (index ghép) |
| `action` | CharField(30) | | Choices `ShipmentAction` |
| `from_status` | CharField(30) | ✔ | `NULL` cho `CREATE_REQUEST` |
| `to_status` | CharField(30) | | |
| `actor` | FK → User | ✔ | `PROTECT` |
| `reason` | CharField(`EVENT_REASON_MAX_LENGTH` = 500) | | `""` |
| `changes` | JSONField | | `{}` — `UPDATE_REQUEST`: `{"receiver_phone": {"from": …, "to": …}}`; phường ghi `{code, name}` |
| `created_at` | DateTimeField | | auto_now_add |

Index: `(shipment, -created_at, -id)`. (Cột `task` FK thêm ở spec 006.)

## Enum / bảng chuyển trạng thái

| Thay đổi | Chi tiết |
|---|---|
| `ShipmentAction.UPDATE_REQUEST` | Nhãn "Sửa yêu cầu" |
| `SHIPMENT_TRANSITIONS[UPDATE_REQUEST]` | `PENDING_APPROVAL → PENDING_APPROVAL`, vai trò `SHOP` |
| Test so khớp checklist | Thêm dòng "Sửa yêu cầu" (trước đây bỏ ra) — bảng khớp đủ checklist mục 4 |

## Hằng số mới (`shipments/constants.py`)

| Hằng số | Giá trị |
|---|---|
| `PACKAGE_COUNT_MIN`, `PACKAGE_COUNT_MAX` | 1, 99 |
| `WEIGHT_GRAMS_MAX` | 100 000 |
| `ADDRESS_MAX_LENGTH`, `DESCRIPTION_MAX_LENGTH`, `NOTE_MAX_LENGTH` | 255, 255, 500 |
| `EVENT_REASON_MAX_LENGTH` (cột lý do lịch sử, mọi hành động); `CANCEL_REASON_MAX_LENGTH` = `EVENT_REASON_MAX_LENGTH` | 500 |

Hằng số dùng chung mới `apps/core/constants.py`: `SEARCH_QUERY_MAX_LENGTH` = 100 (từ khóa tìm ở mọi danh sách).

(`REQUEST_CODE_PREFIX`, `REQUEST_CODE_DIGITS`, `COD_MAX_VND` đã có từ spec 001.)

## Nhật ký thay đổi

| Ngày | Thay đổi |
|---|---|
| 21/11/2026 | Tạo bản đầu |
| 21/11/2026 | Phase 6: `ShipmentEvent.reason` dùng `EVENT_REASON_MAX_LENGTH` thay số 500 viết thẳng — cùng giá trị, **không sinh migration** (`makemigrations --check` sạch) |
| 21/11/2026 | Phase 1: `shipments/0001_initial` áp dụng lên DB local; thêm ràng buộc khối lượng/SĐT/dạng mã/`holder_type`; nạp 5 phường `DEMO-01…05` (`seed_demo --wards`) |
