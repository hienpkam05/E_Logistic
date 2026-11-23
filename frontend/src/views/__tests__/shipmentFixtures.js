// Dữ liệu mẫu dùng chung cho test màn hình vận đơn của Shop.
import { CHOICES } from '../../test-utils'

export const WARDS = [{ code: 'W1', name: 'Phường Dịch Vọng' }, { code: 'W2', name: 'Phường Láng' }]

export const SHIPMENT = {
  id: 12, request_code: 'YC000012', tracking_code: null, status: 'PENDING_APPROVAL',
  sender_name: 'Shop Hoa', sender_phone: '0912345678', pickup_ward: WARDS[0], pickup_address: '12 Trần Thái Tông',
  receiver_name: 'Trần Thị B', receiver_phone: '0987654321', delivery_ward: WARDS[1], delivery_address: '5 Láng Hạ',
  package_description: 'Áo len', package_count: 2, weight_grams: null, cod_amount: 350000, note: '',
  created_at: '2026-11-21T02:00:00Z', updated_at: '2026-11-21T02:00:00.123456Z',
  allowed_actions: ['CANCEL_REQUEST', 'UPDATE_REQUEST'],
}

export const SHIPMENT_CHOICES = {
  ...CHOICES,
  shipment_statuses: [
    { value: 'PENDING_APPROVAL', label: 'Chờ xác nhận', terminal: false },
    { value: 'AWAITING_PICKUP', label: 'Chờ lấy hàng', terminal: false },
    { value: 'PICKUP_ASSIGNED', label: 'Đã phân công lấy hàng', terminal: false },
    { value: 'PICKED_UP', label: 'Đã lấy hàng', terminal: false },
    { value: 'PICKUP_FAILED', label: 'Lấy hàng thất bại', terminal: false },
    { value: 'AT_HUB', label: 'Đã nhập điểm tập kết', terminal: false },
    // Spec 007
    { value: 'OUT_FOR_DELIVERY', label: 'Đang giao hàng', terminal: false },
    { value: 'DELIVERED', label: 'Đã giao hàng', terminal: true },
    { value: 'DELIVERY_FAILED', label: 'Giao hàng thất bại', terminal: false },
    { value: 'AWAITING_REDELIVERY', label: 'Chờ giao lại', terminal: false },
    { value: 'AWAITING_RETURN', label: 'Chờ xử lý hoàn', terminal: false },
    // Spec 008
    { value: 'RETURNING', label: 'Đang hoàn', terminal: false },
    { value: 'AWAITING_SHOP_PICKUP', label: 'Chờ Shop đến lấy', terminal: false },
    { value: 'RETURNED_TO_SHOP', label: 'Đã hoàn về Shop', terminal: true },
    { value: 'PICKUP_ABANDONED', label: 'Kết thúc do không lấy được hàng', terminal: true },
    { value: 'CANCELLED', label: 'Đã hủy', terminal: true },
  ],
  shipment_actions: [
    { value: 'CREATE_REQUEST', label: 'Tạo yêu cầu' }, { value: 'UPDATE_REQUEST', label: 'Sửa yêu cầu' },
    { value: 'CANCEL_REQUEST', label: 'Hủy yêu cầu' },
  ],
  limits: { ...CHOICES.limits, package_count_min: 1, package_count_max: 50, weight_grams_max: 30000 },
  // Spec 006
  holder_types: [{ value: 'SHOP', label: 'Shop' }, { value: 'SHIPPER', label: 'Shipper' },
    { value: 'HUB', label: 'Điểm tập kết' }, { value: 'RECIPIENT', label: 'Người nhận' }],
  task_types: [{ value: 'PICKUP', label: 'Lấy hàng' }, { value: 'DELIVERY', label: 'Giao hàng' },
    { value: 'RETURN', label: 'Hoàn hàng' }],
  task_statuses: [{ value: 'ACTIVE', label: 'Đang thực hiện', terminal: false },
    { value: 'SUCCEEDED', label: 'Hoàn tất', terminal: true }, { value: 'FAILED', label: 'Thất bại', terminal: true }],
  pickup_fail_reasons: [{ value: 'SHOP_ABSENT', label: 'Shop vắng mặt / không liên lạc được' },
    { value: 'NOT_READY', label: 'Hàng chưa sẵn sàng' }, { value: 'OTHER', label: 'Khác' }],
  // Spec 007
  delivery_fail_reasons: [{ value: 'RECEIVER_UNREACHABLE', label: 'Không liên hệ được người nhận' },
    { value: 'COD_NOT_READY', label: 'Người nhận chưa đủ tiền COD' }, { value: 'OTHER', label: 'Khác' }],
}

// Shipper / nhiệm vụ mẫu (spec 006)
export const SHIPPER = { id: 7, username: 'sp_long', full_name: 'Nguyễn Văn Long', phone: '0912000111' }
export const PICKUP_TASK = {
  id: 31, type: 'PICKUP', status: 'ACTIVE', assigned_at: '2026-11-22T03:00:00Z', closed_at: null, needs_attention: false,
  shipment: { id: 12, tracking_code: 'HTT261122K7Q2M', status: 'PICKUP_ASSIGNED', shop_name: 'Shop Hoa',
    sender_name: 'Chị Hoa', sender_phone: '0912345678', pickup_ward: WARDS[0], pickup_address: '12 Trần Thái Tông',
    package_count: 2, package_description: 'Áo len', weight_grams: null, note: 'Gọi trước' },
  allowed_actions: ['CONFIRM_PICKUP', 'FAIL_PICKUP'], result: null,
}

// Nhiệm vụ GIAO mẫu (spec 007): người nhận + COD, không thông tin lấy hàng (D3).
export const DELIVERY_TASK = {
  id: 41, type: 'DELIVERY', status: 'ACTIVE', attempt_no: 2, assigned_at: '2026-11-22T05:00:00Z', closed_at: null,
  needs_attention: false,
  shipment: { id: 12, tracking_code: 'HTT261122K7Q2M', status: 'OUT_FOR_DELIVERY', shop_name: 'Shop Hoa',
    receiver_name: 'Trần Thị B', receiver_phone: '0987654321', delivery_ward: WARDS[1], delivery_address: '5 Láng Hạ',
    package_count: 2, package_description: 'Áo len', weight_grams: null, note: '', cod_amount: 350000 },
  allowed_actions: ['CONFIRM_DELIVERY', 'FAIL_DELIVERY'], result: null,
}

// Nhiệm vụ HOÀN mẫu (spec 008): Shop + kiện hàng + lý do hoàn; không người nhận / COD (D8).
export const RETURN_TASK = {
  id: 61, type: 'RETURN', status: 'ACTIVE', attempt_no: null, assigned_at: '2026-11-23T02:00:00Z', closed_at: null,
  needs_attention: false, handover_reported_at: null,
  shipment: { id: 12, tracking_code: 'HTT261122K7Q2M', status: 'RETURNING', shop_name: 'Shop Hoa',
    package_description: 'Áo len', package_count: 2, weight_grams: null, note: '', return_reason: 'Khách từ chối nhận' },
  allowed_actions: ['REPORT_RETURN_HANDOVER'], result: null,
}

export const page = (results, extra = {}) => ({ count: results.length, next: null, previous: null, results, ...extra })
