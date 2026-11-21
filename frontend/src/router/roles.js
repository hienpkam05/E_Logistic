// Nơi DUY NHẤT ở frontend chứa mã vai trò (cùng utils/statusTones.js cho mã trạng thái).
// Mã khớp UserRole ở backend (apps/accounts/constants.py); nhãn hiển thị lấy từ store meta.

export const ROLES = Object.freeze({ SHOP: 'SHOP', ADMIN: 'ADMIN', SHIPPER: 'SHIPPER' })

/** Mã vai trò hợp lệ? Kiểm tra đồng bộ (không chờ /meta/choices/ tải xong). */
export function isRole(value) {
  return Object.values(ROLES).includes(value)
}

// Vai trò -> tên route trang chủ.
export const ROLE_HOME = Object.freeze({
  [ROLES.SHOP]: 'shop-home',
  [ROLES.ADMIN]: 'staff-home',
  [ROLES.SHIPPER]: 'shipper-home',
})

// Mục menu riêng theo vai trò (thanh trên của AppLayout). Thêm mục cho vai trò khác ở spec sau.
export const ROLE_MENU = Object.freeze({
  [ROLES.ADMIN]: [
    { label: 'Quản lý tài khoản', to: { name: 'staff-accounts' } },
    { label: 'Quản lý Shipper', to: { name: 'staff-accounts', query: { role: ROLES.SHIPPER } } },
  ],
})

export function menuFor(role) {
  return ROLE_MENU[role] ?? []
}

export function homeRouteFor(role) {
  const name = ROLE_HOME[role]
  return name ? { name } : { name: 'login' }
}
