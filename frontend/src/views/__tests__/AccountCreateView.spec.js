import { afterEach, describe, expect, it, vi } from 'vitest'
import * as accountService from '../../services/accountService'
import { ApiError } from '../../services/http'
import { useMetaStore } from '../../stores/meta'
import { CHOICES } from '../../test-utils'
import AccountCreateView from '../staff/AccountCreateView.vue'
import { flush, mountRouted, mountView } from './helpers'

vi.mock('../../services/accountService', () => ({
  list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), lock: vi.fn(), unlock: vi.fn(),
  resetPassword: vi.fn(), events: vi.fn(),
}))

const CREATED = {
  user: { id: 42, username: 'shipper_moi', full_name: 'Shipper Mới', role: 'SHIPPER' },
  temp_password: 'Xk7mP2qR9vTs',
}

async function setup(path = '/staff/accounts/new') {
  const result = await mountView(AccountCreateView, { path })
  useMetaStore().choices = CHOICES
  await flush()
  return result
}

async function fill(wrapper, { role } = {}) {
  const inputs = wrapper.findAll('input')
  await inputs[0].setValue(' shipper_moi ')
  await inputs[1].setValue('Shipper Mới')
  await inputs[2].setValue('0922222222')
  if (role) await wrapper.find('select').setValue(role)
}

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(accountService).forEach((fn) => fn.mockReset())
  vi.restoreAllMocks()
})

describe('AccountCreateView', () => {
  it('?role=SHIPPER: khóa sẵn vai trò, không có ô chọn (UC06.2 BR1)', async () => {
    accountService.create.mockResolvedValue(CREATED)
    const { wrapper } = await setup('/staff/accounts/new?role=SHIPPER')
    expect(wrapper.find('h1').text()).toBe('Thêm Shipper')
    expect(wrapper.find('select').exists()).toBe(false)
    await fill(wrapper)
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(accountService.create).toHaveBeenCalledWith({
      username: 'shipper_moi', full_name: 'Shipper Mới', phone: '0922222222', address: '', role: 'SHIPPER',
    })
  })

  it('không có vai trò sẵn: chọn từ danh sách backend', async () => {
    accountService.create.mockResolvedValue(CREATED)
    const { wrapper } = await setup()
    expect(wrapper.findAll('select option').map((o) => o.text())).toEqual(['Chọn vai trò', 'Shop', 'Nhân viên/Admin', 'Shipper'])
    await fill(wrapper, { role: 'SHOP' })
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(accountService.create.mock.calls[0][0].role).toBe('SHOP')
  })

  it('lỗi trùng: hiện đúng ô, không mất dữ liệu đã nhập', async () => {
    accountService.create.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { username: ['Tên đăng nhập đã được sử dụng.'], role: ['Bắt buộc.'] },
    }))
    const { wrapper } = await setup()
    await fill(wrapper)
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.findAll('.field')[0].find('.field__error').text()).toBe('Tên đăng nhập đã được sử dụng.')
    expect(wrapper.find('select').attributes('aria-invalid')).toBe('true')
    expect(wrapper.findAll('input')[1].element.value).toBe('Shipper Mới')
  })

  it('tạo xong: ẩn form, hiện mật khẩu tạm một lần; "Tôi đã ghi lại" -> trang chi tiết', async () => {
    accountService.create.mockResolvedValue(CREATED)
    const { wrapper, router } = await setup('/staff/accounts/new?role=SHIPPER')
    await fill(wrapper)
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.find('code').text()).toBe('Xk7mP2qR9vTs')
    const done = wrapper.findAll('button').find((b) => b.text() === 'Tôi đã ghi lại')
    await done.trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/staff/accounts/42'))
  })

  it('rời trang khi chưa xác nhận đã ghi lại: hỏi lại; Hủy thì ở lại, Đồng ý thì đi', async () => {
    accountService.create.mockResolvedValue(CREATED)
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper, router } = await mountRouted(AccountCreateView,
      { routePath: '/staff/accounts/new', path: '/staff/accounts/new?role=SHIPPER' })
    useMetaStore().choices = CHOICES
    await flush()
    await fill(wrapper)
    await wrapper.find('form').trigger('submit')
    await flush()
    await router.push('/staff/accounts')
    expect(confirm).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.path).toBe('/staff/accounts/new')
    expect(wrapper.find('code').text()).toBe('Xk7mP2qR9vTs')
    confirm.mockReturnValue(true)
    await router.push('/staff/accounts')
    expect(router.currentRoute.value.path).toBe('/staff/accounts')
  })

  it('chưa tạo gì thì rời trang không hỏi', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    const { router } = await mountRouted(AccountCreateView, { routePath: '/staff/accounts/new', path: '/staff/accounts/new' })
    await router.push('/staff/accounts')
    expect(confirm).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/staff/accounts')
  })

  it('Hủy quay về danh sách đúng vai trò, không gọi API (UC06.2 A1)', async () => {
    const { wrapper } = await setup('/staff/accounts/new?role=SHIPPER')
    const cancel = wrapper.findAll('a').find((a) => a.text() === 'Hủy')
    expect(cancel.attributes('href')).toBe('/staff/accounts?role=SHIPPER')
    expect(accountService.create).not.toHaveBeenCalled()
  })
})
