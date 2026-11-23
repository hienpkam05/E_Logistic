// API nhiệm vụ của Shipper (specs/006-lay-hang-diem-tap-ket/api.md, 007-giao-hang-cod/api.md, 008-hoan-hang/api.md).
// Shipper không dùng API vận đơn.
import { http } from './http'

const base = '/dispatch/tasks/'
const one = (id) => `${base}${encodeURIComponent(id)}/`

// open: true = đang làm, false = đã xong, bỏ trống = tất cả. type: PICKUP / DELIVERY, bỏ trống = mọi loại (spec 007).
export const list = ({ type, open, page } = {}) => http.get(base, { params: { type, open, page } })
export const get = (id) => http.get(one(id))
export const confirmPickup = (id) => http.post(`${one(id)}confirm-pickup/`)
// reasonCode: mã trong /meta/choices/ nhóm pickup_fail_reasons; Khác → note bắt buộc (backend kiểm).
export const failPickup = (id, reasonCode, note = '') =>
  http.post(`${one(id)}fail-pickup/`, { reason_code: reasonCode, note })
// Spec 007. codCollected: số nguyên VND đã thu (đơn không COD → 0); lệch phải thu → 400 nêu chênh lệch.
export const confirmDelivery = (id, codCollected) =>
  http.post(`${one(id)}confirm-delivery/`, { cod_collected: codCollected })
// reasonCode: nhóm delivery_fail_reasons; Khác → note bắt buộc.
export const failDelivery = (id, reasonCode, note = '') =>
  http.post(`${one(id)}fail-delivery/`, { reason_code: reasonCode, note })
// Spec 008: đã đưa hàng hoàn về điểm tập kết — chỉ báo, Nhân viên mới xác nhận tiếp nhận.
export const reportReturnHandover = (id) => http.post(`${one(id)}report-return-handover/`)
