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

async function setup(user = SHIPPER, unread = 0, path = '/shipper') {
  const result = await mountView(AppLayout, { path })
  useMetaStore().choices = CHOICES
  useAuthStore().setUser(user)
  useNotificationStore().unreadCount = unread
  await flush()
  return result
}

const logoutButton = (wrapper) => wrapper.findAll('button').find((b) => b.text().includes('Đăng xuất'))

afterEach(() => {
  document.body.innerHTML = ''
  try { localStorage.clear() } catch { /* bỏ qua */ }
  Object.values(authService).forEach((fn) => fn.mockReset())
})

describe('AppLayout', () => {
  it('hiện tên, nhãn vai trò từ backend, đường dẫn trang chủ theo vai trò', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('.user-menu__name').text()).toBe('Shipper Demo')
    expect(wrapper.find('.user-menu__role').text()).toBe('Shipper')
    expect(wrapper.find('.avatar').text()).toBe('SD')
    expect(wrapper.find('.sidebar__brand').attributes('href')).toBe('/shipper')
  })

  it('số chưa đọc: ẩn khi 0, hiện số, quá 99 hiện 99+', async () => {
    let { wrapper } = await setup(SHIPPER, 0)
    expect(wrapper.find('.topbar__count').exists()).toBe(false)
    ;({ wrapper } = await setup(SHIPPER, 7))
    expect(wrapper.find('.topbar__count').text()).toBe('7')
    ;({ wrapper } = await setup(SHIPPER, 150))
    expect(wrapper.find('.topbar__count').text()).toBe('99+')
  })

  it('menu theo vai trò: Nhân viên có Quản lý tài khoản/Shipper, Shipper thì không', async () => {
    let { wrapper } = await setup({ ...SHIPPER, role: 'ADMIN' })
    const links = wrapper.findAll('.sidebar__nav a').map((a) => [a.text(), a.attributes('href')])
    expect(links).toContainEqual(['Quản lý vận đơn', '/staff/shipments'])
    expect(links).toContainEqual(['Quản lý tài khoản', '/staff/accounts'])
    expect(links).toContainEqual(['Quản lý Shipper', '/staff/accounts?role=SHIPPER'])
    ;({ wrapper } = await setup(SHIPPER))
    expect(wrapper.text()).not.toContain('Quản lý tài khoản')
    const shipperLinks = wrapper.findAll('.sidebar__nav a').map((a) => [a.text(), a.attributes('href')])
    expect(shipperLinks).toContainEqual(['Nhiệm vụ', '/shipper/tasks']) // spec 006, đổi tên ở spec 007 D11
  })

  it('đang dùng mật khẩu tạm: ẩn menu, chuông, hồ sơ; chỉ còn đăng xuất', async () => {
    const { wrapper } = await setup({ ...SHIPPER, must_change_password: true })
    expect(wrapper.find('.sidebar__nav').exists()).toBe(false)
    expect(wrapper.find('.topbar__icon-btn').exists()).toBe(false)
    expect(wrapper.findAll('.user-menu__item').map((i) => i.text())).toEqual(['Đăng xuất'])
  })

  it('đánh dấu đúng MỘT mục đang mở: "Quản lý Shipper" khi ?role=SHIPPER, tiêu đề thanh trên theo mục', async () => {
    let { wrapper } = await setup({ ...SHIPPER, role: 'ADMIN' }, 0, '/staff/accounts?role=SHIPPER')
    expect(wrapper.findAll('.sidebar__link.is-active').map((a) => a.text())).toEqual(['Quản lý Shipper'])
    expect(wrapper.find('.topbar__title').text()).toBe('Quản lý Shipper')
    ;({ wrapper } = await setup({ ...SHIPPER, role: 'ADMIN' }, 0, '/staff/accounts/7'))
    expect(wrapper.findAll('.sidebar__link.is-active').map((a) => a.text())).toEqual(['Quản lý tài khoản'])
  })

  it('menu người dùng: bấm avatar mở, bấm ra ngoài đóng', async () => {
    const { wrapper } = await setup()
    const panel = wrapper.find('.user-menu__panel')
    expect(panel.isVisible()).toBe(false)
    await wrapper.find('.user-menu__trigger').trigger('click')
    expect(panel.isVisible()).toBe(true)
    document.body.click()
    await flush()
    expect(panel.isVisible()).toBe(false)
  })

  it('thu gọn thanh bên được nhớ cho lần sau', async () => {
    let { wrapper } = await setup()
    await wrapper.find('.sidebar__toggle').trigger('click')
    expect(wrapper.find('.shell').classes()).toContain('shell--collapsed')
    ;({ wrapper } = await setup())
    expect(wrapper.find('.shell').classes()).toContain('shell--collapsed')
  })

  it('đăng xuất -> /login', async () => {
    authService.logout.mockResolvedValue(null)
    const { wrapper, router } = await setup()
    await logoutButton(wrapper).trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/login'))
    expect(useAuthStore().isAuthenticated).toBe(false)
  })

  it('đăng xuất khi mất mạng -> /login kèm cờ chưa xác nhận', async () => {
    authService.logout.mockRejectedValue(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'x' }))
    const { wrapper, router } = await setup()
    await logoutButton(wrapper).trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.logout).toBe('unconfirmed'))
    expect(useAuthStore().isAuthenticated).toBe(false)
  })
})
