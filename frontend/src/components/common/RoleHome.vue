<script setup>
// Trang chủ dùng chung cho ba vai trò: lời chào + lối tắt chức năng; chức năng nghiệp vụ thêm ở các spec sau.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { menuFor } from '../../router/roles'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { useNotificationStore } from '../../stores/notifications'
import AppIcon from './AppIcon.vue'

defineProps({
  // Mô tả ngắn các chức năng sắp có của vai trò, hiển thị dạng danh sách.
  upcoming: { type: Array, default: () => [] },
})

const auth = useAuthStore()
const meta = useMetaStore()
const notifications = useNotificationStore()
const roleLabel = computed(() => meta.label('user_roles', auth.role))
const features = computed(() => menuFor(auth.role))
const accountLinks = computed(() => [
  { label: 'Thông báo', to: { name: 'notifications' }, icon: 'bell',
    hint: notifications.unreadCount ? `${notifications.unreadCount} chưa đọc` : 'Không có thông báo mới' },
  { label: 'Thông tin cá nhân', to: { name: 'profile' }, icon: 'user', hint: 'Họ tên, số điện thoại, địa chỉ' },
  { label: 'Đổi mật khẩu', to: { name: 'change-password' }, icon: 'key', hint: 'Bảo vệ tài khoản của bạn' },
])
</script>

<template>
  <section class="page" aria-labelledby="home-title">
    <div class="welcome">
      <div>
        <p class="welcome__role">{{ roleLabel }}</p>
        <h1 id="home-title">Xin chào, {{ auth.user?.full_name }}</h1>
        <p class="welcome__lead">Chúc bạn một ngày làm việc hiệu quả cùng HTT EXPRESS.</p>
      </div>
      <span class="welcome__art" aria-hidden="true"><AppIcon name="truck" :size="64" /></span>
    </div>

    <!-- Số liệu cần chú ý của vai trò (vd Nhân viên: yêu cầu chờ duyệt) -->
    <slot name="highlights" />

    <section v-if="features.length" aria-labelledby="features-title">
      <h2 id="features-title" class="section-title">Chức năng</h2>
      <div class="tiles">
        <RouterLink v-for="item in features" :key="item.label" :to="item.to" class="tile tile--primary">
          <span class="tile__icon"><AppIcon :name="item.icon" :size="22" /></span>
          <span class="tile__label">{{ item.label }}</span>
          <AppIcon name="chevron-right" class="tile__arrow" />
        </RouterLink>
      </div>
    </section>

    <section aria-labelledby="account-title">
      <h2 id="account-title" class="section-title">Tài khoản</h2>
      <div class="tiles">
        <RouterLink v-for="item in accountLinks" :key="item.label" :to="item.to" class="tile">
          <span class="tile__icon"><AppIcon :name="item.icon" :size="22" /></span>
          <span class="tile__text">
            <span class="tile__label">{{ item.label }}</span>
            <span class="tile__hint">{{ item.hint }}</span>
          </span>
          <AppIcon name="chevron-right" class="tile__arrow" />
        </RouterLink>
      </div>
    </section>

    <article v-if="upcoming.length" class="card">
      <h2 class="card__title"><span class="card__title-icon"><AppIcon name="clock" /></span>Sắp có</h2>
      <ul class="upcoming">
        <li v-for="item in upcoming" :key="item">{{ item }}</li>
      </ul>
    </article>
  </section>
</template>

<style scoped>
.welcome {
  position: relative; overflow: hidden; display: flex; align-items: center; justify-content: space-between; gap: 24px;
  padding: 28px 32px; color: var(--brand-contrast); border-radius: var(--radius-lg);
  background: radial-gradient(120% 140% at 0% 0%, var(--brand-light) 0%, var(--brand) 50%, var(--brand-strong) 100%);
  box-shadow: var(--shadow);
}
.welcome h1 { margin: 0; color: var(--brand-contrast); }
.welcome__role { margin: 0 0 6px; font-size: .75rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: rgba(255, 255, 255, .75); }
.welcome__lead { margin: 8px 0 0; color: rgba(255, 255, 255, .8); }
.welcome__art {
  display: grid; place-items: center; width: 112px; height: 112px; flex-shrink: 0; border-radius: 50%;
  background: rgba(255, 255, 255, .12); color: rgba(255, 255, 255, .9);
}
.section-title { margin: 0 0 12px; font-size: .8125rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.tile {
  display: flex; align-items: center; gap: 14px; padding: 18px 20px; color: var(--text); text-decoration: none;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-sm);
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.tile:hover { text-decoration: none; border-color: var(--brand); box-shadow: var(--shadow); transform: translateY(-1px); }
.tile__icon { display: grid; place-items: center; width: 44px; height: 44px; flex-shrink: 0; border-radius: 12px; color: var(--brand); background: var(--brand-soft); }
.tile--primary .tile__icon { color: var(--brand-contrast); background: var(--brand); }
.tile__text { display: flex; flex-direction: column; min-width: 0; }
.tile__label { font-weight: 600; }
.tile__hint { font-size: .8125rem; color: var(--muted); }
.tile__arrow { margin-left: auto; color: var(--subtle); }
.tile:hover .tile__arrow { color: var(--brand); }
.upcoming { margin: 0; padding-left: 20px; color: var(--muted); line-height: 1.9; }
@media (max-width: 640px) {
  .welcome { padding: 22px; }
  .welcome__art { display: none; }
}
</style>
