// Mã hành động vận đơn mà giao diện cần nhận biết (nút theo allowed_actions từ backend) + giá trị tham số API vận đơn.
// Nguồn: ShipmentAction trong backend/apps/shipments/constants.py — test đối chiếu tự động.
// Nhãn hiển thị lấy từ store meta (nhóm shipment_actions), không viết ở đây.

export const SHIPMENT_ACTION = Object.freeze({
  UPDATE_REQUEST: 'UPDATE_REQUEST',
  CANCEL_REQUEST: 'CANCEL_REQUEST',
  // Nhân viên (spec 005)
  APPROVE_REQUEST: 'APPROVE_REQUEST',
  REJECT_REQUEST: 'REJECT_REQUEST',
  // Điều phối lấy hàng (spec 006): Nhân viên
  ASSIGN_PICKUP: 'ASSIGN_PICKUP',
  RECEIVE_AT_HUB: 'RECEIVE_AT_HUB',
  RETRY_PICKUP: 'RETRY_PICKUP',
  ABANDON_PICKUP: 'ABANDON_PICKUP',
  // … và Shipper (trên nhiệm vụ lấy)
  CONFIRM_PICKUP: 'CONFIRM_PICKUP',
  FAIL_PICKUP: 'FAIL_PICKUP',
  // Giao hàng (spec 007): Nhân viên
  ASSIGN_DELIVERY: 'ASSIGN_DELIVERY',
  DECIDE_REDELIVERY: 'DECIDE_REDELIVERY',
  DECIDE_RETURN: 'DECIDE_RETURN',
  // … và Shipper (trên nhiệm vụ giao)
  CONFIRM_DELIVERY: 'CONFIRM_DELIVERY',
  FAIL_DELIVERY: 'FAIL_DELIVERY',
  // Hoàn hàng (spec 008): Nhân viên
  ASSIGN_RETURN: 'ASSIGN_RETURN',
  RECEIVE_RETURN: 'RECEIVE_RETURN',
  REPORT_RETURN_ISSUE: 'REPORT_RETURN_ISSUE',
  CONFIRM_SHOP_RECEIVED: 'CONFIRM_SHOP_RECEIVED',
  // … và Shipper (trên nhiệm vụ hoàn)
  REPORT_RETURN_HANDOVER: 'REPORT_RETURN_HANDOVER',
  // Đổi Shipper (spec 009): Nhân viên và Shipper cũ báo bàn giao.
  SWAP_SHIPPER: 'SWAP_SHIPPER',
  CONFIRM_SWAP_HANDOVER: 'CONFIRM_SWAP_HANDOVER',
  REPORT_SWAP_ISSUE: 'REPORT_SWAP_ISSUE',
  REPORT_SWAP_HANDOVER: 'REPORT_SWAP_HANDOVER',
  RECALL_TO_HUB: 'RECALL_TO_HUB',
})

// Giá trị tham số `ordering` của danh sách vận đơn (SHIPMENT_LIST_ORDERINGS ở backend — test đối chiếu).
export const SHIPMENT_ORDERING = Object.freeze({ NEWEST_FIRST: '-created_at', OLDEST_FIRST: 'created_at' })

// Mã lý do lấy hàng thất bại mà giao diện cần so sánh (Khác → ghi chú bắt buộc — spec 006 D4).
// Nguồn: PickupFailReason ở backend/apps/dispatch/constants.py — test đối chiếu. Nhãn lấy từ meta.
export const PICKUP_FAIL_REASON = Object.freeze({ OTHER: 'OTHER' })

// Lý do giao thất bại giao diện cần nhận biết (spec 007 D4, D5): Khác → ghi chú bắt buộc; "Chưa thu đủ? Ghi giao
// thất bại" chọn sẵn COD_NOT_READY. Nguồn: DeliveryFailReason (dispatch/constants.py) — test đối chiếu.
export const DELIVERY_FAIL_REASON = Object.freeze({ OTHER: 'OTHER', COD_NOT_READY: 'COD_NOT_READY' })

// Loại nhiệm vụ (lọc danh sách Shipper, chọn khối hiển thị). Nguồn: TaskType — test đối chiếu. Nhãn từ meta task_types.
export const TASK_TYPE = Object.freeze({ PICKUP: 'PICKUP', DELIVERY: 'DELIVERY', RETURN: 'RETURN' })

// Người / nơi giữ hàng giao diện cần so sánh (giao lại chỉ bằng Shipper đang giữ — spec 007 D7).
// Nguồn: HolderType ở backend/apps/shipments/constants.py — test đối chiếu. Nhãn từ meta holder_types.
export const HOLDER_TYPE = Object.freeze({ SHIPPER: 'SHIPPER', HUB: 'HUB' })

// Loại nhiệm vụ → nhóm lý do thất bại trong /meta/choices/ (FAIL_REASONS_BY_TASK_TYPE ở backend — test đối chiếu).
export const FAIL_REASON_GROUP = Object.freeze({
  [TASK_TYPE.PICKUP]: 'pickup_fail_reasons',
  [TASK_TYPE.DELIVERY]: 'delivery_fail_reasons',
})

/** Vận đơn có cho phép hành động này với người đang xem không (theo allowed_actions của API). */
export function can(shipment, action) {
  return Array.isArray(shipment?.allowed_actions) && shipment.allowed_actions.includes(action)
}
