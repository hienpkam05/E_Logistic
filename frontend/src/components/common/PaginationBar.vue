<script setup>
// Thanh phân trang dùng chung cho danh sách phân trang của API (count/next/previous).
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
    <button type="button" class="btn btn--ghost" :disabled="!hasPrevious" @click="go(-1)">Trang trước</button>
    <span>Trang {{ page }}<template v-if="total !== null"> · {{ total }} {{ unit }}</template></span>
    <button type="button" class="btn btn--ghost" :disabled="!hasNext" @click="go(1)">Trang sau</button>
  </nav>
</template>

<style scoped>
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; flex-wrap: wrap; }
</style>
