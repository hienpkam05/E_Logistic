# Hệ thống thiết kế giao diện — HTT EXPRESS

Áp dụng cho mọi màn hình frontend (spec 002 trở đi). Màn hình mới phải dùng lại các mẫu dưới đây, **không** tự viết CSS màu/khoảng cách riêng.

## 1. Nguồn

| Thứ | Ở đâu |
|---|---|
| Màu, bo góc, bóng, kích thước khung | Biến CSS ở `:root` trong `frontend/src/assets/styles/main.css` |
| Font | **Be Vietnam Pro** (thiết kế cho tiếng Việt), tự host qua `@fontsource/be-vietnam-pro` — không gọi Google Fonts |
| Icon | `components/common/AppIcon.vue` (bộ Lucide). Cấu hình chỉ ghi **tên** icon (`icon: 'package'`); thêm icon mới thì khai báo trong `ICONS` |
| Khung sau đăng nhập | `layouts/AppLayout.vue` — thanh bên + thanh trên |
| Khung trang công khai | `layouts/AuthLayout.vue` — đăng nhập, quên mật khẩu |

Đổi màu thương hiệu: chỉ sửa nhóm `--brand-*`. Tông trạng thái (`--tone-*`) dùng chung cho `StatusBadge`, `.pill`, `.alert`.

## 2. Khung ứng dụng

- **Thanh bên:** logo, "Tổng quan" + menu theo vai trò (`ROLE_MENU` trong `router/roles.js`, mỗi mục có `icon`), nút "Thu gọn" (nhớ theo trình duyệt).
  - Mục đang mở chọn bằng `utils/navActive.js`: mục khớp cụ thể nhất, tính cả query, nên "Quản lý Shipper" và "Quản lý tài khoản" không cùng sáng.
- **Thanh trên:** tiêu đề = `route.meta.title`, nếu không có thì lấy tên mục menu đang mở. Bên phải có chuông thông báo (số chưa đọc) và menu người dùng (Thông tin cá nhân, Đổi mật khẩu, Đăng xuất).
- **Dưới 960px:** thanh bên thành ngăn kéo, mở bằng nút ☰, đóng bằng nền mờ hoặc Esc.

## 3. Mẫu trang

| Loại trang | Khuôn | Ví dụ |
|---|---|---|
| Danh sách | `h1.sr-only` → `.toolbar` (nút chính `.btn--split` + `.search`) → `.data-card` (`__head`: `.tabs` + `.filter-select` + `__count`; bảng `.table.table--stack`; `__foot`: `PaginationBar`) | `ShipmentListView`, `AccountListView` |
| Chi tiết | `.back-link` → `.detail-header` (`.title-row` + nút) → `.detail-layout` (cột chính + cột lịch sử) | `ShipmentDetailView`, `AccountDetailView` |
| Form | `.page--narrow` → `.page__header` (h1 + `.page__subtitle`) → các `.card` có `.card__title`; trường xếp bằng `.form-grid` (2 cột, `.field--full` chiếm cả hàng) | `ShipmentForm` |
| Trang chủ vai trò | `RoleHome`: banner chào + ô lối tắt `.tile` | `ShopHomeView`… |

Bảng `.table--stack` trên điện thoại (≤640px) tự thành thẻ. **Mỗi `<td>` phải có `data-label`** trùng tiêu đề cột.

## 4. Thành phần dùng chung

| Class / component | Dùng cho |
|---|---|
| `.btn--primary`, `--outline`, `--ghost`, `--danger`, `--danger-outline`, `--sm`, `--icon`, `--block`, `--split` | Nút. Icon đặt trực tiếp trong nút (`<AppIcon name="plus" :size="16" />`) |
| `StatusBadge` | Trạng thái enum backend (màu theo `utils/statusTones.js`) |
| `.pill--success/warning/danger` | Trạng thái không thuộc enum (vd trạng thái tài khoản) |
| `.alert--info/success/warning/danger` | Thông báo trong trang |
| `.empty-state` (+ `__icon`, `__title`) | Danh sách trống / lỗi tải |
| `.loading` + `.spinner` | Đang tải |
| `.events` | Lịch sử dạng dòng thời gian |
| `.details` | Cặp nhãn – giá trị |
| `ConfirmDialog`, `PaginationBar`, `FormField` (có `maxlength`), `WardSelect` | Như tên |

## 5. Quy tắc

- Không viết mã màu hex trong component. Dùng biến `--…`.
- Nhãn, độ dài, giới hạn lấy từ backend (`meta`). Giao diện mới không được phá quy tắc no-hardcode.
- Giữ chữ của nút, liên kết, `role="alert"/"status"`: test và trình đọc màn hình dựa vào chúng.
- Kiểm tra ở 2 bề rộng: 1440px và 390px.
