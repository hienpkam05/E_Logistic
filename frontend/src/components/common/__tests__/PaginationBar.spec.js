import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PaginationBar from '../PaginationBar.vue'

describe('PaginationBar', () => {
  it('ẩn khi chỉ có một trang', () => {
    expect(mount(PaginationBar, { props: { page: 1 } }).find('nav').exists()).toBe(false)
  })

  it('hiện trang, tổng, đơn vị; khóa nút không dùng được', () => {
    const wrapper = mount(PaginationBar, { props: { page: 1, hasNext: true, total: 25, unit: 'tài khoản' } })
    expect(wrapper.text()).toContain('Trang 1 · 25 tài khoản')
    const [prev, next] = wrapper.findAll('button')
    expect(prev.attributes('disabled')).toBeDefined()
    expect(next.attributes('disabled')).toBeUndefined()
  })

  it('phát sự kiện change với trang mới', async () => {
    const wrapper = mount(PaginationBar, { props: { page: 3, hasNext: true, hasPrevious: true } })
    const [prev, next] = wrapper.findAll('button')
    await prev.trigger('click')
    await next.trigger('click')
    expect(wrapper.emitted('change')).toEqual([[2], [4]])
  })

  it('không có total thì không hiện tổng', () => {
    expect(mount(PaginationBar, { props: { page: 2, hasPrevious: true } }).text()).not.toContain('·')
  })
})
