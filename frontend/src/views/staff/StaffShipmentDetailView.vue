<script setup>
// UC05.7 chi tiết + các thao tác của Nhân viên trên đơn: duyệt / từ chối (spec 005), phân công lấy, xác nhận
// tiếp nhận, lấy lại / kết thúc (spec 006), phân công giao, giao lại / hoàn (spec 007). Nút theo allowed_actions
// từ backend (đã lọc theo số lần giao — D8 / nơi giữ hàng — spec 008 D3); hoàn hàng (spec 008). Không có nút đặt
// trạng thái
// tùy ý (UC05.7 BR1). Mọi thao tác gửi updated_at của bản đang xem — 409 thì tải bản mới (E1).
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import ConfirmDialog from '../../components/common/ConfirmDialog.vue'
import FormField from '../../components/common/FormField.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import DispatchCard from '../../components/dispatch/DispatchCard.vue'
import ShipperPicker from '../../components/dispatch/ShipperPicker.vue'
import ShipmentEventList from '../../components/shipments/ShipmentEventList.vue'
import ShipmentInfoCards from '../../components/shipments/ShipmentInfoCards.vue'
import { API_ERROR } from '../../services/http'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatPhone, formatVnd } from '../../utils/format'
import { fieldErrors } from '../../utils/formErrors'
import { FAIL_REASON_GROUP, HOLDER_TYPE, SHIPMENT_ACTION as A, TASK_TYPE, can } from '../../utils/shipmentActions'
import { SHIPMENT_STATUS } from '../../utils/statusTones'

// Nút thao tác — thứ tự hiển thị (nút phụ trước, nút chính sau). `dialog`: hộp xác nhận tương ứng.
const ACTION_BUTTONS = [
  { action: A.REJECT_REQUEST, dialog: 'reject', label: 'Từ chối', icon: 'ban', tone: 'btn--danger-outline' },
  { action: A.APPROVE_REQUEST, dialog: 'approve', label: 'Duyệt', icon: 'check', tone: 'btn--primary' },
  { action: A.ABANDON_PICKUP, dialog: 'abandon', label: 'Kết thúc', icon: 'ban', tone: 'btn--danger-outline' },
  { action: A.RETRY_PICKUP, dialog: 'retry', label: 'Lấy lại', icon: 'reload', tone: 'btn--primary' },
  { action: A.ASSIGN_PICKUP, dialog: 'assign', label: 'Phân công lấy hàng', icon: 'truck', tone: 'btn--primary' },
  { action: A.RECEIVE_AT_HUB, dialog: 'receive', label: 'Xác nhận tiếp nhận', icon: 'warehouse', tone: 'btn--primary' },
  { action: A.DECIDE_RETURN, dialog: 'return', label: 'Chuyển hoàn', icon: 'undo', tone: 'btn--danger-outline' },
  { action: A.DECIDE_REDELIVERY, dialog: 'redeliver', label: 'Giao lại', icon: 'reload', tone: 'btn--primary' },
  { action: A.ASSIGN_DELIVERY, dialog: 'assign-delivery', label: 'Phân công giao hàng', icon: 'truck', tone: 'btn--primary' },
  // Spec 008
  { action: A.REPORT_RETURN_ISSUE, dialog: 'return-issue', label: 'Ghi sai lệch', icon: 'alert', tone: 'btn--danger-outline' },
  { action: A.ASSIGN_RETURN, dialog: 'assign-return', label: 'Phân công hoàn hàng', icon: 'truck', tone: 'btn--primary' },
  { action: A.RECEIVE_RETURN, dialog: 'receive-return', label: 'Tiếp nhận hàng hoàn', icon: 'warehouse', tone: 'btn--primary' },
  { action: A.CONFIRM_SHOP_RECEIVED, dialog: 'shop-received', label: 'Xác nhận Shop đã nhận', icon: 'check', tone: 'btn--primary' },
]

const route = useRoute()
const meta = useMetaStore()

const shipment = ref(null)
const loading = ref(true)
const loadError = ref('')
const notFound = ref(false)
const notice = ref('')
const warning = ref('') // 409: trạng thái/nội dung vừa đổi — đã tải bản mới
const eventList = ref(null)

const id = computed(() => route.params.id)
const buttons = computed(() => ACTION_BUTTONS.filter((b) => can(shipment.value, b.action)))
const allowed = (dialogName) => buttons.value.some((b) => b.dialog === dialogName)

async function load() {
  loading.value = true
  loadError.value = ''
  notFound.value = false
  try {
    shipment.value = await shipmentService.get(id.value)
  } catch (err) {
    shipment.value = null
    if (err?.status === 404) notFound.value = true
    else loadError.value = err?.message || 'Chưa thể tải vận đơn.'
  } finally {
    loading.value = false
  }
}

// --- Hộp thoại: một luồng xử lý kết quả dùng chung ---
const dialog = ref('')
const busy = ref(false)
const dialogError = ref('')
const reasonError = ref('')
const reason = ref('')
const note = ref('')
const shipperId = ref(null)
const handedOver = ref(false) // spec 007 D6: Shipper đã nhận hàng tại điểm tập kết
const receiverName = ref('') // spec 008 D7
const verified = ref(false)

function openDialog(kind) {
  dialog.value = kind
  dialogError.value = ''
  reasonError.value = ''
  reason.value = ''
  note.value = ''
  shipperId.value = null
  handedOver.value = false
  receiverName.value = kind === 'shop-received' ? (shipment.value?.shop?.full_name ?? '') : ''
  verified.value = false
  notice.value = ''
  warning.value = ''
}

async function submit(action, successText) {
  busy.value = true
  dialogError.value = ''
  reasonError.value = ''
  try {
    shipment.value = await action()
    dialog.value = ''
    notice.value = successText(shipment.value)
    eventList.value?.reload()
  } catch (err) {
    if (err?.code === API_ERROR.CONFLICT || err?.code === API_ERROR.INVALID_TRANSITION) {
      // Không xử lý trên dữ liệu cũ — đóng hộp, báo lý do, tải bản mới để xem lại.
      dialog.value = ''
      warning.value = err.message
      await load()
    } else {
      const fields = fieldErrors(err)
      reasonError.value = fields.reason ?? ''
      dialogError.value = reasonError.value ? '' : fields.discrepancy_note || fields.shipper_id || fields.handed_over
        || fields.receiver_name || fields.verified || fields.note || err?.message
        || 'Chưa xử lý được.'
    }
  } finally {
    busy.value = false
  }
}

const version = () => shipment.value.updated_at

function confirmApprove() {
  submit(() => shipmentService.approve(id.value, version()),
    (s) => `Đã duyệt. Mã vận đơn ${s.tracking_code}; Shop đã được thông báo.`)
}

function confirmAssign() {
  submit(() => shipmentService.assignPickup(id.value, shipperId.value, version()),
    (s) => `Đã phân công cho ${s.tasks?.[0]?.shipper?.full_name ?? 'Shipper'}. Shipper đã được thông báo.`)
}

// --- Giao hàng (spec 007) ---
const maxAttempts = computed(() => meta.limits.max_delivery_attempts)
const attempts = computed(() => shipment.value?.delivery_attempts ?? 0)
// D7: giao lại khi hàng đang ở Shipper → chỉ người đó (backend chặn người khác).
const holder = computed(() => (shipment.value?.holder_type === HOLDER_TYPE.SHIPPER ? shipment.value.holder_shipper : null))
const deliveryTasks = computed(() => (shipment.value?.tasks ?? []).filter((t) => t.type === TASK_TYPE.DELIVERY))
// UC04.12 bước 2: lý do lần giao thất bại gần nhất (tasks mới nhất trước).
const lastFailure = computed(() => {
  if (shipment.value?.status !== SHIPMENT_STATUS.DELIVERY_FAILED) return ''
  const r = deliveryTasks.value.find((t) => t.result?.reason_code)?.result
  if (!r) return ''
  const reason = meta.label(FAIL_REASON_GROUP[TASK_TYPE.DELIVERY], r.reason_code)
  return r.note ? `${reason} — ${r.note}` : reason
})
const onlyReturn = computed(() => shipment.value?.status === SHIPMENT_STATUS.DELIVERY_FAILED
  && attempts.value >= maxAttempts.value)

function confirmAssignDelivery() {
  submit(() => shipmentService.assignDelivery(id.value, shipperId.value, version()),
    (s) => `Đã phân công giao lần ${s.tasks?.[0]?.attempt_no ?? attempts.value + 1} cho `
      + `${s.tasks?.[0]?.shipper?.full_name ?? 'Shipper'}. Shipper và Shop đã được thông báo.`)
}

// --- Hoàn hàng (spec 008) ---
const openReturnTask = computed(() => (shipment.value?.tasks ?? []).find((t) => t.type === TASK_TYPE.RETURN && !t.closed_at))
// D5: tiếp nhận được cả khi Shipper chưa báo — cảnh báo để NV chỉ xác nhận khi đã nhận hàng thực tế.
const notReported = computed(() => Boolean(openReturnTask.value && !openReturnTask.value.handover_reported_at))

function confirmAssignReturn() {
  submit(() => shipmentService.assignReturn(id.value, shipperId.value, version()),
    (s) => `Đã phân công hoàn cho ${s.tasks?.[0]?.shipper?.full_name ?? 'Shipper'}. Shipper đã được thông báo.`)
}

function confirmReceiveReturn() {
  submit(() => shipmentService.receiveReturn(id.value, note.value.trim(), version()),
    () => 'Đã tiếp nhận hàng hoàn. Đơn chờ Shop đến lấy; Shop đã được thông báo.')
}

function confirmShopReceived() {
  submit(() => shipmentService.confirmShopReceived(id.value, receiverName.value.trim(), note.value.trim(), version()),
    () => 'Đã xác nhận Shop nhận lại hàng. Luồng hoàn kết thúc; Shop đã được thông báo.')
}

function confirmReceive() {
  submit(() => shipmentService.receiveAtHub(id.value, note.value.trim(), version()),
    () => 'Đã xác nhận tiếp nhận tại điểm tập kết. Đơn đủ điều kiện phân công giao.')
}

// Các thao tác cần lý do: cùng một hộp thoại, khác nội dung.
const REASON_DIALOGS = {
  reject: {
    title: 'Từ chối yêu cầu gửi hàng?', confirm: 'Từ chối', cancel: 'Không từ chối', field: 'Lý do từ chối',
    limit: 'reject_reason_max_length',
    text: (s) => `Yêu cầu ${s.request_code} sẽ chuyển sang Bị từ chối, không cấp mã vận đơn. Shop nhận thông báo kèm lý do.`,
    call: (r) => shipmentService.reject(id.value, r, version()),
    done: () => 'Đã từ chối yêu cầu; Shop đã được thông báo kèm lý do.',
  },
  retry: {
    title: 'Lấy hàng lại?', confirm: 'Lấy lại', cancel: 'Để sau', field: 'Lý do lấy lại', limit: 'task_note_max_length',
    text: (s) => `Đơn ${s.tracking_code} quay về Chờ lấy hàng để phân công Shipper mới. Lịch sử lần lấy trước được giữ.`,
    call: (r) => shipmentService.retryPickup(id.value, r, version()),
    done: () => 'Đã chuyển lấy lại; hãy phân công Shipper. Shop đã được thông báo.',
  },
  redeliver: {
    title: 'Giao lại?', confirm: 'Giao lại', cancel: 'Để sau', field: 'Lý do / quyết định giao lại',
    limit: 'task_note_max_length',
    text: (s) => `Đơn ${s.tracking_code} đã giao ${s.delivery_attempts}/${maxAttempts.value} lần, chuyển sang Chờ giao lại `
      + `để phân công lần ${s.delivery_attempts + 1}. Lịch sử các lần trước được giữ.`,
    call: (r) => shipmentService.decideRedelivery(id.value, r, version()),
    done: () => 'Đã chuyển giao lại; hãy phân công giao. Shop đã được thông báo.',
  },
  return: {
    title: 'Chuyển hoàn về Shop?', confirm: 'Chuyển hoàn', cancel: 'Không hoàn', field: 'Lý do hoàn',
    limit: 'task_note_max_length', danger: true,
    text: (s) => `Đơn ${s.tracking_code} (đã giao ${s.delivery_attempts}/${maxAttempts.value} lần) chuyển sang Chờ xử lý hoàn, `
      + 'không giao tiếp nữa. Phân công hoàn làm ở bước sau.',
    call: (r) => shipmentService.decideReturn(id.value, r, version()),
    done: () => 'Đã chuyển hoàn; Shop đã được thông báo kèm lý do.',
  },
  'return-issue': {
    title: 'Ghi sai lệch hàng hoàn', confirm: 'Ghi sai lệch', cancel: 'Hủy', field: 'Sai lệch (mã, số kiện, tình trạng)',
    limit: 'task_note_max_length', danger: true,
    text: (s) => `Ghi lại sai lệch của hàng hoàn ${s.tracking_code}. Đơn vẫn Đang hoàn, CHƯA tiếp nhận — `
      + 'xử lý xong sai lệch rồi mới "Tiếp nhận hàng hoàn".',
    call: (r) => shipmentService.reportReturnIssue(id.value, r, version()),
    done: () => 'Đã ghi sai lệch vào lịch sử. Đơn vẫn chờ tiếp nhận.',
  },
  abandon: {
    title: 'Kết thúc vận đơn?', confirm: 'Kết thúc', cancel: 'Không kết thúc', field: 'Lý do kết thúc',
    limit: 'task_note_max_length', danger: true,
    text: (s) => `Đơn ${s.tracking_code} sẽ kết thúc do không lấy được hàng, không phân công lấy thêm. Thao tác không hoàn tác được.`,
    call: (r) => shipmentService.abandonPickup(id.value, r, version()),
    done: () => 'Đã kết thúc vận đơn; Shop đã được thông báo kèm lý do.',
  },
}
const reasonDialog = computed(() => REASON_DIALOGS[dialog.value] ?? null)

function confirmReason() {
  const config = reasonDialog.value
  submit(() => config.call(reason.value.trim()), config.done)
}

watch(id, () => {
  notice.value = ''
  warning.value = ''
  load()
}, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="staff-shipment-title">
    <RouterLink :to="{ name: 'staff-shipments' }" class="back-link">
      <AppIcon name="arrow-left" :size="16" />Quản lý vận đơn
    </RouterLink>

    <p v-if="warning" class="alert alert--warning" role="alert">{{ warning }} Đã tải bản mới nhất bên dưới.</p>

    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải vận đơn…</p>

    <div v-else-if="notFound" class="card">
      <h1 id="staff-shipment-title">Không tìm thấy vận đơn</h1>
      <p class="muted">Vận đơn không tồn tại hoặc đã bị xóa khỏi hệ thống.</p>
    </div>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost btn--sm" @click="load">Tải lại</button>
    </div>

    <template v-else-if="shipment">
      <header class="detail-header">
        <div>
          <div class="title-row">
            <h1 id="staff-shipment-title">{{ shipment.tracking_code || shipment.request_code }}</h1>
            <StatusBadge :value="shipment.status" />
          </div>
          <p class="muted">
            Mã yêu cầu {{ shipment.request_code }} ·
            <template v-if="shipment.tracking_code">Mã vận đơn {{ shipment.tracking_code }}</template>
            <template v-else>Chưa có mã vận đơn (cấp khi duyệt)</template>
            · {{ shipment.shop?.full_name }} · Tạo lúc {{ formatDateTime(shipment.created_at) }}
          </p>
        </div>
        <div v-if="buttons.length" class="page__actions">
          <button v-for="b in buttons" :key="b.action" type="button" class="btn" :class="b.tone"
                  @click="openDialog(b.dialog)">
            <AppIcon :name="b.icon" :size="16" />{{ b.label }}
          </button>
        </div>
      </header>

      <p v-if="notice" class="alert alert--success" role="status">{{ notice }}</p>
      <p v-if="lastFailure" class="alert alert--danger">
        <strong>Giao lần {{ attempts }}/{{ maxAttempts }} thất bại:</strong> {{ lastFailure }}
        <template v-if="onlyReturn"> — đã đủ {{ maxAttempts }} lần nên chỉ được chuyển hoàn.</template>
      </p>
      <p v-if="shipment.rejection_reason" class="alert alert--danger">
        <strong>Lý do từ chối:</strong> {{ shipment.rejection_reason }}
      </p>

      <div class="detail-layout">
        <ShipmentInfoCards :shipment="shipment" show-shop>
          <DispatchCard :shipment="shipment" />
        </ShipmentInfoCards>
        <ShipmentEventList ref="eventList" :shipment-id="id" />
      </div>

      <ConfirmDialog :open="dialog === 'approve'" title="Duyệt yêu cầu gửi hàng?" confirm-label="Duyệt"
                     cancel-label="Để sau" :busy="busy" :confirm-disabled="!allowed('approve')"
                     @confirm="confirmApprove" @cancel="dialog = ''">
        <dl class="details">
          <dt>Mã yêu cầu</dt><dd>{{ shipment.request_code }}</dd>
          <dt>Shop</dt><dd>{{ shipment.shop?.full_name }}</dd>
          <dt>Giao đến</dt><dd>{{ shipment.receiver_name }} · {{ shipment.delivery_ward?.name }}</dd>
          <dt>Thu hộ</dt><dd>{{ shipment.cod_amount ? formatVnd(shipment.cod_amount) : 'Không thu hộ' }}</dd>
        </dl>
        <p>Hệ thống sẽ cấp <strong>mã vận đơn</strong>, chuyển sang Chờ lấy hàng và thông báo cho Shop.
          Thao tác này không hoàn tác được.</p>
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'assign'" title="Phân công Shipper lấy hàng" confirm-label="Phân công"
                     cancel-label="Để sau" :busy="busy" :confirm-disabled="!allowed('assign') || !shipperId"
                     @confirm="confirmAssign" @cancel="dialog = ''">
        <p>Lấy tại <strong>{{ shipment.pickup_address }}, {{ shipment.pickup_ward?.name }}</strong>
          · {{ shipment.package_count }} kiện. Shipper được chọn sẽ nhận thông báo.</p>
        <!-- v-if: chỉ tải danh sách Shipper khi mở hộp -->
        <ShipperPicker v-if="dialog === 'assign'" v-model="shipperId" :disabled="busy" />
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'assign-delivery'"
                     :title="holder ? 'Phân công giao lại' : 'Phân công Shipper giao hàng'" confirm-label="Phân công giao"
                     cancel-label="Để sau" :busy="busy"
                     :confirm-disabled="!allowed('assign-delivery') || !shipperId || !handedOver || shipment.holder_locked"
                     @confirm="confirmAssignDelivery" @cancel="dialog = ''">
        <dl class="details">
          <dt>Giao đến</dt><dd>{{ shipment.receiver_name }} · {{ shipment.delivery_address }}, {{ shipment.delivery_ward?.name }}</dd>
          <dt>Thu hộ</dt><dd>{{ shipment.cod_amount ? formatVnd(shipment.cod_amount) : 'Không thu hộ' }}</dd>
          <dt>Lần giao</dt><dd>{{ attempts + 1 }}/{{ maxAttempts }}</dd>
        </dl>
        <p v-if="shipment.holder_locked" class="alert alert--warning" role="alert">
          Shipper đang giữ hàng đã bị khóa — cần bàn giao hàng về điểm tập kết (đổi Shipper) trước khi giao lại.
        </p>
        <template v-else>
          <ShipperPicker v-if="dialog === 'assign-delivery'" v-model="shipperId" :holder="holder" :disabled="busy" />
          <label class="checkbox">
            <input v-model="handedOver" type="checkbox" :disabled="busy" />
            <span>{{ holder ? 'Shipper đang giữ hàng và sẵn sàng giao lại' : 'Shipper đã nhận hàng tại điểm tập kết' }}</span>
          </label>
        </template>
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'assign-return'" title="Phân công hoàn hàng" confirm-label="Phân công hoàn"
                     cancel-label="Để sau" :busy="busy"
                     :confirm-disabled="!allowed('assign-return') || !shipperId || shipment.holder_locked"
                     @confirm="confirmAssignReturn" @cancel="dialog = ''">
        <dl class="details">
          <dt>Kiện hàng</dt><dd>{{ shipment.package_count }} kiện · {{ shipment.package_description }}</dd>
          <dt>Đưa về</dt><dd>{{ meta.hub?.name }}</dd>
        </dl>
        <p class="muted">Lý do hoàn xem ở mục Lịch sử ("Quyết định hoàn hàng").</p>
        <p v-if="shipment.holder_locked" class="alert alert--warning" role="alert">
          Shipper đang giữ hàng đã bị khóa — cần bàn giao hàng về điểm tập kết (đổi Shipper) trước.
        </p>
        <ShipperPicker v-else-if="dialog === 'assign-return'" v-model="shipperId" :holder="holder" :disabled="busy" />
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'receive-return'" title="Tiếp nhận hàng hoàn?" confirm-label="Xác nhận tiếp nhận"
                     cancel-label="Chưa nhận" :busy="busy" :confirm-disabled="!allowed('receive-return')"
                     @confirm="confirmReceiveReturn" @cancel="dialog = ''">
        <dl class="details">
          <dt>Mã vận đơn</dt><dd>{{ shipment.tracking_code }}</dd>
          <dt>Shipper giao</dt><dd>{{ shipment.holder_shipper?.full_name ?? 'Hàng đã ở điểm tập kết' }}</dd>
          <dt>Kiện hàng</dt><dd>{{ shipment.package_count }} kiện · {{ shipment.package_description }}</dd>
        </dl>
        <p v-if="notReported" class="alert alert--warning" role="alert">
          Shipper chưa báo đã đưa hàng về. Chỉ xác nhận khi đã nhận kiện hàng thực tế.
        </p>
        <p>Đối chiếu mã đơn, số kiện, tình trạng hàng. Sau khi xác nhận, đơn chờ Shop đến lấy.</p>
        <FormField v-model="note" label="Ghi chú sai lệch (không bắt buộc)" multiline :disabled="busy"
                   :maxlength="meta.limits.handover_note_max_length" />
        <button v-if="allowed('return-issue')" type="button" class="btn btn--ghost btn--sm" :disabled="busy"
                @click="openDialog('return-issue')">Có sai lệch, chưa nhận?</button>
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'shop-received'" title="Xác nhận Shop đã nhận hàng hoàn?"
                     confirm-label="Xác nhận đã bàn giao" cancel-label="Shop chưa đến" :busy="busy"
                     :confirm-disabled="!allowed('shop-received') || !receiverName.trim() || !verified"
                     @confirm="confirmShopReceived" @cancel="dialog = ''">
        <dl class="details">
          <dt>Mã vận đơn</dt><dd>{{ shipment.tracking_code }}</dd>
          <dt>Shop</dt><dd>{{ shipment.shop?.full_name }} · {{ formatPhone(shipment.shop?.phone) }}</dd>
          <dt>Kiện hàng</dt><dd>{{ shipment.package_count }} kiện · {{ shipment.package_description }}</dd>
        </dl>
        <FormField v-model="receiverName" label="Tên người nhận" required :disabled="busy"
                   :maxlength="meta.limits.handover_receiver_name_max_length"
                   hint="Điền sẵn tên Shop — sửa nếu người đến nhận là người được Shop ủy quyền." />
        <label class="checkbox">
          <input v-model="verified" type="checkbox" :disabled="busy" />
          <span>Đã kiểm tra người nhận thuộc Shop hoặc được Shop ủy quyền</span>
        </label>
        <FormField v-model="note" label="Ghi chú bàn giao (không bắt buộc)" multiline :disabled="busy"
                   :maxlength="meta.limits.handover_note_max_length" />
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'receive'" title="Xác nhận tiếp nhận tại điểm tập kết?"
                     confirm-label="Xác nhận tiếp nhận" cancel-label="Chưa nhận" :busy="busy"
                     :confirm-disabled="!allowed('receive')" @confirm="confirmReceive" @cancel="dialog = ''">
        <dl class="details">
          <dt>Mã vận đơn</dt><dd>{{ shipment.tracking_code }}</dd>
          <dt>Shipper giao</dt><dd>{{ shipment.holder_shipper?.full_name ?? '—' }}</dd>
          <dt>Kiện hàng</dt><dd>{{ shipment.package_count }} kiện · {{ shipment.package_description }}</dd>
        </dl>
        <p>Chỉ xác nhận khi đã nhận kiện hàng thực tế. Nếu hàng không khớp, ghi lại sai lệch.</p>
        <FormField v-model="note" label="Ghi chú sai lệch (không bắt buộc)" multiline :disabled="busy"
                   :maxlength="meta.limits.handover_note_max_length" />
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="Boolean(reasonDialog)" :title="reasonDialog?.title ?? ''"
                     :confirm-label="reasonDialog?.confirm" :cancel-label="reasonDialog?.cancel"
                     :tone="reasonDialog?.danger || dialog === 'reject' ? 'danger' : 'primary'" :busy="busy"
                     :confirm-disabled="!allowed(dialog) || !reason.trim()"
                     @confirm="confirmReason" @cancel="dialog = ''">
        <template v-if="reasonDialog">
          <p>{{ reasonDialog.text(shipment) }}</p>
          <FormField v-model="reason" :label="reasonDialog.field" multiline required :disabled="busy"
                     :maxlength="meta.limits[reasonDialog.limit]" :error="reasonError" />
          <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
        </template>
      </ConfirmDialog>
    </template>
  </section>
</template>
