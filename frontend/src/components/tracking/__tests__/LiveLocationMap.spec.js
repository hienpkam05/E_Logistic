import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LiveLocationMap from '../LiveLocationMap.vue'
import { useAuthStore } from '../../../stores/auth'
import { useMetaStore } from '../../../stores/meta'
import { CHOICES } from '../../../test-utils'
import { ROLES } from '../../../router/roles'
import * as tracking from '../../../services/trackingService'
import { MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from '../../../config'

const leaflet = vi.hoisted(() => ({ maps: [], tiles: [], markers: [] }))
vi.mock('leaflet', () => ({
  map: vi.fn(() => {
    const map = { setView: vi.fn().mockReturnThis(), panTo: vi.fn(), remove: vi.fn(), invalidateSize: vi.fn() }
    leaflet.maps.push(map)
    return map
  }),
  tileLayer: vi.fn((url, options) => {
    const tile = { url, options, events: {}, on: vi.fn((name, fn) => { tile.events[name] = fn; return tile }), addTo: vi.fn().mockReturnThis() }
    leaflet.tiles.push(tile)
    return tile
  }),
  circleMarker: vi.fn(() => {
    const marker = { addTo: vi.fn().mockReturnThis(), setLatLng: vi.fn() }
    leaflet.markers.push(marker)
    return marker
  }),
}))
vi.mock('../../../services/trackingService', () => ({ getLocation: vi.fn() }))

let wrapper, pinia, auth, meta
const visibilityDescriptor = Object.getOwnPropertyDescriptor(document, 'visibilityState')
function data({ taskId = 10, location = {} } = {}) {
  return { task: { id: taskId, type: 'DELIVERY' }, location: location === null ? null : {
    lat: 21, lng: 105, accuracy: 12.5, recorded_at: new Date(Date.now() - 1000).toISOString(),
    received_at: new Date().toISOString(), stale: false, ...location,
  } }
}
async function ready() { await flushPromises(); await flushPromises() }
async function render(props = {}) {
  wrapper = mount(LiveLocationMap, { props: { shipmentId: 5, ...props }, global: { plugins: [pinia] }, attachTo: document.body })
  await ready()
}
function visibility(value) {
  Object.defineProperty(document, 'visibilityState', { configurable: true, value })
  document.dispatchEvent(new Event('visibilitychange'))
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-11-24T01:00:00Z'))
  leaflet.maps.length = leaflet.tiles.length = leaflet.markers.length = 0
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' })
  pinia = createPinia()
  setActivePinia(pinia)
  auth = useAuthStore()
  auth.setUser({ id: 1, role: ROLES.SHOP })
  meta = useMetaStore()
  meta.choices = structuredClone(CHOICES)
  tracking.getLocation.mockReset().mockImplementation(async () => data())
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  vi.useRealTimers()
  vi.unstubAllGlobals()
  if (visibilityDescriptor) Object.defineProperty(document, 'visibilityState', visibilityDescriptor)
  else delete document.visibilityState
})

describe('LiveLocationMap', () => {
  it('vẽ điểm thật từ API, thời gian/sai số, attribution và nền cấu hình', async () => {
    await render()
    expect(tracking.getLocation).toHaveBeenCalledWith(5, { signal: expect.any(AbortSignal) })
    expect(leaflet.maps[0].setView).toHaveBeenCalledWith([21, 105], expect.any(Number))
    expect(leaflet.tiles[0].url).toBe(MAP_TILE_URL)
    expect(leaflet.tiles[0].options).toMatchObject({ attribution: MAP_TILE_ATTRIBUTION, keepBuffer: 0 })
    expect(wrapper.find('a[href="https://www.openstreetmap.org/copyright"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('12.5 m')
    expect(wrapper.text()).toContain('Thời điểm đo')
  })

  it('task chưa có điểm không dựng bản đồ/điểm giả', async () => {
    tracking.getLocation.mockResolvedValue(data({ location: null }))
    await render()
    expect(wrapper.text()).toContain('Chưa có vị trí')
    expect(leaflet.maps).toHaveLength(0)
    expect(leaflet.markers).toHaveLength(0)
  })

  it('task kết thúc xóa marker và dừng polling/clock', async () => {
    await render()
    tracking.getLocation.mockResolvedValue({ task: null, location: null })
    await vi.advanceTimersByTimeAsync(15000)
    await ready()
    expect(leaflet.maps[0].remove).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Không còn nhiệm vụ mở')
    expect(wrapper.emitted('ended')).toHaveLength(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('đổi task không dùng lại GPS người cũ', async () => {
    await render()
    tracking.getLocation.mockResolvedValue(data({ taskId: 11, location: null }))
    await vi.advanceTimersByTimeAsync(15000)
    await ready()
    expect(leaflet.maps[0].remove).toHaveBeenCalledOnce()
    expect(wrapper.text()).not.toContain('Tọa độ:')
    expect(wrapper.text()).toContain('Chưa có vị trí')
  })

  it('điểm mới cập nhật marker thay vì tạo bản đồ chồng', async () => {
    await render()
    tracking.getLocation.mockResolvedValue(data({ location: { lat: 22 } }))
    await vi.advanceTimersByTimeAsync(15000)
    await ready()
    expect(leaflet.maps).toHaveLength(1)
    expect(leaflet.markers[0].setLatLng).toHaveBeenCalledWith([22, 105])
  })

  it('điểm cũ theo metadata hoặc thời gian trôi khi API đang treo phải được ghi rõ', async () => {
    await render()
    tracking.getLocation.mockImplementation(() => new Promise(() => {}))
    await vi.advanceTimersByTimeAsync(315000)
    expect(wrapper.text()).toContain('Vị trí đã cũ')
    expect(tracking.getLocation).toHaveBeenCalledTimes(2) // không chồng request đang treo.
  })

  it('stale từ server vẫn hiện cảnh báo và không đổi tuổi điểm thành thời gian fetch', async () => {
    tracking.getLocation.mockResolvedValue(data({ location: { stale: true } }))
    await render()
    expect(wrapper.text()).toContain('Vị trí đã cũ')
  })

  it('lỗi mạng giữ điểm gần nhất có nhãn lỗi, không coi là đang cập nhật', async () => {
    await render()
    tracking.getLocation.mockRejectedValueOnce({ status: 0, message: 'Mất mạng' })
    await vi.advanceTimersByTimeAsync(15000)
    await ready()
    expect(wrapper.text()).toContain('Mất mạng')
    expect(wrapper.text()).toContain('dữ liệu lần trước')
    expect(wrapper.text()).not.toContain('Đang cập nhật vị trí.')
    await wrapper.get('button').trigger('click')
    await ready()
    expect(wrapper.text()).not.toContain('Mất mạng')
  })

  it.each([401, 403, 404])('mất quyền/API %s xóa điểm cũ và dừng tự gọi lại', async (status) => {
    await render()
    tracking.getLocation.mockRejectedValueOnce({ status, message: 'Không còn quyền' })
    await vi.advanceTimersByTimeAsync(15000)
    await ready()
    expect(wrapper.text()).not.toContain('Tọa độ:')
    expect(leaflet.maps[0].remove).toHaveBeenCalledOnce()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('lỗi tile giữ tọa độ/attribution và cho tải lại bản đồ', async () => {
    await render()
    leaflet.tiles[0].events.tileerror()
    await ready()
    expect(wrapper.text()).toContain('Chưa tải được nền bản đồ')
    expect(wrapper.text()).toContain('Tọa độ: 21, 105')
    expect(wrapper.text()).toContain('OpenStreetMap')
    await wrapper.get('button').trigger('click')
    await ready()
    expect(leaflet.maps[0].remove).toHaveBeenCalledOnce()
    expect(leaflet.maps).toHaveLength(2)
  })

  it('đổi đơn bỏ request/response và sự kiện tile cũ', async () => {
    await render()
    const oldTile = leaflet.tiles[0]
    let resolve
    tracking.getLocation.mockReturnValueOnce(new Promise((done) => { resolve = done }))
    await vi.advanceTimersByTimeAsync(15000)
    const oldSignal = tracking.getLocation.mock.calls[1][1].signal
    await wrapper.setProps({ shipmentId: 6 })
    await ready()
    resolve(data({ location: { lat: 30 } }))
    oldTile.events.tileerror()
    await ready()
    expect(oldSignal.aborted).toBe(true)
    expect(wrapper.text()).not.toContain('30, 105')
    expect(wrapper.text()).not.toContain('Chưa tải được nền bản đồ')
    expect(tracking.getLocation.mock.calls.at(-1)[0]).toBe(6)
  })

  it('ẩn tab/active=false dừng, hiện lại tải mới; unmount dọn timer và observer', async () => {
    const observer = { observe: vi.fn(), disconnect: vi.fn() }
    vi.stubGlobal('ResizeObserver', class { constructor() { return observer } })
    await render()
    visibility('hidden')
    await ready()
    expect(vi.getTimerCount()).toBe(0)
    expect(observer.disconnect).toHaveBeenCalledOnce()
    visibility('visible')
    await ready()
    expect(tracking.getLocation).toHaveBeenCalledTimes(2)
    await wrapper.setProps({ active: false })
    expect(vi.getTimerCount()).toBe(0)
    await wrapper.setProps({ active: true })
    await ready()
    wrapper.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('logout xóa điểm, Shipper không đọc API của Shop/NV', async () => {
    await render()
    auth.setUser(null)
    await ready()
    expect(wrapper.text()).not.toContain('Tọa độ:')
    expect(vi.getTimerCount()).toBe(0)
    auth.setUser({ id: 4, role: ROLES.SHIPPER })
    await ready()
    expect(tracking.getLocation).toHaveBeenCalledTimes(1)
  })

  it('thiếu metadata hoặc tọa độ không hợp lệ có lỗi, không dựng bản đồ', async () => {
    meta.choices.limits = {}
    await render()
    expect(wrapper.text()).toContain('Chưa tải được giới hạn GPS')
    expect(tracking.getLocation).not.toHaveBeenCalled()
    meta.choices = structuredClone(CHOICES)
    tracking.getLocation.mockResolvedValue(data({ location: { lat: 91 } }))
    await wrapper.get('button').trigger('click')
    await ready()
    expect(wrapper.text()).toContain('Dữ liệu vị trí chưa hợp lệ')
    expect(leaflet.maps).toHaveLength(0)
  })
})
