<script setup>
import RoleHome from '../../components/common/RoleHome.vue'

const upcoming = ['Duyệt hoặc từ chối yêu cầu gửi hàng', 'Phân công Shipper lấy, giao, hoàn hàng']
</script>

<template>
  <RoleHome :upcoming="upcoming" />
</template>
