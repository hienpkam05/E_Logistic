// API điều phối cho Nhân viên (specs/006-lay-hang-diem-tap-ket/api.md).
import { http } from './http'

// Shipper đang hoạt động kèm open_task_count, ít việc trước. q: tên / tên đăng nhập / SĐT.
export const shippers = ({ q } = {}) => http.get('/dispatch/shippers/', { params: { q } })
// Spec 009: nhiệm vụ đang mở, kể cả Shipper bị khóa; dùng trong hộp khóa tài khoản.
export const openTasks = (id) => http.get(`/dispatch/shippers/${encodeURIComponent(id)}/open-tasks/`)
