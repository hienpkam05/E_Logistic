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
  // meta.title: tiêu đề thanh trên; trang thuộc menu thì AppLayout lấy tên mục menu đang mở.
  { path: '/account/profile', name: 'profile', component: () => import('../views/account/ProfileView.vue'),
    meta: { title: 'Thông tin cá nhân' } },
  { path: '/account/password', name: CHANGE_PASSWORD_ROUTE,
    component: () => import('../views/account/ChangePasswordView.vue'), meta: { title: 'Đổi mật khẩu' } },
  { path: '/notifications', name: 'notifications', component: () => import('../views/account/NotificationsView.vue'),
    meta: { title: 'Thông báo' } },

  // Trang chủ theo vai trò
  { path: '/shop', name: 'shop-home', component: () => import('../views/shop/ShopHomeView.vue'),
    meta: { roles: [ROLES.SHOP] } },
  // Yêu cầu gửi hàng (spec 004)
  { path: '/shop/shipments', name: 'shop-shipments', component: () => import('../views/shop/ShipmentListView.vue'),
    meta: { roles: [ROLES.SHOP] } },
  { path: '/shop/shipments/new', name: 'shop-shipment-new',
    component: () => import('../views/shop/ShipmentCreateView.vue'), meta: { roles: [ROLES.SHOP] } },
  { path: '/shop/shipments/:id(\\d+)', name: 'shop-shipment-detail',
    component: () => import('../views/shop/ShipmentDetailView.vue'), meta: { roles: [ROLES.SHOP] } },
  { path: '/staff', name: 'staff-home', component: () => import('../views/staff/StaffHomeView.vue'),
    meta: { roles: [ROLES.ADMIN] } },
  // Quản lý vận đơn (spec 005): Nhân viên xem toàn hệ thống, duyệt/từ chối.
  { path: '/staff/shipments', name: 'staff-shipments',
    component: () => import('../views/staff/StaffShipmentListView.vue'), meta: { roles: [ROLES.ADMIN] } },
  { path: '/staff/shipments/:id(\\d+)', name: 'staff-shipment-detail',
    component: () => import('../views/staff/StaffShipmentDetailView.vue'), meta: { roles: [ROLES.ADMIN] } },
  // Quản lý tài khoản (spec 003). "Quản lý Shipper" = cùng màn hình với ?role=SHIPPER.
  { path: '/staff/accounts', name: 'staff-accounts', component: () => import('../views/staff/AccountListView.vue'),
    meta: { roles: [ROLES.ADMIN] } },
  { path: '/staff/accounts/new', name: 'staff-account-new',
    component: () => import('../views/staff/AccountCreateView.vue'), meta: { roles: [ROLES.ADMIN] } },
  { path: '/staff/accounts/:id(\\d+)', name: 'staff-account-detail',
    component: () => import('../views/staff/AccountDetailView.vue'), meta: { roles: [ROLES.ADMIN] } },
  // Nhiệm vụ của Shipper (spec 006). Chú ý `\\d+` trong chuỗi JS — test router thật canh (bài học spec 005).
  { path: '/shipper/tasks', name: 'shipper-tasks', component: () => import('../views/shipper/TaskListView.vue'),
    meta: { roles: [ROLES.SHIPPER] } },
  { path: '/shipper/tasks/:id(\\d+)', name: 'shipper-task-detail',
    component: () => import('../views/shipper/TaskDetailView.vue'), meta: { roles: [ROLES.SHIPPER] } },
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
