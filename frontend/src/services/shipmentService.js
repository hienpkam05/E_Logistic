// API yêu cầu gửi hàng / vận đơn (specs/004-yeu-cau-gui-hang/api.md, specs/005-duyet-van-don/api.md).
import { http } from './http'

const base = '/shipments/'
const one = (id) => `${base}${encodeURIComponent(id)}/`

export const wards = () => http.get(`${base}wards/`)
// status: mảng mã trạng thái (lọc nhiều trạng thái một lúc).
// createdFrom/createdTo: 'YYYY-MM-DD' (giờ VN, gồm cả hai đầu); ordering: SHIPMENT_ORDERING (utils/shipmentActions.js).
export const list = ({ status, q, page, createdFrom, createdTo, ordering } = {}) =>
  http.get(base, { params: { status, q, page, created_from: createdFrom, created_to: createdTo, ordering } })
export const get = (id) => http.get(one(id))
export const create = (data) => http.post(base, data)
// `updatedAt`: updated_at đã tải — backend trả 409 CONFLICT nếu đơn vừa bị thay đổi.
export const update = (id, data, updatedAt) => http.patch(one(id), { ...data, updated_at: updatedAt })
export const cancel = (id, reason = '') => http.post(`${one(id)}cancel/`, { reason })
export const events = (id, { page } = {}) => http.get(`${one(id)}events/`, { params: { page } })
// Nhân viên (spec 005). `updatedAt` của bản đang xem — Shop vừa sửa thì 409 CONFLICT.
export const approve = (id, updatedAt) => http.post(`${one(id)}approve/`, { updated_at: updatedAt })
export const reject = (id, reason, updatedAt) => http.post(`${one(id)}reject/`, { reason, updated_at: updatedAt })
// Điều phối lấy hàng — Nhân viên (spec 006). Cùng khuôn duyệt/từ chối: gửi updated_at của bản đang xem.
export const assignPickup = (id, shipperId, updatedAt) =>
  http.post(`${one(id)}assign-pickup/`, { shipper_id: shipperId, updated_at: updatedAt })
export const receiveAtHub = (id, discrepancyNote, updatedAt) =>
  http.post(`${one(id)}receive-at-hub/`, { discrepancy_note: discrepancyNote, updated_at: updatedAt })
export const retryPickup = (id, reason, updatedAt) => http.post(`${one(id)}retry-pickup/`, { reason, updated_at: updatedAt })
export const abandonPickup = (id, reason, updatedAt) =>
  http.post(`${one(id)}abandon-pickup/`, { reason, updated_at: updatedAt })
// Giao hàng — Nhân viên (spec 007). handed_over: đã giao hàng cho Shipper tại điểm tập kết (D6) — bắt buộc true.
export const assignDelivery = (id, shipperId, updatedAt) =>
  http.post(`${one(id)}assign-delivery/`, { shipper_id: shipperId, handed_over: true, updated_at: updatedAt })
export const decideRedelivery = (id, reason, updatedAt) =>
  http.post(`${one(id)}decide-redelivery/`, { reason, updated_at: updatedAt })
export const decideReturn = (id, reason, updatedAt) => http.post(`${one(id)}decide-return/`, { reason, updated_at: updatedAt })
// Hoàn hàng — Nhân viên (spec 008).
export const assignReturn = (id, shipperId, updatedAt) =>
  http.post(`${one(id)}assign-return/`, { shipper_id: shipperId, updated_at: updatedAt })
export const receiveReturn = (id, discrepancyNote, updatedAt) =>
  http.post(`${one(id)}receive-return/`, { discrepancy_note: discrepancyNote, updated_at: updatedAt })
export const reportReturnIssue = (id, reason, updatedAt) =>
  http.post(`${one(id)}report-return-issue/`, { reason, updated_at: updatedAt })
// verified: Nhân viên đã kiểm tra người nhận thuộc Shop / được ủy quyền (D7) — màn hình chỉ gọi khi đã tích.
export const confirmShopReceived = (id, receiverName, note, updatedAt) =>
  http.post(`${one(id)}confirm-shop-received/`, { receiver_name: receiverName, verified: true, note, updated_at: updatedAt })
