import { afterEach, describe, expect, it, vi } from 'vitest'
import * as authService from '../../services/authService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import ChangePasswordView from '../account/ChangePasswordView.vue'
import { flush, mountView } from './helpers'

vi.mock('../../services/authService', () => ({
  fetchCsrf: vi.fn(), login: vi.fn(), logout: vi.fn(), getMe: vi.fn(), updateMe: vi.fn(), changePassword: vi.fn(),
}))

const SHOP = { id: 1, username: 'shop_a', full_name: 'Shop A', role: 'SHOP', must_change_password: false }

async function submit(wrapper, values = ['cu', 'MatKhauMoi#1', 'MatKhauMoi#1']) {
  const inputs = wrapper.findAll('input')
  for (const [i, value] of values.entries()) await inputs[i].setValue(value)
  await wrapper.find('form').trigger('submit')
  await flush()
}

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(authService).forEach((fn) => fn.mockReset())
})

describe('ChangePasswordView', () => {
  it('lỗi theo trường từ backend hiện đúng ô', async () => {
    authService.changePassword.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { current_password: ['Mật khẩu hiện tại không đúng.'], new_password: ['Quá ngắn.', 'Quá phổ biến.'] },
    }))
    const { wrapper } = await mountView(ChangePasswordView, { path: '/account/password' })
    useAuthStore().setUser(SHOP)
    await submit(wrapper)
    const errors = wrapper.findAll('.field').map((f) => f.find('.field__error').exists() ? f.find('.field__error').text() : '')
    expect(errors).toEqual(['Mật khẩu hiện tại không đúng.', 'Quá ngắn. Quá phổ biến.', ''])
    expect(wrapper.find('[role="alert"]').text()).toBe('Dữ liệu chưa hợp lệ.')
  })

  it('gửi đúng dữ liệu; thành công thì xóa form và báo các thiết bị khác phải đăng nhập lại', async () => {
    authService.changePassword.mockResolvedValue(null)
    authService.getMe.mockResolvedValue(SHOP)
    const { wrapper, router } = await mountView(ChangePasswordView, { path: '/account/password' })
    useAuthStore().setUser(SHOP)
    await submit(wrapper)
    expect(authService.changePassword).toHaveBeenCalledWith({
      currentPassword: 'cu', newPassword: 'MatKhauMoi#1', newPasswordConfirm: 'MatKhauMoi#1',
    })
    expect(wrapper.find('.alert--success').text()).toContain('thiết bị khác')
    expect(wrapper.findAll('input').every((i) => i.element.value === '')).toBe(true)
    expect(router.currentRoute.value.name).not.toBe('shop-home')
  })

  it('chế độ mật khẩu tạm: có cảnh báo; đổi xong -> trang chủ vai trò và hết cờ', async () => {
    authService.changePassword.mockResolvedValue(null)
    authService.getMe.mockResolvedValue(SHOP)
    const { wrapper, router } = await mountView(ChangePasswordView, { path: '/account/password' })
    const auth = useAuthStore()
    auth.setUser({ ...SHOP, must_change_password: true })
    await flush()
    expect(wrapper.find('.alert--warning').text()).toContain('mật khẩu tạm')
    await submit(wrapper)
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('shop-home'))
    expect(auth.mustChangePassword).toBe(false)
  })

  it('có liên kết sang Quên mật khẩu (UC02.3 A1)', async () => {
    const { wrapper } = await mountView(ChangePasswordView, { path: '/account/password' })
    expect(wrapper.find('a[href="/forgot-password"]').exists()).toBe(true)
  })
})
