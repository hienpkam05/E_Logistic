import { afterEach, describe, expect, it, vi } from 'vitest'
import * as authService from '../../services/authService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import LoginView from '../auth/LoginView.vue'
import { flush, mountView } from './helpers'

vi.mock('../../services/authService', () => ({
  fetchCsrf: vi.fn(), login: vi.fn(), logout: vi.fn(), getMe: vi.fn(), updateMe: vi.fn(), changePassword: vi.fn(),
}))

const SHOP = { id: 1, username: 'shop_a', full_name: 'Shop A', role: 'SHOP', must_change_password: false }

async function fillAndSubmit(wrapper, username = ' shop_a ', password = 'mk') {
  const inputs = wrapper.findAll('input')
  await inputs[0].setValue(username)
  await inputs[1].setValue(password)
  await wrapper.find('form').trigger('submit')
}

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(authService).forEach((fn) => fn.mockReset())
})

describe('LoginView', () => {
  it('đăng nhập đúng -> trang chủ vai trò; gửi username đã bỏ khoảng trắng', async () => {
    authService.login.mockResolvedValue(SHOP)
    const { wrapper, router } = await mountView(LoginView, { path: '/login' })
    await fillAndSubmit(wrapper)
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('shop-home'))
    expect(authService.fetchCsrf).toHaveBeenCalled()
    expect(authService.login).toHaveBeenCalledWith('shop_a', 'mk')
  })

  it('có next hợp lệ -> quay lại trang đó; next ra ngoài -> bỏ qua', async () => {
    authService.login.mockResolvedValue(SHOP)
    let { wrapper, router } = await mountView(LoginView, { path: '/login?next=/notifications' })
    await fillAndSubmit(wrapper)
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/notifications'))

    ;({ wrapper, router } = await mountView(LoginView, { path: '/login?next=//evil.example.com' }))
    await fillAndSubmit(wrapper)
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('shop-home'))
  })

  it('mật khẩu tạm -> trang đổi mật khẩu', async () => {
    authService.login.mockResolvedValue({ ...SHOP, must_change_password: true })
    const { wrapper, router } = await mountView(LoginView, { path: '/login' })
    await fillAndSubmit(wrapper)
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('change-password'))
  })

  it('sai thông tin: hiện thông điệp backend, xóa ô mật khẩu, ở lại trang', async () => {
    authService.login.mockRejectedValue(
      new ApiError({ status: 400, code: 'INVALID_CREDENTIALS', message: 'Tên đăng nhập hoặc mật khẩu không đúng.' }),
    )
    const { wrapper, router } = await mountView(LoginView, { path: '/login' })
    await fillAndSubmit(wrapper)
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toBe('Tên đăng nhập hoặc mật khẩu không đúng.')
    expect(wrapper.findAll('input')[1].element.value).toBe('')
    expect(router.currentRoute.value.name).toBe('login')
    expect(useAuthStore().isAuthenticated).toBe(false)
  })

  it('lỗi theo trường hiện dưới đúng ô', async () => {
    authService.login.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.', fields: { username: ['Bắt buộc.'] },
    }))
    const { wrapper } = await mountView(LoginView, { path: '/login' })
    await fillAndSubmit(wrapper, '', '')
    await flush()
    const field = wrapper.findAll('.field')[0]
    expect(field.find('.field__error').text()).toBe('Bắt buộc.')
    expect(field.find('input').attributes('aria-invalid')).toBe('true')
  })

  it('khóa nút và ô nhập khi đang gửi; bấm lại không gửi lần hai', async () => {
    let resolveLogin
    authService.login.mockImplementation(() => new Promise((r) => { resolveLogin = r }))
    const { wrapper } = await mountView(LoginView, { path: '/login' })
    await fillAndSubmit(wrapper)
    await flush()
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
    await wrapper.find('form').trigger('submit')
    expect(authService.login).toHaveBeenCalledOnce()
    resolveLogin(SHOP)
  })

  it('thông báo khi đăng xuất chưa được máy chủ xác nhận', async () => {
    const { wrapper } = await mountView(LoginView, { path: '/login?logout=unconfirmed' })
    expect(wrapper.find('[role="status"]').text()).toContain('chưa xác nhận được với máy chủ')
  })
})
