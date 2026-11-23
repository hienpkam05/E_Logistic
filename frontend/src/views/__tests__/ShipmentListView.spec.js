import { afterEach, describe, expect, it, vi } from 'vitest'
import * as shipmentService from '../../services/shipmentService'
import { ApiError } from '../../services/http'
import { useMetaStore } from '../../stores/meta'
import ShipmentListView from '../shop/ShipmentListView.vue'
import { flush, mountView } from './helpers'
import { SHIPMENT, SHIPMENT_CHOICES, page } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({
  wards: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), cancel: vi.fn(), events: vi.fn(),
}))

async function setup(path = '/shop/shipments', data = page([SHIPMENT])) {
  shipmentService.list.mockResolvedValue(data)
  const result = await mountView(ShipmentListView, { path })
  useMetaStore().choices = SHIPMENT_CHOICES
  await flush()
  return result
}

const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(shipmentService).forEach((fn) => fn.mockReset())
})

describe('ShipmentListView', () => {
  it('hiện mã yêu cầu (chưa có mã vận đơn), người nhận, phường, COD, nhãn trạng thái', async () => {
    const { wrapper } = await setup()
    const cells = wrapper.findAll('tbody td').map((td) => td.text())
    expect(cells[0]).toContain('YC000012')
    expect(cells[0]).toContain('mã yêu cầu')
    expect(cells[1]).toContain('Trần Thị B')
    expect(cells[1]).toContain('0987 654 321')
    expect(cells[2]).toBe('Phường Láng')
    expect(cells[3]).toContain('350.000')
    expect(cells[4]).toBe('Chờ xác nhận')
    expect(wrapper.find('tbody a').attributes('href')).toBe('/shop/shipments/12')
  })

  it('có mã vận đơn: hiện mã vận đơn, không ghi chú "mã yêu cầu"; COD 0 → "—"', async () => {
    const { wrapper } = await setup('/shop/shipments',
      page([{ ...SHIPMENT, tracking_code: 'HTT000045', cod_amount: 0 }]))
    const cells = wrapper.findAll('tbody td').map((td) => td.text())
    expect(cells[0]).toBe('HTT000045')
    expect(cells[3]).toBe('—')
  })

  it('ô tìm giới hạn độ dài theo meta.limits (không viết số ở màn hình)', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('input[type="search"]').attributes('maxlength'))
      .toBe(String(SHIPMENT_CHOICES.limits.search_query_max_length))
  })

  it('bộ lọc đọc từ URL và gửi đúng cho API', async () => {
    const { wrapper } = await setup('/shop/shipments?status=CANCELLED&q=Láng&page=2')
    expect(shipmentService.list).toHaveBeenCalledWith({ status: ['CANCELLED'], q: 'Láng', page: 2 })
    expect(wrapper.find('select').element.value).toBe('CANCELLED')
    expect(wrapper.find('input[type="search"]').element.value).toBe('Láng')
  })

  it('tìm và lọc ghi lên URL, đổi bộ lọc thì về trang 1', async () => {
    const { wrapper, router } = await setup('/shop/shipments?page=3')
    await wrapper.find('input[type="search"]').setValue('  0987 ')
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ q: '0987' })
    await wrapper.find('select').setValue('CANCELLED')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ q: '0987', status: 'CANCELLED' })
    expect(shipmentService.list).toHaveBeenLastCalledWith({ status: ['CANCELLED'], q: '0987', page: 1 })
  })

  it('chưa có đơn nào: mời tạo yêu cầu đầu tiên', async () => {
    const { wrapper } = await setup('/shop/shipments', page([]))
    expect(wrapper.text()).toContain('Bạn chưa có yêu cầu gửi hàng nào.')
    const link = wrapper.findAll('a').find((a) => a.text() === 'Tạo yêu cầu đầu tiên')
    expect(link.attributes('href')).toBe('/shop/shipments/new')
  })

  it('lọc không ra kết quả: "Bỏ lọc" xóa bộ lọc', async () => {
    const { wrapper, router } = await setup('/shop/shipments?q=zzz', page([]))
    expect(wrapper.text()).toContain('Không có vận đơn phù hợp với bộ lọc.')
    await button(wrapper, 'Bỏ lọc').trigger('click')
    await flush()
    expect(router.currentRoute.value.fullPath).toBe('/shop/shipments')
    expect(wrapper.find('input[type="search"]').element.value).toBe('')
  })

  it('lỗi tải: báo lỗi, "Tải lại" gọi lại API', async () => {
    shipmentService.list.mockRejectedValueOnce(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất mạng' }))
    const { wrapper } = await mountView(ShipmentListView, { path: '/shop/shipments?status=BAD' })
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất mạng')
    expect(button(wrapper, 'Bỏ lọc')).toBeDefined()
    shipmentService.list.mockResolvedValue(page([SHIPMENT]))
    await button(wrapper, 'Tải lại').trigger('click')
    await flush()
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })

  it('phản hồi cũ về muộn không đè kết quả mới', async () => {
    let resolveOld
    shipmentService.list.mockReturnValueOnce(new Promise((r) => { resolveOld = r }))
    const { wrapper, router } = await mountView(ShipmentListView, { path: '/shop/shipments' })
    shipmentService.list.mockResolvedValue(page([{ ...SHIPMENT, receiver_name: 'Mới' }]))
    await router.push('/shop/shipments?q=moi')
    await flush()
    resolveOld(page([{ ...SHIPMENT, receiver_name: 'Cũ' }]))
    await flush()
    expect(wrapper.find('tbody').text()).toContain('Mới')
    expect(wrapper.find('tbody').text()).not.toContain('Cũ')
  })
})
