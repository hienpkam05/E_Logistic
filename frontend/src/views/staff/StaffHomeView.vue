<script setup>
// Trang chủ Nhân viên. Spec 005 D8: ô "N yêu cầu chờ duyệt" — số lấy từ `count` của API danh sách, không thêm API.
import { onMounted, ref } from 'vue'
import HighlightTile from '../../components/common/HighlightTile.vue'
import RoleHome from '../../components/common/RoleHome.vue'
import * as shipmentService from '../../services/shipmentService'
import { SHIPMENT_STATUS } from '../../utils/statusTones'

const upcoming = ['Phân công Shipper giao hàng, giao lại, hoàn hàng', 'Đổi Shipper khi nhiệm vụ đang mở']

const pending = ref(null)
const pendingError = ref(false)

onMounted(async () => {
  try {
    pending.value = (await shipmentService.list({ status: [SHIPMENT_STATUS.PENDING_APPROVAL] })).count
  } catch {
    pendingError.value = true
  }
})
</script>

<template>
  <RoleHome :upcoming="upcoming">
    <template #highlights>
      <HighlightTile :to="{ name: 'staff-shipments' }" icon="clipboard" label="yêu cầu chờ duyệt" :value="pending"
                     :error="pendingError" zero-hint="Đã xử lý hết" active-hint="Xử lý theo thứ tự đến (cũ nhất trước)" />
    </template>
  </RoleHome>
</template>
