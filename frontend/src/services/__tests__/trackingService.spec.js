import { afterEach, describe, expect, it, vi } from 'vitest'
import { jsonResponse, mockFetch } from '../../test-utils'
import * as tracking from '../trackingService'
import * as tasks from '../taskService'

afterEach(() => vi.unstubAllGlobals())
describe('GPS services', () => {
  it('mã hóa id, gửi đúng payload và giữ signal qua API client chung', async () => {
    const fetch = mockFetch(async () => jsonResponse(201, { stored: true }))
    const controller = new AbortController()
    const point = { lat: 21, lng: 105, accuracy: 12, recorded_at: '2026-11-24T01:00:00Z' }
    await tracking.sendLocation('a/b', point, { signal: controller.signal })
    const [url, init] = fetch.mock.calls[0]
    expect(url).toBe('/api/v1/dispatch/tasks/a%2Fb/locations/')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual(point)
    expect(init.signal).toBe(controller.signal)
    expect(init.credentials).toBe('same-origin')
    await tracking.getLocation(5, { signal: controller.signal })
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/shipments/5/location/')
    expect(fetch.mock.calls[1][1].signal).toBe(controller.signal)
    await tasks.get(6, { signal: controller.signal })
    expect(fetch.mock.calls[2][1].signal).toBe(controller.signal)
  })
})
