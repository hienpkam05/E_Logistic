import { afterEach, describe, expect, it, vi } from 'vitest'
import ShipmentForm from '../../components/shipments/ShipmentForm.vue'
import * as shipmentService from '../../services/shipmentService'
import { ApiError } from '../../services/http'
import { useMetaStore } from '../../stores/meta'
import { formatVnd } from '../../utils/format'
import ShipmentDetailView from '../shop/ShipmentDetailView.vue'
import { flush, mountView } from './helpers'
import { SHIPMENT, SHIPMENT_CHOICES, WARDS, page } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({
  wards: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), cancel: vi.fn(), events: vi.fn(),
}))

const ACTOR = { id: 3, username: 'shop_hoa', full_name: 'Shop Hoa' }
const CANCELLED = { ...SHIPMENT, status: 'CANCELLED', allowed_actions: [], updated_at: 'sau-huy' }
const APPROVED = { ...SHIPMENT, status: 'AWAITING_PICKUP', tracking_code: 'HTT000045', allowed_actions: [] }

async function setup({ shipment = SHIPMENT, events = page([]), path } = {}) {
  shipmentService.get.mockResolvedValue(shipment)
  shipmentService.events.mockResolvedValue(events)
  shipmentService.wards.mockResolvedValue(WARDS)
  const result = await mountView(ShipmentDetailView, {
    path: path ?? `/shop/shipments/${shipment.id}`,
    beforeMount: () => { useMetaStore().choices = SHIPMENT_CHOICES },
  })
  await flush()
  return result
}

// Nút trên trang (bỏ qua nút trong <dialog> — hộp đóng vẫn nằm trong DOM).
const button = (wrapper, text) =>
  wrapper.findAll('button').find((b) => b.text() === text && !b.element.closest('dialog'))
const details = (wrapper) =>
  Object.fromEntries(wrapper.findAll('dt').map((dt, i) => [dt.text(), wrapper.findAll('dd')[i].text()]))
const openDialog = (wrapper) => wrapper.findAll('dialog').find((d) => d.element.open)
const conflict = (code, message) => new ApiError({ status: 409, code, message })

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(shipmentService).forEach((fn) => fn.mockReset())
})

describe('ShipmentDetailView', () => {
  it('chờ xác nhận: mã yêu cầu, chưa có mã vận đơn, thông tin, nút Sửa/Hủy', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('h1').text()).toBe('YC000012')
    expect(wrapper.find('.title-row').text()).toContain('Chờ xác nhận')
    expect(wrapper.text()).toContain('Mã vận đơn được cấp khi Nhân viên duyệt')
    const d = details(wrapper)
    expect(d['Giao đến']).toBe('5 Láng Hạ, Phường Láng')
    expect(d['Lấy hàng tại']).toBe('12 Trần Thái Tông, Phường Dịch Vọng')
    expect(d['Khối lượng']).toBe('Không ghi')
    expect(d.COD).toBe(formatVnd(350000))
    expect(button(wrapper, 'Sửa yêu cầu')).toBeDefined()
    expect(button(wrapper, 'Hủy yêu cầu')).toBeDefined()
  })

  it('nút theo allowed_actions: đã duyệt → không có nút, hiện mã vận đơn', async () => {
    const { wrapper } = await setup({ shipment: APPROVED })
    expect(wrapper.find('h1').text()).toBe('HTT000045')
    expect(wrapper.text()).toContain('Mã vận đơn HTT000045')
    expect(button(wrapper, 'Sửa yêu cầu')).toBeUndefined()
    expect(button(wrapper, 'Hủy yêu cầu')).toBeUndefined()
  })

  it('chỉ được hủy (không được sửa): chỉ hiện nút Hủy', async () => {
    const { wrapper } = await setup({ shipment: { ...SHIPMENT, allowed_actions: ['CANCEL_REQUEST'] } })
    expect(button(wrapper, 'Sửa yêu cầu')).toBeUndefined()
    expect(button(wrapper, 'Hủy yêu cầu')).toBeDefined()
  })

  it('bị từ chối: hiện khung lý do cho Shop (spec 005 D5)', async () => {
    const { wrapper } = await setup({
      shipment: { ...SHIPMENT, status: 'REJECTED', allowed_actions: [], rejection_reason: 'Thiếu số nhà' },
    })
    expect(wrapper.find('.alert--danger').text()).toBe('Yêu cầu bị từ chối. Lý do: Thiếu số nhà')
    expect(button(wrapper, 'Sửa yêu cầu')).toBeUndefined()
  })

  it('vừa tạo (?created=1): thông báo đã gửi', async () => {
    const { wrapper } = await setup({ path: '/shop/shipments/12?created=1' })
    expect(wrapper.find('.alert--success').text()).toContain('Đã gửi yêu cầu')
  })

  it('404 (không có hoặc của Shop khác): "Không tìm thấy vận đơn"', async () => {
    shipmentService.get.mockRejectedValue(new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' }))
    shipmentService.events.mockRejectedValue(new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' }))
    const { wrapper } = await mountView(ShipmentDetailView, { path: '/shop/shipments/999' })
    await flush()
    expect(wrapper.find('h1').text()).toBe('Không tìm thấy vận đơn')
  })

  it('lỗi tải khác: báo lỗi + "Tải lại"', async () => {
    shipmentService.get.mockRejectedValueOnce(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất mạng' }))
    shipmentService.events.mockResolvedValue(page([]))
    const { wrapper } = await mountView(ShipmentDetailView, { path: '/shop/shipments/12' })
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất mạng')
    shipmentService.get.mockResolvedValue(SHIPMENT)
    await button(wrapper, 'Tải lại').trigger('click')
    await flush()
    expect(wrapper.find('h1').text()).toBe('YC000012')
  })

  it('sửa: form điền sẵn đơn, gửi kèm updated_at đã tải, lưu xong về chế độ xem', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Sửa yêu cầu').trigger('click')
    await flush()
    expect(shipmentService.wards).toHaveBeenCalledOnce()
    expect(wrapper.findComponent(ShipmentForm).props('shipment')).toEqual(SHIPMENT)
    shipmentService.update.mockResolvedValue({ ...SHIPMENT, receiver_name: 'Lê Văn C', updated_at: 'moi' })
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(shipmentService.update).toHaveBeenCalledWith('12',
      expect.objectContaining({ receiver_name: 'Trần Thị B', delivery_ward: 'W2', cod_amount: 350000 }),
      SHIPMENT.updated_at)
    expect(wrapper.findComponent(ShipmentForm).exists()).toBe(false)
    expect(wrapper.text()).toContain('Lê Văn C')
    expect(wrapper.find('.alert--success').text()).toContain('Đã lưu')
    expect(shipmentService.events).toHaveBeenCalledTimes(2)
  })

  it('sửa bị 409 CONFLICT: cảnh báo, "Tải bản mới nhất" nạp bản mới, lần lưu sau dùng updated_at mới', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Sửa yêu cầu').trigger('click')
    shipmentService.update.mockRejectedValue(conflict('CONFLICT', 'Yêu cầu vừa được thay đổi. Vui lòng tải lại.'))
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.find('.alert--warning').text()).toContain('vừa được thay đổi')
    shipmentService.get.mockResolvedValue({ ...SHIPMENT, receiver_name: 'Bản mới', updated_at: 'moi' })
    await button(wrapper, 'Tải bản mới nhất').trigger('click')
    await flush()
    expect(wrapper.find('.alert--warning').exists()).toBe(false)
    expect(wrapper.findComponent(ShipmentForm).exists()).toBe(true)
    expect(wrapper.findAll('input').map((i) => i.element.value)).toContain('Bản mới')
    shipmentService.update.mockResolvedValue({ ...SHIPMENT, updated_at: 'moi-2' })
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(shipmentService.update).toHaveBeenLastCalledWith('12', expect.anything(), 'moi')
  })

  it('sửa bị 409 INVALID_TRANSITION (vừa được duyệt): tải lại thì thoát sửa, hiện trạng thái mới (UC05.1 E1)', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Sửa yêu cầu').trigger('click')
    shipmentService.update.mockRejectedValue(conflict('INVALID_TRANSITION',
      'Yêu cầu không còn ở trạng thái Chờ xác nhận nên không sửa được.'))
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.find('.alert--warning').text()).toContain('không sửa được')
    shipmentService.get.mockResolvedValue(APPROVED)
    await button(wrapper, 'Tải bản mới nhất').trigger('click')
    await flush()
    expect(wrapper.findComponent(ShipmentForm).exists()).toBe(false)
    expect(wrapper.find('h1').text()).toBe('HTT000045')
    expect(button(wrapper, 'Sửa yêu cầu')).toBeUndefined()
  })

  it('sửa lỗi kiểm tra: lỗi theo trường, không hiện "Tải bản mới nhất"', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Sửa yêu cầu').trigger('click')
    shipmentService.update.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { cod_amount: ['Tiền thu hộ vượt mức tối đa.'] },
    }))
    await wrapper.find('form').trigger('submit')
    await flush()
    expect(wrapper.text()).toContain('Tiền thu hộ vượt mức tối đa.')
    expect(button(wrapper, 'Tải bản mới nhất')).toBeUndefined()
  })

  it('hủy: hộp xác nhận, gửi lý do đã cắt khoảng trắng, cập nhật trạng thái, ẩn nút', async () => {
    const { wrapper } = await setup()
    shipmentService.cancel.mockResolvedValue(CANCELLED)
    await button(wrapper, 'Hủy yêu cầu').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('YC000012')
    await dialog.find('textarea').setValue('  Khách đổi ý ')
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.cancel).toHaveBeenCalledWith('12', 'Khách đổi ý')
    expect(openDialog(wrapper)).toBeUndefined()
    expect(wrapper.text()).toContain('Đã hủy yêu cầu.')
    expect(wrapper.find('.title-row').text()).toContain('Đã hủy')
    expect(button(wrapper, 'Sửa yêu cầu')).toBeUndefined()
    expect(shipmentService.events).toHaveBeenCalledTimes(2)
  })

  it('hủy: ô lý do giới hạn theo meta.limits; lỗi lý do hiện ngay dưới ô', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Hủy yêu cầu').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('textarea').attributes('maxlength'))
      .toBe(String(SHIPMENT_CHOICES.limits.cancel_reason_max_length))
    shipmentService.cancel.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.',
      fields: { reason: ['Lý do tối đa 500 ký tự.'] },
    }))
    await dialog.find('form').trigger('submit')
    await flush()
    expect(dialog.find('.field__error').text()).toBe('Lý do tối đa 500 ký tự.')
    expect(dialog.find('.alert--danger').exists()).toBe(false)
    expect(dialog.element.open).toBe(true)
  })

  it('hủy → "Không hủy": đóng hộp, không gọi API', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Hủy yêu cầu').trigger('click')
    await flush()
    await openDialog(wrapper).findAll('button').find((b) => b.text() === 'Không hủy').trigger('click')
    await flush()
    expect(openDialog(wrapper)).toBeUndefined()
    expect(shipmentService.cancel).not.toHaveBeenCalled()
  })

  it('hủy bị 409 (vừa được duyệt): tải lại trạng thái mới, không còn nút', async () => {
    const { wrapper } = await setup()
    shipmentService.cancel.mockRejectedValue(conflict('INVALID_TRANSITION',
      'Yêu cầu không còn ở trạng thái Chờ xác nhận nên không hủy được.'))
    await button(wrapper, 'Hủy yêu cầu').trigger('click')
    await flush()
    shipmentService.get.mockResolvedValue(APPROVED)
    await openDialog(wrapper).find('form').trigger('submit')
    await flush()
    expect(shipmentService.get).toHaveBeenCalledTimes(2)
    expect(wrapper.find('h1').text()).toBe('HTT000045')
    expect(button(wrapper, 'Hủy yêu cầu')).toBeUndefined()
    const dialog = openDialog(wrapper)
    expect(dialog.find('[role="alert"]').text()).toContain('không hủy được')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeDefined() // không bấm hủy lại được
  })

  it('lịch sử: nhãn thao tác, chuyển trạng thái, người làm, thay đổi trước/sau, lý do', async () => {
    const events = page([
      { id: 3, action: 'CANCEL_REQUEST', from_status: 'PENDING_APPROVAL', to_status: 'CANCELLED', actor: ACTOR,
        reason: 'Khách đổi ý', changes: {}, created_at: '2026-11-21T04:00:00Z' },
      { id: 2, action: 'UPDATE_REQUEST', from_status: 'PENDING_APPROVAL', to_status: 'PENDING_APPROVAL', actor: ACTOR,
        reason: '', created_at: '2026-11-21T03:00:00Z',
        changes: { cod_amount: { from: 0, to: 350000 }, delivery_ward: { from: WARDS[0], to: WARDS[1] },
          note: { from: '', to: 'Gọi trước' } } },
      { id: 1, action: 'CREATE_REQUEST', from_status: null, to_status: 'PENDING_APPROVAL', actor: null,
        reason: '', changes: {}, created_at: '2026-11-21T02:00:00Z' },
    ])
    const { wrapper } = await setup({ events })
    const items = wrapper.findAll('.events__item').map((li) => li.text())
    expect(items[0]).toContain('Hủy yêu cầu')
    expect(items[0]).toMatch(/Chờ xác nhận\s*→\s*Đã hủy/)
    expect(items[0]).toContain('Shop Hoa')
    expect(items[0]).toContain('Lý do: Khách đổi ý')
    expect(items[1]).not.toContain('→ Chờ xác nhận') // cùng trạng thái: không ghi "A → A"
    expect(items[1]).toContain(`COD: ${formatVnd(0)} → ${formatVnd(350000)}`)
    expect(items[1]).toContain('Phường/xã giao hàng: Phường Dịch Vọng → Phường Láng')
    expect(items[1]).toContain('Ghi chú: (trống) → Gọi trước')
    expect(items[2]).toContain('Hệ thống')
  })
})

// ---------------------------------------------------------------- Spec 008: Shop nhận lại hàng hoàn
describe('ShipmentDetailView — hoàn hàng (spec 008)', () => {
  it('Chờ Shop đến lấy: thẻ "Đến nhận hàng hoàn tại" với địa chỉ + SĐT điểm tập kết', async () => {
    const { wrapper } = await setup({ shipment: { ...SHIPMENT, status: 'AWAITING_SHOP_PICKUP', tracking_code: 'HTT1',
      allowed_actions: [] } })
    expect(wrapper.text()).toContain('Đến nhận hàng hoàn tại')
    expect(wrapper.text()).toContain('1 Tràng Tiền, Hoàn Kiếm')
    expect(wrapper.find('a[href="tel:0241234567"]').exists()).toBe(true)
  })

  it('Đã hoàn về Shop: thẻ "Kết quả hoàn" (người nhận, thời gian); không còn thẻ đến nhận', async () => {
    const { wrapper } = await setup({ shipment: { ...SHIPMENT, status: 'RETURNED_TO_SHOP', tracking_code: 'HTT1',
      allowed_actions: [], return_result: { received_at: '2026-11-23T05:00:00Z', receiver_name: 'Chị Hoa' } } })
    expect(wrapper.text()).toContain('Kết quả hoàn')
    expect(wrapper.text()).toContain('Chị Hoa')
    expect(wrapper.text()).not.toContain('Đến nhận hàng hoàn tại')
  })
})

