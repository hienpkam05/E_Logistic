// Enum + giới hạn nghiệp vụ lấy từ backend. Nguồn nhãn duy nhất cho giao diện —
// component không tự viết nhãn trạng thái/vai trò.
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getChoices } from '../services/metaService'

export const useMetaStore = defineStore('meta', () => {
  const choices = ref(null)
  const loading = ref(false)
  const error = ref(null)
  let pending = null

  const ready = computed(() => choices.value !== null)
  const limits = computed(() => choices.value?.limits ?? {})

  // { group: Map(value -> item) } để tra cứu O(1).
  const index = computed(() => {
    const result = {}
    for (const [group, items] of Object.entries(choices.value ?? {})) {
      if (Array.isArray(items)) result[group] = new Map(items.map((item) => [item.value, item]))
    }
    return result
  })

  // Tải một lần; các lời gọi đồng thời dùng chung một request.
  function load({ force = false } = {}) {
    if (choices.value && !force) return Promise.resolve(choices.value)
    if (pending) return pending
    loading.value = true
    error.value = null
    pending = getChoices()
      .then((data) => {
        choices.value = data
        return data
      })
      .catch((err) => {
        error.value = err
        throw err
      })
      .finally(() => {
        loading.value = false
        pending = null
      })
    return pending
  }

  function options(group) {
    return choices.value?.[group] ?? []
  }

  // Chưa tải xong hoặc mã lạ: trả lại chính mã đó để không hiển thị rỗng.
  function label(group, value) {
    if (value === null || value === undefined || value === '') return ''
    return index.value[group]?.get(value)?.label ?? String(value)
  }

  function isTerminal(value, group = 'shipment_statuses') {
    return index.value[group]?.get(value)?.terminal === true
  }

  return { choices, loading, error, ready, limits, load, options, label, isTerminal }
})
