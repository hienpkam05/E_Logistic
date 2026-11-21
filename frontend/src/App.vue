<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'
import { useAuthStore } from './stores/auth'
import { useMetaStore } from './stores/meta'

const meta = useMetaStore()
const auth = useAuthStore()
const route = useRoute()

// Trang công khai (đăng nhập, quên mật khẩu, 404) dùng khung trống.
const withLayout = computed(() => auth.isAuthenticated && !route.meta.public)

function loadChoices(force = false) {
  // Lỗi đã nằm trong meta.error để hiển thị; không chặn trang.
  meta.load({ force }).catch(() => {})
}

onMounted(() => loadChoices())
</script>

<template>
  <div v-if="meta.error" class="app-alert" role="alert">
    <span>Chưa tải được danh mục trạng thái: {{ meta.error.message }}</span>
    <button type="button" :disabled="meta.loading" @click="loadChoices(true)">Thử lại</button>
  </div>
  <AppLayout v-if="withLayout">
    <RouterView />
  </AppLayout>
  <RouterView v-else />
</template>
