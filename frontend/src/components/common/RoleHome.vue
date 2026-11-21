<script setup>
// Trang chủ tạm dùng chung cho ba vai trò; chức năng nghiệp vụ thêm ở các spec sau.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { menuFor } from '../../router/roles'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'

defineProps({
  // Mô tả ngắn các chức năng sắp có của vai trò, hiển thị dạng danh sách.
  upcoming: { type: Array, default: () => [] },
})

const auth = useAuthStore()
const meta = useMetaStore()
const roleLabel = computed(() => meta.label('user_roles', auth.role))
const features = computed(() => menuFor(auth.role))
</script>

<template>
  <section class="page" aria-labelledby="home-title">
    <p class="eyebrow">{{ roleLabel }}</p>
    <h1 id="home-title">Xin chào, {{ auth.user?.full_name }}</h1>

    <div class="grid">
      <article v-if="features.length" class="card">
        <h2>Chức năng</h2>
        <ul class="link-list">
          <li v-for="item in features" :key="item.label"><RouterLink :to="item.to">{{ item.label }}</RouterLink></li>
        </ul>
      </article>
      <article class="card">
        <h2>Tài khoản</h2>
        <ul class="link-list">
          <li><RouterLink :to="{ name: 'notifications' }">Xem thông báo</RouterLink></li>
          <li><RouterLink :to="{ name: 'profile' }">Thông tin cá nhân</RouterLink></li>
          <li><RouterLink :to="{ name: 'change-password' }">Đổi mật khẩu</RouterLink></li>
        </ul>
      </article>
      <article v-if="upcoming.length" class="card">
        <h2>Sắp có</h2>
        <ul>
          <li v-for="item in upcoming" :key="item">{{ item }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>
