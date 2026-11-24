// Chỉ ánh xạ mã trạng thái -> tông màu. Nhãn lấy từ store meta (backend).
// Mã mới chưa khai báo ở đây sẽ hiển thị tông 'neutral'.

export const TONES = ['neutral', 'info', 'warning', 'success', 'danger']

export const STATUS_TONES = {
  shipment_statuses: {
    PENDING_APPROVAL: 'warning',
    CANCELLED: 'neutral',
    REJECTED: 'danger',
    AWAITING_PICKUP: 'info',
    PICKUP_ASSIGNED: 'info',
    PICKED_UP: 'info',
    PICKUP_FAILED: 'danger',
    PICKUP_ABANDONED: 'danger',
    AT_HUB: 'info',
    OUT_FOR_DELIVERY: 'info',
    DELIVERED: 'success',
    DELIVERY_FAILED: 'danger',
    AWAITING_REDELIVERY: 'warning',
    AWAITING_RETURN: 'warning',
    RETURNING: 'warning',
    AWAITING_SHOP_PICKUP: 'warning',
    RETURNED_TO_SHOP: 'neutral',
  },
  task_statuses: {
    ACTIVE: 'info',
    PENDING_SWAP_HANDOVER: 'warning',
    SUCCEEDED: 'success',
    FAILED: 'danger',
    REPLACED: 'neutral',
  },
}

// Mã trạng thái vận đơn mà giao diện cần so sánh trực tiếp (tab Chờ xác nhận của Nhân viên — spec 005).
// Test bắt buộc mọi giá trị ở đây là key của STATUS_TONES.shipment_statuses (đã đối chiếu backend).
export const SHIPMENT_STATUS = Object.freeze({
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  // Tab hàng việc của Nhân viên (spec 006 D10)
  AWAITING_PICKUP: 'AWAITING_PICKUP',
  PICKUP_FAILED: 'PICKUP_FAILED',
  PICKED_UP: 'PICKED_UP',
  // … và spec 007 D11
  AT_HUB: 'AT_HUB',
  AWAITING_REDELIVERY: 'AWAITING_REDELIVERY',
  DELIVERY_FAILED: 'DELIVERY_FAILED',
  // … và spec 008 (giai đoạn Hoàn hàng)
  AWAITING_RETURN: 'AWAITING_RETURN',
  RETURNING: 'RETURNING',
  AWAITING_SHOP_PICKUP: 'AWAITING_SHOP_PICKUP',
})

// Trạng thái nhiệm vụ cần nhận biết ở khối điều phối / trang Shipper (spec 009).
// Nhãn và tông màu vẫn dùng meta + STATUS_TONES; test đối chiếu TaskStatus backend.
export const TASK_STATUS = Object.freeze({
  ACTIVE: 'ACTIVE',
  PENDING_SWAP_HANDOVER: 'PENDING_SWAP_HANDOVER',
  REPLACED: 'REPLACED',
})

export function toneOf(group, value) {
  return STATUS_TONES[group]?.[value] ?? 'neutral'
}
