<script setup>
// Thanh phân trang dùng chung cho danh sách phân trang của API (count/next/previous).
import AppIcon from './AppIcon.vue'

const props = defineProps({
  page: { type: Number, required: true },
  hasPrevious: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false },
  total: { type: Number, default: null },
  unit: { type: String, default: 'mục' },
})
const emit = defineEmits(['change'])

function go(delta) {
  emit('change', props.page + delta)
}
</script>

<template>
  <nav v-if="hasPrevious || hasNext" class="pagination" aria-label="Phân trang">
    <span class="pagination__info">Trang {{ page }}<template v-if="total !== null"> · {{ total }} {{ unit }}</template></span>
    <div class="pagination__buttons">
      <button type="button" class="btn btn--ghost btn--sm" :disabled="!hasPrevious" @click="go(-1)">
        <AppIcon name="chevron-left" :size="16" /> Trang trước
      </button>
      <button type="button" class="btn btn--ghost btn--sm" :disabled="!hasNext" @click="go(1)">
        Trang sau <AppIcon name="chevron-right" :size="16" />
      </button>
    </div>
  </nav>
</template>

<style scoped>
.pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.pagination__info { color: var(--muted); font-size: .875rem; }
.pagination__buttons { display: flex; gap: 8px; }
</style>
