import { describe, expect, it } from 'vitest'
import { fieldErrors, generalMessage } from '../formErrors'

describe('formErrors', () => {
  it('gộp nhiều thông điệp của một trường, bỏ non_field_errors', () => {
    const err = { fields: { phone: ['Sai.', 'Trùng.'], name: 'Bắt buộc.', non_field_errors: ['Chung'] } }
    expect(fieldErrors(err)).toEqual({ phone: 'Sai. Trùng.', name: 'Bắt buộc.' })
    expect(fieldErrors(null)).toEqual({})
  })

  it('thông điệp chung ưu tiên non_field_errors', () => {
    expect(generalMessage({ message: 'Dữ liệu chưa hợp lệ.', fields: { non_field_errors: ['A', 'B'] } })).toBe('A B')
    expect(generalMessage({ message: 'Lỗi', fields: {} })).toBe('Lỗi')
    expect(generalMessage(null)).toBe('')
  })
})
