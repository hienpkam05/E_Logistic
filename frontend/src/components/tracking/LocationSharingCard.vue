<script setup>
import { computed } from 'vue'
import { useLocationSharing } from '../../composables/useLocationSharing'
import { useMetaStore } from '../../stores/meta'
import { LOCATION_SHARING_LABEL } from '../../utils/location'
import { formatDateTime } from '../../utils/format'
const props = defineProps({ taskId: { type: [Number, String], required: true }, taskStatus: { type: String, required: true } })
const emit = defineEmits(['task-updated'])
const meta = useMetaStore()
const { enabled, state, message, lastRecordedAt, start, stop } = useLocationSharing(() => props.taskId,
  { taskStatus: () => props.taskStatus, onTask: (task) => emit('task-updated', task) })
const label = computed(() => LOCATION_SHARING_LABEL[state.value])
</script>
<template>
  <article class="card location-sharing" aria-label="Chia sẻ vị trí">
    <h2 class="card__title">Chia sẻ vị trí</h2>
    <p>Chỉ chia sẻ khi làm nhiệm vụ. Shop của đơn và Nhân viên xem được điểm gần nhất.</p>
    <p class="muted">Bạn có thể tắt bất cứ lúc nào; rời màn hình hoặc kết thúc nhiệm vụ sẽ dừng chia sẻ.
      <template v-if="meta.limits.location_retention_days">Dữ liệu được dọn theo thời hạn {{ meta.limits.location_retention_days }} ngày.</template>
    </p>
    <p role="status">{{ label }}</p>
    <p v-if="message" class="alert alert--info" role="status">{{ message }}</p>
    <p v-if="lastRecordedAt" class="muted">Điểm đã gửi: {{ formatDateTime(lastRecordedAt) }}</p>
    <div class="form__actions">
      <button v-if="!enabled" type="button" class="btn btn--primary" @click="start">Bật chia sẻ vị trí</button>
      <button v-else type="button" class="btn btn--outline" @click="stop()">Tắt chia sẻ vị trí</button>
    </div>
  </article>
</template>
<style scoped>
.location-sharing { display: grid; gap: 12px; }
.location-sharing p { margin: 0; }
</style>
