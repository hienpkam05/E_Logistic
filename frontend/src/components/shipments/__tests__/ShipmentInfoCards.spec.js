import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { formatVnd } from '../../../utils/format'
import { SHIPMENT } from '../../../views/__tests__/shipmentFixtures'
import ShipmentInfoCards from '../ShipmentInfoCards.vue'

const SHOP = { id: 3, username: 'shop_hoa', full_name: 'Shop Hoa', phone: '0999000003' }
const titles = (wrapper) => wrapper.findAll('.card__title').map((h) => h.text())
const details = (wrapper) =>
  Object.fromEntries(wrapper.findAll('dt').map((dt, i) => [dt.text(), wrapper.findAll('dd')[i].text()]))

describe('ShipmentInfoCards', () => {
  it('4 thẻ thông tin; giá trị trống có nhãn rõ', () => {
    const wrapper = mount(ShipmentInfoCards, { props: { shipment: SHIPMENT } })
    expect(titles(wrapper)).toEqual(['Người gửi', 'Người nhận', 'Kiện hàng', 'Thu hộ'])
    const d = details(wrapper)
    expect(d['Giao đến']).toBe('5 Láng Hạ, Phường Láng')
    expect(d['Khối lượng']).toBe('Không ghi')
    expect(d.COD).toBe(formatVnd(350000))
    expect(d['Ghi chú']).toBe('Không có')
  })

  it('COD 0 → "Không thu hộ"', () => {
    const wrapper = mount(ShipmentInfoCards, { props: { shipment: { ...SHIPMENT, cod_amount: 0 } } })
    expect(details(wrapper).COD).toBe('Không thu hộ')
  })

  it('showShop: thêm thẻ Shop đầu tiên (Nhân viên); không có shop thì không vỡ', () => {
    const wrapper = mount(ShipmentInfoCards, { props: { shipment: { ...SHIPMENT, shop: SHOP }, showShop: true } })
    expect(titles(wrapper)[0]).toBe('Shop gửi hàng')
    expect(details(wrapper)['Tên Shop']).toBe('Shop Hoa')
    expect(wrapper.text()).toContain('0999 000 003')
    expect(titles(mount(ShipmentInfoCards, { props: { shipment: SHIPMENT, showShop: true } }))).toHaveLength(4)
    expect(titles(mount(ShipmentInfoCards, { props: { shipment: { ...SHIPMENT, shop: SHOP } } }))).toHaveLength(4)
  })

  it('slot: màn hình gắn thêm thẻ riêng vào cùng lưới', () => {
    const wrapper = mount(ShipmentInfoCards, {
      props: { shipment: SHIPMENT }, slots: { default: '<article class="card extra">Điều phối</article>' },
    })
    expect(wrapper.find('.detail-layout__main .extra').text()).toBe('Điều phối')
  })
})
