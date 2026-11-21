<script setup>
import RoleHome from '../../components/common/RoleHome.vue'

const upcoming = ['Xem nhiệm vụ lấy, giao, hoàn hàng được phân công', 'Cập nhật kết quả và ghi nhận COD', 'Chia sẻ vị trí khi làm nhiệm vụ']
</script>

<template>
  <RoleHome :upcoming="upcoming" />
</template>
