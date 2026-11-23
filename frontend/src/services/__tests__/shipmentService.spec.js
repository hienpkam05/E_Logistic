import { describe, expect, it } from 'vitest'
import { jsonResponse, mockFetch } from '../../test-utils'
import * as shipmentService from '../shipmentService'

const call = async (fn) => {
  const fetch = mockFetch(async () => jsonResponse(200, {}))
  await fn()
  const [url, init] = fetch.mock.calls[0]
  return { url, method: init.method, body: init.body ? JSON.parse(init.body) : undefined }
}

describe('shipmentService — khớp specs/004 api.md', () => {
  it('wards / list nhiều trạng thái / get', async () => {
    expect((await call(() => shipmentService.wards())).url).toBe('/api/v1/shipments/wards/')
    expect((await call(() => shipmentService.list({ status: ['PENDING_APPROVAL', 'CANCELLED'], q: '', page: 2 }))).url)
      .toBe('/api/v1/shipments/?status=PENDING_APPROVAL&status=CANCELLED&page=2')
    expect((await call(() => shipmentService.get(15))).url).toBe('/api/v1/shipments/15/')
  })

  it('create / update kèm updated_at / cancel / events', async () => {
    expect(await call(() => shipmentService.create({ receiver_name: 'B' })))
      .toEqual({ url: '/api/v1/shipments/', method: 'POST', body: { receiver_name: 'B' } })
    expect(await call(() => shipmentService.update(15, { note: 'x' }, '2026-11-21T10:00:00+07:00'))).toEqual({
      url: '/api/v1/shipments/15/', method: 'PATCH', body: { note: 'x', updated_at: '2026-11-21T10:00:00+07:00' },
    })
    expect(await call(() => shipmentService.cancel(15, 'Khách đổi ý')))
      .toEqual({ url: '/api/v1/shipments/15/cancel/', method: 'POST', body: { reason: 'Khách đổi ý' } })
    expect((await call(() => shipmentService.events(15, { page: 2 }))).url).toBe('/api/v1/shipments/15/events/?page=2')
  })

  it('điều phối lấy hàng kèm updated_at (spec 006)', async () => {
    const v = '2026-11-22T10:00:00+07:00'
    expect(await call(() => shipmentService.assignPickup(15, 7, v)))
      .toEqual({ url: '/api/v1/shipments/15/assign-pickup/', method: 'POST', body: { shipper_id: 7, updated_at: v } })
    expect(await call(() => shipmentService.receiveAtHub(15, 'Thiếu 1 kiện', v))).toEqual({
      url: '/api/v1/shipments/15/receive-at-hub/', method: 'POST', body: { discrepancy_note: 'Thiếu 1 kiện', updated_at: v },
    })
    expect(await call(() => shipmentService.retryPickup(15, 'Hẹn lại', v)))
      .toEqual({ url: '/api/v1/shipments/15/retry-pickup/', method: 'POST', body: { reason: 'Hẹn lại', updated_at: v } })
    expect(await call(() => shipmentService.abandonPickup(15, 'Shop đóng cửa', v))).toEqual({
      url: '/api/v1/shipments/15/abandon-pickup/', method: 'POST', body: { reason: 'Shop đóng cửa', updated_at: v },
    })
  })

  it('giao hàng — Nhân viên (spec 007)', async () => {
    const v = '2026-11-22T08:00:00.123456Z'
    expect(await call(() => shipmentService.assignDelivery(15, 7, v))).toEqual({
      url: '/api/v1/shipments/15/assign-delivery/', method: 'POST',
      body: { shipper_id: 7, handed_over: true, updated_at: v }, // D6: chỉ gọi sau khi NV tích "đã nhận hàng"
    })
    expect(await call(() => shipmentService.decideRedelivery(15, 'Khách hẹn lại', v))).toEqual({
      url: '/api/v1/shipments/15/decide-redelivery/', method: 'POST', body: { reason: 'Khách hẹn lại', updated_at: v },
    })
    expect(await call(() => shipmentService.decideReturn(15, 'Từ chối nhận', v))).toEqual({
      url: '/api/v1/shipments/15/decide-return/', method: 'POST', body: { reason: 'Từ chối nhận', updated_at: v },
    })
  })

  it('hoàn hàng — Nhân viên (spec 008)', async () => {
    const v = '2026-11-23T08:00:00.123456Z'
    expect(await call(() => shipmentService.assignReturn(15, 7, v)))
      .toEqual({ url: '/api/v1/shipments/15/assign-return/', method: 'POST', body: { shipper_id: 7, updated_at: v } })
    expect(await call(() => shipmentService.receiveReturn(15, 'Móp hộp', v))).toEqual({
      url: '/api/v1/shipments/15/receive-return/', method: 'POST', body: { discrepancy_note: 'Móp hộp', updated_at: v },
    })
    expect(await call(() => shipmentService.reportReturnIssue(15, 'Thiếu 1 kiện', v))).toEqual({
      url: '/api/v1/shipments/15/report-return-issue/', method: 'POST', body: { reason: 'Thiếu 1 kiện', updated_at: v },
    })
    expect(await call(() => shipmentService.confirmShopReceived(15, 'Chị Hoa', '', v))).toEqual({
      url: '/api/v1/shipments/15/confirm-shop-received/', method: 'POST',
      body: { receiver_name: 'Chị Hoa', verified: true, note: '', updated_at: v }, // D7: chỉ gọi sau khi NV tích
    })
  })

  it('Nhân viên: list lọc ngày + sắp xếp; duyệt / từ chối kèm updated_at (spec 005)', async () => {
    expect((await call(() => shipmentService.list({
      status: ['PENDING_APPROVAL'], createdFrom: '2026-11-01', createdTo: '2026-11-21', ordering: 'created_at',
    }))).url).toBe('/api/v1/shipments/?status=PENDING_APPROVAL&created_from=2026-11-01&created_to=2026-11-21&ordering=created_at')
    expect((await call(() => shipmentService.list({ q: 'shop' }))).url).toBe('/api/v1/shipments/?q=shop')
    expect(await call(() => shipmentService.approve(15, '2026-11-21T10:00:00+07:00'))).toEqual({
      url: '/api/v1/shipments/15/approve/', method: 'POST', body: { updated_at: '2026-11-21T10:00:00+07:00' },
    })
    expect(await call(() => shipmentService.reject(15, 'Thiếu số nhà', '2026-11-21T10:00:00+07:00'))).toEqual({
      url: '/api/v1/shipments/15/reject/', method: 'POST',
      body: { reason: 'Thiếu số nhà', updated_at: '2026-11-21T10:00:00+07:00' },
    })
  })
})
