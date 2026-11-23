import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WardSelect from '../WardSelect.vue'

const WARDS = [
  { code: '00070', name: 'Phường Hoàn Kiếm' },
  { code: '00160', name: 'Phường Ba Đình' },
  { code: '00300', name: 'Xã Đông Anh' },
]

const render = (props = {}) =>
  mount(WardSelect, { props: { label: 'Phường/xã giao hàng', wards: WARDS, modelValue: '', ...props } })
const optionTexts = (wrapper) => wrapper.findAll('option').slice(1).map((o) => o.text())

describe('WardSelect', () => {
  it('liệt kê phường, chọn phát ra MÃ', async () => {
    const wrapper = render()
    expect(optionTexts(wrapper)).toEqual(['Phường Hoàn Kiếm', 'Phường Ba Đình', 'Xã Đông Anh'])
    await wrapper.find('select').setValue('00160')
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['00160'])
  })

  it('lọc không dấu, không phân biệt hoa thường (kể cả đ/Đ)', async () => {
    const wrapper = render()
    await wrapper.find('input').setValue('hoan kiem')
    expect(optionTexts(wrapper)).toEqual(['Phường Hoàn Kiếm'])
    await wrapper.find('input').setValue('DONG')
    expect(optionTexts(wrapper)).toEqual(['Xã Đông Anh'])
  })

  it('phường đang chọn vẫn hiện dù không khớp bộ lọc', async () => {
    const wrapper = render({ modelValue: '00160' })
    await wrapper.find('input').setValue('hoan')
    expect(optionTexts(wrapper)).toEqual(['Phường Ba Đình', 'Phường Hoàn Kiếm'])
  })

  it('không khớp gì: báo rõ', async () => {
    const wrapper = render()
    await wrapper.find('input').setValue('khong-co')
    expect(wrapper.find('option').text()).toBe('Không có phường/xã phù hợp')
  })

  it('lỗi hiện dưới ô, gắn aria', () => {
    const wrapper = render({ error: 'Địa chỉ phải thuộc Hà Nội.' })
    const select = wrapper.find('select')
    expect(select.attributes('aria-invalid')).toBe('true')
    expect(wrapper.find(`#${select.attributes('aria-describedby')}`).text()).toBe('Địa chỉ phải thuộc Hà Nội.')
  })
})
