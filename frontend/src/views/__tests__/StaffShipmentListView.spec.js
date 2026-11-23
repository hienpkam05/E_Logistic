import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/http'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import StaffShipmentListView from '../staff/StaffShipmentListView.vue'
import { flush, mountView } from './helpers'
import { SHIPMENT, SHIPMENT_CHOICES, page } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({
  wards: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), cancel: vi.fn(), events: vi.fn(),
  approve: vi.fn(), reject: vi.fn(),
}))

const SHOP = { id: 3, username: 'shop_hoa', full_name: 'Shop Hoa', phone: '0999000003' }
const ROW = { ...SHIPMENT, shop: SHOP }

async function setup(path = '/staff/shipments', data = page([ROW])) {
  shipmentService.list.mockResolvedValue(data)
  const result = await mountView(StaffShipmentListView, {
    path, beforeMount: () => { useMetaStore().choices = SHIPMENT_CHOICES },
  })
  await flush()
  return result
}

const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)
const lastCall = () => shipmentService.list.mock.calls.at(-1)[0]

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(shipmentService).forEach((fn) => fn.mockReset())
})

describe('StaffShipmentListView', () => {
  it('mặc định tab Chờ xác nhận: lọc trạng thái chờ, cũ nhất trước (D7)', async () => {
    const { wrapper } = await setup()
    expect(lastCall()).toEqual({ status: ['PENDING_APPROVAL'], q: undefined, createdFrom: undefined,
      createdTo: undefined, ordering: 'created_at', page: 1 })
    expect(button(wrapper, 'Chờ xác nhận').attributes('aria-pressed')).toBe('true')
    expect(wrapper.find('.filter-select').exists()).toBe(false) // tab chờ không lọc trạng thái khác
    expect(wrapper.find('.data-card__count').text()).toBe('1 yêu cầu chờ duyệt')
  })

  it('hàng: mã yêu cầu, Shop, người nhận, liên kết chi tiết Nhân viên', async () => {
    const { wrapper } = await setup()
    const cells = wrapper.findAll('tbody td').map((td) => td.text())
    expect(cells[0]).toContain('YC000012')
    expect(cells[1]).toContain('Shop Hoa')
    expect(cells[1]).toContain('shop_hoa')
    expect(cells[2]).toContain('Trần Thị B')
    expect(wrapper.find('tbody a').attributes('href')).toBe('/staff/shipments/12')
  })

  it('tab Tất cả: mới nhất trước, có lọc trạng thái; đổi tab bỏ trạng thái + về trang 1', async () => {
    const { wrapper, router } = await setup('/staff/shipments?page=2')
    await button(wrapper, 'Tất cả').trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ tab: 'all' })
    expect(lastCall()).toMatchObject({ status: undefined, ordering: '-created_at', page: 1 })
    await wrapper.find('.filter-select select').setValue('CANCELLED')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ tab: 'all', status: 'CANCELLED' })
    expect(lastCall()).toMatchObject({ status: ['CANCELLED'] })
    await button(wrapper, 'Chờ xác nhận').trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('URL giữ bộ lọc: tìm + khoảng ngày gửi đúng tham số', async () => {
    const { wrapper } = await setup('/staff/shipments?tab=all&q=hoa&from=2026-11-01&to=2026-11-21')
    expect(lastCall()).toMatchObject({ q: 'hoa', createdFrom: '2026-11-01', createdTo: '2026-11-21' })
    const [fromInput, toInput] = wrapper.findAll('input[type="date"]')
    expect(fromInput.element.value).toBe('2026-11-01')
    expect(toInput.attributes('min')).toBe('2026-11-01') // không chọn được đến ngày trước từ ngày
    expect(fromInput.attributes('max')).toBe('2026-11-21')
  })

  it('tìm và chọn ngày ghi lên URL, giữ tab', async () => {
    const { wrapper, router } = await setup('/staff/shipments?tab=all')
    await wrapper.find('input[type="search"]').setValue('  0999 ')
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ tab: 'all', q: '0999' })
    await wrapper.findAll('input[type="date"]')[0].setValue('2026-11-10')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ tab: 'all', q: '0999', from: '2026-11-10' })
  })

  it('tab chờ trống: báo đã hết việc; có lọc mà trống: "Bỏ lọc"', async () => {
    let { wrapper } = await setup('/staff/shipments', page([]))
    expect(wrapper.text()).toContain('Không có yêu cầu nào đang chờ duyệt.')
    let router
    ;({ wrapper, router } = await setup('/staff/shipments?tab=all&q=zzz&from=2026-11-01', page([])))
    expect(wrapper.text()).toContain('Không có kết quả phù hợp với bộ lọc.')
    await button(wrapper, 'Bỏ lọc').trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ tab: 'all' }) // giữ tab, bỏ mọi bộ lọc
    expect(lastCall()).toMatchObject({ q: undefined, createdFrom: undefined })
  })

  it('khoảng ngày sai (backend 400): báo lỗi, có Bỏ lọc và Tải lại', async () => {
    shipmentService.list.mockRejectedValueOnce(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { created_to: ['Đến ngày phải bằng hoặc sau Từ ngày.'] },
    }))
    const { wrapper } = await mountView(StaffShipmentListView, {
      path: '/staff/shipments?tab=all&from=2026-11-22&to=2026-11-01',
      beforeMount: () => { useMetaStore().choices = SHIPMENT_CHOICES },
    })
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toContain('Dữ liệu chưa hợp lệ.')
    expect(button(wrapper, 'Bỏ lọc')).toBeDefined()
  })

  it('tab giai đoạn (spec 008 D10): nhãn từ backend; mỗi tab lọc mọi trạng thái của giai đoạn, cũ nhất trước', async () => {
    const { wrapper, router } = await setup('/staff/shipments', page([]))
    const labels = wrapper.findAll('.tabs__item').map((b) => b.text())
    expect(labels).toEqual(['Chờ xác nhận', 'Lấy hàng', 'Giao hàng', 'Hoàn hàng', 'Tất cả'])
    expect(wrapper.find('.chips').exists()).toBe(false) // Chờ xác nhận chỉ một trạng thái → không có chip
    for (const [label, key, statuses] of [
      ['Lấy hàng', 'pickup', ['AWAITING_PICKUP', 'PICKUP_FAILED', 'PICKED_UP']],
      ['Giao hàng', 'delivery', ['AT_HUB', 'AWAITING_REDELIVERY', 'DELIVERY_FAILED']],
      ['Hoàn hàng', 'return', ['AWAITING_RETURN', 'RETURNING', 'AWAITING_SHOP_PICKUP']]]) {
      await button(wrapper, label).trigger('click')
      await flush()
      expect(router.currentRoute.value.query).toEqual({ tab: key })
      expect(lastCall()).toMatchObject({ status: statuses, ordering: 'created_at', page: 1 })
      expect(wrapper.text()).toContain('Không có vận đơn nào cần xử lý ở bước này.')
      expect(wrapper.find('.filter-select').exists()).toBe(false)
    }
    await button(wrapper, 'Chờ xác nhận').trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({}) // tab mặc định không ghi lên URL
  })

  it('chip trạng thái con: lọc một trạng thái trong giai đoạn, vẫn là hàng việc; trạng thái ngoài giai đoạn bị bỏ', async () => {
    const { wrapper, router } = await setup('/staff/shipments?tab=return', page([]))
    const chips = wrapper.findAll('.chips .chip')
    expect(chips.map((c) => c.text())).toEqual(['Tất cả', 'Chờ xử lý hoàn', 'Đang hoàn', 'Chờ Shop đến lấy'])
    expect(chips[0].attributes('aria-pressed')).toBe('true')
    await chips[2].trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ tab: 'return', status: 'RETURNING' })
    expect(lastCall()).toMatchObject({ status: ['RETURNING'], ordering: 'created_at' })
    expect(wrapper.text()).toContain('Không có vận đơn nào cần xử lý ở bước này.') // chip không phải "bộ lọc"
    await setup('/staff/shipments?tab=return&status=DELIVERED')
    expect(lastCall()).toMatchObject({ status: ['AWAITING_RETURN', 'RETURNING', 'AWAITING_SHOP_PICKUP'] })
  })

  it('?tab lạ → tab mặc định', async () => {
    await setup('/staff/shipments?tab=xyz')
    expect(lastCall()).toMatchObject({ status: ['PENDING_APPROVAL'] })
  })
})
