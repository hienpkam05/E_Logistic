import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useMetaStore } from '../../../stores/meta'
import { CHOICES } from '../../../test-utils'
import ShipmentForm from '../ShipmentForm.vue'

const WARDS = [{ code: '00070', name: 'Phường Hoàn Kiếm' }, { code: '00160', name: 'Phường Ba Đình' }]
const LIMITS = { ...CHOICES.limits, package_count_min: 1, package_count_max: 99, weight_grams_max: 100000 }
const SHIPMENT = {
  id: 15, sender_name: 'Shop Hoa An', sender_phone: '0901234567',
  pickup_ward: { code: '00070', name: 'Phường Hoàn Kiếm' }, pickup_address: '12 Hàng Bạc',
  receiver_name: 'Trần Thị B', receiver_phone: '0912345678',
  delivery_ward: { code: '00160', name: 'Phường Ba Đình' }, delivery_address: '5 Đội Cấn',
  package_description: 'Áo thun', package_count: 2, weight_grams: null, cod_amount: 350000, note: '',
}

let pinia
beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  useMetaStore().choices = { ...CHOICES, limits: LIMITS }
})

const render = (props = {}) => mount(ShipmentForm, { props: { wards: WARDS, ...props }, global: { plugins: [pinia] } })
const input = (wrapper, label) => {
  const field = wrapper.findAll('.field').find((f) => f.find('label').text().startsWith(label))
  // WardSelect có ô lọc (input) trước ô chọn — lấy select nếu có.
  return field.find('select').exists() ? field.find('select') : field.find('input, textarea')
}

describe('ShipmentForm', () => {
  it('tạo mới: điền sẵn người gửi từ hồ sơ (D4), số kiện 1, COD 0', () => {
    const wrapper = render({ senderDefaults: { name: 'Shop Hoa An', phone: '0901234567', address: '12 Hàng Bạc' } })
    expect(input(wrapper, 'Họ tên người gửi').element.value).toBe('Shop Hoa An')
    expect(input(wrapper, 'Địa chỉ lấy hàng').element.value).toBe('12 Hàng Bạc')
    expect(input(wrapper, 'Số kiện').element.value).toBe('1')
    expect(input(wrapper, 'Số tiền thu hộ').element.value).toBe('0')
    expect(wrapper.text()).toContain('Không thu hộ')
  })

  it('sửa: nạp giá trị của đơn', () => {
    const wrapper = render({ shipment: SHIPMENT })
    expect(input(wrapper, 'Họ tên người nhận').element.value).toBe('Trần Thị B')
    expect(input(wrapper, 'Phường/xã giao hàng').element.value).toBe('00160')
    expect(input(wrapper, 'Khối lượng').element.value).toBe('')
  })

  it('gửi: bỏ khoảng trắng, đổi số, khối lượng trống -> null', async () => {
    const wrapper = render({ shipment: SHIPMENT })
    await input(wrapper, 'Họ tên người nhận').setValue('  Trần Thị C  ')
    await input(wrapper, 'Số kiện').setValue('3')
    await input(wrapper, 'Số tiền thu hộ').setValue('400000')
    await wrapper.find('form').trigger('submit')
    const payload = wrapper.emitted('submit')[0][0]
    expect(payload).toMatchObject({
      receiver_name: 'Trần Thị C', package_count: 3, cod_amount: 400000, weight_grams: null,
      pickup_ward: '00070', delivery_ward: '00160',
    })
    expect(Object.keys(payload)).not.toContain('status')
  })

  it('COD hiển thị định dạng tiền; giới hạn lấy từ backend', async () => {
    const wrapper = render({ shipment: SHIPMENT })
    expect(wrapper.find('.cod-preview').text().replace(/ /g, ' ')).toBe('350.000 ₫')
    expect(wrapper.text()).toContain('Từ 1 đến 99 kiện.')
    expect(wrapper.text()).toContain('Tối đa 100000 gram.')
  })

  it('lỗi theo trường hiện đúng ô (kể cả ô phường/xã)', () => {
    const wrapper = render({ errors: { receiver_phone: 'SĐT sai.', delivery_ward: 'Địa chỉ phải thuộc Hà Nội.' } })
    const texts = wrapper.findAll('.field__error').map((e) => e.text())
    expect(texts).toEqual(['SĐT sai.', 'Địa chỉ phải thuộc Hà Nội.'])
  })

  it('đang gửi: khóa ô và nút, không phát submit lần hai; Hủy phát cancel', async () => {
    let wrapper = render({ submitting: true })
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
    wrapper = render()
    await wrapper.findAll('button').find((b) => b.text() === 'Hủy').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
