<script setup>
// UC05.4 chi tiết, UC05.1 sửa, UC05.5 hủy — của Shop. Nút theo allowed_actions từ backend.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import ConfirmDialog from '../../components/common/ConfirmDialog.vue'
import FormField from '../../components/common/FormField.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import HubCard from '../../components/dispatch/HubCard.vue'
import ShipmentEventList from '../../components/shipments/ShipmentEventList.vue'
import ShipmentForm from '../../components/shipments/ShipmentForm.vue'
import ShipmentInfoCards from '../../components/shipments/ShipmentInfoCards.vue'
import { API_ERROR } from '../../services/http'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import { useWardStore } from '../../stores/wards'
import { formatDateTime } from '../../utils/format'
import { fieldErrors, generalMessage } from '../../utils/formErrors'
import { SHIPMENT_ACTION, can } from '../../utils/shipmentActions'
import { SHIPMENT_STATUS } from '../../utils/statusTones'

const route = useRoute()
const meta = useMetaStore()
const wardStore = useWardStore()

const shipment = ref(null)
const loading = ref(true)
const loadError = ref('')
const notFound = ref(false)
const notice = ref('')
const eventList = ref(null) // ShipmentEventList — tải lại sau khi đổi đơn

const id = computed(() => route.params.id)
const canEdit = computed(() => can(shipment.value, SHIPMENT_ACTION.UPDATE_REQUEST))
const canCancel = computed(() => can(shipment.value, SHIPMENT_ACTION.CANCEL_REQUEST))
const awaitingPickup = computed(() => shipment.value?.status === SHIPMENT_STATUS.AWAITING_SHOP_PICKUP)


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

// --- Sửa (UC05.1) ---
const editing = ref(false)
const saving = ref(false)
const errors = ref({})
const formMessage = ref('')
const staleState = ref('') // '' | 'conflict' | 'status'

function startEdit() {
  wardStore.load().catch(() => {})
  errors.value = {}
  formMessage.value = ''
  staleState.value = ''
  notice.value = ''
  editing.value = true
}

async function save(payload) {
  saving.value = true
  errors.value = {}
  formMessage.value = ''
  staleState.value = ''
  try {
    shipment.value = await shipmentService.update(id.value, payload, shipment.value.updated_at)
    editing.value = false
    notice.value = 'Đã lưu thay đổi yêu cầu.'
    eventList.value?.reload()
  } catch (err) {
    errors.value = fieldErrors(err)
    formMessage.value = generalMessage(err)
    if (err?.code === API_ERROR.CONFLICT) staleState.value = 'conflict'
    else if (err?.code === API_ERROR.INVALID_TRANSITION) staleState.value = 'status'
  } finally {
    saving.value = false
  }
}

// Sau 409: tải bản mới nhất. Nếu đã hết được sửa (vd vừa được duyệt) thì thoát chế độ sửa (UC05.1 E1).
async function reloadLatest() {
  await load() // khối nội dung gắn lại → lịch sử tự tải lại
  staleState.value = ''
  formMessage.value = ''
  if (!canEdit.value) editing.value = false
}

// --- Hủy (UC05.5) ---
const cancelOpen = ref(false)
const cancelBusy = ref(false)
const cancelError = ref('')
const cancelFieldError = ref('')
const cancelReason = ref('')

function openCancel() {
  cancelOpen.value = true
  cancelError.value = ''
  cancelFieldError.value = ''
  cancelReason.value = ''
  notice.value = ''
}

async function confirmCancel() {
  cancelBusy.value = true
  cancelError.value = ''
  cancelFieldError.value = ''
  try {
    shipment.value = await shipmentService.cancel(id.value, cancelReason.value.trim())
    cancelOpen.value = false
    notice.value = 'Đã hủy yêu cầu.'
    eventList.value?.reload()
  } catch (err) {
    cancelFieldError.value = fieldErrors(err).reason ?? ''
    cancelError.value = cancelFieldError.value ? '' : err?.message || 'Chưa hủy được.'
    if (err?.code === API_ERROR.INVALID_TRANSITION) load() // trạng thái mới (E1)
  } finally {
    cancelBusy.value = false
  }
}

watch(id, () => {
  editing.value = false
  notice.value = route.query.created ? 'Đã gửi yêu cầu. Nhân viên sẽ kiểm tra và duyệt.' : ''
  load()
}, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="shipment-title">
    <RouterLink :to="{ name: 'shop-shipments' }" class="back-link">
      <AppIcon name="arrow-left" :size="16" />Vận đơn của tôi
    </RouterLink>

    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải vận đơn…</p>

    <div v-else-if="notFound" class="card">
      <h1 id="shipment-title">Không tìm thấy vận đơn</h1>
      <p class="muted">Vận đơn không tồn tại hoặc không thuộc Shop của bạn.</p>
    </div>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost btn--sm" @click="load">Tải lại</button>
    </div>

    <template v-else-if="shipment">
      <header class="detail-header">
        <div>
          <div class="title-row">
            <h1 id="shipment-title">{{ shipment.tracking_code || shipment.request_code }}</h1>
            <StatusBadge :value="shipment.status" />
          </div>
          <p class="muted">
            Mã yêu cầu {{ shipment.request_code }} ·
            <template v-if="shipment.tracking_code">Mã vận đơn {{ shipment.tracking_code }}</template>
            <template v-else>Mã vận đơn được cấp khi Nhân viên duyệt</template>
            · Tạo lúc {{ formatDateTime(shipment.created_at) }}
          </p>
        </div>
        <div v-if="!editing && (canEdit || canCancel)" class="page__actions">
          <button v-if="canCancel" type="button" class="btn btn--danger-outline" @click="openCancel">
            <AppIcon name="ban" :size="16" />Hủy yêu cầu
          </button>
          <button v-if="canEdit" type="button" class="btn btn--primary" @click="startEdit">
            <AppIcon name="pencil" :size="16" />Sửa yêu cầu
          </button>
        </div>
      </header>

      <p v-if="notice" class="alert alert--success" role="status">{{ notice }}</p>
      <p v-if="shipment.rejection_reason" class="alert alert--danger">
        <strong>Yêu cầu bị từ chối.</strong> Lý do: {{ shipment.rejection_reason }}
      </p>

      <div class="detail-layout">
        <!-- Xem -->
        <ShipmentInfoCards v-if="!editing" :shipment="shipment">
          <!-- Spec 008 D6: hàng hoàn đã về điểm tập kết → Shop biết đến đâu nhận -->
          <HubCard v-if="awaitingPickup" title="Đến nhận hàng hoàn tại">
            <p class="muted hub-hint">Hàng hoàn đang ở điểm tập kết. Khi đến nhận, Nhân viên sẽ kiểm tra người nhận
              thuộc Shop hoặc được Shop ủy quyền.</p>
          </HubCard>
        </ShipmentInfoCards>

        <!-- Sửa -->
        <div v-else class="detail-edit">
          <div v-if="staleState" class="alert alert--warning" role="alert">
            <p class="alert__text">{{ formMessage }}</p>
            <button type="button" class="btn btn--ghost" @click="reloadLatest">Tải bản mới nhất</button>
          </div>
          <p v-else-if="formMessage" class="alert alert--danger" role="alert">{{ formMessage }}</p>
          <ShipmentForm :shipment="shipment" :wards="wardStore.items ?? []" :errors="errors" :submitting="saving"
                        submit-label="Lưu thay đổi" @submit="save" @cancel="editing = false" />
        </div>

        <!-- Lịch sử -->
        <ShipmentEventList ref="eventList" :shipment-id="id" />
      </div>

      <ConfirmDialog :open="cancelOpen" title="Hủy yêu cầu gửi hàng?" confirm-label="Hủy yêu cầu"
                     cancel-label="Không hủy" tone="danger" :busy="cancelBusy" :confirm-disabled="!canCancel"
                     @confirm="confirmCancel" @cancel="cancelOpen = false">
        <p>Yêu cầu <strong>{{ shipment.request_code }}</strong> sẽ chuyển sang Đã hủy và không được duyệt nữa.
          Bản ghi vẫn được giữ để tra cứu.</p>
        <FormField v-model="cancelReason" label="Lý do (không bắt buộc)" multiline :disabled="cancelBusy"
                   :maxlength="meta.limits.cancel_reason_max_length" :error="cancelFieldError" />
        <p v-if="cancelError" class="alert alert--danger" role="alert">{{ cancelError }}</p>
      </ConfirmDialog>
    </template>
  </section>
</template>

<style scoped>
.hub-hint { margin: 12px 0 0; font-size: .875rem; }
</style>
