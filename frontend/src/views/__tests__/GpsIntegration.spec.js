import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import TaskDetailView from '../shipper/TaskDetailView.vue'
import ShipmentDetailView from '../shop/ShipmentDetailView.vue'
import StaffShipmentDetailView from '../staff/StaffShipmentDetailView.vue'
import { mountView } from './helpers'
import { PICKUP_TASK, DELIVERY_TASK, RETURN_TASK, SHIPMENT, SHIPMENT_CHOICES, page } from './shipmentFixtures'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { ROLES } from '../../router/roles'
import { directionsUrl, taskDestination } from '../../utils/location'
import * as tasks from '../../services/taskService'
import * as shipments from '../../services/shipmentService'
import * as tracking from '../../services/trackingService'

vi.mock('../../services/taskService', () => ({ get: vi.fn() }))
vi.mock('../../services/shipmentService', () => ({ get: vi.fn(), events: vi.fn(), approve: vi.fn() }))
vi.mock('../../services/trackingService', () => ({ getLocation: vi.fn(), sendLocation: vi.fn() }))
const geoDescriptor = Object.getOwnPropertyDescriptor(navigator, 'geolocation')
let wrapper, failure, success, geo
const choices = (role) => () => { useMetaStore().choices = structuredClone(SHIPMENT_CHOICES); useAuthStore().setUser({ id: 4, role }) }
const button = (label) => wrapper.findAll('button').find((item) => item.text() === label)
async function renderTask(task = DELIVERY_TASK) {
  tasks.get.mockResolvedValue(task)
  const result = await mountView(TaskDetailView, { path: `/shipper/tasks/${task.id}`, beforeMount: choices(ROLES.SHIPPER) })
  wrapper = result.wrapper
  await flushPromises()
  return result
}
beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-11-24T04:00:00Z'))
  vi.stubGlobal('isSecureContext', true)
  geo = { watchPosition: vi.fn((ok, fail) => { success = ok; failure = fail; return 3 }), clearWatch: vi.fn() }
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: geo })
  tracking.sendLocation.mockResolvedValue({ stored: true })
  tracking.getLocation.mockResolvedValue({ task: null, location: null })
  shipments.get.mockResolvedValue(SHIPMENT)
  shipments.events.mockResolvedValue(page([]))
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  vi.useRealTimers()
  vi.unstubAllGlobals()
  if (geoDescriptor) Object.defineProperty(navigator, 'geolocation', geoDescriptor)
  else delete navigator.geolocation
})

describe('GPS on task/shipment screens', () => {
  it.each([PICKUP_TASK, DELIVERY_TASK, RETURN_TASK,
    { ...DELIVERY_TASK, status: 'PENDING_SWAP_HANDOVER', allowed_actions: ['REPORT_SWAP_HANDOVER'] }])(
    'điểm đến $type/$status và URL chỉ gửi địa chỉ, không danh tính/COD', async (task) => {
      await renderTask(task)
      const link = wrapper.get('a[aria-label="Chỉ đường bằng Google Maps (mở tab mới)"]')
      const url = new URL(link.attributes('href'))
      expect(url.origin).toBe('https://www.google.com')
      expect([...url.searchParams.keys()]).toEqual(['api', 'destination'])
      expect(url.searchParams.get('destination')).toBe(taskDestination(task, SHIPMENT_CHOICES.hub))
      expect(link.attributes('rel')).toBe('noopener noreferrer')
      expect(geo.watchPosition).not.toHaveBeenCalled()
    })

  it('URL encode ký tự &, #, tiếng Việt; thiếu địa chỉ/task đóng không tạo link', () => {
    const url = new URL(directionsUrl('12 Hàng Bạc & ngõ #2'))
    expect(url.searchParams.get('destination')).toBe('12 Hàng Bạc & ngõ #2')
    expect(directionsUrl(' ')).toBeNull()
    expect(taskDestination({ ...DELIVERY_TASK, status: 'SUCCEEDED' }, SHIPMENT_CHOICES.hub)).toBe('')
  })

  it('giải thích trước khi xin GPS; từ chối vẫn giữ địa chỉ/chỉ đường và thao tác nhiệm vụ', async () => {
    await renderTask()
    expect(wrapper.text()).toContain('Shop của đơn và Nhân viên xem được điểm gần nhất')
    expect(wrapper.text()).toContain('30 ngày')
    await button('Bật chia sẻ vị trí').trigger('click')
    await flushPromises()
    failure({ code: 1 })
    await flushPromises()
    expect(wrapper.text()).toContain('Chưa cấp quyền vị trí')
    expect(wrapper.text()).toContain('5 Láng Hạ')
    expect(wrapper.find('a[aria-label^="Chỉ đường"]').exists()).toBe(true)
    expect(button('Giao thành công').attributes('disabled')).toBeUndefined()
    expect(tracking.sendLocation).not.toHaveBeenCalled()
  })

  it('bật gửi/tắt thực tế, rời view không có callback ghi tiếp', async () => {
    await renderTask(PICKUP_TASK)
    await button('Bật chia sẻ vị trí').trigger('click')
    await flushPromises()
    success({ timestamp: Date.now(), coords: { latitude: 21, longitude: 105, accuracy: 10 } })
    await flushPromises()
    expect(wrapper.text()).toContain('Đang chia sẻ vị trí')
    expect(tracking.sendLocation).toHaveBeenCalledOnce()
    await button('Tắt chia sẻ vị trí').trigger('click')
    expect(geo.clearWatch).toHaveBeenCalledWith(3)
    wrapper.unmount()
    success({ timestamp: Date.now() + 16000, coords: { latitude: 22, longitude: 106, accuracy: 10 } })
    await flushPromises()
    expect(tracking.sendLocation).toHaveBeenCalledOnce()
  })

  it('health check đổi bàn giao cập nhật điểm đến hub; task đóng bỏ khối chia sẻ/chỉ đường', async () => {
    await renderTask()
    await button('Bật chia sẻ vị trí').trigger('click')
    await flushPromises()
    tasks.get.mockResolvedValueOnce({ ...DELIVERY_TASK, status: 'PENDING_SWAP_HANDOVER', allowed_actions: ['REPORT_SWAP_HANDOVER'] })
    await vi.advanceTimersByTimeAsync(15000)
    await flushPromises()
    expect(new URL(wrapper.get('a[aria-label^="Chỉ đường"]').attributes('href')).searchParams.get('destination')).toBe(SHIPMENT_CHOICES.hub.address)
    expect(wrapper.find('.cod-card').exists()).toBe(false)
    tasks.get.mockResolvedValueOnce({ ...DELIVERY_TASK, status: 'REPLACED', allowed_actions: [] })
    await vi.advanceTimersByTimeAsync(15000)
    await flushPromises()
    expect(wrapper.find('.location-sharing').exists()).toBe(false)
    expect(wrapper.find('a[aria-label^="Chỉ đường"]').exists()).toBe(false)
    expect(geo.clearWatch).toHaveBeenCalledWith(3)
  })

  it.each([[ShipmentDetailView, ROLES.SHOP, '/shop/shipments/12'], [StaffShipmentDetailView, ROLES.ADMIN, '/staff/shipments/12']])(
    'chi tiết %s chỉ hiện khối khi API có task mở, đóng thì bỏ khối', async (component, role, path) => {
      tracking.getLocation.mockResolvedValue({ task: { id: 1, type: 'PICKUP' }, location: null })
      const result = await mountView(component, { path, beforeMount: choices(role) })
      wrapper = result.wrapper
      await flushPromises()
      expect(wrapper.get('.live-map').isVisible()).toBe(true)
      expect(wrapper.text()).toContain('Chưa có vị trí được chia sẻ')
      tracking.getLocation.mockResolvedValue({ task: null, location: null })
      await vi.advanceTimersByTimeAsync(15000)
      await flushPromises()
      expect(wrapper.get('.live-map').isVisible()).toBe(false)
      expect(vi.getTimerCount()).toBe(0)
    })

  it('mutation cùng đơn làm mới theo dõi ngay, kể cả trước đó không có task và đã dừng polling', async () => {
    shipments.get.mockResolvedValue({ ...SHIPMENT, allowed_actions: ['APPROVE_REQUEST'] })
    shipments.approve.mockResolvedValue({ ...SHIPMENT, status: 'AWAITING_PICKUP', allowed_actions: [], updated_at: '2026-11-24T05:00:00Z' })
    const result = await mountView(StaffShipmentDetailView, { path: '/staff/shipments/12', beforeMount: choices(ROLES.ADMIN) })
    wrapper = result.wrapper
    await flushPromises()
    expect(tracking.getLocation).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
    await button('Duyệt').trigger('click')
    await flushPromises()
    const dialog = wrapper.findAll('dialog').find((item) => item.element.open)
    await dialog.find('form').trigger('submit')
    await flushPromises()
    expect(shipments.approve).toHaveBeenCalledOnce()
    expect(tracking.getLocation).toHaveBeenCalledTimes(2)
  })
})
