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

// Mục menu riêng theo vai trò (thanh bên của AppLayout). `icon`: tên trong components/common/AppIcon.vue.
// Thêm mục cho vai trò khác ở spec sau.
export const ROLE_MENU = Object.freeze({
  [ROLES.SHOP]: [
    { label: 'Vận đơn của tôi', to: { name: 'shop-shipments' }, icon: 'package' },
    { label: 'Tạo yêu cầu gửi hàng', to: { name: 'shop-shipment-new' }, icon: 'package-plus' },
  ],
  [ROLES.ADMIN]: [
    { label: 'Quản lý vận đơn', to: { name: 'staff-shipments' }, icon: 'clipboard' },
    { label: 'Quản lý tài khoản', to: { name: 'staff-accounts' }, icon: 'users' },
    { label: 'Quản lý Shipper', to: { name: 'staff-accounts', query: { role: ROLES.SHIPPER } }, icon: 'truck' },
  ],
  [ROLES.SHIPPER]: [
    { label: 'Nhiệm vụ', to: { name: 'shipper-tasks' }, icon: 'package' }, // lấy + giao (spec 007 D11)
  ],
})

// Vai trò -> route chi tiết vận đơn (thông báo "Xem vận đơn" mở đúng màn của người xem). Shipper: spec 006.
export const ROLE_SHIPMENT_DETAIL = Object.freeze({
  [ROLES.SHOP]: 'shop-shipment-detail',
  [ROLES.ADMIN]: 'staff-shipment-detail',
})

/** Route chi tiết vận đơn cho vai trò, hoặc null nếu vai trò chưa có màn xem vận đơn. */
export function shipmentRouteFor(role, id) {
  const name = ROLE_SHIPMENT_DETAIL[role]
  return name && id ? { name, params: { id: String(id) } } : null
}

/**
 * Liên kết "Xem" của một thông báo theo vai trò người xem (spec 005 D6, 006 D8).
 * Shipper làm việc theo NHIỆM VỤ (payload.task_id) — không có màn vận đơn; vai trò khác mở chi tiết vận đơn.
 */
export function notificationLinkFor(role, payload = {}) {
  if (role === ROLES.SHIPPER) {
    return payload?.task_id ? { name: 'shipper-task-detail', params: { id: String(payload.task_id) } } : null
  }
  return shipmentRouteFor(role, payload?.shipment_id)
}

export function menuFor(role) {
  return ROLE_MENU[role] ?? []
}

export function homeRouteFor(role) {
  const name = ROLE_HOME[role]
  return name ? { name } : { name: 'login' }
}
