<script setup>
// Chi tiết nhiệm vụ của Shipper — LẤY (UC04.1–04.3, spec 006), GIAO (UC04.4–04.7, spec 007), HOÀN (UC04.8–04.9, spec 008).
// Mỗi loại chỉ hiện thông tin cần cho việc đó (D3); nút theo allowed_actions. Khác biệt giữa hai loại khai báo
// trong bảng TYPE_VIEW, không rải if/else. Thiết kế cho điện thoại: nút gọi điện, thanh thao tác dính đáy.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import ConfirmDialog from '../../components/common/ConfirmDialog.vue'
import FormField from '../../components/common/FormField.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import CodInput from '../../components/dispatch/CodInput.vue'
import HubCard from '../../components/dispatch/HubCard.vue'
import { API_ERROR } from '../../services/http'
import * as taskService from '../../services/taskService'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatPhone, formatVnd } from '../../utils/format'
import { fieldErrors } from '../../utils/formErrors'
import {
  DELIVERY_FAIL_REASON, FAIL_REASON_GROUP, PICKUP_FAIL_REASON, SHIPMENT_ACTION as A, TASK_TYPE, can,
} from '../../utils/shipmentActions'

const TYPE_VIEW = {
  [TASK_TYPE.PICKUP]: {
    confirm: A.CONFIRM_PICKUP, fail: A.FAIL_PICKUP, other: PICKUP_FAIL_REASON.OTHER,
    confirmLabel: 'Đã lấy hàng', failLabel: 'Lấy hàng thất bại',
    confirmTitle: 'Xác nhận đã lấy hàng?', confirmButton: 'Tôi đã nhận đủ hàng', failTitle: 'Lấy hàng thất bại',
    confirmCall: (id) => taskService.confirmPickup(id),
    failCall: (id, code, note) => taskService.failPickup(id, code, note),
    confirmDone: 'Đã ghi nhận lấy hàng. Hãy mang hàng về điểm tập kết để Nhân viên tiếp nhận.',
    failDone: 'Đã ghi nhận lấy hàng thất bại. Nhân viên sẽ quyết định lấy lại hay kết thúc.',
    succeeded: 'Đã lấy hàng lúc', failed: 'Lấy thất bại',
  },
  [TASK_TYPE.DELIVERY]: {
    confirm: A.CONFIRM_DELIVERY, fail: A.FAIL_DELIVERY, other: DELIVERY_FAIL_REASON.OTHER,
    confirmLabel: 'Giao thành công', failLabel: 'Giao thất bại',
    confirmTitle: 'Xác nhận giao thành công?', confirmButton: 'Người nhận đã nhận hàng', failTitle: 'Giao hàng thất bại',
    confirmCall: (id, cod) => taskService.confirmDelivery(id, cod),
    failCall: (id, code, note) => taskService.failDelivery(id, code, note),
    confirmDone: 'Đã ghi nhận giao thành công. Shop đã được thông báo.',
    failDone: 'Đã ghi nhận giao thất bại. Hàng vẫn do bạn giữ — Nhân viên sẽ quyết định giao lại hay hoàn.',
    succeeded: 'Đã giao lúc', failed: 'Giao thất bại',
  },
  // Hoàn (spec 008 D4): chỉ một thao tác — báo đã đưa hàng về; Nhân viên mới xác nhận tiếp nhận (UC04.9 BR1).
  [TASK_TYPE.RETURN]: {
    confirm: A.REPORT_RETURN_HANDOVER, fail: null, other: null,
    confirmLabel: 'Đã đưa hàng về điểm tập kết', failLabel: '',
    confirmTitle: 'Xác nhận đã đưa hàng về điểm tập kết?', confirmButton: 'Tôi đã giao hàng cho điểm tập kết',
    failTitle: '',
    confirmCall: (id) => taskService.reportReturnHandover(id),
    failCall: null,
    confirmDone: 'Đã báo đưa hàng về. Nhân viên điểm tập kết sẽ kiểm tra và xác nhận tiếp nhận.',
    failDone: '',
    succeeded: 'Điểm tập kết đã tiếp nhận lúc', failed: '',
  },
}

const route = useRoute()
const meta = useMetaStore()

const task = ref(null)
const loading = ref(true)
const loadError = ref('')
const notFound = ref(false)
const notice = ref('')
const warning = ref('')

const id = computed(() => route.params.id)
const shipment = computed(() => task.value?.shipment)
const view = computed(() => TYPE_VIEW[task.value?.type] ?? TYPE_VIEW[TASK_TYPE.PICKUP])
const isDelivery = computed(() => task.value?.type === TASK_TYPE.DELIVERY)
const isReturn = computed(() => task.value?.type === TASK_TYPE.RETURN)
// UC04.9 A1: đã báo bàn giao nhưng Nhân viên chưa xác nhận — nhiệm vụ vẫn mở.
const waitingIntake = computed(() => Boolean(task.value?.handover_reported_at && !task.value?.closed_at))
const canConfirm = computed(() => can(task.value, view.value.confirm))
const canFail = computed(() => can(task.value, view.value.fail))
const reasons = computed(() => meta.options(FAIL_REASON_GROUP[task.value?.type] ?? FAIL_REASON_GROUP[TASK_TYPE.PICKUP]))
const maxAttempts = computed(() => meta.limits.max_delivery_attempts)

async function load() {
  loading.value = true
  loadError.value = ''
  notFound.value = false
  try {
    task.value = await taskService.get(id.value)
  } catch (err) {
    task.value = null
    if (err?.status === 404) notFound.value = true // UC04.1 E1, UC04.4 E1: đã chuyển / thu hồi
    else loadError.value = err?.message || 'Chưa thể tải nhiệm vụ.'
  } finally {
    loading.value = false
  }
}

// --- Thao tác ---
const dialog = ref('') // '' | 'confirm' | 'fail'
const busy = ref(false)
const dialogError = ref('')
const reasonCode = ref('')
const note = ref('')
const noteError = ref('')
const cod = ref(null)
const codError = ref('')
const noteRequired = computed(() => reasonCode.value === view.value.other) // D4
const failReady = computed(() => reasonCode.value && (!noteRequired.value || note.value.trim()))
// Giao: chỉ cho xác nhận khi số đã thu khớp phải thu (backend vẫn kiểm lại — D5).
const confirmReady = computed(() => !isDelivery.value || cod.value === shipment.value?.cod_amount)

function openDialog(kind, presetReason = '') {
  dialog.value = kind
  dialogError.value = ''
  noteError.value = ''
  codError.value = ''
  reasonCode.value = presetReason
  note.value = ''
  cod.value = null
  notice.value = ''
  warning.value = ''
}

async function submit(action, successText) {
  busy.value = true
  dialogError.value = ''
  noteError.value = ''
  codError.value = ''
  try {
    task.value = await action()
    dialog.value = ''
    notice.value = successText
  } catch (err) {
    if (err?.status === 404) {
      dialog.value = ''
      task.value = null
      notFound.value = true
    } else if (err?.code === API_ERROR.INVALID_TRANSITION || err?.code === API_ERROR.CONFLICT) {
      // Nhiệm vụ không còn cho ghi kết quả — báo, tải trạng thái mới, không ghi thêm.
      dialog.value = ''
      warning.value = err.message
      await load()
    } else {
      const fields = fieldErrors(err)
      noteError.value = fields.note ?? ''
      codError.value = fields.cod_collected ?? '' // UC04.7 E1.1: chênh lệch từ backend
      dialogError.value = noteError.value || codError.value ? '' : fields.reason_code || err?.message || 'Chưa lưu được.'
    }
  } finally {
    busy.value = false
  }
}

function confirmTask() {
  submit(() => view.value.confirmCall(id.value, cod.value), view.value.confirmDone)
}

function failTask() {
  submit(() => view.value.failCall(id.value, reasonCode.value, note.value.trim()), view.value.failDone)
}

const resultText = computed(() => {
  const r = task.value?.result
  if (!r) return ''
  if (!r.reason_code) {
    const collected = r.cod_collected ? ` · đã thu COD ${formatVnd(r.cod_collected)}` : ''
    return `${view.value.succeeded} ${formatDateTime(r.recorded_at)}${collected}`
  }
  const reason = meta.label(FAIL_REASON_GROUP[task.value.type], r.reason_code)
  return `${view.value.failed}: ${reason}${r.note ? ` — ${r.note}` : ''} (${formatDateTime(r.recorded_at)})`
})

watch(id, () => {
  notice.value = ''
  warning.value = ''
  load()
}, { immediate: true })
</script>

<template>
  <section class="page page--narrow task-page" aria-labelledby="task-title">
    <RouterLink :to="{ name: 'shipper-tasks' }" class="back-link">
      <AppIcon name="arrow-left" :size="16" />Nhiệm vụ
    </RouterLink>

    <p v-if="warning" class="alert alert--warning" role="alert">{{ warning }}</p>

    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải nhiệm vụ…</p>

    <div v-else-if="notFound" class="card">
      <h1 id="task-title">Không tìm thấy nhiệm vụ</h1>
      <p class="muted">Nhiệm vụ không tồn tại hoặc đã chuyển cho Shipper khác.</p>
      <RouterLink :to="{ name: 'shipper-tasks' }" class="btn btn--ghost">Về danh sách</RouterLink>
    </div>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost btn--sm" @click="load">Tải lại</button>
    </div>

    <template v-else-if="task">
      <header class="detail-header">
        <div>
          <p class="task-type">
            {{ meta.label('task_types', task.type) }}
            <template v-if="task.attempt_no"> · lần {{ task.attempt_no }}/{{ maxAttempts }}</template>
          </p>
          <div class="title-row">
            <h1 id="task-title">{{ shipment.tracking_code }}</h1>
            <StatusBadge group="task_statuses" :value="task.status" />
          </div>
          <p class="muted">Phân công lúc {{ formatDateTime(task.assigned_at) }}</p>
        </div>
      </header>

      <p v-if="notice" class="alert alert--success" role="status">{{ notice }}</p>
      <p v-if="resultText" class="alert alert--info">{{ resultText }}</p>
      <p v-if="waitingIntake" class="alert alert--info" role="status">
        Đã báo đưa hàng về lúc {{ formatDateTime(task.handover_reported_at) }} — chờ Nhân viên điểm tập kết xác nhận tiếp nhận.
      </p>

      <!-- Giao: người nhận + COD (UC04.4 bước 5) -->
      <template v-if="isDelivery">
        <article class="card">
          <h2 class="card__title"><span class="card__title-icon"><AppIcon name="map-pin" /></span>Giao đến</h2>
          <p class="place__name">{{ shipment.receiver_name }}</p>
          <p class="place__address">{{ shipment.delivery_address }}, {{ shipment.delivery_ward?.name }}</p>
          <div class="place__contact">
            <!-- D3: nhiệm vụ đã đóng → backend ẩn SĐT (null) -->
            <span v-if="shipment.receiver_phone">{{ formatPhone(shipment.receiver_phone) }}</span>
            <a v-if="shipment.receiver_phone" :href="`tel:${shipment.receiver_phone}`" class="btn btn--outline btn--sm">
              <AppIcon name="phone" :size="16" />Gọi người nhận
            </a>
          </div>
        </article>
        <article class="card cod-card">
          <h2 class="card__title"><span class="card__title-icon"><AppIcon name="wallet" /></span>Thu hộ (COD)</h2>
          <p class="cod-card__amount" :class="{ muted: !shipment.cod_amount }">
            {{ shipment.cod_amount ? formatVnd(shipment.cod_amount) : 'Không thu hộ' }}
          </p>
          <p v-if="shipment.cod_amount" class="muted cod-card__hint">Thu đủ số này trước khi bấm "Giao thành công".</p>
        </article>
      </template>

      <!-- Hoàn: đưa về điểm tập kết (UC04.8 bước 3, D8) -->
      <HubCard v-else-if="isReturn" title="Đưa hàng về">
        <p v-if="shipment.return_reason" class="return-reason"><strong>Lý do hoàn:</strong> {{ shipment.return_reason }}</p>
      </HubCard>

      <!-- Lấy: nơi lấy + người gửi -->
      <article v-else class="card">
        <h2 class="card__title"><span class="card__title-icon"><AppIcon name="map-pin" /></span>Lấy hàng tại</h2>
        <p class="place__name">{{ shipment.shop_name }}</p>
        <p class="place__address">{{ shipment.pickup_address }}, {{ shipment.pickup_ward?.name }}</p>
        <div class="place__contact">
          <span>{{ shipment.sender_name }}<template v-if="shipment.sender_phone"> · {{ formatPhone(shipment.sender_phone) }}</template></span>
          <a v-if="shipment.sender_phone" :href="`tel:${shipment.sender_phone}`" class="btn btn--outline btn--sm">
            <AppIcon name="phone" :size="16" />Gọi
          </a>
        </div>
      </article>

      <article class="card">
        <h2 class="card__title"><span class="card__title-icon"><AppIcon name="box" /></span>Kiện hàng</h2>
        <dl class="details">
          <template v-if="isDelivery || isReturn"><dt>Hàng của Shop</dt><dd>{{ shipment.shop_name }}</dd></template>
          <dt>Mô tả</dt><dd>{{ shipment.package_description }}</dd>
          <dt>Số kiện</dt><dd>{{ shipment.package_count }}</dd>
          <dt>Khối lượng</dt><dd>{{ shipment.weight_grams ? `${shipment.weight_grams} gram` : 'Không ghi' }}</dd>
          <dt>Ghi chú</dt><dd>{{ shipment.note || 'Không có' }}</dd>
        </dl>
      </article>

      <div v-if="canConfirm || canFail" class="task-actions">
        <button v-if="canFail" type="button" class="btn btn--danger-outline" @click="openDialog('fail')">
          <AppIcon name="ban" :size="16" />{{ view.failLabel }}
        </button>
        <button v-if="canConfirm" type="button" class="btn btn--primary" @click="openDialog('confirm')">
          <AppIcon name="check" :size="16" />{{ view.confirmLabel }}
        </button>
      </div>

      <ConfirmDialog :open="dialog === 'confirm'" :title="view.confirmTitle" :confirm-label="view.confirmButton"
                     cancel-label="Chưa" :busy="busy" :confirm-disabled="!canConfirm || !confirmReady"
                     @confirm="confirmTask" @cancel="dialog = ''">
        <dl class="details">
          <dt>Mã vận đơn</dt><dd>{{ shipment.tracking_code }}</dd>
          <template v-if="isDelivery"><dt>Người nhận</dt><dd>{{ shipment.receiver_name }}</dd></template>
          <template v-else><dt>Shop</dt><dd>{{ shipment.shop_name }}</dd></template>
          <dt>Số kiện</dt><dd>{{ shipment.package_count }}</dd>
          <dt>Hàng</dt><dd>{{ shipment.package_description }}</dd>
        </dl>
        <template v-if="isDelivery">
          <CodInput v-if="dialog === 'confirm'" v-model="cod" :expected="shipment.cod_amount"
                    :max="meta.limits.cod_max_vnd" :error="codError" :disabled="busy" />
          <!-- UC04.5 E1.3: chưa thu đủ thì ghi giao thất bại, không thu một phần -->
          <button v-if="shipment.cod_amount && canFail" type="button" class="btn btn--ghost btn--sm"
                  :disabled="busy" @click="openDialog('fail', DELIVERY_FAIL_REASON.COD_NOT_READY)">
            Chưa thu đủ? Ghi giao thất bại
          </button>
        </template>
        <p v-else-if="isReturn">
          Chỉ bấm khi đã giao hàng tận tay cho Nhân viên tại điểm tập kết. Nhân viên sẽ đối chiếu mã đơn, số kiện
          và xác nhận tiếp nhận.
        </p>
        <p v-else>Chỉ xác nhận khi đã nhận đủ hàng thực tế. Nếu hàng không khớp, chọn "Lấy hàng thất bại".</p>
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'fail'" :title="view.failTitle" confirm-label="Ghi nhận thất bại"
                     cancel-label="Hủy" tone="danger" :busy="busy" :confirm-disabled="!canFail || !failReady"
                     @confirm="failTask" @cancel="dialog = ''">
        <p v-if="isDelivery" class="muted">
          Lần giao {{ task.attempt_no }}/{{ maxAttempts }}. Hàng vẫn do bạn giữ; bạn không tự quyết định hoàn.
        </p>
        <div class="field">
          <label for="fail-reason">Lý do<span class="field__required" aria-hidden="true"> *</span></label>
          <select id="fail-reason" v-model="reasonCode" :disabled="busy" required>
            <option value="" disabled>Chọn lý do</option>
            <option v-for="r in reasons" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>
        <FormField v-model="note" :label="noteRequired ? 'Ghi chú (bắt buộc với lý do Khác)' : 'Ghi chú (không bắt buộc)'"
                   multiline :required="noteRequired" :disabled="busy" :error="noteError"
                   :maxlength="meta.limits.task_note_max_length" />
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>
    </template>
  </section>
</template>

<style scoped>
.task-type { margin: 0 0 4px; font-size: .8125rem; font-weight: 600; letter-spacing: .02em; color: var(--brand); text-transform: uppercase; }
.return-reason { margin: 12px 0 0; }
.place__name { margin: 0 0 4px; font-weight: 600; font-size: 1.0625rem; }
.place__address { margin: 0 0 12px; }
.place__contact { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; color: var(--muted); }
.cod-card__amount { margin: 0; font-size: 1.75rem; font-weight: 700; color: var(--brand); }
.cod-card__amount.muted { font-size: 1.0625rem; font-weight: 500; color: var(--muted); }
.cod-card__hint { margin: 4px 0 0; font-size: .875rem; }
.task-actions { display: flex; gap: 12px; justify-content: flex-end; flex-wrap: wrap; }
/* Điện thoại: thanh thao tác dính đáy, nút to dễ bấm */
@media (max-width: 640px) {
  .task-page { padding-bottom: 88px; }
  .task-actions {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 10; padding: 12px 16px; flex-wrap: nowrap;
    background: var(--surface); border-top: 1px solid var(--border); box-shadow: var(--shadow-lg);
  }
  .task-actions .btn { flex: 1; padding: 13px 12px; }
}
</style>
