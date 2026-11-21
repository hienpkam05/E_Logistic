import { describe, expect, it } from 'vitest'
import { resolveNavigation, safeNext } from '../guard'

const anon = { isAuthenticated: false, role: null, mustChangePassword: false }
const shop = { isAuthenticated: true, role: 'SHOP', mustChangePassword: false }
const tempShop = { ...shop, mustChangePassword: true }

const route = (name, fullPath, meta = {}) => ({ name, fullPath, meta })
const LOGIN = route('login', '/login', { public: true, guestOnly: true })
const STAFF = route('staff-home', '/staff', { roles: ['ADMIN'] })
const PROFILE = route('profile', '/account/profile?tab=1')
const CHANGE = route('change-password', '/account/password')

describe('resolveNavigation', () => {
  it('trang công khai: ai cũng vào', () => {
    expect(resolveNavigation(route('forgot-password', '/forgot-password', { public: true }), anon)).toBe(true)
  })

  it('chưa đăng nhập vào trang cần đăng nhập -> /login kèm next', () => {
    expect(resolveNavigation(PROFILE, anon)).toEqual({ name: 'login', query: { next: '/account/profile?tab=1' } })
  })

  it('đã đăng nhập mở /login -> trang chủ vai trò (UC01.1 A1)', () => {
    expect(resolveNavigation(LOGIN, shop)).toEqual({ name: 'shop-home' })
  })

  it('sai vai trò -> trang chủ của vai trò mình', () => {
    expect(resolveNavigation(STAFF, shop)).toEqual({ name: 'shop-home' })
  })

  it('đúng vai trò / trang chung -> cho vào', () => {
    expect(resolveNavigation(route('shop-home', '/shop', { roles: ['SHOP'] }), shop)).toBe(true)
    expect(resolveNavigation(PROFILE, shop)).toBe(true)
  })

  it('đang dùng mật khẩu tạm -> chỉ trang đổi mật khẩu', () => {
    expect(resolveNavigation(PROFILE, tempShop)).toEqual({ name: 'change-password' })
    expect(resolveNavigation(STAFF, tempShop)).toEqual({ name: 'change-password' })
    expect(resolveNavigation(CHANGE, tempShop)).toBe(true)
  })

  it('vai trò lạ (dữ liệu hỏng) -> về đăng nhập, không vào trang có giới hạn', () => {
    expect(resolveNavigation(STAFF, { ...shop, role: 'KHACH' })).toEqual({ name: 'login' })
  })
})

describe('safeNext', () => {
  it.each([
    ['/account/profile', '/account/profile'],
    ['/shop?x=1#y', '/shop?x=1#y'],
    ['//evil.example.com', null],
    ['https://evil.example.com', null],
    ['/\\evil.example.com', null],
    ['javascript:alert(1)', null],
    ['/a\nb', null],
    [undefined, null],
    [['/shop'], null],
  ])('%j -> %j', (input, expected) => {
    expect(safeNext(input)).toBe(expected)
  })
})
