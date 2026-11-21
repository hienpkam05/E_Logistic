import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ConfirmDialog from '../ConfirmDialog.vue'

const render = (props = {}) =>
  mount(ConfirmDialog, {
    props: { title: 'Khóa tài khoản?', ...props },
    slots: { default: '<p class="msg">Người này sẽ bị đăng xuất.</p>' },
    attachTo: document.body,
  })

afterEach(() => { document.body.innerHTML = '' })

describe('ConfirmDialog', () => {
  it('mở/đóng theo prop open (fallback thuộc tính open khi không có showModal)', async () => {
    const wrapper = render({ open: false })
    await wrapper.vm.$nextTick()
    const dialog = wrapper.find('dialog').element
    expect(dialog.open).toBe(false)
    await wrapper.setProps({ open: true })
    await vi.waitFor(() => expect(dialog.open).toBe(true))
    await wrapper.setProps({ open: false })
    await vi.waitFor(() => expect(dialog.open).toBe(false))
  })

  it('dùng showModal()/close() khi trình duyệt hỗ trợ', async () => {
    const showModal = vi.fn(function () { this.setAttribute('open', '') })
    const close = vi.fn(function () { this.removeAttribute('open') })
    HTMLDialogElement.prototype.showModal = showModal
    HTMLDialogElement.prototype.close = close
    try {
      const wrapper = render({ open: true })
      await vi.waitFor(() => expect(showModal).toHaveBeenCalledOnce())
      await wrapper.setProps({ open: false })
      await vi.waitFor(() => expect(close).toHaveBeenCalledOnce())
    } finally {
      delete HTMLDialogElement.prototype.showModal
      delete HTMLDialogElement.prototype.close
    }
  })

  it('tiêu đề gắn aria-labelledby, nội dung slot', async () => {
    const wrapper = render({ open: true })
    const dialog = wrapper.find('dialog')
    expect(wrapper.find(`#${dialog.attributes('aria-labelledby')}`).text()).toBe('Khóa tài khoản?')
    expect(wrapper.find('.msg').exists()).toBe(true)
  })

  it('Xác nhận / Hủy / Esc phát sự kiện', async () => {
    const wrapper = render({ open: true, confirmLabel: 'Khóa', tone: 'danger' })
    const submit = wrapper.find('button[type="submit"]')
    expect(submit.text()).toBe('Khóa')
    expect(submit.classes()).toContain('btn--danger')
    await wrapper.find('form').trigger('submit')
    await wrapper.find('button[type="button"]').trigger('click')
    const esc = new Event('cancel', { cancelable: true })
    wrapper.find('dialog').element.dispatchEvent(esc)
    expect(wrapper.emitted('confirm')).toHaveLength(1)
    expect(wrapper.emitted('cancel')).toHaveLength(2)
    expect(esc.defaultPrevented).toBe(true) // component cha quyết định đóng
  })

  it('đang xử lý: khóa nút, Hủy/Esc không có tác dụng', async () => {
    const wrapper = render({ open: true, busy: true })
    expect(wrapper.find('button[type="submit"]').text()).toBe('Đang xử lý…')
    wrapper.findAll('button').forEach((b) => expect(b.attributes('disabled')).toBeDefined())
    wrapper.find('dialog').element.dispatchEvent(new Event('cancel', { cancelable: true }))
    expect(wrapper.emitted('cancel')).toBeUndefined()
  })

  it('confirmDisabled khóa riêng nút xác nhận', () => {
    const wrapper = render({ open: true, confirmDisabled: true })
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[type="button"]').attributes('disabled')).toBeUndefined()
  })
})
