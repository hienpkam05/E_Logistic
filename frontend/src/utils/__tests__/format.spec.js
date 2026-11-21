import { describe, expect, it } from 'vitest'
import { formatDateTime, formatPhone, formatVnd } from '../format'

const normalize = (s) => s.replace(/ | /g, ' ')

describe('format', () => {
  it('formatVnd', () => {
    expect(normalize(formatVnd(200000))).toBe('200.000 ₫')
    expect(normalize(formatVnd(0))).toBe('0 ₫')
    expect(normalize(formatVnd('150000'))).toBe('150.000 ₫')
    expect(formatVnd(null)).toBe('')
    expect(formatVnd('abc')).toBe('')
  })

  it('formatDateTime luôn theo giờ Việt Nam', () => {
    const text = normalize(formatDateTime('2026-11-20T02:30:00Z'))
    expect(text).toContain('20/11/2026')
    expect(text).toContain('09:30')
    expect(formatDateTime('khong-phai-ngay')).toBe('')
    expect(formatDateTime(null)).toBe('')
  })

  it('formatPhone', () => {
    expect(formatPhone('0901234567')).toBe('0901 234 567')
    expect(formatPhone('123')).toBe('123')
    expect(formatPhone('')).toBe('')
  })
})
