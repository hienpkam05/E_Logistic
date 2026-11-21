// API quản lý tài khoản — chỉ Nhân viên/Admin (specs/003-quan-ly-tai-khoan/api.md).
import { http } from './http'

const base = '/accounts/users/'
const one = (id) => `${base}${encodeURIComponent(id)}/`

export const list = ({ role, isActive, q, page } = {}) =>
  http.get(base, { params: { role, is_active: isActive, q, page } })
export const get = (id) => http.get(one(id))
export const create = (data) => http.post(base, data)
// `updatedAt`: giá trị updated_at đã tải — backend trả 409 nếu người khác vừa sửa.
export const update = (id, data, updatedAt) => http.patch(one(id), { ...data, updated_at: updatedAt })
export const lock = (id, reason = '') => http.post(`${one(id)}lock/`, { reason })
export const unlock = (id) => http.post(`${one(id)}unlock/`)
export const resetPassword = (id) => http.post(`${one(id)}reset-password/`, { identity_verified: true })
export const events = (id, { page } = {}) => http.get(`${one(id)}events/`, { params: { page } })
