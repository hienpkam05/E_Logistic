// Tiện ích dùng chung cho test Vitest (không đóng gói vào bản build vì chỉ test import).
import { mount } from '@vue/test-utils'
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
  limits: {
    max_delivery_attempts: 3, cod_max_vnd: 50000000, search_query_max_length: 100, cancel_reason_max_length: 500, reject_reason_max_length: 500,
    task_note_max_length: 500, handover_note_max_length: 500, handover_receiver_name_max_length: 100,
    location_ping_max_age_seconds: 120, location_ping_max_future_seconds: 60,
    location_ping_min_interval_seconds: 15, location_ping_max_accuracy_m: 1000,
    location_stale_seconds: 300, location_poll_interval_seconds: 15, location_retention_days: 30,
  },
  hub: { name: 'Điểm tập kết HTT EXPRESS', address: '1 Tràng Tiền, Hoàn Kiếm', phone: '0241234567' },
}

// v-model thật: cập nhật prop khi component phát sự kiện (kể cả phát ngay lúc dựng — khi đó wrapper chưa có).
export function mountWithModel(component, props) {
  let wrapper = null
  const pending = []
  wrapper = mount(component, {
    props: {
      modelValue: null,
      'onUpdate:modelValue': (v) => (wrapper ? wrapper.setProps({ modelValue: v }) : pending.push(v)),
      ...props,
    },
  })
  if (pending.length) wrapper.setProps({ modelValue: pending.at(-1) })
  return wrapper
}
