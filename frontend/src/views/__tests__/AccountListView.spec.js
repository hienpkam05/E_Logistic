import { afterEach, describe, expect, it, vi } from 'vitest'
import * as accountService from '../../services/accountService'
import { ApiError } from '../../services/http'
import { useMetaStore } from '../../stores/meta'
import { CHOICES } from '../../test-utils'
import AccountListView from '../staff/AccountListView.vue'
import { flush, mountView } from './helpers'

vi.mock('../../services/accountService', () => ({
  list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), lock: vi.fn(), unlock: vi.fn(),
  resetPassword: vi.fn(), events: vi.fn(),
}))

const user = (id, extra = {}) => ({
  id, username: `user_${id}`, full_name: `Người ${id}`, phone: '0901234567', address: '', role: 'SHIPPER',
  is_active: true, must_change_password: false, last_login: null, date_joined: '2026-11-21T02:00:00Z',
  updated_at: '2026-11-21T02:00:00Z', ...extra,
})
const page = (results, extra = {}) => ({ count: results.length, next: null, previous: null, results, ...extra })

async function setup(path = '/staff/accounts') {
  const result = await mountView(AccountListView, { path })
  useMetaStore().choices = CHOICES
  await flush()
  await flush()
  return result
}

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(accountService).forEach((fn) => fn.mockReset())
})

describe('AccountListView', () => {
  it('bảng: tên đăng nhập là liên kết chi tiết, SĐT định dạng, nhãn vai trò, trạng thái', async () => {
    accountService.list.mockResolvedValue(page([
      user(1), user(2, { is_active: false, role: 'SHOP' }), user(3, { must_change_password: true }),
    ]))
    const { wrapper } = await setup()
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(3)
    expect(rows[0].find('a').attributes('href')).toBe('/staff/accounts/1')
    expect(rows[0].text()).toContain('0901 234 567')
    expect(rows[0].text()).toContain('Shipper')
    expect(rows.map((r) => r.find('.pill').text())).toEqual(['Hoạt động', 'Bị khóa', 'Chờ đổi mật khẩu'])
    expect(rows[1].find('.pill').classes()).toContain('pill--danger')
  })

  it('tab vai trò lấy nhãn từ backend', async () => {
    accountService.list.mockResolvedValue(page([]))
    const { wrapper } = await setup()
    expect(wrapper.findAll('.tabs__item').map((b) => b.text())).toEqual(['Tất cả', 'Shop', 'Nhân viên/Admin', 'Shipper'])
  })

  it('"Quản lý Shipper" (?role=SHIPPER): lọc API, tiêu đề, nút thêm mang sẵn vai trò', async () => {
    accountService.list.mockResolvedValue(page([user(1)]))
    const { wrapper } = await setup('/staff/accounts?role=SHIPPER')
    expect(accountService.list).toHaveBeenLastCalledWith({ role: 'SHIPPER', isActive: undefined, q: undefined, page: 1 })
    expect(wrapper.find('h1').text()).toBe('Quản lý Shipper')
    const add = wrapper.find('.page__header a')
    expect(add.text()).toBe('Thêm Shipper')
    expect(add.attributes('href')).toBe('/staff/accounts/new?role=SHIPPER')
  })

  it('mở thẳng ?role=SHIPPER khi danh mục chưa tải xong vẫn lọc đúng (lỗi đã sửa)', async () => {
    accountService.list.mockResolvedValue(page([]))
    await mountView(AccountListView, { path: '/staff/accounts?role=SHIPPER' }) // không nạp meta
    await flush()
    expect(accountService.list).toHaveBeenCalledOnce()
    expect(accountService.list.mock.calls[0][0].role).toBe('SHIPPER')
  })

  it('lọc trạng thái + tìm kiếm cập nhật URL, về trang 1, gọi API đúng tham số', async () => {
    accountService.list.mockResolvedValue(page([user(1)]))
    const { wrapper, router } = await setup('/staff/accounts?role=SHOP&page=3')
    await wrapper.find('select').setValue('locked')
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ role: 'SHOP', status: 'locked' }))
    await wrapper.find('input[type="search"]').setValue('  hoa  ')
    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.query.q).toBe('hoa'))
    await vi.waitFor(() => expect(accountService.list)
      .toHaveBeenLastCalledWith({ role: 'SHOP', isActive: false, q: 'hoa', page: 1 }))
  })

  it('tham số URL lạ bị bỏ qua', async () => {
    accountService.list.mockResolvedValue(page([]))
    await setup('/staff/accounts?role=KHACH&status=xyz&page=abc')
    expect(accountService.list).toHaveBeenLastCalledWith({ role: undefined, isActive: undefined, q: undefined, page: 1 })
  })

  it('trống có lọc: "Bỏ lọc" xóa toàn bộ bộ lọc (UC06.1 A1)', async () => {
    accountService.list.mockResolvedValue(page([]))
    const { wrapper, router } = await setup('/staff/accounts?role=SHIPPER&q=khong')
    expect(wrapper.text()).toContain('Không có tài khoản phù hợp với bộ lọc.')
    await wrapper.find('.empty button').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({}))
  })

  it('lỗi tải: báo lỗi, không hiện dữ liệu, tải lại được (UC06.1 E1)', async () => {
    accountService.list
      .mockRejectedValueOnce(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất kết nối.' }))
      .mockResolvedValueOnce(page([user(1)]))
    const { wrapper } = await setup()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất kết nối.')
    expect(wrapper.find('table').exists()).toBe(false)
    await wrapper.find('[role="alert"] button').trigger('click')
    await flush()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })

  it('phân trang giữ bộ lọc', async () => {
    accountService.list.mockResolvedValue(page([user(1)], { count: 30, next: 'x' }))
    const { wrapper, router } = await setup('/staff/accounts?role=SHOP')
    await wrapper.findAll('.pagination button')[1].trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ role: 'SHOP', page: '2' }))
  })
})
