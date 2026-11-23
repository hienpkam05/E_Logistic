<script setup>
// Ô số liệu nổi bật ở trang chủ vai trò (vd "N yêu cầu chờ duyệt", "N nhiệm vụ đang làm"). Bấm để mở danh sách.
// value: số (null = đang tải); error: không tải được (ô vẫn bấm được). attention: tô màu cần chú ý khi > 0.
import { RouterLink } from 'vue-router'
import AppIcon from './AppIcon.vue'

defineProps({
  to: { type: Object, required: true },
  icon: { type: String, required: true },
  label: { type: String, required: true },
  value: { type: Number, default: null },
  error: { type: Boolean, default: false },
  zeroHint: { type: String, default: '' },
  activeHint: { type: String, default: '' },
})
</script>

<template>
  <RouterLink :to="to" class="highlight" :class="{ 'highlight--attention': value }">
    <span class="highlight__icon"><AppIcon :name="icon" :size="24" /></span>
    <span class="highlight__text">
      <strong class="highlight__value">
        <template v-if="error">—</template>
        <template v-else-if="value === null">…</template>
        <template v-else>{{ value }}</template>
      </strong>
      <span>{{ label }}</span>
      <span v-if="error" class="highlight__hint">Chưa tải được số liệu — bấm để mở danh sách</span>
      <span v-else-if="value === 0 && zeroHint" class="highlight__hint">{{ zeroHint }}</span>
      <span v-else-if="value && activeHint" class="highlight__hint">{{ activeHint }}</span>
    </span>
    <AppIcon name="chevron-right" class="highlight__arrow" />
  </RouterLink>
</template>

<style scoped>
.highlight {
  display: flex; align-items: center; gap: 16px; padding: 20px 24px; color: var(--text); text-decoration: none;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-sm);
  transition: border-color .15s, box-shadow .15s;
}
.highlight:hover { text-decoration: none; border-color: var(--brand); box-shadow: var(--shadow); }
.highlight--attention { border-color: var(--tone-warning-border); background: var(--tone-warning-bg); }
.highlight__icon {
  display: grid; place-items: center; width: 52px; height: 52px; flex-shrink: 0; border-radius: 14px;
  color: var(--brand-contrast); background: var(--brand);
}
.highlight--attention .highlight__icon { background: var(--tone-warning-fg); }
.highlight__text { display: flex; flex-direction: column; }
.highlight__value { font-size: 1.75rem; line-height: 1.1; }
.highlight__hint { font-size: .8125rem; color: var(--muted); }
.highlight__arrow { margin-left: auto; color: var(--subtle); }
</style>
