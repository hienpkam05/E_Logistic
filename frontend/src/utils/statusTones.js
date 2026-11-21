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

export function toneOf(group, value) {
  return STATUS_TONES[group]?.[value] ?? 'neutral'
}
