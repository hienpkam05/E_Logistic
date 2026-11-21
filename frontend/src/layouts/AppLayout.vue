<script setup>
// Khung chung cho mọi trang cần đăng nhập (spec 002 mục 4.2).
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { homeRouteFor, menuFor } from '../router/roles'
import { useAuthStore } from '../stores/auth'
import { useMetaStore } from '../stores/meta'
import { useNotificationStore } from '../stores/notifications'

const auth = useAuthStore()
const meta = useMetaStore()
const notifications = useNotificationStore()
const router = useRouter()

const roleLabel = computed(() => meta.label('user_roles', auth.role))
const homeRoute = computed(() => homeRouteFor(auth.role))
const roleMenu = computed(() => menuFor(auth.role))
const unread = computed(() => notifications.unreadCount)
const unreadText = computed(() => (unread.value > 99 ? '99+' : String(unread.value)))
const loggingOut = ref(false)

async function onLogout() {
  loggingOut.value = true
  const { serverConfirmed } = await auth.logout()
  loggingOut.value = false
  router.push({ name: 'login', query: serverConfirmed ? {} : { logout: 'unconfirmed' } })
}
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink :to="homeRoute" class="app-header__brand">HTT EXPRESS</RouterLink>

      <nav v-if="!auth.mustChangePassword" class="app-header__nav" aria-label="Điều hướng chính">
        <RouterLink v-for="item in roleMenu" :key="item.label" :to="item.to">{{ item.label }}</RouterLink>
        <RouterLink :to="{ name: 'notifications' }" class="app-header__bell">
          Thông báo
          <span v-if="unread > 0" class="app-header__count" :aria-label="`${unread} chưa đọc`">{{ unreadText }}</span>
        </RouterLink>
        <RouterLink :to="{ name: 'profile' }">Thông tin cá nhân</RouterLink>
        <RouterLink :to="{ name: 'change-password' }">Đổi mật khẩu</RouterLink>
      </nav>

      <div class="app-header__user">
        <span class="app-header__name">{{ auth.user?.full_name }}</span>
        <span class="app-header__role">{{ roleLabel }}</span>
        <button type="button" class="btn btn--ghost" :disabled="loggingOut" @click="onLogout">
          {{ loggingOut ? 'Đang đăng xuất…' : 'Đăng xuất' }}
        </button>
      </div>
    </header>

    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-header {
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  padding: 12px 24px; background: white; border-bottom: 1px solid var(--border);
}
.app-header__brand { font-weight: 800; letter-spacing: .06em; text-decoration: none; color: var(--brand); }
.app-header__nav { display: flex; gap: 16px; flex-wrap: wrap; flex: 1; }
.app-header__nav a { text-decoration: none; color: var(--text); }
.app-header__nav a.router-link-active { color: var(--brand); font-weight: 600; }
.app-header__bell { display: inline-flex; align-items: center; gap: 6px; }
.app-header__count {
  min-width: 20px; padding: 0 6px; border-radius: 999px; text-align: center;
  font-size: .75rem; font-weight: 700; color: white; background: var(--tone-danger-fg);
}
.app-header__user { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.app-header__name { font-weight: 600; }
.app-header__role { font-size: .8125rem; color: var(--muted); }
.app-main { flex: 1; width: 100%; max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
@media (max-width: 720px) {
  .app-header { padding: 12px 16px; gap: 12px; }
  .app-header__user { margin-left: 0; width: 100%; }
  .app-main { padding: 20px 16px; }
}
</style>
