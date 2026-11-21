import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import OneTimeSecret from '../OneTimeSecret.vue'

const render = () =>
  mount(OneTimeSecret, { props: { secret: 'Xk7mP2qR9vTs', username: 'shipper_moi' }, attachTo: document.body })

afterEach(() => { document.body.innerHTML = '' })

describe('OneTimeSecret', () => {
  it('hiện mật khẩu, tên đăng nhập và cảnh báo chỉ hiện một lần', () => {
    const wrapper = render()
    expect(wrapper.find('code').text()).toBe('Xk7mP2qR9vTs')
    expect(wrapper.text()).toContain('shipper_moi')
    expect(wrapper.text()).toContain('Chỉ hiển thị một lần.')
  })

  it('sao chép vào clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue()
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = render()
    await wrapper.findAll('button')[0].trigger('click')
    await vi.waitFor(() => expect(wrapper.find('.alert--success').exists()).toBe(true))
    expect(writeText).toHaveBeenCalledWith('Xk7mP2qR9vTs')
  })

  it('clipboard bị chặn: chọn sẵn chữ và hướng dẫn Ctrl+C', async () => {
    vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
    const wrapper = render()
    await wrapper.findAll('button')[0].trigger('click')
    await vi.waitFor(() => expect(wrapper.find('.alert--info').text()).toContain('Ctrl+C'))
    expect(window.getSelection().toString()).toBe('Xk7mP2qR9vTs')
  })

  it('"Tôi đã ghi lại" phát sự kiện done', async () => {
    const wrapper = render()
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('done')).toHaveLength(1)
  })
})
