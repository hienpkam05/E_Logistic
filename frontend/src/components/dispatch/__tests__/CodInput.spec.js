// Ô COD thực thu (spec 007 D5).
import { afterEach, describe, expect, it } from 'vitest'
import { mountWithModel } from '../../../test-utils'
import CodInput from '../CodInput.vue'

const flush = () => new Promise((resolve) => setTimeout(resolve))
const normalize = (text) => text.replace(/\s+/g, ' ') // Intl dùng khoảng trắng không ngắt trước ₫
const mountCod = (props = {}) => mountWithModel(CodInput, { expected: 350000, ...props })

afterEach(() => {
  document.body.innerHTML = ''
})

describe('CodInput (UC04.5 bước 3, UC04.7)', () => {
  it('hiện COD phải thu, ô để trống — không điền sẵn (D5)', () => {
    const wrapper = mountCod()
    expect(normalize(wrapper.find('.cod__amount').text())).toBe('350.000 ₫')
    expect(wrapper.find('input').element.value).toBe('')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.find('[role="status"]').text()).toContain('Nhập số tiền')
  })

  it('gõ số: chỉ nhận chữ số, hiển thị có dấu chấm, báo khớp / thiếu / thừa', async () => {
    const wrapper = mountCod()
    const input = wrapper.find('input')
    await input.setValue('330.000đ')
    expect(wrapper.props('modelValue')).toBe(330000)
    expect(input.element.value).toBe('330.000')
    expect(normalize(wrapper.find('[role="status"]').text())).toContain('Thiếu 20.000 ₫')
    expect(wrapper.vm.matches).toBe(false)
    await input.setValue('370000')
    expect(normalize(wrapper.find('[role="status"]').text())).toContain('Thừa 20.000 ₫')
    await input.setValue('350000')
    expect(wrapper.find('[role="status"]').text()).toContain('Khớp')
    expect(wrapper.vm.matches).toBe(true)
    await input.setValue('')
    expect(wrapper.props('modelValue')).toBeNull()
  })

  it('không vượt giới hạn meta (cod_max_vnd)', async () => {
    const wrapper = mountCod({ max: 50000000 })
    await wrapper.find('input').setValue('999999999')
    expect(wrapper.props('modelValue')).toBe(50000000)
  })

  it('đơn không COD (A1): không có ô nhập, giá trị 0, coi như khớp', async () => {
    const wrapper = mountCod({ expected: 0 })
    await flush()
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.text()).toContain('Đơn không thu COD')
    expect(wrapper.props('modelValue')).toBe(0)
    expect(wrapper.vm.matches).toBe(true)
  })

  it('hiện lỗi backend (fields.cod_collected)', () => {
    const wrapper = mountCod({ error: 'Thiếu 20.000 ₫ so với COD phải thu 350.000 ₫.' })
    expect(wrapper.find('[role="alert"]').text()).toContain('Thiếu 20.000')
    expect(wrapper.find('input').attributes('aria-invalid')).toBe('true')
  })
})
