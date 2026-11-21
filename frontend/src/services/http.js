// API client duy nhất của frontend. Mọi lời gọi backend đi qua đây.
// Định dạng lỗi backend: specs/001-nen-tang/api.md#định-dạng-lỗi

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '')
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
const CSRF_COOKIE = 'csrftoken'

// Mã lỗi backend mà frontend xử lý riêng (khớp ErrorCode ở backend/apps/core/errors.py).
export const API_ERROR = Object.freeze({
  NOT_AUTHENTICATED: 'NOT_AUTHENTICATED',
  PASSWORD_CHANGE_REQUIRED: 'PASSWORD_CHANGE_REQUIRED',
  CONFLICT: 'CONFLICT',
})

// Mã lỗi chỉ phát sinh phía client (backend không trả các mã này).
export const CLIENT_ERROR = {
  NETWORK_ERROR: {
    code: 'NETWORK_ERROR',
    message: 'Không kết nối được máy chủ. Vui lòng kiểm tra mạng và thử lại.',
  },
  BAD_RESPONSE: {
    code: 'SERVER_ERROR',
    message: 'Hệ thống gặp lỗi. Vui lòng thử lại sau.',
  },
}

// Xử lý phiên dùng chung, do app đăng ký (tránh import vòng http ↔ store/router).
let unauthorizedHandler = null
let passwordChangeRequiredHandler = null

/** Gọi khi API trả 401 (phiên hết hạn, bị khóa, đã đăng xuất nơi khác). */
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

/** Gọi khi API trả 403 PASSWORD_CHANGE_REQUIRED. */
export function setPasswordChangeRequiredHandler(fn) {
  passwordChangeRequiredHandler = fn
}

export class ApiError extends Error {
  constructor({ status, code, message, fields = {} }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

function readCookie(name) {
  if (typeof document === 'undefined') return null
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

function buildUrl(path, params) {
  const url = `${BASE_URL}/${String(path).replace(/^\/+/, '')}`
  if (!params) return url
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item))
    else query.append(key, value)
  }
  const qs = query.toString()
  return qs ? `${url}?${qs}` : url
}

// skipSessionHandlers: dùng cho login/logout/khôi phục phiên — tự xử lý 401, không kích hoạt handler chung.
export async function request(path, { method = 'GET', params, body, signal, skipSessionHandlers = false } = {}) {
  method = method.toUpperCase()
  const headers = { Accept: 'application/json' }
  let payload

  if (body !== undefined) {
    if (body instanceof FormData) {
      payload = body
    } else {
      headers['Content-Type'] = 'application/json'
      payload = JSON.stringify(body)
    }
  }
  if (!SAFE_METHODS.has(method)) {
    const token = readCookie(CSRF_COOKIE)
    if (token) headers['X-CSRFToken'] = token
  }

  let response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: payload,
      credentials: 'same-origin',
      signal,
    })
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    throw new ApiError({ status: 0, ...CLIENT_ERROR.NETWORK_ERROR })
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const error = data?.error
    const apiError = new ApiError({
      status: response.status,
      code: error?.code || CLIENT_ERROR.BAD_RESPONSE.code,
      message: error?.message || CLIENT_ERROR.BAD_RESPONSE.message,
      fields: error?.fields || {},
    })
    if (!skipSessionHandlers) {
      if (apiError.status === 401) unauthorizedHandler?.(apiError)
      else if (apiError.code === API_ERROR.PASSWORD_CHANGE_REQUIRED) passwordChangeRequiredHandler?.(apiError)
    }
    throw apiError
  }
  return data
}

export const http = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
}
