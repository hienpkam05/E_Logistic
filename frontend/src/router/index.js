import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { CHANGE_PASSWORD_ROUTE, resolveNavigation } from './guard'
import { ROLES } from './roles'

const routes = [
  // "/" -> /login; guard đưa người đã đăng nhập từ /login về trang chủ vai trò (guestOnly).
  { path: '/', name: 'home', redirect: { name: 'login' } },

  // Công khai
  { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'),
    meta: { public: true, guestOnly: true } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('../views/auth/ForgotPasswordView.vue'),
    meta: { public: true } },

  // Mọi vai trò đã đăng nhập
  { path: '/account/profile', name: 'profile', component: () => import('../views/account/ProfileView.vue') },
  { path: '/account/password', name: CHANGE_PASSWORD_ROUTE,
    component: () => import('../views/account/ChangePasswordView.vue') },
  { path: '/notifications', name: 'notifications', component: () => import('../views/account/NotificationsView.vue') },

  // Trang chủ theo vai trò
  { path: '/shop', name: 'shop-home', component: () => import('../views/shop/ShopHomeView.vue'),
    meta: { roles: [ROLES.SHOP] } },
  { path: '/staff', name: 'staff-home', component: () => import('../views/staff/StaffHomeView.vue'),
    meta: { roles: [ROLES.ADMIN] } },
  // Quản lý tài khoản (spec 003). "Quản lý Shipper" = cùng màn hình với ?role=SHIPPER.
  { path: '/staff/accounts', name: 'staff-accounts', component: () => import('../views/staff/AccountListView.vue'),
    meta: { roles: [ROLES.ADMIN] } },
  { path: '/staff/accounts/new', name: 'staff-account-new',
    component: () => import('../views/staff/AccountCreateView.vue'), meta: { roles: [ROLES.ADMIN] } },
  { path: '/staff/accounts/:id(\\d+)', name: 'staff-account-detail',
    component: () => import('../views/staff/AccountDetailView.vue'), meta: { roles: [ROLES.ADMIN] } },
  { path: '/shipper', name: 'shipper-home', component: () => import('../views/shipper/ShipperHomeView.vue'),
    meta: { roles: [ROLES.SHIPPER] } },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue'),
    meta: { public: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.restore() // chỉ gọi backend lần đầu
  return resolveNavigation(to, auth)
})

export default router
