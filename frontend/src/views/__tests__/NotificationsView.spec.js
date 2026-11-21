import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/http'
import * as notificationService from '../../services/notificationService'
import { useMetaStore } from '../../stores/meta'
import { useNotificationStore } from '../../stores/notifications'
import { CHOICES } from '../../test-utils'
import NotificationsView from '../account/NotificationsView.vue'
import { flush, mountView } from './helpers'

vi.mock('../../services/notificationService', () => ({
  list: vi.fn(), unreadCount: vi.fn(), markRead: vi.fn(), markAllRead: vi.fn(),
}))

const KINDS = { ...CHOICES, notification_kinds: [{ value: 'REQUEST_APPROVED', label: 'Yêu cầu đã được duyệt' }] }
const note = (id, isRead = false) => ({
  id, kind: 'REQUEST_APPROVED', title: `Thông báo ${id}`, body: id === 1 ? 'Mã vận đơn HTT1' : '',
  payload: {}, created_at: '2026-11-20T02:30:00Z', read_at: isRead ? '2026-11-20T03:00:00Z' : null, is_read: isRead,
})
const page = (results, extra = {}) => ({ count: results.length, next: null, previous: null, results, ...extra })

async function setup(path = '/notifications', unread = 1) {
  notificationService.unreadCount.mockResolvedValue({ count: unread })
  const result = await mountView(NotificationsView, { path })
  useMetaStore().choices = KINDS
  await flush()
  await flush()
  return result
}

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(notificationService).forEach((fn) => fn.mockReset())
})

describe('NotificationsView', () => {
  it('hiện danh sách: nhãn loại từ backend, giờ VN, đánh dấu chưa đọc', async () => {
    notificationService.list.mockResolvedValue(page([note(1), note(2, true)]))
    const { wrapper } = await setup()
    const items = wrapper.findAll('.notification')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('Yêu cầu đã được duyệt')
    expect(items[0].text()).toContain('09:30')
    expect(items[0].text()).toContain('Mã vận đơn HTT1')
    expect(items[0].classes()).toContain('notification--unread')
    expect(items[1].classes()).not.toContain('notification--unread')
    expect(notificationService.list).toHaveBeenCalledWith({ unread: undefined, page: 1 })
  })

  it('bấm thông báo chưa đọc: đánh dấu đã đọc, giảm số đếm; đã đọc thì không gọi API', async () => {
    notificationService.list.mockResolvedValue(page([note(1), note(2, true)]))
    notificationService.markRead.mockResolvedValue(note(1, true))
    const { wrapper } = await setup('/notifications', 1)
    const store = useNotificationStore()
    expect(store.unreadCount).toBe(1)
    await wrapper.findAll('.notification')[0].trigger('click')
    await flush()
    expect(notificationService.markRead).toHaveBeenCalledWith(1)
    expect(store.unreadCount).toBe(0)
    expect(wrapper.findAll('.notification')[0].classes()).not.toContain('notification--unread')
    await wrapper.findAll('.notification')[1].trigger('click')
    expect(notificationService.markRead).toHaveBeenCalledOnce()
  })

  it('lọc chưa đọc qua URL; đổi bộ lọc cập nhật URL và tải lại', async () => {
    notificationService.list.mockResolvedValue(page([note(1)]))
    const { wrapper, router } = await setup('/notifications?unread=true')
    expect(notificationService.list).toHaveBeenLastCalledWith({ unread: true, page: 1 })
    const [all] = wrapper.findAll('.tabs__item')
    await all.trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.unread).toBeUndefined())
    await vi.waitFor(() => expect(notificationService.list).toHaveBeenLastCalledWith({ unread: undefined, page: 1 }))
  })

  it('đánh dấu tất cả: gọi API, về 0, tải lại; nút khóa khi không còn chưa đọc', async () => {
    notificationService.list.mockResolvedValue(page([note(1)]))
    notificationService.markAllRead.mockResolvedValue({ updated: 1 })
    const { wrapper } = await setup('/notifications', 1)
    const button = wrapper.find('.page__header button')
    await button.trigger('click')
    await flush()
    expect(notificationService.markAllRead).toHaveBeenCalledOnce()
    expect(useNotificationStore().unreadCount).toBe(0)
    expect(notificationService.list).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.page__header button').attributes('disabled')).toBeDefined()
  })

  it('trống: thông điệp theo bộ lọc', async () => {
    notificationService.list.mockResolvedValue(page([]))
    let { wrapper } = await setup('/notifications', 0)
    expect(wrapper.text()).toContain('Chưa có thông báo nào.')
    ;({ wrapper } = await setup('/notifications?unread=true', 0))
    expect(wrapper.text()).toContain('Không có thông báo chưa đọc.')
  })

  it('lỗi tải: báo lỗi và tải lại được', async () => {
    notificationService.list
      .mockRejectedValueOnce(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất kết nối.' }))
      .mockResolvedValueOnce(page([note(1)]))
    const { wrapper } = await setup()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất kết nối.')
    await wrapper.find('[role="alert"] button').trigger('click')
    await flush()
    expect(wrapper.findAll('.notification')).toHaveLength(1)
  })

  it('phân trang theo URL', async () => {
    notificationService.list.mockResolvedValue(page([note(1)], { count: 25, next: 'x', previous: null }))
    const { wrapper, router } = await setup()
    const [prev, next] = wrapper.findAll('.pagination button')
    expect(prev.attributes('disabled')).toBeDefined()
    await next.trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.page).toBe('2'))
    await vi.waitFor(() => expect(notificationService.list).toHaveBeenLastCalledWith({ unread: undefined, page: 2 }))
  })

  it('page trên URL không hợp lệ -> trang 1', async () => {
    notificationService.list.mockResolvedValue(page([]))
    await setup('/notifications?page=abc')
    expect(notificationService.list).toHaveBeenLastCalledWith({ unread: undefined, page: 1 })
  })
})
