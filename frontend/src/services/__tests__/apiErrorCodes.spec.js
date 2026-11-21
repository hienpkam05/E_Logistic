import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { API_ERROR } from '../http'

// Mã lỗi frontend xử lý riêng phải tồn tại ở backend (core/errors.py), tránh lệch khi đổi tên.
describe('API_ERROR khớp backend', () => {
  it('mọi mã có trong ErrorCode', () => {
    const source = readFileSync(resolve(process.cwd(), '..', 'backend', 'apps', 'core', 'errors.py'), 'utf8')
    for (const code of Object.values(API_ERROR)) {
      expect(source, code).toMatch(new RegExp(`^\\s+${code} = `, 'm'))
    }
  })
})
