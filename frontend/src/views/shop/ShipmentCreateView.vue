<script setup>
// UC05.2 — tạo yêu cầu gửi hàng. Hủy/rời form không tạo gì (A1).
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ShipmentForm from '../../components/shipments/ShipmentForm.vue'
import * as shipmentService from '../../services/shipmentService'
import { useAuthStore } from '../../stores/auth'
import { useWardStore } from '../../stores/wards'
import { fieldErrors, generalMessage } from '../../utils/formErrors'

const router = useRouter()
const auth = useAuthStore()
const wardStore = useWardStore()

const errors = ref({})
const message = ref('')
const submitting = ref(false)

// D4: người gửi điền sẵn từ hồ sơ Shop, sửa được trên từng đơn.
const senderDefaults = computed(() => ({
  name: auth.user?.full_name, phone: auth.user?.phone, address: auth.user?.address,
}))

function loadWards(force = false) {
  wardStore.load({ force }).catch(() => {})
}

async function onSubmit(payload) {
  submitting.value = true
  errors.value = {}
  message.value = ''
  try {
    const shipment = await shipmentService.create(payload)
    await router.replace({ name: 'shop-shipment-detail', params: { id: shipment.id }, query: { created: '1' } })
  } catch (err) {
    errors.value = fieldErrors(err)
    message.value = generalMessage(err)
    window.scrollTo?.({ top: 0, behavior: 'smooth' })
  } finally {
    submitting.value = false
  }
}

onMounted(() => loadWards())
</script>

<template>
  <section class="page page--narrow" aria-labelledby="create-shipment-title">
    <div class="page__header">
      <div>
        <h1 id="create-shipment-title">Tạo yêu cầu gửi hàng</h1>
        <p class="page__subtitle">Yêu cầu sẽ ở trạng thái Chờ xác nhận. Mã vận đơn được cấp khi Nhân viên duyệt.</p>
      </div>
    </div>

    <div v-if="wardStore.error" class="alert alert--danger" role="alert">
      <p class="alert__text">Chưa tải được danh sách phường/xã: {{ wardStore.error.message }}</p>
      <button type="button" class="btn btn--ghost" @click="loadWards(true)">Tải lại</button>
    </div>
    <p v-else-if="wardStore.ready && !wardStore.items.length" class="alert alert--warning" role="alert">
      Hệ thống chưa có danh sách phường/xã Hà Nội nên chưa tạo được yêu cầu. Vui lòng liên hệ Nhân viên.
    </p>

    <p v-if="message" class="alert alert--danger" role="alert">{{ message }}</p>

    <ShipmentForm :wards="wardStore.items ?? []" :sender-defaults="senderDefaults" :errors="errors"
                  :submitting="submitting" submit-label="Gửi yêu cầu"
                  @submit="onSubmit" @cancel="router.push({ name: 'shop-shipments' })" />
  </section>
</template>
