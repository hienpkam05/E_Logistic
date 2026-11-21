// Trạng thái phiên đăng nhập. Vai trò luôn lấy từ backend (UC01.1 BR2).
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authService from '../services/authService'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  // unknown: chưa hỏi backend; authenticated / anonymous: đã biết.
  const status = ref('unknown')
  const restoreError = ref(null)
  let restoring = null

  const isAuthenticated = computed(() => status.value === 'authenticated')
  const role = computed(() => user.value?.role ?? null)
  const mustChangePassword = computed(() => user.value?.must_change_password === true)

  function setUser(data) {
    user.value = data
    status.value = data ? 'authenticated' : 'anonymous'
  }

  function clearLocal() {
    user.value = null
    status.value = 'anonymous'
  }

  // Hỏi backend phiên hiện tại một lần khi mở app (UC01.1 A1). Lời gọi đồng thời dùng chung request.
  function restore() {
    if (status.value !== 'unknown') return Promise.resolve(user.value)
    if (restoring) return restoring
    restoring = authService
      .getMe()
      .then((data) => {
        restoreError.value = null
        setUser(data)
        return data
      })
      .catch((err) => {
        // 401: chưa đăng nhập. Lỗi khác (mất mạng…): coi như chưa đăng nhập, giữ lỗi để màn hình báo.
        restoreError.value = err?.status === 401 ? null : err
        clearLocal()
        return null
      })
      .finally(() => {
        restoring = null
      })
    return restoring
  }

  async function login(username, password) {
    await authService.fetchCsrf()
    const data = await authService.login(username, password)
    restoreError.value = null
    setUser(data)
    return data
  }

  /**
   * Luôn xóa trạng thái cục bộ, kể cả khi mất mạng (UC01.2 E1).
   * Trả { serverConfirmed } để màn hình báo nếu máy chủ chưa xác nhận.
   */
  async function logout() {
    let serverConfirmed = true
    try {
      await authService.logout()
    } catch {
      serverConfirmed = false
    }
    clearLocal()
    return { serverConfirmed }
  }

  // Phiên hết hạn / bị khóa phát hiện qua API 401: chỉ xóa cục bộ, không gọi lại backend.
  function handleUnauthorized() {
    clearLocal()
  }

  function markPasswordChangeRequired() {
    if (user.value) user.value = { ...user.value, must_change_password: true }
  }

  return {
    user, status, restoreError,
    isAuthenticated, role, mustChangePassword,
    restore, login, logout, setUser, handleUnauthorized, markPasswordChangeRequired,
  }
})
