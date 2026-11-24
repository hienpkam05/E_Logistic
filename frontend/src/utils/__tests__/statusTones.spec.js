import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { SHIPMENT_STATUS, TASK_STATUS, STATUS_TONES, TONES, toneOf } from '../statusTones'

// Đối chiếu với mã trạng thái thật ở backend (đọc thẳng constants.py, không chạy backend).
// Vitest chạy từ thư mục frontend/.
const BACKEND_APPS = resolve(process.cwd(), '..', 'backend', 'apps')

function backendCodes(file, className) {
  const source = readFileSync(resolve(BACKEND_APPS, file), 'utf8')
  const block = source.split(`class ${className}(models.TextChoices):`)[1].split(/\n\S/)[0]
  return [...block.matchAll(/^\s+([A-Z_]+) = "/gm)].map((m) => m[1])
}

describe('statusTones', () => {
  it('TASK_STATUS của spec 009 khớp TaskStatus backend và có tông màu', () => {
    const codes = backendCodes('dispatch/constants.py', 'TaskStatus')
    expect(Object.keys(TASK_STATUS).sort()).toEqual(['ACTIVE', 'PENDING_SWAP_HANDOVER', 'REPLACED'])
    for (const [key, value] of Object.entries(TASK_STATUS)) {
      expect(value).toBe(key)
      expect(codes).toContain(value)
      expect(STATUS_TONES.task_statuses[value]).toBeDefined()
    }
  })

  it.each([
    ['shipment_statuses', 'shipments/constants.py', 'ShipmentStatus'],
    ['task_statuses', 'dispatch/constants.py', 'TaskStatus'],
  ])('%s khớp đủ mã backend', (group, file, className) => {
    const codes = backendCodes(file, className)
    expect(codes.length).toBeGreaterThan(3)
    expect(Object.keys(STATUS_TONES[group]).sort()).toEqual([...codes].sort())
    expect(Object.values(STATUS_TONES[group]).every((tone) => TONES.includes(tone))).toBe(true)
  })

  it('SHIPMENT_STATUS chỉ chứa mã trạng thái thật (key = value)', () => {
    for (const [key, value] of Object.entries(SHIPMENT_STATUS)) {
      expect(key).toBe(value)
      expect(Object.keys(STATUS_TONES.shipment_statuses)).toContain(value)
    }
  })

  it('mã lạ -> neutral', () => {
    expect(toneOf('shipment_statuses', 'MA_MOI')).toBe('neutral')
    expect(toneOf('nhom_la', 'X')).toBe('neutral')
  })
})
