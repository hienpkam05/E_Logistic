import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as shipmentService from '../../../services/shipmentService'
import { useMetaStore } from '../../../stores/meta'
import { SHIPMENT_CHOICES, page } from '../../../views/__tests__/shipmentFixtures'
import ShipmentEventList from '../ShipmentEventList.vue'

vi.mock('../../../services/shipmentService', () => ({ events: vi.fn() }))

const flush = () => new Promise((r) => setTimeout(r, 0))
const ADMIN = { id: 1, username: 'nv_a', full_name: 'Nhân viên A' }

function mountList(shipmentId = 12) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useMetaStore().choices = {
    ...SHIPMENT_CHOICES,
    shipment_actions: [...SHIPMENT_CHOICES.shipment_actions, { value: 'APPROVE_REQUEST', label: 'Duyệt yêu cầu' }],
  }
  return mount(ShipmentEventList, { props: { shipmentId }, global: { plugins: [pinia] } })
}

beforeEach(() => shipmentService.events.mockReset())
afterEach(() => vi.restoreAllMocks())

describe('ShipmentEventList', () => {
  it('tự tải trang 1; mốc duyệt hiện mã vận đơn cấp mới', async () => {
    shipmentService.events.mockResolvedValue(page([
      { id: 2, action: 'APPROVE_REQUEST', from_status: 'PENDING_APPROVAL', to_status: 'AWAITING_PICKUP', actor: ADMIN,
        reason: '', changes: { tracking_code: { from: null, to: 'HTT261121K7Q2M' } }, created_at: '2026-11-21T03:00:00Z' },
    ]))
    const wrapper = mountList()
    await flush()
    expect(shipmentService.events).toHaveBeenCalledWith(12, { page: 1 })
    const item = wrapper.find('.events__item').text()
    expect(item).toContain('Duyệt yêu cầu')
    expect(item).toMatch(/Chờ xác nhận\s*→\s*Chờ lấy hàng/)
    expect(item).toContain('Nhân viên A')
    expect(item).toContain('Mã vận đơn: (trống) → HTT261121K7Q2M')
  })

  it('reload() tải lại trang 1; đổi đơn thì tải đơn mới', async () => {
    shipmentService.events.mockResolvedValue(page([]))
    const wrapper = mountList()
    await flush()
    await wrapper.vm.reload()
    expect(shipmentService.events).toHaveBeenCalledTimes(2)
    await wrapper.setProps({ shipmentId: 13 })
    await flush()
    expect(shipmentService.events).toHaveBeenLastCalledWith(13, { page: 1 })
    expect(wrapper.text()).toContain('Chưa có mốc nào.')
  })

  it('lỗi tải: báo lỗi', async () => {
    shipmentService.events.mockRejectedValue(new Error('Mất mạng'))
    const wrapper = mountList()
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toBe('Mất mạng')
  })

  it('phản hồi cũ về muộn không đè dữ liệu đơn mới', async () => {
    let resolveOld
    shipmentService.events.mockReturnValueOnce(new Promise((r) => { resolveOld = r }))
    const wrapper = mountList(12)
    shipmentService.events.mockResolvedValue(page([
      { id: 9, action: 'CREATE_REQUEST', from_status: null, to_status: 'PENDING_APPROVAL', actor: null, reason: '',
        changes: {}, created_at: '2026-11-21T01:00:00Z' },
    ]))
    await wrapper.setProps({ shipmentId: 13 })
    await flush()
    resolveOld(page([]))
    await flush()
    expect(wrapper.findAll('.events__item')).toHaveLength(1)
  })

  it('mốc điều phối (spec 006): hiện Shipper được giao, người giữ hàng, ghi chú sai lệch', async () => {
    shipmentService.events.mockResolvedValue(page([
      { id: 4, action: 'RECEIVE_AT_HUB', from_status: 'PICKED_UP', to_status: 'AT_HUB', actor: ADMIN, reason: '',
        changes: { holder: { from: { id: 7, name: 'Shipper Long' }, to: { name: 'Điểm tập kết' } },
          discrepancy_note: { from: null, to: 'Thiếu 1 kiện' } }, created_at: '2026-11-22T05:00:00Z' },
      { id: 3, action: 'ASSIGN_PICKUP', from_status: 'AWAITING_PICKUP', to_status: 'PICKUP_ASSIGNED', actor: ADMIN,
        reason: '', changes: { shipper: { from: null, to: { id: 7, name: 'Shipper Long' } } }, created_at: '2026-11-22T03:00:00Z' },
    ]))
    const wrapper = mountList()
    await flush()
    const [received, assigned] = wrapper.findAll('.events__item').map((li) => li.text())
    expect(assigned).toContain('Shipper: (trống) → Shipper Long')
    expect(received).toContain('Người giữ hàng: Shipper Long → Điểm tập kết')
    expect(received).toContain('Ghi chú sai lệch: (trống) → Thiếu 1 kiện')
  })
})

