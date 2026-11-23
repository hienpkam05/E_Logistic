<script setup>
// Trang chủ Shipper: ô số nhiệm vụ đang làm theo loại (spec 006 lấy, spec 007 D11 giao) — count của danh sách mở.
import { onMounted, reactive } from 'vue'
import HighlightTile from '../../components/common/HighlightTile.vue'
import RoleHome from '../../components/common/RoleHome.vue'
import * as taskService from '../../services/taskService'
import { TASK_TYPE } from '../../utils/shipmentActions'

const upcoming = ['Chia sẻ vị trí khi làm nhiệm vụ']

const TILES = [
  { type: TASK_TYPE.DELIVERY, icon: 'truck', label: 'nhiệm vụ giao hàng đang làm',
    zeroHint: 'Chưa có đơn cần giao', activeHint: 'Bấm để xem người nhận và COD' },
  { type: TASK_TYPE.PICKUP, icon: 'package', label: 'nhiệm vụ lấy hàng đang làm',
    zeroHint: 'Chưa có nhiệm vụ mới', activeHint: 'Bấm để xem địa chỉ lấy hàng' },
  { type: TASK_TYPE.RETURN, icon: 'warehouse', label: 'nhiệm vụ hoàn hàng đang làm',  // spec 008
    zeroHint: 'Chưa có hàng cần hoàn', activeHint: 'Bấm để xem hàng cần đưa về điểm tập kết' },
]
const counts = reactive(Object.fromEntries(TILES.map((t) => [t.type, { value: null, error: false }])))

onMounted(() => Promise.all(TILES.map(async ({ type }) => {
  try {
    counts[type].value = (await taskService.list({ type, open: true })).count
  } catch {
    counts[type].error = true
  }
})))
</script>

<template>
  <RoleHome :upcoming="upcoming">
    <template #highlights>
      <div class="home-tiles">
        <HighlightTile v-for="t in TILES" :key="t.type" :to="{ name: 'shipper-tasks', query: { type: t.type } }"
                       :icon="t.icon" :label="t.label" :value="counts[t.type].value" :error="counts[t.type].error"
                       :zero-hint="t.zeroHint" :active-hint="t.activeHint" />
      </div>
    </template>
  </RoleHome>
</template>

<style scoped>
.home-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
</style>
