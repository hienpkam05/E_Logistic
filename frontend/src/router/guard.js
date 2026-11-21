// Quyết định điều hướng thuần (không phụ thuộc Vue) để test dễ.
// meta.public: không cần đăng nhập; meta.guestOnly: đã đăng nhập thì về trang chủ (UC01.1 A1);
// meta.roles: danh sách vai trò được vào; không khai báo = mọi vai trò đã đăng nhập.
import { homeRouteFor } from './roles'

export const CHANGE_PASSWORD_ROUTE = 'change-password'

/** Chỉ nhận đường dẫn nội bộ dạng "/..." — chặn chuyển hướng ra ngoài (open redirect). */
export function safeNext(next) {
  if (typeof next !== 'string' || !next.startsWith('/')) return null
  if (next.startsWith('//') || next.includes('\\') || /[\u0000-\u001f]/.test(next)) return null
  return next
}

/** auth: { isAuthenticated, role, mustChangePassword } */
export function resolveNavigation(to, auth) {
  const meta = to.meta ?? {}

  if (meta.public) {
    if (auth.isAuthenticated && meta.guestOnly) return homeRouteFor(auth.role)
    return true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: to.fullPath && to.fullPath !== '/' ? { next: to.fullPath } : {} }
  }
  if (auth.mustChangePassword && to.name !== CHANGE_PASSWORD_ROUTE) {
    return { name: CHANGE_PASSWORD_ROUTE }
  }
  if (Array.isArray(meta.roles) && !meta.roles.includes(auth.role)) {
    return homeRouteFor(auth.role)
  }
  return true
}
