// Cấu hình frontend đọc từ env (frontend/.env) — nơi duy nhất đọc import.meta.env ngoài http.js.

// Thông tin liên hệ hiển thị ở trang Quên mật khẩu (spec 002 D7).
export const SUPPORT_CONTACT = (import.meta.env.VITE_SUPPORT_CONTACT || '').trim()

// Chu kỳ cập nhật số thông báo chưa đọc (spec 002 D8).
export const NOTIFICATION_POLL_MS = Number(import.meta.env.VITE_NOTIFICATION_POLL_MS) || 60_000
