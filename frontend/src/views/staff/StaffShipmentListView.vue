<script setup>
// UC05.9 — danh sách vận đơn của Nhân viên (toàn hệ thống).
// Tab GIAI ĐOẠN (spec 008 D10, gộp các tab hàng việc của spec 005–007): mỗi tab gồm các trạng thái Nhân viên cần
// xử lý, cũ nhất trước; chip con lọc một trạng thái trong giai đoạn. Tab Tất cả: mới nhất trước, lọc mọi trạng thái.
// Nhãn lấy từ /meta/choices/ (giai đoạn = nhãn loại nhiệm vụ) — không viết chữ ở đây.
// Mọi bộ lọc nằm trên URL: ?tab=<key>&status=&q=&from=&to=&page=
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import PaginationBar from '../../components/common/PaginationBar.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import { usePagedList } from '../../composables/usePagedList'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatPhone, formatVnd } from '../../utils/format'
import { SHIPMENT_ORDERING, TASK_TYPE } from '../../utils/shipmentActions'
import { SHIPMENT_STATUS } from '../../utils/statusTones'

const S = SHIPMENT_STATUS
// key trên URL → các trạng thái của giai đoạn (đúng thứ tự xử lý). Tab đầu là mặc định (không có ?tab).
// `type`: nhãn tab lấy theo loại nhiệm vụ; không có `type` → nhãn của trạng thái duy nhất.
const QUEUES = [
  { key: 'pending', statuses: [S.PENDING_APPROVAL] },
  { key: 'pickup', type: TASK_TYPE.PICKUP, statuses: [S.AWAITING_PICKUP, S.PICKUP_FAILED, S.PICKED_UP] },
  { key: 'delivery', type: TASK_TYPE.DELIVERY, statuses: [S.AT_HUB, S.AWAITING_REDELIVERY, S.DELIVERY_FAILED] },
  { key: 'return', type: TASK_TYPE.RETURN, statuses: [S.AWAITING_RETURN, S.RETURNING, S.AWAITING_SHOP_PICKUP] },
]
const ALL = 'all'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const text = (key) => (typeof route.query[key] === 'string' ? route.query[key] : '')
const queue = computed(() => QUEUES.find((item) => item.key === route.query.tab)
  ?? (route.query.tab === ALL ? null : QUEUES[0]))
const tab = computed(() => queue.value?.key ?? ALL)
const queueTab = computed(() => queue.value !== null)
const pendingTab = computed(() => queue.value?.key === QUEUES[0].key)
// Trong tab giai đoạn chỉ nhận trạng thái thuộc giai đoạn đó (link lạ → cả giai đoạn).
const status = computed(() => {
  const value = text('status')
  return !queueTab.value || queue.value.statuses.includes(value) ? value : ''
})
const tabLabel = (item) => (item.type ? meta.label('task_types', item.type) : meta.label('shipment_statuses', item.statuses[0]))
const subStatuses = computed(() => (queueTab.value && queue.value.statuses.length > 1 ? queue.value.statuses : []))
const q = computed(() => text('q'))
const from = computed(() => text('from'))
const to = computed(() => text('to'))
const page = computed(() => Math.max(1, Number.parseInt(route.query.page, 10) || 1))
// Chip trạng thái trong giai đoạn không tính là "bộ lọc" (vẫn là hàng việc).
const filtered = computed(() => Boolean((queueTab.value ? '' : status.value) || q.value || from.value || to.value))
const statusOptions = computed(() => meta.options('shipment_statuses'))

const searchText = ref(q.value)
const { items, total, hasNext, hasPrevious, loading, error: loadError, load } = usePagedList(() => {
  const statuses = status.value ? [status.value] : queueTab.value ? queue.value.statuses : undefined
  return shipmentService.list({
    status: statuses,
    q: q.value || undefined,
    createdFrom: from.value || undefined,
    createdTo: to.value || undefined,
    ordering: queueTab.value ? SHIPMENT_ORDERING.OLDEST_FIRST : SHIPMENT_ORDERING.NEWEST_FIRST,
    page: page.value,
  })
})

function push(query) {
  router.push({ name: 'staff-shipments', query: Object.fromEntries(Object.entries(query).filter(([, v]) => v)) })
}

// Tab mặc định không ghi lên URL.
const tabParam = (key) => (key === QUEUES[0].key ? '' : key)

// Đổi bộ lọc thì về trang 1 (bỏ page).
function setQuery(patch) {
  push({ tab: tabParam(tab.value), status: status.value, q: q.value, from: from.value, to: to.value, ...patch })
}

function setTab(next) {
  setQuery({ tab: tabParam(next), status: '' })
}

function goPage(next) {
  router.push({ name: 'staff-shipments', query: { ...route.query, page: next > 1 ? String(next) : undefined } })
}

function clearFilters() {
  searchText.value = ''
  push({ tab: tabParam(tab.value) })
}

watch(q, (value) => { searchText.value = value })
watch([tab, status, q, from, to, page], load, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="staff-shipments-title">
    <h1 id="staff-shipments-title" class="sr-only">Quản lý vận đơn</h1>

    <div class="toolbar">
      <form class="search" role="search" @submit.prevent="setQuery({ q: searchText.trim() })">
        <AppIcon name="search" :size="20" />
        <input v-model="searchText" type="search" :maxlength="meta.limits.search_query_max_length"
               aria-label="Từ khóa tìm kiếm" placeholder="Tìm mã, người nhận, tên/SĐT Shop" />
      </form>
      <span class="toolbar__spacer" />
      <label class="date-filter">
        <span>Từ ngày</span>
        <input type="date" :value="from" :max="to || undefined" @change="setQuery({ from: $event.target.value })" />
      </label>
      <label class="date-filter">
        <span>Đến ngày</span>
        <input type="date" :value="to" :min="from || undefined" @change="setQuery({ to: $event.target.value })" />
      </label>
    </div>

    <div class="data-card">
      <div class="data-card__head">
        <div class="tabs" role="group" aria-label="Hàng việc">
          <button v-for="item in QUEUES" :key="item.key" type="button" class="tabs__item"
                  :aria-pressed="tab === item.key" @click="setTab(item.key)">{{ tabLabel(item) }}</button>
          <button type="button" class="tabs__item" :aria-pressed="!queueTab" @click="setTab(ALL)">Tất cả</button>
        </div>
        <label v-if="!queueTab" class="filter-select">
          <AppIcon name="filter" :size="16" />
          <span class="sr-only">Lọc theo trạng thái</span>
          <select :value="status" @change="setQuery({ status: $event.target.value })">
            <option value="">Mọi trạng thái</option>
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </label>
        <span v-else class="muted hint">Cũ nhất trước — xử lý theo thứ tự đến</span>
        <div v-if="subStatuses.length" class="chips" role="group" aria-label="Trạng thái trong giai đoạn">
          <button type="button" class="chip" :aria-pressed="!status" @click="setQuery({ status: '' })">Tất cả</button>
          <button v-for="s in subStatuses" :key="s" type="button" class="chip" :aria-pressed="status === s"
                  @click="setQuery({ status: s })">{{ meta.label('shipment_statuses', s) }}</button>
        </div>
        <span v-if="!loading && !loadError" class="data-card__count">
          {{ total }} {{ pendingTab ? 'yêu cầu chờ duyệt' : 'vận đơn' }}
        </span>
      </div>

      <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải danh sách…</p>

      <div v-else-if="loadError" class="empty-state" role="alert">
        <span class="empty-state__icon"><AppIcon name="alert" :size="26" /></span>
        <p class="empty-state__title">Chưa tải được danh sách</p>
        <p>{{ loadError }}</p>
        <div class="form__actions">
          <button type="button" class="btn btn--primary" @click="load"><AppIcon name="reload" :size="16" />Tải lại</button>
          <button v-if="filtered" type="button" class="btn btn--ghost" @click="clearFilters">Bỏ lọc</button>
        </div>
      </div>

      <div v-else-if="!items.length" class="empty-state">
        <span class="empty-state__icon"><AppIcon :name="filtered ? 'search' : 'check'" :size="26" /></span>
        <template v-if="filtered">
          <p class="empty-state__title">Không có kết quả phù hợp với bộ lọc.</p>
          <button type="button" class="btn btn--ghost" @click="clearFilters">Bỏ lọc</button>
        </template>
        <p v-else-if="pendingTab" class="empty-state__title">Không có yêu cầu nào đang chờ duyệt.</p>
        <p v-else-if="queueTab" class="empty-state__title">Không có vận đơn nào cần xử lý ở bước này.</p>
        <p v-else class="empty-state__title">Chưa có vận đơn nào.</p>
      </div>

      <template v-else>
        <div class="table-wrap">
          <table class="table table--stack">
            <thead>
              <tr>
                <th>Mã</th><th>Shop</th><th>Người nhận</th><th>Giao đến</th><th class="num">Thu hộ</th>
                <th>Trạng thái</th><th>Ngày tạo</th><th class="cell-actions">Xem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in items" :key="s.id">
                <td data-label="Mã">
                  <RouterLink :to="{ name: 'staff-shipment-detail', params: { id: s.id } }">{{ s.tracking_code || s.request_code }}</RouterLink>
                  <span v-if="!s.tracking_code" class="cell-sub">mã yêu cầu</span>
                </td>
                <td data-label="Shop">{{ s.shop?.full_name }}<span class="cell-sub">{{ s.shop?.username }}</span></td>
                <td data-label="Người nhận">{{ s.receiver_name }}<span class="cell-sub">{{ formatPhone(s.receiver_phone) }}</span></td>
                <td data-label="Giao đến">{{ s.delivery_ward?.name }}</td>
                <td class="num" data-label="Thu hộ">{{ s.cod_amount ? formatVnd(s.cod_amount) : '—' }}</td>
                <td data-label="Trạng thái"><StatusBadge :value="s.status" /></td>
                <td data-label="Ngày tạo">{{ formatDateTime(s.created_at) }}</td>
                <td class="cell-actions" data-label="Xem">
                  <RouterLink :to="{ name: 'staff-shipment-detail', params: { id: s.id } }" class="row-action"
                              :aria-label="`Xem ${s.tracking_code || s.request_code}`">
                    <AppIcon name="eye" :size="18" />
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hasNext || hasPrevious" class="data-card__foot">
          <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total"
                         :unit="pendingTab ? 'yêu cầu' : 'vận đơn'" @change="goPage" />
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.date-filter { display: flex; align-items: center; gap: 8px; font-size: .875rem; color: var(--muted); white-space: nowrap; }
.date-filter input {
  font: inherit; color: var(--text); padding: 8px 10px; border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm); background: var(--surface);
}
.date-filter input:focus { outline: none; border-color: var(--brand); box-shadow: var(--focus-ring); }
.hint { font-size: .875rem; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; flex-basis: 100%; }
.chip {
  padding: 5px 12px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface);
  font: inherit; font-size: .8125rem; color: var(--text); cursor: pointer;
}
.chip:hover { border-color: var(--brand); }
.chip[aria-pressed='true'] { border-color: var(--brand); background: var(--brand); color: var(--brand-contrast); }
@media (max-width: 640px) {
  .toolbar__spacer { display: none; }
  .date-filter { flex: 1 1 calc(50% - 6px); flex-direction: column; align-items: stretch; gap: 4px; }
  .date-filter input { width: 100%; }
}
</style>
