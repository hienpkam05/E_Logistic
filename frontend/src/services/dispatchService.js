// API điều phối cho Nhân viên (specs/006-lay-hang-diem-tap-ket/api.md).
import { http } from './http'

// Shipper đang hoạt động kèm open_task_count, ít việc trước. q: tên / tên đăng nhập / SĐT.
export const shippers = ({ q } = {}) => http.get('/dispatch/shippers/', { params: { q } })
