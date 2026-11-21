// Số thông báo chưa đọc: tải khi đăng nhập, định kỳ khi tab đang hiển thị (spec 002 D8).
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { NOTIFICATION_POLL_MS } from '../config'
import * as notificationService from '../services/notificationService'

const isVisible = () => typeof document === 'undefined' || document.visibilityState === 'visible'

export const useNotificationStore = defineStore('notifications', () => {
  const unreadCount = ref(0)
  let timer = null

  async function refreshCount() {
    try {
      unreadCount.value = (await notificationService.unreadCount()).count
    } catch {
      // Giữ số cũ; lỗi phiên đã được http.js xử lý chung.
    }
  }

  function onVisibilityChange() {
    if (isVisible()) refreshCount()
  }

  function startPolling() {
    if (timer) return
    refreshCount()
    timer = setInterval(() => {
      if (isVisible()) refreshCount()
    }, NOTIFICATION_POLL_MS)
    document.addEventListener('visibilitychange', onVisibilityChange)
  }

  function stopPolling() {
    if (timer) clearInterval(timer)
    timer = null
    document.removeEventListener('visibilitychange', onVisibilityChange)
    unreadCount.value = 0
  }

  async function markRead(notification) {
    const updated = await notificationService.markRead(notification.id)
    if (!notification.is_read && unreadCount.value > 0) unreadCount.value -= 1
    return updated
  }

  async function markAllRead() {
    const result = await notificationService.markAllRead()
    unreadCount.value = 0
    return result
  }

  return { unreadCount, refreshCount, startPolling, stopPolling, markRead, markAllRead }
})
