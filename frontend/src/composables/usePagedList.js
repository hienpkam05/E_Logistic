// Danh sách phân trang của API (count/next/previous): trạng thái tải, lỗi, và chặn phản hồi cũ về muộn
// (người dùng đổi bộ lọc liên tục thì chỉ kết quả của lần gọi mới nhất được hiển thị).
import { ref } from 'vue'

/**
 * @param fetchPage () => Promise<{results, count, next, previous}> — đọc bộ lọc hiện tại (thường từ route).
 * @param fallbackError thông điệp khi lỗi không có message.
 */
export function usePagedList(fetchPage, fallbackError = 'Chưa thể tải danh sách.') {
  const items = ref([])
  const total = ref(0)
  const hasNext = ref(false)
  const hasPrevious = ref(false)
  const loading = ref(false)
  const error = ref('')

  let requestId = 0
  async function load() {
    const current = ++requestId
    loading.value = true
    error.value = ''
    try {
      const data = await fetchPage()
      if (current !== requestId) return
      items.value = data.results
      total.value = data.count
      hasNext.value = Boolean(data.next)
      hasPrevious.value = Boolean(data.previous)
    } catch (err) {
      if (current !== requestId) return
      items.value = []
      error.value = err?.message || fallbackError
    } finally {
      if (current === requestId) loading.value = false
    }
  }

  return { items, total, hasNext, hasPrevious, loading, error, load }
}
