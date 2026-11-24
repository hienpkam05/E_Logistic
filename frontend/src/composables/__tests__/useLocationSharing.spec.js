import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useLocationSharing } from '../useLocationSharing'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { CHOICES } from '../../test-utils'
import { TASK_STATUS } from '../../utils/statusTones'
import { ROLES } from '../../router/roles'
import { LOCATION_SHARING_STATE as S } from '../../utils/location'
import * as tasks from '../../services/taskService'
import * as tracking from '../../services/trackingService'
import * as authService from '../../services/authService'

vi.mock('../../services/taskService', () => ({ get: vi.fn() }))
vi.mock('../../services/trackingService', () => ({ sendLocation: vi.fn() }))
vi.mock('../../services/authService', () => ({ logout: vi.fn() }))

const descriptors = Object.fromEntries(['geolocation', 'permissions', 'onLine'].map((key) => [key, Object.getOwnPropertyDescriptor(navigator, key)]))
let wrapper, sharing, id, status, auth, meta, success, failure, geo, permission, online
function fix(timestamp = Date.now(), changes = {}) {
  return { timestamp, coords: { latitude: 21, longitude: 105, accuracy: 12.5, ...changes } }
}
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b }); return { promise, resolve, reject } }

beforeEach(() => {
  vi.resetAllMocks()
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-11-24T01:00:00Z'))
  vi.stubGlobal('isSecureContext', true)
  online = true
  permission = new EventTarget()
  permission.state = 'granted'
  geo = { watchPosition: vi.fn((ok, fail) => { success = ok; failure = fail; return 0 }), clearWatch: vi.fn() }
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: geo })
  Object.defineProperty(navigator, 'permissions', { configurable: true, value: { query: vi.fn().mockResolvedValue(permission) } })
  Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => online })
  tasks.get.mockResolvedValue({ id: 17, status: TASK_STATUS.ACTIVE })
  tracking.sendLocation.mockResolvedValue({ stored: true })
  const pinia = createPinia()
  setActivePinia(pinia)
  auth = useAuthStore()
  auth.setUser({ id: 4, role: ROLES.SHIPPER })
  meta = useMetaStore()
  meta.choices = structuredClone(CHOICES)
  id = ref(17)
  status = ref(TASK_STATUS.ACTIVE)
  wrapper = mount(defineComponent({ setup() { sharing = useLocationSharing(id, { taskStatus: status }); return () => null } }),
    { global: { plugins: [pinia] } })
})
afterEach(() => {
  wrapper.unmount()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  for (const [key, descriptor] of Object.entries(descriptors)) {
    if (descriptor) Object.defineProperty(navigator, key, descriptor)
    else delete navigator[key]
  }
})

describe('useLocationSharing', () => {
  it('không tự bật; xác minh nhiệm vụ rồi mới xin vị trí, gửi đúng timestamp và signal', async () => {
    expect(geo.watchPosition).not.toHaveBeenCalled()
    await sharing.start()
    expect(tasks.get).toHaveBeenCalledWith(17, { signal: expect.any(AbortSignal) })
    expect(geo.watchPosition).toHaveBeenCalledWith(expect.any(Function), expect.any(Function),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 120000 })
    const sample = fix(Date.now() - 1000)
    success(sample)
    await flushPromises()
    expect(tracking.sendLocation).toHaveBeenCalledWith(17,
      { lat: 21, lng: 105, accuracy: 12.5, recorded_at: new Date(sample.timestamp).toISOString() }, { signal: expect.any(AbortSignal) })
    expect(sharing.lastRecordedAt.value).toBe(new Date(sample.timestamp).toISOString())
    expect(sharing.state.value).toBe(S.SHARING)
  })

  it('chỉ Shipper có phiên, HTTPS và metadata hợp lệ được bật', async () => {
    auth.setUser({ id: 4, role: ROLES.SHOP })
    await sharing.start()
    expect(geo.watchPosition).not.toHaveBeenCalled()
    auth.setUser({ id: 4, role: ROLES.SHIPPER })
    vi.stubGlobal('isSecureContext', false)
    await sharing.start()
    expect(sharing.state.value).toBe(S.UNSUPPORTED)
    vi.stubGlobal('isSecureContext', true)
    meta.choices.limits = {}
    await sharing.start()
    expect(sharing.state.value).toBe(S.ERROR)
    expect(sharing.enabled.value).toBe(false)
    expect(geo.watchPosition).not.toHaveBeenCalled()
  })

  it('không xin quyền khi API xác nhận nhiệm vụ đã đóng; chờ bàn giao vẫn được bật', async () => {
    tasks.get.mockResolvedValueOnce({ status: TASK_STATUS.REPLACED })
    await sharing.start()
    expect(geo.watchPosition).not.toHaveBeenCalled()
    tasks.get.mockResolvedValueOnce({ status: TASK_STATUS.PENDING_SWAP_HANDOVER })
    await sharing.start()
    expect(geo.watchPosition).toHaveBeenCalledTimes(1)
  })

  it('từ chối hoặc thu hồi quyền dừng watcher/timer; callback muộn không gửi', async () => {
    await sharing.start()
    permission.state = 'denied'
    permission.dispatchEvent(new Event('change'))
    expect(sharing.state.value).toBe(S.DENIED)
    expect(geo.clearWatch).toHaveBeenCalledWith(0)
    success(fix())
    await vi.advanceTimersByTimeAsync(60000)
    expect(tracking.sendLocation).not.toHaveBeenCalled()
    expect(tasks.get).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('browser từ chối quyền qua callback hoặc Permissions API đều không thu thập tiếp', async () => {
    await sharing.start()
    failure({ code: 1 })
    expect(sharing.state.value).toBe(S.DENIED)
    permission.state = 'denied'
    await sharing.start()
    expect(geo.watchPosition).toHaveBeenCalledTimes(1)
  })

  it('mất tín hiệu chờ mẫu mới; mẫu cũ/tương lai/sai số lớn/sai tọa độ không gửi', async () => {
    await sharing.start()
    failure({ code: 2 })
    expect(sharing.state.value).toBe(S.UNAVAILABLE)
    for (const sample of [fix(Date.now() - 120001), fix(Date.now() + 60001), fix(Date.now(), { accuracy: 1001 }),
      fix(Date.now(), { latitude: 91 }), fix(Date.now(), { longitude: NaN }), fix(Date.now(), { accuracy: -1 })]) success(sample)
    await flushPromises()
    expect(tracking.sendLocation).not.toHaveBeenCalled()
    success(fix(Date.now(), { accuracy: null }))
    await flushPromises()
    expect(sharing.state.value).toBe(S.SHARING)
  })

  it('bỏ mẫu quá dày, trùng hoặc lùi; không dùng timer gửi lại mẫu đã bỏ', async () => {
    await sharing.start()
    success(fix())
    await flushPromises()
    await vi.advanceTimersByTimeAsync(1000)
    const dropped = fix()
    success(dropped)
    await vi.advanceTimersByTimeAsync(14000)
    success(dropped)
    expect(tracking.sendLocation).toHaveBeenCalledTimes(1)
    success(fix())
    await flushPromises()
    expect(tracking.sendLocation).toHaveBeenCalledTimes(2)
    expect(tasks.get.mock.calls.length).toBeGreaterThan(1)
  })

  it('mất mạng không giữ hàng đợi; chỉ callback mới được thử sau kết nối lại', async () => {
    await sharing.start()
    online = false
    const offlineSample = fix()
    success(offlineSample)
    expect(sharing.state.value).toBe(S.NETWORK_ERROR)
    online = true
    await vi.advanceTimersByTimeAsync(15000)
    success(offlineSample)
    expect(tracking.sendLocation).not.toHaveBeenCalled()
    success(fix())
    await flushPromises()
    expect(tracking.sendLocation).toHaveBeenCalledTimes(1)
  })

  it('request lỗi mạng không coi là đã gửi; lần sau chỉ gửi điểm mới', async () => {
    tracking.sendLocation.mockRejectedValueOnce({ status: 0, message: 'Mất mạng' })
    await sharing.start()
    const sample = fix()
    success(sample)
    await flushPromises()
    expect(sharing.state.value).toBe(S.NETWORK_ERROR)
    expect(sharing.lastRecordedAt.value).toBeNull()
    await vi.advanceTimersByTimeAsync(15000)
    success(sample)
    expect(tracking.sendLocation).toHaveBeenCalledTimes(1)
    success(fix())
    await flushPromises()
    expect(sharing.state.value).toBe(S.SHARING)
  })

  it.each([401, 403, 404, 409])('API %s dừng chia sẻ và abort request', async (code) => {
    tracking.sendLocation.mockRejectedValueOnce({ status: code })
    await sharing.start()
    success(fix())
    await flushPromises()
    expect(sharing.enabled.value).toBe(false)
    expect(geo.clearWatch).toHaveBeenCalledWith(0)
    expect(tracking.sendLocation.mock.calls[0][2].signal.aborted).toBe(true)
  })

  it('vẫn kiểm task khi đứng yên và dừng khi task đóng', async () => {
    await sharing.start()
    tasks.get.mockResolvedValueOnce({ status: TASK_STATUS.REPLACED })
    await vi.advanceTimersByTimeAsync(15000)
    expect(sharing.enabled.value).toBe(false)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('không có điểm mới quá tuổi thì báo mất tín hiệu, không POST định kỳ', async () => {
    await sharing.start()
    await vi.advanceTimersByTimeAsync(135000)
    expect(sharing.state.value).toBe(S.UNAVAILABLE)
    expect(tracking.sendLocation).not.toHaveBeenCalled()
  })

  it('stop/đổi task bỏ response cũ và callback cũ, phiên bật mới vẫn hoạt động', async () => {
    const pending = deferred()
    tracking.sendLocation.mockReturnValueOnce(pending.promise)
    await sharing.start()
    const oldCallback = success
    success(fix())
    id.value = 18
    await sharing.start()
    pending.resolve({ stored: true })
    oldCallback(fix())
    await flushPromises()
    expect(sharing.state.value).toBe(S.WAITING)
    expect(sharing.lastRecordedAt.value).toBeNull()
    success(fix())
    await flushPromises()
    expect(tracking.sendLocation.mock.calls.at(-1)[0]).toBe(18)
  })

  it('response kiểm task cũ không đóng phiên mới', async () => {
    const pending = deferred()
    tasks.get.mockReturnValueOnce(pending.promise)
    const starting = sharing.start()
    await flushPromises()
    sharing.stop()
    await sharing.start()
    pending.resolve({ status: TASK_STATUS.REPLACED })
    await starting
    expect(sharing.state.value).toBe(S.WAITING)
    expect(sharing.enabled.value).toBe(true)
  })

  it('đăng xuất dừng ngay trước khi request logout hoàn tất; unmount không còn timer', async () => {
    const pending = deferred()
    authService.logout.mockReturnValueOnce(pending.promise)
    await sharing.start()
    const logout = auth.logout()
    expect(sharing.enabled.value).toBe(false)
    expect(geo.clearWatch).toHaveBeenCalledWith(0)
    pending.resolve()
    await logout
    await sharing.start()
    expect(geo.watchPosition).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('taskStatus đóng hoặc unmount dọn mọi tài nguyên', async () => {
    await sharing.start()
    status.value = TASK_STATUS.REPLACED
    expect(sharing.enabled.value).toBe(false)
    status.value = TASK_STATUS.ACTIVE
    await sharing.start()
    wrapper.unmount()
    expect(vi.getTimerCount()).toBe(0)
    expect(geo.clearWatch).toHaveBeenCalledTimes(2)
  })
})
