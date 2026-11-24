<script setup>
// Chọn Shipper khi phân công (UC06.5 bước 2–3, spec 006 D10): Shipper đang hoạt động, ít việc trước,
// kèm số nhiệm vụ đang mở để chia việc. v-model = id Shipper được chọn (hoặc null).
// `holder` (spec 007 D7): giao lại khi hàng đang ở Shipper này → chỉ được chọn đúng người đó, không tải danh sách;
// đổi người cần bàn giao về điểm tập kết (đổi Shipper — spec 009).
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import * as dispatchService from '../../services/dispatchService'
import { formatPhone, initials } from '../../utils/format'
import AppIcon from '../common/AppIcon.vue'

const SEARCH_DELAY_MS = 250 // gõ liên tục chỉ gọi API khi ngừng gõ

const props = defineProps({
  disabled: { type: Boolean, default: false },
  holder: { type: Object, default: null }, // { id, username, full_name, phone }
  exclude: { type: Number, default: null }, // spec 009: id người cũ, không được chọn lại
})
const model = defineModel({ type: Number, default: null })

const name = useId()
const query = ref('')
const items = ref([])
const visibleItems = computed(() => items.value.filter((shipper) => shipper.id !== props.exclude))
const loading = ref(false)
const error = ref('')
const searched = computed(() => Boolean(query.value.trim()))

let requestId = 0
async function load() {
  const current = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await dispatchService.shippers({ q: query.value.trim() || undefined })
    if (current !== requestId) return
    items.value = data
  } catch (err) {
    if (current !== requestId) return
    items.value = []
    error.value = err?.message || 'Chưa tải được danh sách Shipper.'
  } finally {
    if (current === requestId) loading.value = false
  }
}

let timer = null
watch([model, () => props.exclude, () => props.holder?.id], ([value, excluded, holderId]) => {
  if (holderId != null) {
    const next = holderId === excluded ? null : holderId
    if (value !== next) model.value = next
  } else if (value != null && value === excluded) {
    model.value = null
  }
}, { immediate: true })
watch(query, () => {
  clearTimeout(timer)
  timer = setTimeout(load, SEARCH_DELAY_MS)
})
onMounted(() => {
  if (!props.holder) load()
})
onBeforeUnmount(() => clearTimeout(timer))

function workload(count) {
  return count ? `${count} nhiệm vụ đang mở` : 'Đang rảnh'
}
</script>

<template>
  <div v-if="props.holder" class="picker">
    <label v-if="props.holder.id !== props.exclude" class="picker__item is-selected">
      <input type="radio" :name="name" :value="props.holder.id" checked disabled />
      <span class="picker__avatar" aria-hidden="true">{{ initials(props.holder.full_name || props.holder.username) }}</span>
      <span class="picker__who">
        <strong>{{ props.holder.full_name }}</strong>
        <span class="picker__sub">{{ props.holder.username }} · {{ formatPhone(props.holder.phone) }}</span>
      </span>
    </label>
    <p v-else class="picker__empty muted" role="status">Không có Shipper phù hợp để chọn.</p>
    <p class="picker__note muted">
      Hàng đang ở Shipper này nên giao lại phải dùng đúng người đang giữ. Muốn đổi người cần bàn giao hàng về điểm
      tập kết (đổi Shipper).
    </p>
  </div>

  <div v-else class="picker">
    <div class="search picker__search">
      <AppIcon name="search" :size="18" />
      <input v-model="query" type="search" aria-label="Tìm Shipper" placeholder="Tìm tên, tên đăng nhập, SĐT"
             :disabled="props.disabled" />
    </div>

    <p v-if="loading && !visibleItems.length" class="loading" role="status"><span class="spinner" />Đang tải Shipper…</p>
    <div v-else-if="error" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ error }}</p>
      <button type="button" class="btn btn--ghost btn--sm" @click="load">Tải lại</button>
    </div>
    <p v-else-if="!visibleItems.length" class="picker__empty muted" role="status">
      <template v-if="searched || props.exclude != null">Không tìm thấy Shipper phù hợp.</template>
      <!-- UC06.5 A1 -->
      <template v-else>Không có Shipper đang hoạt động. Giữ đơn ở Chờ lấy hàng và phân công sau.</template>
    </p>

    <div v-else class="picker__list" role="radiogroup" aria-label="Chọn Shipper">
      <label v-for="s in visibleItems" :key="s.id" class="picker__item" :class="{ 'is-selected': model === s.id }">
        <input v-model="model" type="radio" :name="name" :value="s.id" :disabled="props.disabled" />
        <span class="picker__avatar" aria-hidden="true">{{ initials(s.full_name || s.username) }}</span>
        <span class="picker__who">
          <strong>{{ s.full_name }}</strong>
          <span class="picker__sub">{{ s.username }} · {{ formatPhone(s.phone) }}</span>
        </span>
        <span class="picker__load" :class="{ 'picker__load--free': !s.open_task_count }">
          {{ workload(s.open_task_count) }}
        </span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.picker { display: flex; flex-direction: column; gap: 12px; }
.picker__search { max-width: none; flex: none; }
.picker__note { margin: 0; font-size: .875rem; }
.picker__empty { margin: 0; padding: 16px; text-align: center; background: var(--surface-muted); border-radius: var(--radius-sm); }
.picker__list { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
.picker__item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px; cursor: pointer;
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface);
}
.picker__item:hover { border-color: var(--brand); }
.picker__item.is-selected { border-color: var(--brand); background: var(--brand-softer); box-shadow: var(--focus-ring); }
.picker__item input { accent-color: var(--brand); }
.picker__avatar {
  display: grid; place-items: center; width: 34px; height: 34px; flex-shrink: 0; border-radius: 50%;
  font-size: .75rem; font-weight: 700; color: var(--brand); background: var(--brand-soft);
}
.picker__who { display: flex; flex-direction: column; min-width: 0; }
.picker__sub { font-size: .8125rem; color: var(--muted); }
.picker__load {
  margin-left: auto; padding: 2px 10px; border-radius: 999px; white-space: nowrap; font-size: .8125rem;
  color: var(--tone-warning-fg); background: var(--tone-warning-bg);
}
.picker__load--free { color: var(--tone-success-fg); background: var(--tone-success-bg); }
</style>
