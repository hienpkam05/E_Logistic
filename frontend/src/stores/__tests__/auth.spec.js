import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authService from '../../services/authService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../auth'

vi.mock('../../services/authService', () => ({
  fetchCsrf: vi.fn(), login: vi.fn(), logout: vi.fn(), getMe: vi.fn(), updateMe: vi.fn(), changePassword: vi.fn(),
}))

const USER = { id: 1, username: 'shop_a', role: 'SHOP', must_change_password: false }
const unauthorized = new ApiError({ status: 401, code: 'NOT_AUTHENTICATED', message: 'x' })

beforeEach(() => {
  setActivePinia(createPinia())
  Object.values(authService).forEach((fn) => fn.mockReset())
})

describe('store auth', () => {
  it('restore: hỏi backend đúng một lần, dùng chung request', async () => {
    authService.getMe.mockResolvedValue(USER)
    const auth = useAuthStore()
    await Promise.all([auth.restore(), auth.restore()])
    await auth.restore()
    expect(authService.getMe).toHaveBeenCalledOnce()
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.role).toBe('SHOP')
  })

  it('restore: 401 -> anonymous, không coi là lỗi', async () => {
    authService.getMe.mockRejectedValue(unauthorized)
    const auth = useAuthStore()
    await auth.restore()
    expect(auth.status).toBe('anonymous')
    expect(auth.restoreError).toBeNull()
  })

  it('restore: mất mạng -> anonymous và giữ lỗi để màn hình báo', async () => {
    const network = new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'mất mạng' })
    authService.getMe.mockRejectedValue(network)
    const auth = useAuthStore()
    await auth.restore()
    expect(auth.status).toBe('anonymous')
    expect(auth.restoreError).toBe(network)
  })

  it('login: lấy CSRF trước rồi mới đăng nhập', async () => {
    const order = []
    authService.fetchCsrf.mockImplementation(async () => order.push('csrf'))
    authService.login.mockImplementation(async () => { order.push('login'); return USER })
    const auth = useAuthStore()
    await auth.login('shop_a', 'mk')
    expect(order).toEqual(['csrf', 'login'])
    expect(authService.login).toHaveBeenCalledWith('shop_a', 'mk')
    expect(auth.user).toEqual(USER)
  })

  it('login lỗi: không đổi trạng thái, ném lỗi cho màn hình', async () => {
    authService.login.mockRejectedValue(new ApiError({ status: 400, code: 'INVALID_CREDENTIALS', message: 'x' }))
    const auth = useAuthStore()
    await expect(auth.login('a', 'b')).rejects.toMatchObject({ code: 'INVALID_CREDENTIALS' })
    expect(auth.isAuthenticated).toBe(false)
  })

  it('logout thành công', async () => {
    authService.logout.mockResolvedValue(null)
    const auth = useAuthStore()
    auth.setUser(USER)
    expect(await auth.logout()).toEqual({ serverConfirmed: true })
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
  })

  it('logout khi mất mạng: vẫn xóa trạng thái cục bộ, báo chưa xác nhận (UC01.2 E1)', async () => {
    authService.logout.mockRejectedValue(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'x' }))
    const auth = useAuthStore()
    auth.setUser(USER)
    expect(await auth.logout()).toEqual({ serverConfirmed: false })
    expect(auth.isAuthenticated).toBe(false)
  })

  it('mật khẩu tạm', () => {
    const auth = useAuthStore()
    auth.setUser(USER)
    expect(auth.mustChangePassword).toBe(false)
    auth.markPasswordChangeRequired()
    expect(auth.mustChangePassword).toBe(true)
  })
})
