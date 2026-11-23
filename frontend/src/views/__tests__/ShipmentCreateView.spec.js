import { afterEach, describe, expect, it, vi } from 'vitest'
import ShipmentForm from '../../components/shipments/ShipmentForm.vue'
import * as shipmentService from '../../services/shipmentService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import ShipmentCreateView from '../shop/ShipmentCreateView.vue'
import { flush, mountView } from './helpers'
import { SHIPMENT, SHIPMENT_CHOICES, WARDS } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({
  wards: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), cancel: vi.fn(), events: vi.fn(),
}))

const SHOP = {
  id: 3, username: 'shop_hoa', full_name: 'Shop Hoa', phone: '0912345678', address: '12 Trần Thái Tông',
  role: 'SHOP', must_change_password: false,
}

async function setup({ wards = WARDS } = {}) {
  if (wards instanceof Error) shipmentService.wards.mockRejectedValueOnce(wards)
  else shipmentService.wards.mockResolvedValue(wards)
  const result = await mountView(ShipmentCreateView, {
    path: '/shop/shipments/new',
    beforeMount: () => {
      useAuthStore().setUser(SHOP)
      useMetaStore().choices = SHIPMENT_CHOICES
    },
  })
  await flush()
  return result
}

const button = (wrapper, text) => wrapper.findAll('button').find((b) => b.text() === text)
const values = (wrapper) => wrapper.findAll('input, textarea').map((el) => el.element.value)

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(shipmentService).forEach((fn) => fn.mockReset())
  vi.restoreAllMocks()
})

describe('ShipmentCreateView', () => {
  it('điền sẵn người gửi từ hồ sơ Shop (D4), tải danh mục phường', async () => {
    const { wrapper } = await setup()
    expect(values(wrapper)).toEqual(expect.arrayContaining(['Shop Hoa', '0912345678', '12 Trần Thái Tông']))
    expect(shipmentService.wards).toHaveBeenCalledOnce()
    expect(wrapper.findComponent(ShipmentForm).props('wards')).toEqual(WARDS)
  })

  it('gửi thành công → sang chi tiết với thông báo đã gửi', async () => {
    const { wrapper, router } = await setup()
    shipmentService.create.mockResolvedValue(SHIPMENT)
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(shipmentService.create).toHaveBeenCalledWith(expect.objectContaining({
      sender_name: 'Shop Hoa', sender_phone: '0912345678', pickup_address: '12 Trần Thái Tông',
    }))
    expect(router.currentRoute.value.name).toBe('shop-shipment-detail')
    expect(router.currentRoute.value.params.id).toBe('12')
    expect(router.currentRoute.value.query).toEqual({ created: '1' })
  })

  it('lỗi kiểm tra: hiện lỗi theo trường và lỗi chung, ở lại form', async () => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    const { wrapper, router } = await setup()
    shipmentService.create.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { delivery_ward: ['Phường/xã không thuộc Hà Nội.'], receiver_phone: ['Số điện thoại không hợp lệ.'] },
    }))
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.text()).toContain('Phường/xã không thuộc Hà Nội.')
    expect(wrapper.text()).toContain('Số điện thoại không hợp lệ.')
    expect(router.currentRoute.value.name).toBe('shop-shipment-new')
    expect(button(wrapper, 'Gửi yêu cầu').attributes('disabled')).toBeUndefined()
  })

  it('Hủy: về danh sách, không tạo gì (A1)', async () => {
    const { wrapper, router } = await setup()
    await button(wrapper, 'Hủy').trigger('click')
    await flush()
    expect(router.currentRoute.value.name).toBe('shop-shipments')
    expect(shipmentService.create).not.toHaveBeenCalled()
  })

  it('không tải được phường: báo lỗi, "Tải lại" tải lại', async () => {
    const { wrapper } = await setup({ wards: new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất mạng' }) })
    expect(wrapper.find('.alert--danger').text()).toContain('Mất mạng')
    shipmentService.wards.mockResolvedValue(WARDS)
    await button(wrapper, 'Tải lại').trigger('click')
    await flush()
    expect(shipmentService.wards).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.alert--danger').exists()).toBe(false)
  })

  it('danh mục phường rỗng: cảnh báo chưa tạo được', async () => {
    const { wrapper } = await setup({ wards: [] })
    expect(wrapper.find('.alert--warning').text()).toContain('chưa có danh sách phường/xã')
  })
})
