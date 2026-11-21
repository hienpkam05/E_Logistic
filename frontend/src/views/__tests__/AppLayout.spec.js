import { afterEach, describe, expect, it, vi } from 'vitest'
import AppLayout from '../../layouts/AppLayout.vue'
import * as authService from '../../services/authService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { useNotificationStore } from '../../stores/notifications'
import { CHOICES } from '../../test-utils'
import { flush, mountView } from './helpers'

vi.mock('../../services/authService', () => ({
  fetchCsrf: vi.fn(), login: vi.fn(), logout: vi.fn(), getMe: vi.fn(), updateMe: vi.fn(), changePassword: vi.fn(),
}))

const SHIPPER = { id: 3, username: 'sp', full_name: 'Shipper Demo', role: 'SHIPPER', must_change_password: false }

async function setup(user = SHIPPER, unread = 0) {
  const result = await mountView(AppLayout, { path: '/shipper' })
  useMetaStore().choices = CHOICES
  useAuthStore().setUser(user)
  useNotificationStore().unreadCount = unread
  await flush()
  return result
}

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(authService).forEach((fn) => fn.mockReset())
})

describe('AppLayout', () => {
  it('hiện tên, nhãn vai trò từ backend, đường dẫn trang chủ theo vai trò', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('.app-header__name').text()).toBe('Shipper Demo')
    expect(wrapper.find('.app-header__role').text()).toBe('Shipper')
    expect(wrapper.find('.app-header__brand').attributes('href')).toBe('/shipper')
  })

  it('số chưa đọc: ẩn khi 0, hiện số, quá 99 hiện 99+', async () => {
    let { wrapper } = await setup(SHIPPER, 0)
    expect(wrapper.find('.app-header__count').exists()).toBe(false)
    ;({ wrapper } = await setup(SHIPPER, 7))
    expect(wrapper.find('.app-header__count').text()).toBe('7')
    ;({ wrapper } = await setup(SHIPPER, 150))
    expect(wrapper.find('.app-header__count').text()).toBe('99+')
  })

  it('menu theo vai trò: Nhân viên có Quản lý tài khoản/Shipper, Shipper thì không', async () => {
    let { wrapper } = await setup({ ...SHIPPER, role: 'ADMIN' })
    const links = wrapper.findAll('.app-header__nav a').map((a) => [a.text(), a.attributes('href')])
    expect(links).toContainEqual(['Quản lý tài khoản', '/staff/accounts'])
    expect(links).toContainEqual(['Quản lý Shipper', '/staff/accounts?role=SHIPPER'])
    ;({ wrapper } = await setup(SHIPPER))
    expect(wrapper.text()).not.toContain('Quản lý tài khoản')
  })

  it('đang dùng mật khẩu tạm: ẩn menu, chỉ còn đăng xuất', async () => {
    const { wrapper } = await setup({ ...SHIPPER, must_change_password: true })
    expect(wrapper.find('.app-header__nav').exists()).toBe(false)
    expect(wrapper.find('button').text()).toBe('Đăng xuất')
  })

  it('đăng xuất -> /login', async () => {
    authService.logout.mockResolvedValue(null)
    const { wrapper, router } = await setup()
    await wrapper.find('button').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/login'))
    expect(useAuthStore().isAuthenticated).toBe(false)
  })

  it('đăng xuất khi mất mạng -> /login kèm cờ chưa xác nhận', async () => {
    authService.logout.mockRejectedValue(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'x' }))
    const { wrapper, router } = await setup()
    await wrapper.find('button').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.logout).toBe('unconfirmed'))
    expect(useAuthStore().isAuthenticated).toBe(false)
  })
})
