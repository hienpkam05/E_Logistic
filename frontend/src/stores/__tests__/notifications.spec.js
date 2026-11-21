import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { NOTIFICATION_POLL_MS } from '../../config'
import * as notificationService from '../../services/notificationService'
import { useNotificationStore } from '../notifications'

vi.mock('../../services/notificationService', () => ({
  list: vi.fn(), unreadCount: vi.fn(), markRead: vi.fn(), markAllRead: vi.fn(),
}))

let visibility = 'visible'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.useFakeTimers()
  visibility = 'visible'
  vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibility)
  Object.values(notificationService).forEach((fn) => fn.mockReset())
  notificationService.unreadCount.mockResolvedValue({ count: 3 })
})

afterEach(() => {
  useNotificationStore().stopPolling()
  vi.useRealTimers()
})

describe('store notifications', () => {
  it('chu kỳ mặc định 60 giây (D8)', () => {
    expect(NOTIFICATION_POLL_MS).toBe(60_000)
  })

  it('startPolling: tải ngay, rồi mỗi chu kỳ; gọi lại không tạo timer thứ hai', async () => {
    const store = useNotificationStore()
    store.startPolling()
    store.startPolling()
    await vi.advanceTimersByTimeAsync(0)
    expect(store.unreadCount).toBe(3)
    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS * 2)
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(3)
  })

  it('tab ẩn: không gọi API; hiện lại: cập nhật ngay', async () => {
    const store = useNotificationStore()
    store.startPolling()
    await vi.advanceTimersByTimeAsync(0)
    visibility = 'hidden'
    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS * 3)
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(1)
    visibility = 'visible'
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(2)
  })

  it('stopPolling (đăng xuất): dừng hẳn, về 0', async () => {
    const store = useNotificationStore()
    store.startPolling()
    await vi.advanceTimersByTimeAsync(0)
    store.stopPolling()
    expect(store.unreadCount).toBe(0)
    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS * 3)
    document.dispatchEvent(new Event('visibilitychange'))
    expect(notificationService.unreadCount).toHaveBeenCalledTimes(1)
  })

  it('lỗi tải số: giữ số cũ', async () => {
    const store = useNotificationStore()
    store.startPolling()
    await vi.advanceTimersByTimeAsync(0)
    notificationService.unreadCount.mockRejectedValue(new Error('mất mạng'))
    await vi.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS)
    expect(store.unreadCount).toBe(3)
  })

  it('markRead giảm số đếm (chỉ khi chưa đọc); markAllRead về 0', async () => {
    const store = useNotificationStore()
    store.unreadCount = 2
    notificationService.markRead.mockResolvedValue({})
    notificationService.markAllRead.mockResolvedValue({ updated: 1 })
    await store.markRead({ id: 1, is_read: false })
    await store.markRead({ id: 2, is_read: true })
    expect(store.unreadCount).toBe(1)
    await store.markAllRead()
    expect(store.unreadCount).toBe(0)
  })
})
