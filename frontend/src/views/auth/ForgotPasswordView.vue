<script setup>
// UC01.3 Quên mật khẩu — phương án Nhân viên hỗ trợ sau xác minh (spec 001 D4, spec 002 D7).
import { RouterLink } from 'vue-router'
import { SUPPORT_CONTACT } from '../../config'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const contact = SUPPORT_CONTACT || 'Liên hệ Nhân viên HTT Express'
</script>

<template>
  <main class="auth-page">
    <section class="card auth-card" aria-labelledby="forgot-title">
      <p class="eyebrow">HTT EXPRESS · HÀ NỘI</p>
      <h1 id="forgot-title">Quên mật khẩu</h1>

      <p>Hệ thống không tự đặt lại mật khẩu qua email hay tin nhắn. Để lấy lại quyền truy cập:</p>
      <ol class="steps">
        <li><strong>{{ contact }}</strong> và cung cấp tên đăng nhập.</li>
        <li>Nhân viên xác minh danh tính của bạn (họ tên và số điện thoại đã đăng ký).</li>
        <li>Sau khi xác minh, Nhân viên cấp cho bạn một mật khẩu tạm.</li>
        <li>Đăng nhập bằng mật khẩu tạm — hệ thống sẽ yêu cầu bạn đặt mật khẩu mới ngay.</li>
      </ol>
      <p class="muted">Nhân viên không bao giờ hỏi mật khẩu hiện tại của bạn.</p>

      <RouterLink v-if="auth.isAuthenticated" :to="{ name: 'change-password' }" class="auth-card__link">
        Quay lại đổi mật khẩu
      </RouterLink>
      <RouterLink v-else :to="{ name: 'login' }" class="auth-card__link">Quay lại đăng nhập</RouterLink>
    </section>
  </main>
</template>
