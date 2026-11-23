<script setup>
// UC04.1 / UC04.4 — nhiệm vụ của Shipper (lấy + giao). Bộ lọc loại (?type=) và tab Đang làm / Đã xong (?done=1)
// nằm trên URL. Thiết kế cho điện thoại: mỗi nhiệm vụ một thẻ bấm được cả khối; thẻ giao hiện người nhận + COD.
import { computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import PaginationBar from '../../components/common/PaginationBar.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import { usePagedList } from '../../composables/usePagedList'
import * as taskService from '../../services/taskService'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatVnd } from '../../utils/format'
import { TASK_TYPE } from '../../utils/shipmentActions'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const TYPES = Object.values(TASK_TYPE)
const type = computed(() => (TYPES.includes(route.query.type) ? route.query.type : ''))
const done = computed(() => route.query.done === '1')
const page = computed(() => Math.max(1, Number.parseInt(route.query.page, 10) || 1))
const typeFilters = computed(() => [
  { value: '', label: 'Tất cả' },
  ...TYPES.map((value) => ({ value, label: meta.label('task_types', value) })),
])
const isDelivery = (task) => task.type === TASK_TYPE.DELIVERY
const isReturn = (task) => task.type === TASK_TYPE.RETURN

const { items, total, hasNext, hasPrevious, loading, error, load } = usePagedList(
  () => taskService.list({ type: type.value || undefined, open: !done.value, page: page.value }),
  'Chưa thể tải nhiệm vụ.')

function go(query) {
  const merged = { type: type.value || undefined, done: done.value ? '1' : undefined, ...query }
  router.push({ name: 'shipper-tasks', query: Object.fromEntries(Object.entries(merged).filter(([, v]) => v)) })
}

const setType = (value) => go({ type: value || undefined, page: undefined })
const setTab = (isDone) => go({ done: isDone ? '1' : undefined, page: undefined })
const goPage = (next) => go({ page: next > 1 ? String(next) : undefined })

const emptyTitle = computed(() => {
  const kind = type.value ? meta.label('task_types', type.value).toLowerCase() : ''
  return done.value ? 'Chưa có nhiệm vụ đã xong.' : `Chưa có nhiệm vụ${kind ? ` ${kind}` : ''}.`
})

watch([type, done, page], load, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="tasks-title">
    <div class="page__header">
      <h1 id="tasks-title">Nhiệm vụ</h1>
      <button type="button" class="btn btn--ghost btn--sm" :disabled="loading" @click="load">
        <AppIcon name="reload" :size="16" />Tải lại
      </button>
    </div>

    <div class="filters">
      <div class="chips" role="group" aria-label="Loại nhiệm vụ">
        <button v-for="f in typeFilters" :key="f.value || 'all'" type="button" class="chip"
                :aria-pressed="type === f.value" @click="setType(f.value)">{{ f.label }}</button>
      </div>
      <div class="tabs" role="group" aria-label="Nhóm nhiệm vụ">
        <button type="button" class="tabs__item" :aria-pressed="!done" @click="setTab(false)">Đang làm</button>
        <button type="button" class="tabs__item" :aria-pressed="done" @click="setTab(true)">Đã xong</button>
      </div>
    </div>

    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải nhiệm vụ…</p>

    <div v-else-if="error" class="card empty-state" role="alert">
      <span class="empty-state__icon"><AppIcon name="alert" :size="26" /></span>
      <p class="empty-state__title">Chưa tải được nhiệm vụ</p>
      <p>{{ error }}</p>
      <button type="button" class="btn btn--primary" @click="load"><AppIcon name="reload" :size="16" />Tải lại</button>
    </div>

    <!-- UC04.1 A1, UC04.4 A1: chưa được phân công -->
    <div v-else-if="!items.length" class="card empty-state">
      <span class="empty-state__icon"><AppIcon name="inbox" :size="26" /></span>
      <p class="empty-state__title">{{ emptyTitle }}</p>
      <p v-if="!done">Khi Nhân viên phân công, nhiệm vụ sẽ hiện ở đây. Bấm Tải lại để kiểm tra.</p>
    </div>

    <template v-else>
      <p class="muted count">{{ total }} nhiệm vụ</p>
      <ul class="task-list">
        <li v-for="task in items" :key="task.id">
          <RouterLink :to="{ name: 'shipper-task-detail', params: { id: task.id } }" class="task-card"
                      :class="{ 'task-card--delivery': isDelivery(task) }">
            <div class="task-card__head">
              <span class="task-card__type">
                {{ meta.label('task_types', task.type) }}
                <template v-if="task.attempt_no"> · lần {{ task.attempt_no }}/{{ meta.limits.max_delivery_attempts }}</template>
              </span>
              <StatusBadge group="task_statuses" :value="task.status" />
            </div>
            <strong class="task-card__code">{{ task.shipment.tracking_code }}</strong>
            <template v-if="isDelivery(task)">
              <div class="task-card__who"><AppIcon name="user" :size="16" />{{ task.shipment.receiver_name }}</div>
              <div class="task-card__address">
                <AppIcon name="map-pin" :size="16" />
                <span>{{ task.shipment.delivery_address }}, {{ task.shipment.delivery_ward?.name }}</span>
              </div>
            </template>
            <!-- Hoàn (spec 008): hàng của Shop nào, đưa về điểm tập kết nào -->
            <template v-else-if="isReturn(task)">
              <div class="task-card__who"><AppIcon name="user" :size="16" />{{ task.shipment.shop_name }}</div>
              <div v-if="meta.hub" class="task-card__address">
                <AppIcon name="warehouse" :size="16" /><span>Về {{ meta.hub.name }}</span>
              </div>
            </template>
            <template v-else>
              <div class="task-card__who"><AppIcon name="user" :size="16" />{{ task.shipment.shop_name }}</div>
              <div class="task-card__address">
                <AppIcon name="map-pin" :size="16" />
                <span>{{ task.shipment.pickup_address }}, {{ task.shipment.pickup_ward?.name }}</span>
              </div>
            </template>
            <div class="task-card__foot">
              <span v-if="isDelivery(task)" class="task-card__cod">
                <AppIcon name="wallet" :size="14" />
                {{ task.shipment.cod_amount ? `COD ${formatVnd(task.shipment.cod_amount)}` : 'Không thu hộ' }}
              </span>
              <span v-else><AppIcon name="box" :size="14" /> {{ task.shipment.package_count }} kiện</span>
              <span v-if="isReturn(task) && task.handover_reported_at && !task.closed_at" class="task-card__flag">
                Đã báo đưa về — chờ xác nhận
              </span>
              <span>Phân công {{ formatDateTime(task.assigned_at) }}</span>
            </div>
          </RouterLink>
        </li>
      </ul>
      <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total" unit="nhiệm vụ"
                     @change="goPage" />
    </template>
  </section>
</template>

<style scoped>
.page__header { align-items: center; }
.filters { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  padding: 6px 14px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface);
  font: inherit; font-size: .875rem; color: var(--text); cursor: pointer;
}
.chip:hover { border-color: var(--brand); }
.chip[aria-pressed='true'] { border-color: var(--brand); background: var(--brand); color: var(--brand-contrast); }
.count { margin: 0; font-size: .875rem; }
.task-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.task-card {
  display: flex; flex-direction: column; gap: 8px; padding: 16px 18px; color: var(--text); text-decoration: none;
  background: var(--surface); border: 1px solid var(--border); border-left: 4px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow-sm); transition: border-color .15s, box-shadow .15s;
}
.task-card--delivery { border-left-color: var(--brand); }
.task-card:hover { text-decoration: none; border-color: var(--brand); box-shadow: var(--shadow); }
.task-card__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.task-card__type { font-size: .75rem; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; color: var(--muted); }
.task-card--delivery .task-card__type { color: var(--brand); }
.task-card__code { color: var(--brand); font-size: 1.0625rem; }
.task-card__who, .task-card__address { display: flex; align-items: flex-start; gap: 8px; }
.task-card__who .icon, .task-card__address .icon { margin-top: 3px; color: var(--muted); }
.task-card__address { font-weight: 500; }
.task-card__foot { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; font-size: .8125rem; color: var(--muted); }
.task-card__foot span { display: inline-flex; align-items: center; gap: 4px; }
.task-card__cod { font-weight: 600; color: var(--text); }
.task-card__flag { padding: 1px 8px; border-radius: 999px; color: var(--tone-info-fg); background: var(--tone-info-bg); }
@media (max-width: 640px) { .task-list { grid-template-columns: 1fr; } }
</style>
