import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { CHOICES } from '../../../test-utils'
import { useMetaStore } from '../../../stores/meta'
import StatusBadge from '../StatusBadge.vue'

let pinia

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  useMetaStore().choices = CHOICES
})

const render = (props) => mount(StatusBadge, { props, global: { plugins: [pinia] } })

describe('StatusBadge', () => {
  it('nhãn từ backend, tông theo statusTones', () => {
    const wrapper = render({ value: 'DELIVERED' })
    expect(wrapper.text()).toBe('Đã giao hàng')
    expect(wrapper.classes()).toContain('status-badge--success')
    expect(wrapper.attributes('data-status')).toBe('DELIVERED')
  })

  it('nhóm trạng thái nhiệm vụ', () => {
    const wrapper = render({ group: 'task_statuses', value: 'PENDING_SWAP_HANDOVER' })
    expect(wrapper.text()).toBe('Chờ bàn giao đổi Shipper')
    expect(wrapper.classes()).toContain('status-badge--warning')
  })

  it('mã lạ: hiện mã, tông neutral', () => {
    const wrapper = render({ value: 'MA_MOI' })
    expect(wrapper.text()).toBe('MA_MOI')
    expect(wrapper.classes()).toContain('status-badge--neutral')
  })

  it('giá trị rỗng: không render', () => {
    expect(render({ value: '' }).find('.status-badge').exists()).toBe(false)
  })
})
