// Trạng thái hiển thị của tài khoản (từ is_active / must_change_password) — dùng chung danh sách + chi tiết.
// Không phải enum backend nên không có trong /meta/choices/.

export function accountStatus(user) {
  if (!user) return null
  if (!user.is_active) return { label: 'Bị khóa', tone: 'danger' }
  if (user.must_change_password) return { label: 'Chờ đổi mật khẩu', tone: 'warning' }
  return { label: 'Hoạt động', tone: 'success' }
}

// Bộ lọc trạng thái trên URL (?status=) <-> tham số API is_active.
export const STATUS_FILTERS = [
  { value: '', label: 'Mọi trạng thái', isActive: undefined },
  { value: 'active', label: 'Đang hoạt động', isActive: true },
  { value: 'locked', label: 'Bị khóa', isActive: false },
]

export function isActiveFromFilter(value) {
  return STATUS_FILTERS.find((f) => f.value === value)?.isActive
}
