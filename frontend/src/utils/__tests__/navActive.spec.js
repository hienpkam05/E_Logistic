import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { activeIndex } from '../navActive'

const Blank = { template: '<div />' }
const router = createRouter({
  history: createMemoryHistory(),
  routes: ['/shop', '/shop/shipments', '/shop/shipments/new', '/shop/shipments/:id', '/staff', '/staff/accounts',
    '/staff/accounts/:id', '/account/profile'].map((path, i) => ({ path, name: `r${i}`, component: Blank })),
})
const resolve = (to) => router.resolve(to)
const at = (fullPath) => router.resolve(fullPath)

const SHOP = [{ to: '/shop' }, { to: '/shop/shipments' }, { to: '/shop/shipments/new' }]
const ADMIN = [{ to: '/staff' }, { to: { path: '/staff/accounts' } }, { to: { path: '/staff/accounts', query: { role: 'SHIPPER' } } }]

describe('activeIndex', () => {
  it('chọn mục khớp cụ thể nhất theo đường dẫn', () => {
    expect(activeIndex(SHOP, at('/shop'), resolve)).toBe(0)
    expect(activeIndex(SHOP, at('/shop/shipments'), resolve)).toBe(1)
    expect(activeIndex(SHOP, at('/shop/shipments/12'), resolve)).toBe(1)
    expect(activeIndex(SHOP, at('/shop/shipments/new'), resolve)).toBe(2)
  })

  it('cùng đường dẫn: mục có query khớp thắng; query không khớp thì bỏ', () => {
    expect(activeIndex(ADMIN, at('/staff/accounts?role=SHIPPER'), resolve)).toBe(2)
    expect(activeIndex(ADMIN, at('/staff/accounts?role=SHOP'), resolve)).toBe(1)
    expect(activeIndex(ADMIN, at('/staff/accounts/5'), resolve)).toBe(1)
  })

  it('không thuộc mục nào → -1; không nhầm tiền tố chuỗi (/shopx)', () => {
    expect(activeIndex(SHOP, at('/account/profile'), resolve)).toBe(-1)
    expect(activeIndex([{ to: '/staff' }], at('/staffing'), resolve)).toBe(-1)
  })
})
