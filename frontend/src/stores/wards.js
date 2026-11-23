// Danh mục phường/xã Hà Nội (spec 004 D1): tải một lần mỗi phiên, dùng chung cho mọi form địa chỉ.
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as shipmentService from '../services/shipmentService'

export const useWardStore = defineStore('wards', () => {
  const items = ref(null)
  const loading = ref(false)
  const error = ref(null)
  let pending = null

  const ready = computed(() => items.value !== null)
  const byCode = computed(() => new Map((items.value ?? []).map((w) => [w.code, w])))

  function load({ force = false } = {}) {
    if (items.value && !force) return Promise.resolve(items.value)
    if (pending) return pending
    loading.value = true
    error.value = null
    pending = shipmentService
      .wards()
      .then((data) => {
        items.value = data
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

  return { items, loading, error, ready, byCode, load }
})
