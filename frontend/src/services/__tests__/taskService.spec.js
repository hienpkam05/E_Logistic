import { describe, expect, it } from 'vitest'
import { jsonResponse, mockFetch } from '../../test-utils'
import * as dispatchService from '../dispatchService'
import * as taskService from '../taskService'

const call = async (fn) => {
  const fetch = mockFetch(async () => jsonResponse(200, {}))
  await fn()
  const [url, init] = fetch.mock.calls[0]
  return { url, method: init.method, body: init.body ? JSON.parse(init.body) : undefined }
}

describe('taskService / dispatchService — khớp specs/006, 007 api.md', () => {
  it('danh sách / chi tiết nhiệm vụ', async () => {
    expect((await call(() => taskService.list({ open: true, page: 2 }))).url).toBe('/api/v1/dispatch/tasks/?open=true&page=2')
    expect((await call(() => taskService.list({ open: false }))).url).toBe('/api/v1/dispatch/tasks/?open=false')
    expect((await call(() => taskService.list())).url).toBe('/api/v1/dispatch/tasks/')
    expect((await call(() => taskService.get(31))).url).toBe('/api/v1/dispatch/tasks/31/')
    expect((await call(() => taskService.list({ type: 'DELIVERY', open: true }))).url)
      .toBe('/api/v1/dispatch/tasks/?type=DELIVERY&open=true')
  })

  it('Shipper ghi kết quả lấy hàng', async () => {
    expect(await call(() => taskService.confirmPickup(31)))
      .toEqual({ url: '/api/v1/dispatch/tasks/31/confirm-pickup/', method: 'POST', body: undefined })
    expect(await call(() => taskService.failPickup(31, 'OTHER', 'Cổng khóa'))).toEqual({
      url: '/api/v1/dispatch/tasks/31/fail-pickup/', method: 'POST', body: { reason_code: 'OTHER', note: 'Cổng khóa' },
    })
  })

  it('Shipper ghi kết quả giao (spec 007)', async () => {
    expect(await call(() => taskService.confirmDelivery(31, 350000))).toEqual({
      url: '/api/v1/dispatch/tasks/31/confirm-delivery/', method: 'POST', body: { cod_collected: 350000 },
    })
    expect((await call(() => taskService.confirmDelivery(31, 0))).body).toEqual({ cod_collected: 0 }) // không COD
    expect(await call(() => taskService.failDelivery(31, 'RECEIVER_REFUSED'))).toEqual({
      url: '/api/v1/dispatch/tasks/31/fail-delivery/', method: 'POST', body: { reason_code: 'RECEIVER_REFUSED', note: '' },
    })
  })

  it('Shipper báo đã đưa hàng hoàn về (spec 008)', async () => {
    expect(await call(() => taskService.reportReturnHandover(61)))
      .toEqual({ url: '/api/v1/dispatch/tasks/61/report-return-handover/', method: 'POST', body: undefined })
    expect((await call(() => taskService.list({ type: 'RETURN' }))).url).toBe('/api/v1/dispatch/tasks/?type=RETURN')
  })

  it('danh sách Shipper để phân công', async () => {
    expect((await call(() => dispatchService.shippers())).url).toBe('/api/v1/dispatch/shippers/')
    expect((await call(() => dispatchService.shippers({ q: 'long' }))).url).toBe('/api/v1/dispatch/shippers/?q=long')
  })
})
