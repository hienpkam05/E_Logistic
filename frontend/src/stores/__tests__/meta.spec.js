import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CHOICES } from '../../test-utils'
import { getChoices } from '../../services/metaService'
import { useMetaStore } from '../meta'

vi.mock('../../services/metaService', () => ({ getChoices: vi.fn() }))

beforeEach(() => {
  setActivePinia(createPinia())
  getChoices.mockReset()
})

describe('store meta', () => {
  it('tải đúng một lần cho nhiều lời gọi đồng thời và lần sau', async () => {
    getChoices.mockResolvedValue(CHOICES)
    const meta = useMetaStore()
    const [a, b] = await Promise.all([meta.load(), meta.load()])
    await meta.load()
    expect(getChoices).toHaveBeenCalledOnce()
    expect(a).toBe(b)
    expect(meta.ready).toBe(true)
  })

  it('label, isTerminal, options, limits', async () => {
    getChoices.mockResolvedValue(CHOICES)
    const meta = useMetaStore()
    await meta.load()
    expect(meta.label('shipment_statuses', 'AWAITING_SHOP_PICKUP')).toBe('Chờ Shop đến lấy')
    expect(meta.label('shipment_statuses', 'MA_MOI')).toBe('MA_MOI')
    expect(meta.label('shipment_statuses', '')).toBe('')
    expect(meta.isTerminal('DELIVERED')).toBe(true)
    expect(meta.isTerminal('AT_HUB')).toBe(false)
    expect(meta.isTerminal('REPLACED', 'task_statuses')).toBe(true)
    expect(meta.options('user_roles')).toHaveLength(3)
    expect(meta.limits.max_delivery_attempts).toBe(3)
  })

  it('lỗi tải: lưu error, lần sau tải lại được', async () => {
    getChoices.mockRejectedValueOnce(new Error('mất mạng')).mockResolvedValueOnce(CHOICES)
    const meta = useMetaStore()
    await expect(meta.load()).rejects.toThrow('mất mạng')
    expect(meta.error).toBeTruthy()
    await meta.load({ force: true })
    expect(meta.error).toBeNull()
    expect(meta.ready).toBe(true)
  })
})
