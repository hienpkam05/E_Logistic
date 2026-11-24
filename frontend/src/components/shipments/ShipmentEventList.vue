<script setup>
// Lịch sử vận đơn (UC05.4, UC05.7) — tự tải và phân trang. Màn cha gọi `reload()` sau mỗi thao tác đổi đơn.
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatVnd } from '../../utils/format'
import AppIcon from '../common/AppIcon.vue'
import PaginationBar from '../common/PaginationBar.vue'
import { SHIPMENT_ACTION as A, SHIPMENT_ORDERING, TASK_TYPE } from '../../utils/shipmentActions'

const props = defineProps({
  shipmentId: { type: [String, Number], required: true },
})

const meta = useMetaStore()
const events = ref([])
const page = ref(1)
const total = ref(0)
const hasNext = ref(false)
const hasPrevious = ref(false)
const error = ref('')
const loading = ref(false)
const hasTransport = ref(null)
const ordering = ref(SHIPMENT_ORDERING.NEWEST_FIRST)
const section = ref(null)
const SWAP_ACTIONS = new Set([A.SWAP_SHIPPER, A.CONFIRM_SWAP_HANDOVER, A.REPORT_SWAP_ISSUE, A.REPORT_SWAP_HANDOVER])
function taskLabel(event) {
  const labels = []
  if (event.task?.type === TASK_TYPE.DELIVERY && event.task.attempt_no) labels.push(`Lần giao ${event.task.attempt_no}`)
  if (event.task?.type === TASK_TYPE.PICKUP && event.task.pickup_no) labels.push(`Lần lấy ${event.task.pickup_no}`)
  if (SWAP_ACTIONS.has(event.action)) labels.push('Đổi Shipper')
  return labels.join(' · ')
}

// Tên trường trong `changes` của lịch sử (sửa yêu cầu, duyệt cấp mã…).
const FIELD_LABELS = {
  sender_name: 'Người gửi', sender_phone: 'SĐT người gửi', pickup_ward: 'Phường/xã lấy hàng',
  pickup_address: 'Địa chỉ lấy hàng', receiver_name: 'Người nhận', receiver_phone: 'SĐT người nhận',
  delivery_ward: 'Phường/xã giao hàng', delivery_address: 'Địa chỉ giao hàng',
  package_description: 'Mô tả hàng', package_count: 'Số kiện', weight_grams: 'Khối lượng (gram)',
  cod_amount: 'COD', note: 'Ghi chú', tracking_code: 'Mã vận đơn',
  // Spec 006: phân công / lấy hàng / nhập điểm tập kết ghi {id, name} → hiện tên.
  shipper: 'Shipper', holder: 'Người giữ hàng', discrepancy_note: 'Ghi chú sai lệch',
  swap_candidate: 'Shipper dự kiến',
  // Spec 007: phân công giao / kết quả giao.
  attempt_no: 'Lần giao', delivery_attempts: 'Số lần đã giao', cod_collected: 'COD đã thu',
}
const MONEY_FIELDS = new Set(['cod_amount', 'cod_collected'])

function shown(field, value) {
  if (value === null || value === undefined || value === '') return '(trống)'
  if (MONEY_FIELDS.has(field)) return formatVnd(value)
  if (typeof value === 'object' && value.name) return value.name
  return String(value)
}

function describe(event) {
  const lines = Object.entries(event.changes || {})
    .filter(([field]) => FIELD_LABELS[field])
    .map(([field, c]) => `${FIELD_LABELS[field]}: ${shown(field, c.from)} → ${shown(field, c.to)}`)
  if (event.reason) lines.push(`Lý do: ${event.reason}`)
  return lines
}

let requestId = 0
async function load(pageNumber = page.value) {
  const current = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await shipmentService.events(props.shipmentId, { page: pageNumber, ordering: ordering.value })
    if (current !== requestId) return
    events.value = data.results
    total.value = data.count
    hasNext.value = Boolean(data.next)
    hasPrevious.value = Boolean(data.previous)
    page.value = pageNumber
    hasTransport.value = data.has_transport_activity ?? null
    await nextTick()
    if (window.location.hash === '#shipment-history') section.value?.scrollIntoView?.({ block: 'start' })
  } catch (err) {
    if (current !== requestId) return
    error.value = err?.message || 'Chưa thể tải lịch sử.'
  } finally {
    if (current === requestId) loading.value = false
  }
}

/** Tải lại từ trang 1 (mốc mới nhất ở đầu). */
function reload() {
  return load(1)
}

watch(() => props.shipmentId, () => {
  events.value = []
  total.value = 0
  hasNext.value = false
  hasPrevious.value = false
  hasTransport.value = null
  ordering.value = SHIPMENT_ORDERING.NEWEST_FIRST
  reload()
}, { immediate: true })
onBeforeUnmount(() => { requestId++ })
defineExpose({ reload })
</script>

<template>
  <section id="shipment-history" ref="section" class="card" aria-labelledby="events-title" tabindex="-1">
    <h2 id="events-title" class="card__title"><span class="card__title-icon"><AppIcon name="clock" /></span>Lịch sử</h2>
    <label class="field">Thứ tự lịch sử
      <select v-model="ordering" :disabled="loading" @change="reload">
        <option :value="SHIPMENT_ORDERING.NEWEST_FIRST">Mới nhất trước</option>
        <option :value="SHIPMENT_ORDERING.OLDEST_FIRST">Cũ nhất trước</option>
      </select>
    </label>
    <p v-if="loading" class="loading" role="status">Đang tải lịch sử…</p>
    <div v-else-if="error" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ error }}</p><button type="button" class="btn btn--ghost btn--sm" @click="load()">Thử lại</button>
    </div>
    <p v-if="!loading && !error && hasTransport === false" class="alert alert--info" role="status">
      Chưa phát sinh vận chuyển — mốc lấy hàng sẽ hiện khi Nhân viên phân công.
    </p>
    <p v-if="!loading && !error && !events.length" class="muted">Chưa có mốc nào.</p>
    <ol v-if="!loading && !error && events.length" class="events">
      <li v-for="event in events" :key="event.id" class="events__item">
        <div class="events__head">
          <strong>{{ meta.label('shipment_actions', event.action) }}</strong>
          <time :datetime="event.created_at">{{ formatDateTime(event.created_at) }}</time>
        </div>
        <span class="muted">
          <template v-if="event.from_status && event.from_status !== event.to_status">
            {{ meta.label('shipment_statuses', event.from_status) }} →
          </template>
          {{ meta.label('shipment_statuses', event.to_status) }}
          · {{ event.actor ? event.actor.full_name : 'Hệ thống' }}
        </span>
        <span v-if="taskLabel(event)" class="pill pill--warning">{{ taskLabel(event) }}</span>
        <ul v-if="describe(event).length" class="events__changes">
          <li v-for="line in describe(event)" :key="line">{{ line }}</li>
        </ul>
      </li>
    </ol>
    <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total" unit="mốc"
                   @change="load" />
  </section>
</template>

<style scoped>
#shipment-history { scroll-margin-top: calc(var(--topbar-height) + 16px); }
</style>
