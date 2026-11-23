<script setup>
// Thẻ thông tin vận đơn (người gửi, người nhận, kiện hàng, thu hộ) — dùng chung màn Shop (UC05.4) và Nhân viên (UC05.7).
// `showShop`: thêm thẻ Shop gửi hàng (Nhân viên cần biết ai gửi). Slot mặc định: thẻ bổ sung của từng màn.
import { computed } from 'vue'
import { formatDateTime, formatPhone, formatVnd } from '../../utils/format'
import AppIcon from '../common/AppIcon.vue'

const props = defineProps({
  shipment: { type: Object, required: true },
  showShop: { type: Boolean, default: false },
})

const sections = computed(() => {
  const s = props.shipment
  const list = [
    ['Người gửi', 'send', [['Họ tên', s.sender_name], ['Số điện thoại', formatPhone(s.sender_phone)],
      ['Lấy hàng tại', `${s.pickup_address}, ${s.pickup_ward?.name ?? ''}`]]],
    ['Người nhận', 'map-pin', [['Họ tên', s.receiver_name], ['Số điện thoại', formatPhone(s.receiver_phone)],
      ['Giao đến', `${s.delivery_address}, ${s.delivery_ward?.name ?? ''}`]]],
    ['Kiện hàng', 'box', [['Mô tả', s.package_description], ['Số kiện', s.package_count],
      ['Khối lượng', s.weight_grams ? `${s.weight_grams} gram` : 'Không ghi']]],
    ['Thu hộ', 'wallet', [['COD', s.cod_amount ? formatVnd(s.cod_amount) : 'Không thu hộ'], ['Ghi chú', s.note || 'Không có']]],
  ]
  // Spec 007 D11: đơn Đã giao → kết quả giao (backend chỉ trả `delivery` khi Đã giao).
  if (s.delivery) {
    list.unshift(['Kết quả giao', 'check', [['Giao lúc', formatDateTime(s.delivery.delivered_at)],
      ['Lần giao', String(s.delivery.attempt_no)],
      ['COD đã thu', s.delivery.cod_collected ? formatVnd(s.delivery.cod_collected) : 'Không thu hộ']]])
  }
  // Spec 008: đơn Đã hoàn về Shop → ai nhận lại, lúc nào (backend chỉ trả `return_result` khi đã hoàn tất).
  if (s.return_result) {
    list.unshift(['Kết quả hoàn', 'check', [['Nhận lại lúc', formatDateTime(s.return_result.received_at)],
      ['Người nhận', s.return_result.receiver_name]]])
  }
  if (props.showShop && s.shop) {
    list.unshift(['Shop gửi hàng', 'user', [['Tên Shop', s.shop.full_name], ['Tên đăng nhập', s.shop.username],
      ['Số điện thoại', formatPhone(s.shop.phone)]]])
  }
  return list
})
</script>

<template>
  <div class="detail-layout__main">
    <article v-for="[title, icon, rows] in sections" :key="title" class="card">
      <h2 class="card__title"><span class="card__title-icon"><AppIcon :name="icon" /></span>{{ title }}</h2>
      <dl class="details">
        <template v-for="[label, value] in rows" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value }}</dd>
        </template>
      </dl>
    </article>
    <slot />
  </div>
</template>
