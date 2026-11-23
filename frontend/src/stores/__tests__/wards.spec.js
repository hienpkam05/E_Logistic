import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as shipmentService from '../../services/shipmentService'
import { useWardStore } from '../wards'

vi.mock('../../services/shipmentService', () => ({ wards: vi.fn() }))

const WARDS = [{ code: 'A', name: 'Phường A' }, { code: 'B', name: 'Xã B' }]

beforeEach(() => {
  setActivePinia(createPinia())
  shipmentService.wards.mockReset()
})

describe('store wards', () => {
  it('tải một lần cho nhiều lời gọi; tra theo mã', async () => {
    shipmentService.wards.mockResolvedValue(WARDS)
    const store = useWardStore()
    await Promise.all([store.load(), store.load()])
    await store.load()
    expect(shipmentService.wards).toHaveBeenCalledOnce()
    expect(store.byCode.get('B').name).toBe('Xã B')
  })

  it('lỗi: giữ error, tải lại được', async () => {
    shipmentService.wards.mockRejectedValueOnce(new Error('mất mạng')).mockResolvedValueOnce(WARDS)
    const store = useWardStore()
    await expect(store.load()).rejects.toThrow()
    expect(store.error).toBeTruthy()
    await store.load({ force: true })
    expect(store.ready).toBe(true)
    expect(store.error).toBeNull()
  })
})
