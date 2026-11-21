// Dựng router + pinia tối thiểu để mount view trong test.
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

const Blank = { template: '<div class="blank-route" />' }
const ROUTE_NAMES = [
  ['/login', 'login'], ['/forgot-password', 'forgot-password'], ['/account/profile', 'profile'],
  ['/account/password', 'change-password'], ['/notifications', 'notifications'],
  ['/shop', 'shop-home'], ['/staff', 'staff-home'], ['/shipper', 'shipper-home'],
  ['/staff/accounts', 'staff-accounts'], ['/staff/accounts/new', 'staff-account-new'],
  ['/staff/accounts/:id', 'staff-account-detail'],
]

export async function mountView(component, { path = '/', props = {} } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: Blank }, ...ROUTE_NAMES.map(([p, name]) => ({ path: p, name, component: Blank }))],
  })
  await router.push(path)
  const wrapper = mount(component, { props, global: { plugins: [pinia, router] }, attachTo: document.body })
  return { wrapper, router, pinia }
}

/**
 * Mount view QUA <RouterView> như app thật — cần cho guard trong component (onBeforeRouteLeave),
 * vì guard chỉ đăng ký khi component là route component đang được RouterView render.
 */
export async function mountRouted(component, { routePath, path }) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const routes = [{ path: '/', component: Blank }, ...ROUTE_NAMES.map(([p, name]) => ({
    path: p, name, component: p === routePath ? component : Blank,
  }))]
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  const wrapper = mount({ template: '<RouterView />' }, { global: { plugins: [pinia, router] }, attachTo: document.body })
  return { wrapper, router, pinia }
}

export const flush = () => new Promise((resolve) => setTimeout(resolve, 0))
