import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiError, jsonResponse, mockFetch } from '../../test-utils'
import {
  ApiError,
  http,
  setPasswordChangeRequiredHandler,
  setUnauthorizedHandler,
} from '../http'

afterEach(() => {
  setUnauthorizedHandler(null)
  setPasswordChangeRequiredHandler(null)
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
})

describe('http client', () => {
  it('GET trả JSON, gửi cookie phiên cùng origin', async () => {
    const fetch = mockFetch(async () => jsonResponse(200, { ok: 1 }))
    expect(await http.get('/meta/choices/')).toEqual({ ok: 1 })
    const [url, init] = fetch.mock.calls[0]
    expect(url).toBe('/api/v1/meta/choices/')
    expect(init.credentials).toBe('same-origin')
    expect(init.method).toBe('GET')
  })

  it('ghép params: bỏ giá trị rỗng, lặp mảng', async () => {
    const fetch = mockFetch(async () => jsonResponse(200, {}))
    await http.get('/a/', { params: { status: ['X', 'Y'], q: '', page: 2, n: null, u: undefined } })
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/a/?status=X&status=Y&page=2')
  })

  it('POST gửi JSON + X-CSRFToken từ cookie; GET không gửi CSRF', async () => {
    document.cookie = 'csrftoken=abc%3D'
    const fetch = mockFetch(async () => jsonResponse(200, {}))
    await http.post('/a/', { x: 1 })
    let init = fetch.mock.calls[0][1]
    expect(init.headers['X-CSRFToken']).toBe('abc=')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.body).toBe('{"x":1}')
    await http.get('/a/')
    init = fetch.mock.calls[1][1]
    expect(init.headers['X-CSRFToken']).toBeUndefined()
  })

  it('đọc lại cookie CSRF ở mỗi request (Django xoay token sau đăng nhập)', async () => {
    const fetch = mockFetch(async () => jsonResponse(200, {}))
    document.cookie = 'csrftoken=cu'
    await http.post('/a/')
    document.cookie = 'csrftoken=moi'
    await http.post('/a/')
    expect(fetch.mock.calls.map((c) => c[1].headers['X-CSRFToken'])).toEqual(['cu', 'moi'])
  })

  it('204 trả null', async () => {
    mockFetch(async () => new Response(null, { status: 204 }))
    expect(await http.delete('/a/')).toBeNull()
  })

  it('lỗi backend -> ApiError đúng code/message/fields', async () => {
    mockFetch(async () => apiError(400, 'VALIDATION_ERROR', 'Dữ liệu chưa hợp lệ.', { phone: ['Sai'] }))
    const err = await http.post('/a/', {}).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { phone: ['Sai'] } })
  })

  it('lỗi không phải JSON -> SERVER_ERROR giữ HTTP status', async () => {
    mockFetch(async () => new Response('<html>Bad gateway</html>', { status: 502 }))
    const err = await http.get('/a/').catch((e) => e)
    expect(err).toMatchObject({ status: 502, code: 'SERVER_ERROR' })
    expect(err.message).toBeTruthy()
  })

  it('mất mạng -> NETWORK_ERROR status 0', async () => {
    mockFetch(async () => { throw new TypeError('fetch failed') })
    await expect(http.get('/a/')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 })
  })

  it('hủy request giữ nguyên AbortError', async () => {
    mockFetch(async () => { throw Object.assign(new Error('aborted'), { name: 'AbortError' }) })
    await expect(http.get('/a/')).rejects.toMatchObject({ name: 'AbortError' })
  })

  describe('handler phiên', () => {
    it('401 gọi unauthorized handler', async () => {
      const onUnauthorized = vi.fn()
      setUnauthorizedHandler(onUnauthorized)
      mockFetch(async () => apiError(401, 'NOT_AUTHENTICATED'))
      await http.get('/a/').catch(() => {})
      expect(onUnauthorized).toHaveBeenCalledOnce()
    })

    it('403 PASSWORD_CHANGE_REQUIRED gọi handler riêng, 403 khác thì không', async () => {
      const onPassword = vi.fn()
      setPasswordChangeRequiredHandler(onPassword)
      mockFetch(async () => apiError(403, 'PASSWORD_CHANGE_REQUIRED'))
      await http.get('/a/').catch(() => {})
      mockFetch(async () => apiError(403, 'PERMISSION_DENIED'))
      await http.get('/a/').catch(() => {})
      expect(onPassword).toHaveBeenCalledOnce()
    })

    it('skipSessionHandlers không kích hoạt handler (dùng cho login/khôi phục phiên)', async () => {
      const onUnauthorized = vi.fn()
      setUnauthorizedHandler(onUnauthorized)
      mockFetch(async () => apiError(401, 'NOT_AUTHENTICATED'))
      await expect(http.get('/a/', { skipSessionHandlers: true })).rejects.toMatchObject({ status: 401 })
      expect(onUnauthorized).not.toHaveBeenCalled()
    })
  })
})
