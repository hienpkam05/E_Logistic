<script setup>
import RoleHome from '../../components/common/RoleHome.vue'

const upcoming = ['Tạo và quản lý yêu cầu gửi hàng', 'Theo dõi vận đơn và lịch sử vận chuyển', 'Nhận hàng hoàn tại điểm tập kết']
</script>

<template>
  <RoleHome :upcoming="upcoming" />
</template>
