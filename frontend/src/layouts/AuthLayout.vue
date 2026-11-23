<script setup>
// Khung trang công khai (đăng nhập, quên mật khẩu): nửa trái giới thiệu, nửa phải là nội dung (slot).
import AppIcon from '../components/common/AppIcon.vue'

const FEATURES = [
  ['package', 'Shop tạo và theo dõi yêu cầu gửi hàng'],
  ['clipboard', 'Nhân viên duyệt đơn, điều phối lấy – giao'],
  ['truck', 'Shipper cập nhật kết quả lấy, giao hàng'],
]
</script>

<template>
  <div class="auth-page">
    <aside class="auth-hero">
      <div class="auth-hero__brand">
        <span class="auth-hero__logo"><AppIcon name="truck" :size="22" /></span>
        HTT EXPRESS
      </div>
      <div>
        <h2>Giao nhận nội thành Hà Nội, gọn trong một hệ thống.</h2>
        <p>Theo dõi từng vận đơn từ lúc Shop gửi yêu cầu đến khi giao tận tay người nhận.</p>
      </div>
      <ul class="auth-hero__features">
        <li v-for="[icon, text] in FEATURES" :key="text"><AppIcon :name="icon" :size="20" />{{ text }}</li>
      </ul>
      <p class="auth-hero__foot">© HTT EXPRESS · Hà Nội</p>
    </aside>
    <main class="auth-main">
      <slot />
    </main>
  </div>
</template>
