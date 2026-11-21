// API thông báo nội bộ (specs/002-xac-thuc/api.md).
import { http } from './http'

export const list = ({ unread, page, pageSize } = {}) =>
  http.get('/notifications/', { params: { unread, page, page_size: pageSize } })
export const unreadCount = () => http.get('/notifications/unread-count/')
export const markRead = (id) => http.post(`/notifications/${encodeURIComponent(id)}/read/`)
export const markAllRead = () => http.post('/notifications/read-all/')
