<script setup>
// Thẻ "Điều phối" ở chi tiết vận đơn của Nhân viên (UC05.7 bước 4): người giữ hàng, Shipper phụ trách,
// số lần giao, lịch sử nhiệm vụ. Cảnh báo khi Shipper của nhiệm vụ đang mở đã bị khóa (spec 006 D9) hoặc Shipper
// đang giữ hàng đã bị khóa (spec 007 D7 — chờ đổi Shipper).
import { computed } from 'vue'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatPhone, formatVnd } from '../../utils/format'
import { FAIL_REASON_GROUP } from '../../utils/shipmentActions'
import AppIcon from '../common/AppIcon.vue'
import StatusBadge from '../common/StatusBadge.vue'
import { SHIPMENT_ACTION as A, can } from '../../utils/shipmentActions'
import { TASK_STATUS } from '../../utils/statusTones'

const NOT_YET = 'Chưa phát sinh' // UC05.7 A1.2

const props = defineProps({
  shipment: { type: Object, required: true },
})
const meta = useMetaStore()
const emit = defineEmits(['action'])

const tasks = computed(() => props.shipment.tasks ?? [])
const openTask = computed(() => tasks.value.find((t) => !t.closed_at) ?? null)
const needsAttention = computed(() => Boolean(openTask.value?.needs_attention))
const holderLocked = computed(() => Boolean(props.shipment.holder_locked) && !needsAttention.value)
const swapPending = computed(() => openTask.value?.status === TASK_STATUS.PENDING_SWAP_HANDOVER)
const recoveryActions = computed(() => [
  { action: A.SWAP_SHIPPER, label: swapPending.value ? 'Đổi người dự kiến' : 'Đổi Shipper' },
  { action: A.CONFIRM_SWAP_HANDOVER, label: 'Xác nhận nhận hàng bàn giao' },
  { action: A.RECALL_TO_HUB, label: 'Nhận hàng về điểm tập kết' },
  { action: A.RECEIVE_RETURN, label: 'Tiếp nhận hàng hoàn' },
].filter((item) => can(props.shipment, item.action)))

const rows = computed(() => {
  const s = props.shipment
  const holder = meta.label('holder_types', s.holder_type)
  return [
    ['Đang giữ hàng', s.holder_shipper ? `${holder} · ${s.holder_shipper.full_name}` : holder],
    ['Shipper phụ trách', openTask.value
      ? `${openTask.value.shipper.full_name} · ${formatPhone(openTask.value.shipper.phone)}` : NOT_YET],
    ['Số lần giao', `${s.delivery_attempts ?? 0}/${meta.limits.max_delivery_attempts}`],
  ]
})

function resultText(task) {
  const r = task.result
  if (!r) return ''
  if (!r.reason_code) return r.cod_collected ? `Đã thu COD ${formatVnd(r.cod_collected)}` : ''
  const reason = meta.label(FAIL_REASON_GROUP[task.type], r.reason_code)
  return `Lý do: ${r.note ? `${reason} — ${r.note}` : reason}`
}
</script>

<template>
  <article class="card">
    <h2 class="card__title"><span class="card__title-icon"><AppIcon name="truck" /></span>Điều phối</h2>
    <p v-if="needsAttention" class="alert alert--warning attention" role="alert">
      Shipper phụ trách đã bị khóa tài khoản khi nhiệm vụ còn mở — cần Nhân viên xử lý bàn giao.
    </p>
    <p v-else-if="holderLocked" class="alert alert--warning attention" role="alert">
      Shipper đang giữ hàng đã bị khóa tài khoản — chưa phân công giao được; cần bàn giao hàng về điểm tập kết (đổi Shipper).
    </p>
    <div v-if="swapPending" class="alert alert--warning attention" role="status">
      <p class="alert__text">Chờ bàn giao đổi Shipper — dự kiến: <strong>{{ openTask.swap_candidate?.full_name }}</strong>.
        Người mới chưa có quyền nhiệm vụ. Người cũ đưa hàng về {{ meta.hub?.name }} để Nhân viên kiểm tra và xác nhận.</p>
    </div>
    <div v-if="needsAttention || holderLocked || swapPending" class="form__actions attention">
      <button v-for="item in recoveryActions" :key="item.action" type="button" class="btn btn--outline btn--sm"
              @click="emit('action', item.action)">{{ item.label }}</button>
    </div>
    <dl class="details">
      <template v-for="[label, value] in rows" :key="label">
        <dt>{{ label }}</dt>
        <dd :class="{ muted: value === NOT_YET }">{{ value }}</dd>
      </template>
    </dl>
    <h3 class="tasks__title">Nhiệm vụ</h3>
    <p v-if="!tasks.length" class="muted">{{ NOT_YET }}</p>
    <ul v-else class="tasks">
      <li v-for="task in tasks" :key="task.id" class="tasks__item">
        <div class="tasks__head">
          <strong>{{ meta.label('task_types', task.type) }}<template v-if="task.attempt_no"> · lần {{ task.attempt_no }}</template></strong>
          <StatusBadge group="task_statuses" :value="task.status" />
        </div>
        <span class="muted">{{ task.shipper.full_name }} · phân công {{ formatDateTime(task.assigned_at) }}</span>
        <span v-if="resultText(task)" class="tasks__result">{{ resultText(task) }}</span>
        <span v-if="task.handover_reported_at" class="tasks__result">
          Shipper đã báo đưa hàng về lúc {{ formatDateTime(task.handover_reported_at) }}
        </span>
        <span v-if="task.replaced_by" class="tasks__result">Đã thay thế → {{ task.replaced_by.shipper?.full_name }}</span>
      </li>
    </ul>
  </article>
</template>

<style scoped>
.attention { margin: 0 0 16px; }
.tasks__title { margin: 20px 0 10px; font-size: .875rem; color: var(--muted); font-weight: 600; }
.tasks { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.tasks__item { display: flex; flex-direction: column; gap: 4px; padding: 10px 12px; background: var(--surface-muted); border-radius: var(--radius-sm); }
.tasks__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.tasks__item .muted { font-size: .8125rem; }
.tasks__result { font-size: .875rem; }
</style>
