<script setup>
// Nhãn trạng thái: chữ lấy từ backend (store meta), màu lấy từ utils/statusTones.
import { computed } from 'vue'
import { useMetaStore } from '../../stores/meta'
import { toneOf } from '../../utils/statusTones'

const props = defineProps({
  group: { type: String, default: 'shipment_statuses' },
  value: { type: String, default: '' },
})

const meta = useMetaStore()
const text = computed(() => meta.label(props.group, props.value))
const tone = computed(() => toneOf(props.group, props.value))
</script>

<template>
  <span v-if="value" class="status-badge" :class="`status-badge--${tone}`" :data-status="value">{{ text }}</span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
  color: var(--tone-fg);
  background: var(--tone-bg);
  border: 1px solid var(--tone-border);
}
.status-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status-badge--neutral { --tone-fg: var(--tone-neutral-fg); --tone-bg: var(--tone-neutral-bg); --tone-border: var(--tone-neutral-border); }
.status-badge--info { --tone-fg: var(--tone-info-fg); --tone-bg: var(--tone-info-bg); --tone-border: var(--tone-info-border); }
.status-badge--warning { --tone-fg: var(--tone-warning-fg); --tone-bg: var(--tone-warning-bg); --tone-border: var(--tone-warning-border); }
.status-badge--success { --tone-fg: var(--tone-success-fg); --tone-bg: var(--tone-success-bg); --tone-border: var(--tone-success-border); }
.status-badge--danger { --tone-fg: var(--tone-danger-fg); --tone-bg: var(--tone-danger-bg); --tone-border: var(--tone-danger-border); }
</style>
