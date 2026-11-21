// Formatter dùng chung. Component không tự định dạng tiền, ngày giờ, số điện thoại.

export const APP_LOCALE = 'vi-VN'
// Khớp TIME_ZONE của backend (config/settings.py).
export const APP_TIME_ZONE = 'Asia/Ho_Chi_Minh'

const vndFormatter = new Intl.NumberFormat(APP_LOCALE, {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
})

const dateTimeFormatter = new Intl.DateTimeFormat(APP_LOCALE, {
  timeZone: APP_TIME_ZONE,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const isBlank = (value) => value === null || value === undefined || value === ''

// 200000 -> "200.000 ₫"
export function formatVnd(value) {
  if (isBlank(value)) return ''
  const number = Number(value)
  return Number.isFinite(number) ? vndFormatter.format(number) : ''
}

// "2026-11-20T02:30:00Z" -> "09:30 20/11/2026" (giờ Việt Nam, bất kể múi giờ máy người xem)
export function formatDateTime(value) {
  if (isBlank(value)) return ''
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? '' : dateTimeFormatter.format(date)
}

// "0901234567" -> "0901 234 567"; giá trị không đúng 10 số giữ nguyên.
export function formatPhone(value) {
  if (isBlank(value)) return ''
  const digits = String(value).replace(/\D/g, '')
  return digits.length === 10 ? `${digits.slice(0, 4)} ${digits.slice(4, 7)} ${digits.slice(7)}` : String(value)
}
