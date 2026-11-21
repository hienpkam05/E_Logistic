// Tiện ích dùng chung cho test Vitest (không đóng gói vào bản build vì chỉ test import).
import { vi } from 'vitest'

export function jsonResponse(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function apiError(status, code, message = 'Lỗi', fields = {}) {
  return jsonResponse(status, { error: { code, message, fields } })
}

/** Thay fetch toàn cục; trả mock để kiểm tra lời gọi. */
export function mockFetch(impl) {
  const fn = vi.fn(impl)
  vi.stubGlobal('fetch', fn)
  return fn
}

export const CHOICES = {
  user_roles: [
    { value: 'SHOP', label: 'Shop' },
    { value: 'ADMIN', label: 'Nhân viên/Admin' },
    { value: 'SHIPPER', label: 'Shipper' },
  ],
  shipment_statuses: [
    { value: 'AT_HUB', label: 'Đã nhập điểm tập kết', terminal: false },
    { value: 'DELIVERED', label: 'Đã giao hàng', terminal: true },
    { value: 'AWAITING_SHOP_PICKUP', label: 'Chờ Shop đến lấy', terminal: false },
  ],
  task_statuses: [
    { value: 'PENDING_SWAP_HANDOVER', label: 'Chờ bàn giao đổi Shipper', terminal: false },
    { value: 'REPLACED', label: 'Đã thay thế', terminal: true },
  ],
  limits: { max_delivery_attempts: 3, cod_max_vnd: 50000000 },
}
