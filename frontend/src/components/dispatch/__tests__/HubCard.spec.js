// Thẻ điểm tập kết (spec 008 D6): dữ liệu từ meta.hub.
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useMetaStore } from '../../../stores/meta'
import { CHOICES } from '../../../test-utils'
import HubCard from '../HubCard.vue'

let pinia
beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
})

const mountCard = (props = {}, slots = {}) => mount(HubCard, { props, slots, global: { plugins: [pinia] } })

describe('HubCard', () => {
  it('hiện tên, địa chỉ, SĐT + nút gọi từ meta.hub', () => {
    useMetaStore().choices = CHOICES
    const wrapper = mountCard({ title: 'Đưa hàng về', callLabel: 'Gọi' }, { default: '<p class="extra">Lý do</p>' })
    expect(wrapper.find('.card__title').text()).toBe('Đưa hàng về')
    expect(wrapper.find('.hub__name').text()).toBe('Điểm tập kết HTT EXPRESS')
    expect(wrapper.find('.hub__address').text()).toBe('1 Tràng Tiền, Hoàn Kiếm')
    expect(wrapper.find('a[href="tel:0241234567"]').text()).toContain('Gọi')
    expect(wrapper.find('.extra').exists()).toBe(true) // slot cho nội dung riêng của từng màn
  })

  it('chưa có dữ liệu điểm tập kết: không vẽ gì', () => {
    expect(mountCard().find('.card').exists()).toBe(false)
  })

  it('không có SĐT: không có nút gọi', () => {
    useMetaStore().choices = { ...CHOICES, hub: { ...CHOICES.hub, phone: '' } }
    expect(mountCard().find('a[href^="tel:"]').exists()).toBe(false)
  })
})
