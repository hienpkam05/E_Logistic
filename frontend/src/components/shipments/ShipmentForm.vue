<script setup>
// Form yêu cầu gửi hàng dùng chung cho TẠO (UC05.2) và SỬA (UC05.1).
// Giá trị giữ dạng chuỗi trong form; đổi sang số/null khi gửi. Giới hạn số lấy từ /meta/choices/ (limits).
import { computed, reactive, watch } from 'vue'
import AppIcon from '../common/AppIcon.vue'
import FormField from '../common/FormField.vue'
import WardSelect from '../common/WardSelect.vue'
import { useMetaStore } from '../../stores/meta'
import { formatVnd } from '../../utils/format'

const props = defineProps({
  // Đơn đang sửa (API Shipment) hoặc null khi tạo mới.
  shipment: { type: Object, default: null },
  // Điền sẵn người gửi khi tạo mới (D4): { name, phone, address } từ hồ sơ Shop.
  senderDefaults: { type: Object, default: () => ({}) },
  wards: { type: Array, default: () => [] },
  errors: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false },
  submitLabel: { type: String, default: 'Gửi yêu cầu' },
})
const emit = defineEmits(['submit', 'cancel'])

const meta = useMetaStore()
const limits = computed(() => meta.limits)

const text = (value) => (value === null || value === undefined ? '' : String(value))

function fromShipment(s) {
  return {
    sender_name: text(s.sender_name), sender_phone: text(s.sender_phone),
    pickup_ward: text(s.pickup_ward?.code), pickup_address: text(s.pickup_address),
    receiver_name: text(s.receiver_name), receiver_phone: text(s.receiver_phone),
    delivery_ward: text(s.delivery_ward?.code), delivery_address: text(s.delivery_address),
    package_description: text(s.package_description), package_count: text(s.package_count),
    weight_grams: text(s.weight_grams), cod_amount: text(s.cod_amount), note: text(s.note),
  }
}

function blank() {
  const d = props.senderDefaults
  return {
    sender_name: text(d.name), sender_phone: text(d.phone), pickup_ward: '', pickup_address: text(d.address),
    receiver_name: '', receiver_phone: '', delivery_ward: '', delivery_address: '',
    package_description: '', package_count: '1', weight_grams: '', cod_amount: '0', note: '',
  }
}

const form = reactive(props.shipment ? fromShipment(props.shipment) : blank())
// Nạp lại khi đơn được tải lại (vd sau xung đột 409).
watch(() => props.shipment, (s) => { if (s) Object.assign(form, fromShipment(s)) })

const codPreview = computed(() => {
  const n = Number(form.cod_amount)
  if (!form.cod_amount || !Number.isFinite(n)) return ''
  return n === 0 ? 'Không thu hộ' : formatVnd(n)
})

const toInt = (value) => (String(value).trim() === '' ? null : Number(value))

function payload() {
  return {
    sender_name: form.sender_name.trim(), sender_phone: form.sender_phone.trim(),
    pickup_ward: form.pickup_ward, pickup_address: form.pickup_address.trim(),
    receiver_name: form.receiver_name.trim(), receiver_phone: form.receiver_phone.trim(),
    delivery_ward: form.delivery_ward, delivery_address: form.delivery_address.trim(),
    package_description: form.package_description.trim(),
    package_count: toInt(form.package_count),
    weight_grams: toInt(form.weight_grams),
    cod_amount: toInt(form.cod_amount) ?? 0,
    note: form.note.trim(),
  }
}

function onSubmit() {
  if (!props.submitting) emit('submit', payload())
}
</script>

<template>
  <form class="form shipment-form" novalidate @submit.prevent="onSubmit">
    <fieldset class="card">
      <legend><span class="card__title-icon"><AppIcon name="send" /></span>Người gửi</legend>
      <div class="form-grid">
        <FormField v-model="form.sender_name" label="Họ tên người gửi" required :error="errors.sender_name" :disabled="submitting" />
        <FormField v-model="form.sender_phone" label="Số điện thoại" type="tel" required :error="errors.sender_phone" :disabled="submitting" />
        <WardSelect v-model="form.pickup_ward" label="Phường/xã lấy hàng" :wards="wards" required
                    :error="errors.pickup_ward" :disabled="submitting" />
        <FormField v-model="form.pickup_address" label="Địa chỉ lấy hàng (số nhà, đường)" required
                   :error="errors.pickup_address" :disabled="submitting" />
      </div>
    </fieldset>

    <fieldset class="card">
      <legend><span class="card__title-icon"><AppIcon name="map-pin" /></span>Người nhận</legend>
      <div class="form-grid">
        <FormField v-model="form.receiver_name" label="Họ tên người nhận" required :error="errors.receiver_name" :disabled="submitting" />
        <FormField v-model="form.receiver_phone" label="Số điện thoại" type="tel" required :error="errors.receiver_phone" :disabled="submitting" />
        <WardSelect v-model="form.delivery_ward" label="Phường/xã giao hàng" :wards="wards" required
                    :error="errors.delivery_ward" :disabled="submitting" />
        <FormField v-model="form.delivery_address" label="Địa chỉ giao hàng (số nhà, đường)" required
                   :error="errors.delivery_address" :disabled="submitting" />
      </div>
    </fieldset>

    <fieldset class="card">
      <legend><span class="card__title-icon"><AppIcon name="box" /></span>Kiện hàng</legend>
      <div class="form-grid">
        <FormField v-model="form.package_description" class="field--full" label="Mô tả hàng" required :error="errors.package_description" :disabled="submitting" />
        <FormField v-model="form.package_count" label="Số kiện" type="number" required
                   :hint="`Từ ${limits.package_count_min ?? 1} đến ${limits.package_count_max ?? ''} kiện.`"
                   :error="errors.package_count" :disabled="submitting" />
        <FormField v-model="form.weight_grams" label="Khối lượng (gram, không bắt buộc)" type="number"
                   :hint="limits.weight_grams_max ? `Tối đa ${limits.weight_grams_max} gram.` : ''"
                   :error="errors.weight_grams" :disabled="submitting" />
      </div>
    </fieldset>

    <fieldset class="card">
      <legend><span class="card__title-icon"><AppIcon name="wallet" /></span>Thu hộ (COD)</legend>
      <div class="form-grid">
        <FormField v-model="form.cod_amount" label="Số tiền thu hộ (VND)" type="number" required
                   :hint="`Nhập 0 nếu không thu hộ.${limits.cod_max_vnd ? ` Tối đa ${formatVnd(limits.cod_max_vnd)}.` : ''}`"
                   :error="errors.cod_amount" :disabled="submitting" />
        <p v-if="codPreview" class="muted cod-preview field--full" aria-live="polite">{{ codPreview }}</p>
        <FormField v-model="form.note" class="field--full" label="Ghi chú cho Shipper (không bắt buộc)" multiline :error="errors.note" :disabled="submitting" />
      </div>
    </fieldset>

    <p class="muted">Phí vận chuyển và thanh toán không xử lý trong hệ thống.</p>
    <div class="form__actions">
      <button type="submit" class="btn btn--primary" :disabled="submitting">
        {{ submitting ? 'Đang gửi…' : submitLabel }}
      </button>
      <button type="button" class="btn btn--ghost" :disabled="submitting" @click="emit('cancel')">Hủy</button>
    </div>
  </form>
</template>

<style scoped>
.shipment-form fieldset { display: flex; flex-direction: column; gap: 18px; margin: 0; min-width: 0; }
.shipment-form legend { display: flex; align-items: center; gap: 10px; float: left; width: 100%; padding: 0; font-weight: 600; font-size: 1rem; }
.shipment-form legend + .form-grid { clear: both; }
.cod-preview { margin: -8px 0 0; font-weight: 600; color: var(--brand); }
</style>
