import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { apiError, mockFetch } from '../../test-utils'
import { http, setPasswordChangeRequiredHandler, setUnauthorizedHandler } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notifications'
import { installSessionHandlers } from '../session'

vi.mock('../../services/notificationService', () => ({
  list: vi.fn(), unreadCount: vi.fn().mockResolvedValue({ count: 0 }), markRead: vi.fn(), markAllRead: vi.fn(),
}))

const Blank = { template: '<div />' }

async function setup(path) {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: Blank, meta: { public: true } },
      { path: '/account/password', name: 'change-password', component: Blank },
      { path: '/notifications', name: 'notifications', component: Blank },
    ],
  })
  await router.push(path)
  installSessionHandlers(router)
  return router
}

beforeEach(() => {
  setUnauthorizedHandler(null)
  setPasswordChangeRequiredHandler(null)
})

describe('installSessionHandlers', () => {
  it('API trả 401 khi đang dùng -> xóa phiên, về /login giữ trang đang xem', async () => {
    const router = await setup('/notifications?page=2')
    const auth = useAuthStore()
    auth.setUser({ id: 1, role: 'SHOP' })
    mockFetch(async () => apiError(401, 'NOT_AUTHENTICATED'))
    await http.get('/notifications/').catch(() => {})
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('login'))
    expect(router.currentRoute.value.query.next).toBe('/notifications?page=2')
    expect(auth.isAuthenticated).toBe(false)
  })

  it('403 PASSWORD_CHANGE_REQUIRED -> trang đổi mật khẩu', async () => {
    const router = await setup('/notifications')
    const auth = useAuthStore()
    auth.setUser({ id: 1, role: 'SHOP', must_change_password: false })
    mockFetch(async () => apiError(403, 'PASSWORD_CHANGE_REQUIRED'))
    await http.get('/notifications/').catch(() => {})
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('change-password'))
    expect(auth.mustChangePassword).toBe(true)
  })

  it('đăng nhập bật polling thông báo, đăng xuất tắt', async () => {
    await setup('/login')
    const auth = useAuthStore()
    const notifications = useNotificationStore()
    const start = vi.spyOn(notifications, 'startPolling')
    const stop = vi.spyOn(notifications, 'stopPolling')
    auth.setUser({ id: 1, role: 'SHOP' })
    await vi.waitFor(() => expect(start).toHaveBeenCalled())
    auth.handleUnauthorized()
    await vi.waitFor(() => expect(stop).toHaveBeenCalled())
  })
})
