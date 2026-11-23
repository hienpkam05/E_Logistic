<script setup>
// Khung chung cho mọi trang cần đăng nhập (spec 002 mục 4.2): thanh bên (menu theo vai trò) + thanh trên.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/common/AppIcon.vue'
import { homeRouteFor, menuFor } from '../router/roles'
import { useAuthStore } from '../stores/auth'
import { useMetaStore } from '../stores/meta'
import { useNotificationStore } from '../stores/notifications'
import { initials } from '../utils/format'
import { activeIndex } from '../utils/navActive'

const COLLAPSE_KEY = 'htt.sidebar.collapsed' // chỉ là tiện ích hiển thị của từng trình duyệt

const auth = useAuthStore()
const meta = useMetaStore()
const notifications = useNotificationStore()
const route = useRoute()
const router = useRouter()

const roleLabel = computed(() => meta.label('user_roles', auth.role))
const homeRoute = computed(() => homeRouteFor(auth.role))
const navItems = computed(() => [
  { label: 'Tổng quan', to: homeRoute.value, icon: 'home' },
  ...menuFor(auth.role),
])
const activeNav = computed(() => activeIndex(navItems.value, route, (to) => router.resolve(to)))
const pageTitle = computed(() => route.meta.title || navItems.value[activeNav.value]?.label || 'HTT EXPRESS')
const unread = computed(() => notifications.unreadCount)
const unreadText = computed(() => (unread.value > 99 ? '99+' : String(unread.value)))
const userInitials = computed(() => initials(auth.user?.full_name || auth.user?.username))

// --- Thu gọn thanh bên (máy tính) / ngăn kéo (điện thoại) ---
function readCollapsed() {
  try { return localStorage.getItem(COLLAPSE_KEY) === '1' } catch { return false }
}
const collapsed = ref(readCollapsed())
const drawerOpen = ref(false)
function toggleCollapsed() {
  collapsed.value = !collapsed.value
  try { localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0') } catch { /* không lưu được thì thôi */ }
}

// --- Menu người dùng ---
const userMenuOpen = ref(false)
const userMenu = ref(null)
function onDocumentClick(event) {
  if (userMenuOpen.value && userMenu.value && !userMenu.value.contains(event.target)) userMenuOpen.value = false
}
function onKeydown(event) {
  if (event.key === 'Escape') {
    userMenuOpen.value = false
    drawerOpen.value = false
  }
}
onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
})
watch(() => route.fullPath, () => {
  drawerOpen.value = false
  userMenuOpen.value = false
})

const loggingOut = ref(false)
async function onLogout() {
  loggingOut.value = true
  const { serverConfirmed } = await auth.logout()
  loggingOut.value = false
  router.push({ name: 'login', query: serverConfirmed ? {} : { logout: 'unconfirmed' } })
}
</script>

<template>
  <div class="shell" :class="{ 'shell--collapsed': collapsed, 'shell--drawer': drawerOpen }">
    <aside class="sidebar" aria-label="Thanh bên">
      <RouterLink :to="homeRoute" class="sidebar__brand" title="HTT EXPRESS">
        <span class="sidebar__logo"><AppIcon name="truck" :size="20" /></span>
        <span class="sidebar__brand-text">HTT <strong>EXPRESS</strong></span>
      </RouterLink>
      <button type="button" class="sidebar__close btn btn--icon" aria-label="Đóng menu" @click="drawerOpen = false">
        <AppIcon name="close" />
      </button>

      <nav v-if="!auth.mustChangePassword" class="sidebar__nav" aria-label="Điều hướng chính">
        <RouterLink v-for="(item, index) in navItems" :key="item.label" :to="item.to" class="sidebar__link"
                    :class="{ 'is-active': index === activeNav }" :aria-current="index === activeNav ? 'page' : undefined"
                    :title="collapsed ? item.label : undefined">
          <AppIcon :name="item.icon" :size="20" />
          <span class="sidebar__label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <button type="button" class="sidebar__toggle" :aria-expanded="!collapsed" @click="toggleCollapsed">
        <AppIcon :name="collapsed ? 'panel-open' : 'panel-close'" :size="18" />
        <span class="sidebar__label">Thu gọn</span>
      </button>
    </aside>
    <div class="shell__backdrop" aria-hidden="true" @click="drawerOpen = false" />

    <div class="shell__body">
      <header class="topbar">
        <button type="button" class="topbar__menu btn btn--icon" aria-label="Mở menu" @click="drawerOpen = true">
          <AppIcon name="menu" :size="20" />
        </button>
        <p class="topbar__title">{{ pageTitle }}</p>

        <div class="topbar__actions">
          <RouterLink v-if="!auth.mustChangePassword" :to="{ name: 'notifications' }" class="topbar__icon-btn"
                      :aria-label="unread > 0 ? `Thông báo, ${unread} chưa đọc` : 'Thông báo'">
            <AppIcon name="bell" :size="20" />
            <span v-if="unread > 0" class="topbar__count">{{ unreadText }}</span>
          </RouterLink>

          <div ref="userMenu" class="user-menu">
            <button type="button" class="user-menu__trigger" aria-haspopup="menu" :aria-expanded="userMenuOpen"
                    @click="userMenuOpen = !userMenuOpen">
              <span class="avatar" aria-hidden="true">{{ userInitials }}</span>
              <span class="user-menu__who">
                <span class="user-menu__name">{{ auth.user?.full_name }}</span>
                <span class="user-menu__role">{{ roleLabel }}</span>
              </span>
              <AppIcon name="chevron-right" :size="16" class="user-menu__chevron" />
            </button>
            <div v-show="userMenuOpen" class="user-menu__panel" role="menu">
              <template v-if="!auth.mustChangePassword">
                <RouterLink :to="{ name: 'profile' }" class="user-menu__item" role="menuitem">
                  <AppIcon name="user" /> Thông tin cá nhân
                </RouterLink>
                <RouterLink :to="{ name: 'change-password' }" class="user-menu__item" role="menuitem">
                  <AppIcon name="key" /> Đổi mật khẩu
                </RouterLink>
                <hr class="user-menu__sep" />
              </template>
              <button type="button" class="user-menu__item user-menu__item--danger" role="menuitem"
                      :disabled="loggingOut" @click="onLogout">
                <AppIcon name="logout" /> {{ loggingOut ? 'Đang đăng xuất…' : 'Đăng xuất' }}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main class="shell__main">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: flex; }

/* ----- Thanh bên ----- */
.sidebar {
  position: sticky; top: 0; height: 100vh; width: var(--sidebar-width); flex-shrink: 0;
  display: flex; flex-direction: column; background: var(--surface); border-right: 1px solid var(--border);
  transition: width .2s ease;
}
.sidebar__brand {
  display: flex; align-items: center; gap: 12px; height: var(--topbar-height); padding: 0 20px;
  border-bottom: 1px solid var(--border); color: var(--brand); text-decoration: none; white-space: nowrap; overflow: hidden;
}
.sidebar__brand:hover { text-decoration: none; }
.sidebar__logo {
  display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; border-radius: 10px;
  color: var(--brand-contrast); background: linear-gradient(135deg, var(--brand-light), var(--brand-strong)); box-shadow: var(--shadow);
}
.sidebar__brand-text { font-size: 1.0625rem; letter-spacing: .04em; font-weight: 500; }
.sidebar__brand-text strong { font-weight: 800; }
.sidebar__close { display: none; }
.sidebar__nav { flex: 1; display: flex; flex-direction: column; gap: 4px; padding: 16px 12px; overflow-y: auto; }
.sidebar__link {
  display: flex; align-items: center; gap: 12px; padding: 11px 14px; border-radius: 10px;
  color: var(--text-secondary); font-weight: 500; white-space: nowrap; text-decoration: none; transition: background .15s, color .15s;
}
.sidebar__link:hover { background: var(--surface-muted); color: var(--text); text-decoration: none; }
.sidebar__link.is-active { color: var(--brand); background: var(--brand-soft); font-weight: 600; }
.sidebar__link .icon { color: var(--muted); }
.sidebar__link.is-active .icon { color: var(--brand); }
.sidebar__toggle {
  display: flex; align-items: center; justify-content: center; gap: 10px; margin: 0; padding: 18px;
  font: inherit; font-size: .875rem; color: var(--muted); cursor: pointer; background: none;
  border: none; border-top: 1px solid var(--border);
}
.sidebar__toggle:hover { color: var(--brand); }

.shell--collapsed .sidebar { width: var(--sidebar-collapsed); }
.shell--collapsed .sidebar__label, .shell--collapsed .sidebar__brand-text { display: none; }
.shell--collapsed .sidebar__brand { justify-content: center; padding: 0; }
.shell--collapsed .sidebar__link { justify-content: center; padding: 11px; }

/* ----- Thân trang ----- */
.shell__body { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar {
  position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 12px;
  height: var(--topbar-height); padding: 0 28px; background: rgba(255, 255, 255, .92);
  backdrop-filter: blur(8px); border-bottom: 1px solid var(--border);
}
.topbar__menu { display: none; color: var(--text); }
.topbar__title { margin: 0; font-size: 1.0625rem; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.topbar__actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.topbar__icon-btn {
  position: relative; display: grid; place-items: center; width: 42px; height: 42px; border-radius: 50%;
  color: var(--text-tertiary); transition: background .15s;
}
.topbar__icon-btn:hover { background: var(--surface-muted); color: var(--brand); }
.topbar__icon-btn.router-link-active { color: var(--brand); background: var(--brand-soft); }
.topbar__count {
  position: absolute; top: 4px; right: 2px; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 999px;
  display: grid; place-items: center; font-size: .6875rem; font-weight: 700; color: var(--brand-contrast);
  background: var(--tone-danger-fg); border: 2px solid var(--surface);
}

.user-menu { position: relative; }
.user-menu__trigger {
  display: flex; align-items: center; gap: 10px; padding: 5px 10px 5px 5px; border-radius: 999px;
  font: inherit; text-align: left; cursor: pointer; background: none; border: 1px solid transparent;
}
.user-menu__trigger:hover, .user-menu__trigger[aria-expanded='true'] { background: var(--surface-muted); border-color: var(--border); }
.avatar {
  display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  font-size: .8125rem; font-weight: 700; color: var(--brand); background: var(--brand-soft);
}
.user-menu__who { display: flex; flex-direction: column; line-height: 1.25; }
.user-menu__name { font-weight: 600; font-size: .875rem; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-menu__role { font-size: .75rem; color: var(--muted); }
.user-menu__chevron { color: var(--subtle); transform: rotate(90deg); }
.user-menu__panel {
  position: absolute; right: 0; top: calc(100% + 8px); min-width: 220px; padding: 6px; z-index: 30;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-lg);
}
.user-menu__item {
  display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: var(--radius-sm);
  font: inherit; font-size: .9375rem; color: var(--text); text-decoration: none; background: none; border: none; cursor: pointer;
}
.user-menu__item:hover { background: var(--surface-muted); text-decoration: none; }
.user-menu__item .icon { color: var(--muted); }
.user-menu__item--danger, .user-menu__item--danger .icon { color: var(--tone-danger-fg); }
.user-menu__sep { margin: 6px 0; border: none; border-top: 1px solid var(--border); }

.shell__main { flex: 1; width: 100%; max-width: 1440px; margin: 0 auto; padding: 28px; }
.shell__backdrop { display: none; }

/* ----- Điện thoại / máy tính bảng: thanh bên thành ngăn kéo ----- */
@media (max-width: 960px) {
  .sidebar {
    position: fixed; z-index: 50; left: 0; width: var(--sidebar-width) !important;
    transform: translateX(-100%); transition: transform .2s ease; box-shadow: var(--shadow-lg);
  }
  .shell--drawer .sidebar { transform: none; }
  .shell--collapsed .sidebar__label, .shell--collapsed .sidebar__brand-text { display: inline; }
  .shell--collapsed .sidebar__brand { justify-content: flex-start; padding: 0 20px; }
  .shell--collapsed .sidebar__link { justify-content: flex-start; padding: 11px 14px; }
  .sidebar__toggle { display: none; }
  .sidebar__close { display: grid; position: absolute; top: 14px; right: 12px; color: var(--muted); }
  .shell--drawer .shell__backdrop { display: block; position: fixed; inset: 0; z-index: 40; background: rgba(16, 24, 40, .45); }
  .topbar { padding: 0 16px; }
  .topbar__menu { display: grid; }
  .user-menu__who, .user-menu__chevron { display: none; }
  .user-menu__trigger { padding: 3px; }
  .shell__main { padding: 20px 16px; }
}
</style>
