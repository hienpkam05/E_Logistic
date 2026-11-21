import { afterEach, describe, expect, it, vi } from 'vitest'
import * as authService from '../../services/authService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { CHOICES } from '../../test-utils'
import ProfileView from '../account/ProfileView.vue'
import { flush, mountView } from './helpers'

vi.mock('../../services/authService', () => ({
  fetchCsrf: vi.fn(), login: vi.fn(), logout: vi.fn(), getMe: vi.fn(), updateMe: vi.fn(), changePassword: vi.fn(),
}))

const ME = {
  id: 1, username: 'shop_a', full_name: 'Shop Hoa An', phone: '0901234567', address: '',
  role: 'SHOP', must_change_password: false, date_joined: '2026-11-20T02:30:00Z',
}

async function setup() {
  const result = await mountView(ProfileView, { path: '/account/profile' })
  useMetaStore().choices = CHOICES
  await flush()
  return result
}

const details = (wrapper) =>
  Object.fromEntries(wrapper.findAll('dt').map((dt, i) => [dt.text(), wrapper.findAll('dd')[i].text()]))

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(authService).forEach((fn) => fn.mockReset())
})

describe('ProfileView', () => {
  it('tải hồ sơ mới từ máy chủ; trường trống hiện "Chưa cập nhật"; định dạng SĐT, vai trò', async () => {
    authService.getMe.mockResolvedValue(ME)
    const { wrapper } = await setup()
    expect(authService.getMe).toHaveBeenCalledOnce()
    const d = details(wrapper)
    expect(d['Địa chỉ liên hệ']).toBe('Chưa cập nhật')
    expect(d['Số điện thoại']).toBe('0901 234 567')
    expect(d['Vai trò']).toBe('Shop')
    expect(d['Tên đăng nhập']).toBe('shop_a')
    expect(useAuthStore().user).toEqual(ME)
  })

  it('không tải được: báo lỗi, không hiện dữ liệu, tải lại được (UC02.1 E1)', async () => {
    authService.getMe.mockRejectedValueOnce(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất kết nối.' }))
    authService.getMe.mockResolvedValueOnce(ME)
    const { wrapper } = await setup()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất kết nối.')
    expect(wrapper.find('dl').exists()).toBe(false)
    await wrapper.find('[role="alert"] button').trigger('click')
    await flush()
    expect(wrapper.find('dl').exists()).toBe(true)
  })

  it('Hủy: không gọi API, giữ nguyên dữ liệu (UC02.2 A1)', async () => {
    authService.getMe.mockResolvedValue(ME)
    const { wrapper } = await setup()
    await wrapper.find('button').trigger('click') // Chỉnh sửa
    await wrapper.findAll('input')[0].setValue('Tên mới')
    const cancel = wrapper.findAll('button').find((b) => b.text() === 'Hủy')
    await cancel.trigger('click')
    expect(authService.updateMe).not.toHaveBeenCalled()
    expect(details(wrapper)['Họ tên']).toBe('Shop Hoa An')
    // mở lại form: giá trị là dữ liệu đã lưu, không phải bản nháp đã hủy
    await wrapper.find('button').trigger('click')
    expect(wrapper.findAll('input')[0].element.value).toBe('Shop Hoa An')
  })

  it('Lưu: gửi 3 trường đã bỏ khoảng trắng, cập nhật màn hình và store', async () => {
    authService.getMe.mockResolvedValue(ME)
    const saved = { ...ME, address: '1 Tràng Tiền' }
    authService.updateMe.mockResolvedValue(saved)
    const { wrapper } = await setup()
    await wrapper.find('button').trigger('click')
    await wrapper.find('textarea').setValue('  1 Tràng Tiền  ')
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(authService.updateMe).toHaveBeenCalledWith({ full_name: 'Shop Hoa An', phone: '0901234567', address: '1 Tràng Tiền' })
    expect(details(wrapper)['Địa chỉ liên hệ']).toBe('1 Tràng Tiền')
    expect(wrapper.find('.alert--success').exists()).toBe(true)
    expect(useAuthStore().user.address).toBe('1 Tràng Tiền')
  })

  it('lỗi theo trường: ở lại form, hiện đúng ô', async () => {
    authService.getMe.mockResolvedValue(ME)
    authService.updateMe.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { phone: ['Số điện thoại đã được sử dụng.'] },
    }))
    const { wrapper } = await setup()
    await wrapper.find('button').trigger('click')
    await wrapper.findAll('input')[1].setValue('0900000002')
    await wrapper.find('form').trigger('submit')
    await flush()
    const phoneField = wrapper.findAll('.field')[1]
    expect(phoneField.find('.field__error').text()).toBe('Số điện thoại đã được sử dụng.')
    expect(wrapper.find('form').exists()).toBe(true)
    expect(useAuthStore().user.phone).toBe('0901234567')
  })
})
