import { describe, expect, it } from 'vitest'
import { jsonResponse, mockFetch } from '../../test-utils'
import * as accountService from '../accountService'

const call = async (fn) => {
  const fetch = mockFetch(async () => jsonResponse(200, {}))
  await fn()
  const [url, init] = fetch.mock.calls[0]
  return { url, method: init.method, body: init.body ? JSON.parse(init.body) : undefined }
}

describe('accountService — khớp specs/003 api.md', () => {
  it('list: đổi tên tham số, bỏ giá trị rỗng', async () => {
    expect((await call(() => accountService.list({ role: 'SHIPPER', isActive: false, q: '', page: 2 }))).url)
      .toBe('/api/v1/accounts/users/?role=SHIPPER&is_active=false&page=2')
  })

  it('create / get', async () => {
    expect(await call(() => accountService.create({ username: 'a' })))
      .toEqual({ url: '/api/v1/accounts/users/', method: 'POST', body: { username: 'a' } })
    expect((await call(() => accountService.get(7))).url).toBe('/api/v1/accounts/users/7/')
  })

  it('update gửi kèm updated_at đã tải', async () => {
    expect(await call(() => accountService.update(7, { phone: '0912345678' }, '2026-11-21T09:00:00+07:00'))).toEqual({
      url: '/api/v1/accounts/users/7/', method: 'PATCH',
      body: { phone: '0912345678', updated_at: '2026-11-21T09:00:00+07:00' },
    })
  })

  it('lock / unlock / reset-password / events', async () => {
    expect(await call(() => accountService.lock(7, 'Nghỉ việc')))
      .toEqual({ url: '/api/v1/accounts/users/7/lock/', method: 'POST', body: { reason: 'Nghỉ việc' } })
    expect((await call(() => accountService.unlock(7))).url).toBe('/api/v1/accounts/users/7/unlock/')
    expect((await call(() => accountService.resetPassword(7))).body).toEqual({ identity_verified: true })
    expect((await call(() => accountService.events(7, { page: 2 }))).url).toBe('/api/v1/accounts/users/7/events/?page=2')
  })
})
