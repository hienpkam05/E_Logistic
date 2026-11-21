// Nối http.js với store/router: phiên hết hạn, mật khẩu tạm, polling thông báo.
import { watch } from 'vue'
import { setPasswordChangeRequiredHandler, setUnauthorizedHandler } from '../services/http'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import { CHANGE_PASSWORD_ROUTE } from './guard'

export function installSessionHandlers(router) {
  const auth = useAuthStore()
  const notifications = useNotificationStore()

  // API trả 401 khi đang dùng: phiên hết hạn/bị khóa/đăng xuất nơi khác → về đăng nhập, giữ trang đang xem.
  setUnauthorizedHandler(() => {
    if (!auth.isAuthenticated) return
    auth.handleUnauthorized()
    const current = router.currentRoute.value
    router.push({ name: 'login', query: current.meta?.public ? {} : { next: current.fullPath } })
  })

  setPasswordChangeRequiredHandler(() => {
    auth.markPasswordChangeRequired()
    router.push({ name: CHANGE_PASSWORD_ROUTE })
  })

  watch(
    () => auth.isAuthenticated,
    (loggedIn) => (loggedIn ? notifications.startPolling() : notifications.stopPolling()),
    { immediate: true },
  )
}
