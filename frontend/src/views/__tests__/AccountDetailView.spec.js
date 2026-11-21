import { afterEach, describe, expect, it, vi } from 'vitest'
import * as accountService from '../../services/accountService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { CHOICES } from '../../test-utils'
import AccountDetailView from '../staff/AccountDetailView.vue'
import { flush, mountRouted, mountView } from './helpers'

vi.mock('../../services/accountService', () => ({
  list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), lock: vi.fn(), unlock: vi.fn(),
  resetPassword: vi.fn(), events: vi.fn(),
}))

const ME = { id: 1, username: 'nv_a', full_name: 'Nhân viên A', role: 'ADMIN', must_change_password: false }
const ACCOUNT = {
  id: 7, username: 'shipper_long', full_name: 'Nguyễn Văn Long', phone: '0912345678', address: '', role: 'SHIPPER',
  is_active: true, must_change_password: false, last_login: null, date_joined: '2026-11-21T02:00:00Z',
  updated_at: '2026-11-21T02:00:00.123456Z',
}
const KIND_CHOICES = {
  ...CHOICES,
  account_actions: [
    { value: 'CREATED', label: 'Tạo tài khoản' }, { value: 'UPDATED', label: 'Cập nhật hồ sơ' },
    { value: 'LOCKED', label: 'Khóa tài khoản' }, { value: 'UNLOCKED', label: 'Mở khóa tài khoản' },
    { value: 'PASSWORD_RESET', label: 'Đặt lại mật khẩu' },
  ],
}
const empty = { count: 0, next: null, previous: null, results: [] }

async function setup({ account = ACCOUNT, events = empty, me = ME } = {}) {
  accountService.get.mockResolvedValue(account)
  accountService.events.mockResolvedValue(events)
  const result = await mountView(AccountDetailView, { path: `/staff/accounts/${account.id}` })
  useMetaStore().choices = KIND_CHOICES
  useAuthStore().setUser(me)
  await flush()
  await flush()
  return result
}

const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)
const details = (wrapper) =>
  Object.fromEntries(wrapper.findAll('dt').map((dt, i) => [dt.text(), wrapper.findAll('dd')[i].text()]))

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(accountService).forEach((fn) => fn.mockReset())
  vi.restoreAllMocks()
})

describe('AccountDetailView', () => {
  it('hiện hồ sơ, trạng thái, các thao tác', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('h1').text()).toBe('Nguyễn Văn Long')
    expect(wrapper.find('.pill').text()).toBe('Hoạt động')
    const d = details(wrapper)
    expect(d['Số điện thoại']).toBe('0912 345 678')
    expect(d['Địa chỉ liên hệ']).toBe('Chưa cập nhật')
    expect(d['Đăng nhập gần nhất']).toBe('Chưa đăng nhập')
    expect(['Chỉnh sửa', 'Khóa tài khoản', 'Đặt lại mật khẩu'].every((t) => button(wrapper, t))).toBe(true)
  })

  it('tài khoản của chính mình: ẩn mọi thao tác, chỉ dẫn sang Hồ sơ (D1)', async () => {
    const { wrapper } = await setup({ account: { ...ACCOUNT, id: 1 } })
    expect(wrapper.text()).toContain('Đây là tài khoản của bạn')
    expect(button(wrapper, 'Chỉnh sửa')).toBeUndefined()
    expect(button(wrapper, 'Khóa tài khoản')).toBeUndefined()
  })

  it('không tồn tại: báo không tìm thấy', async () => {
    accountService.get.mockRejectedValue(new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' }))
    accountService.events.mockRejectedValue(new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' }))
    const { wrapper } = await mountView(AccountDetailView, { path: '/staff/accounts/999' })
    await flush()
    expect(wrapper.find('h1').text()).toBe('Không tìm thấy tài khoản')
  })

  it('sửa: gửi updated_at đã tải; thành công cập nhật màn hình và lịch sử', async () => {
    const { wrapper } = await setup()
    accountService.update.mockResolvedValue({ ...ACCOUNT, address: 'Cầu Giấy' })
    await button(wrapper, 'Chỉnh sửa').trigger('click')
    await wrapper.find('textarea').setValue(' Cầu Giấy ')
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(accountService.update).toHaveBeenCalledWith('7', { full_name: 'Nguyễn Văn Long', phone: '0912345678',
      address: 'Cầu Giấy' }, ACCOUNT.updated_at)
    expect(details(wrapper)['Địa chỉ liên hệ']).toBe('Cầu Giấy')
    expect(accountService.events).toHaveBeenCalledTimes(2)
  })

  it('409 người khác vừa sửa: cảnh báo + "Tải bản mới nhất" nạp dữ liệu mới vào form (UC06.3 E1)', async () => {
    const { wrapper } = await setup()
    accountService.update.mockRejectedValue(new ApiError({
      status: 409, code: 'CONFLICT', message: 'Tài khoản vừa được người khác thay đổi. Vui lòng tải lại.',
    }))
    await button(wrapper, 'Chỉnh sửa').trigger('click')
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.find('.alert--warning').text()).toContain('người khác')
    accountService.get.mockResolvedValue({ ...ACCOUNT, address: 'Người khác sửa', updated_at: 'moi' })
    await button(wrapper, 'Tải bản mới nhất').trigger('click')
    await flush()
    expect(wrapper.find('textarea').element.value).toBe('Người khác sửa')
    expect(wrapper.find('.alert--warning').exists()).toBe(false)
  })

  it('khóa: hộp xác nhận nêu ảnh hưởng, gửi lý do, cập nhật trạng thái', async () => {
    const { wrapper } = await setup()
    accountService.lock.mockResolvedValue({ ...ACCOUNT, is_active: false })
    await button(wrapper, 'Khóa tài khoản').trigger('click')
    await flush()
    const dialog = wrapper.findAll('dialog').find((d) => d.element.open)
    expect(dialog.text()).toContain('đăng xuất ngay trên mọi thiết bị')
    expect(dialog.text()).toContain('Nhiệm vụ đang mở của Shipper') // UC06.4 bước 2 — cảnh báo
    await dialog.find('textarea').setValue('  Nghỉ việc ')
    await dialog.find('form').trigger('submit')
    await flush()
    expect(accountService.lock).toHaveBeenCalledWith('7', 'Nghỉ việc')
    expect(wrapper.find('.pill').text()).toBe('Bị khóa')
    expect(button(wrapper, 'Mở khóa')).toBeDefined()
    expect(wrapper.findAll('dialog').some((d) => d.element.open)).toBe(false)
  })

  it('khóa bị từ chối (Admin cuối cùng): lỗi hiện trong hộp, hộp vẫn mở', async () => {
    const { wrapper } = await setup({ account: { ...ACCOUNT, role: 'ADMIN' } })
    accountService.lock.mockRejectedValue(new ApiError({
      status: 409, code: 'LIMIT_REACHED', message: 'Không thể khóa Nhân viên/Admin đang hoạt động cuối cùng.',
    }))
    await button(wrapper, 'Khóa tài khoản').trigger('click')
    await flush()
    const dialog = wrapper.findAll('dialog').find((d) => d.element.open)
    expect(dialog.text()).not.toContain('Nhiệm vụ đang mở') // không phải Shipper
    await dialog.find('form').trigger('submit')
    await flush()
    expect(dialog.find('[role="alert"]').text()).toContain('cuối cùng')
    expect(dialog.element.open).toBe(true)
  })

  it('mở khóa', async () => {
    const { wrapper } = await setup({ account: { ...ACCOUNT, is_active: false } })
    accountService.unlock.mockResolvedValue(ACCOUNT)
    await button(wrapper, 'Mở khóa').trigger('click')
    await flush()
    await wrapper.findAll('dialog').find((d) => d.element.open).find('form').trigger('submit')
    await flush()
    expect(accountService.unlock).toHaveBeenCalledWith('7')
    expect(wrapper.find('.pill').text()).toBe('Hoạt động')
  })

  it('đặt lại mật khẩu: phải tick đã xác minh; xong hiện mật khẩu tạm một lần', async () => {
    const { wrapper } = await setup()
    accountService.resetPassword.mockResolvedValue({
      user: { ...ACCOUNT, must_change_password: true }, temp_password: 'Ab3dEfGh7kMn',
    })
    await button(wrapper, 'Đặt lại mật khẩu').trigger('click')
    await flush()
    const dialog = wrapper.findAll('dialog').find((d) => d.element.open)
    const submit = dialog.find('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined()
    await dialog.find('input[type="checkbox"]').setValue(true)
    expect(submit.attributes('disabled')).toBeUndefined()
    await dialog.find('form').trigger('submit')
    await flush()
    expect(accountService.resetPassword).toHaveBeenCalledWith('7')
    expect(wrapper.find('code').text()).toBe('Ab3dEfGh7kMn')
    expect(wrapper.find('.pill').text()).toBe('Chờ đổi mật khẩu')
    await button(wrapper, 'Tôi đã ghi lại').trigger('click')
    expect(wrapper.find('code').exists()).toBe(false)
  })

  it('đang hiện mật khẩu tạm mới: rời trang thì hỏi lại', async () => {
    accountService.get.mockResolvedValue(ACCOUNT)
    accountService.events.mockResolvedValue(empty)
    accountService.resetPassword.mockResolvedValue({ user: ACCOUNT, temp_password: 'Ab3dEfGh7kMn' })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper, router } = await mountRouted(AccountDetailView,
      { routePath: '/staff/accounts/:id', path: '/staff/accounts/7' })
    useMetaStore().choices = KIND_CHOICES
    useAuthStore().setUser(ME)
    await flush()
    await button(wrapper, 'Đặt lại mật khẩu').trigger('click')
    await flush()
    const dialog = wrapper.findAll('dialog').find((d) => d.element.open)
    await dialog.find('input[type="checkbox"]').setValue(true)
    await dialog.find('form').trigger('submit')
    await flush()
    await router.push('/staff/accounts')
    expect(confirm).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.path).toBe('/staff/accounts/7')
  })

  it('lịch sử: nhãn thao tác, người thực hiện, thay đổi trước/sau, lý do, hệ thống', async () => {
    const events = {
      count: 3, next: null, previous: null,
      results: [
        { id: 3, action: 'LOCKED', actor: { id: 1, username: 'nv_a', full_name: 'Nhân viên A' }, changes: {},
          reason: 'Nghỉ việc', created_at: '2026-11-21T03:00:00Z' },
        { id: 2, action: 'UPDATED', actor: { id: 1, username: 'nv_a', full_name: 'Nhân viên A' },
          changes: { address: { from: '', to: 'Cầu Giấy' } }, reason: '', created_at: '2026-11-21T02:30:00Z' },
        { id: 1, action: 'PASSWORD_RESET', actor: null, changes: { identity_verified: true }, reason: '',
          created_at: '2026-11-21T02:00:00Z' },
      ],
    }
    const { wrapper } = await setup({ events })
    const items = wrapper.findAll('.events__item')
    expect(items[0].text()).toContain('Khóa tài khoản')
    expect(items[0].text()).toContain('bởi Nhân viên A (nv_a)')
    expect(items[0].text()).toContain('Lý do: Nghỉ việc')
    expect(items[1].text()).toContain('Địa chỉ liên hệ: (trống) → Cầu Giấy')
    expect(items[2].text()).toContain('bởi Hệ thống')
    expect(items[2].text()).toContain('đã xác minh danh tính')
  })
})
