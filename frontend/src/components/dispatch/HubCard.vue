<script setup>
// Thẻ điểm tập kết (spec 008 D6): Shipper biết mang hàng hoàn về đâu (UC04.8 bước 3), Shop biết đến đâu nhận lại hàng.
// Dữ liệu lấy từ meta.hub (cấu hình backend .env) — một nguồn, không viết địa chỉ ở màn hình.
import { computed } from 'vue'
import { useMetaStore } from '../../stores/meta'
import { formatPhone } from '../../utils/format'
import AppIcon from '../common/AppIcon.vue'

const props = defineProps({
  title: { type: String, default: 'Điểm tập kết' },
  callLabel: { type: String, default: 'Gọi điểm tập kết' },
})
const meta = useMetaStore()
const hub = computed(() => meta.hub)
</script>

<template>
  <article v-if="hub" class="card">
    <h2 class="card__title"><span class="card__title-icon"><AppIcon name="warehouse" /></span>{{ props.title }}</h2>
    <p class="hub__name">{{ hub.name }}</p>
    <p class="hub__address">{{ hub.address }}</p>
    <div v-if="hub.phone" class="hub__contact">
      <span>{{ formatPhone(hub.phone) }}</span>
      <a :href="`tel:${hub.phone}`" class="btn btn--outline btn--sm"><AppIcon name="phone" :size="16" />{{ props.callLabel }}</a>
    </div>
    <slot />
  </article>
</template>

<style scoped>
.hub__name { margin: 0 0 4px; font-weight: 600; font-size: 1.0625rem; }
.hub__address { margin: 0 0 12px; }
.hub__contact { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; color: var(--muted); }
</style>
