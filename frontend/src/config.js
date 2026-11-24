// Cấu hình frontend đọc từ env (frontend/.env) — nơi duy nhất đọc import.meta.env ngoài http.js.

// Thông tin liên hệ hiển thị ở trang Quên mật khẩu (spec 002 D7).
export const SUPPORT_CONTACT = (import.meta.env.VITE_SUPPORT_CONTACT || '').trim()

// Chu kỳ cập nhật số thông báo chưa đọc (spec 002 D8).
export const NOTIFICATION_POLL_MS = Number(import.meta.env.VITE_NOTIFICATION_POLL_MS) || 60_000

// Nền bản đồ cấu hình ở một nơi. Provider riêng phải khai báo attribution tương ứng.
const customTileUrl = (import.meta.env.VITE_MAP_TILE_URL || '').trim()
export const MAP_TILE_URL = customTileUrl || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export const MAP_TILE_ATTRIBUTION = (import.meta.env.VITE_MAP_TILE_ATTRIBUTION ||
  (customTileUrl ? '' : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors')).trim()
export const MAP_INITIAL_ZOOM = 15
export const MAP_MAX_ZOOM = 19
export const MAP_DIRECTIONS_URL = 'https://www.google.com/maps/dir/'
