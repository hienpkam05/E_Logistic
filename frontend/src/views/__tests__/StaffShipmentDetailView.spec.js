import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/http'
import * as dispatchService from '../../services/dispatchService'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import { formatVnd } from '../../utils/format'
import StaffShipmentDetailView from '../staff/StaffShipmentDetailView.vue'
import { flush, mountView } from './helpers'

const normalize = (text) => text.replace(/\s+/g, ' ')
import { SHIPMENT, SHIPMENT_CHOICES, SHIPPER, page } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({
  wards: vi.fn(), list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), cancel: vi.fn(), events: vi.fn(),
  approve: vi.fn(), reject: vi.fn(), assignPickup: vi.fn(), receiveAtHub: vi.fn(), retryPickup: vi.fn(),
  abandonPickup: vi.fn(), assignDelivery: vi.fn(), decideRedelivery: vi.fn(), decideReturn: vi.fn(),
  assignReturn: vi.fn(), receiveReturn: vi.fn(), reportReturnIssue: vi.fn(), confirmShopReceived: vi.fn(),
}))
vi.mock('../../services/dispatchService', () => ({ shippers: vi.fn() }))

const SHOP = { id: 3, username: 'shop_hoa', full_name: 'Shop Hoa', phone: '0999000003' }
const PENDING = {
  ...SHIPMENT, shop: SHOP, holder_type: 'SHOP', delivery_attempts: 0, rejection_reason: null,
  allowed_actions: ['APPROVE_REQUEST', 'REJECT_REQUEST'],
}
const APPROVED = { ...PENDING, status: 'AWAITING_PICKUP', tracking_code: 'HTT261121K7Q2M', allowed_actions: [],
  updated_at: 'sau-duyet' }
const REJECTED = { ...PENDING, status: 'REJECTED', allowed_actions: [], rejection_reason: 'Thiếu số nhà' }
const CHOICES = SHIPMENT_CHOICES

async function setup(shipment = PENDING) {
  shipmentService.get.mockResolvedValue(shipment)
  shipmentService.events.mockResolvedValue(page([]))
  const result = await mountView(StaffShipmentDetailView, {
    path: `/staff/shipments/${shipment.id}`, beforeMount: () => { useMetaStore().choices = CHOICES },
  })
  await flush()
  return result
}

const button = (wrapper, text) =>
  wrapper.findAll('button').find((b) => b.text() === text && !b.element.closest('dialog'))
const openDialog = (wrapper) => wrapper.findAll('dialog').find((d) => d.element.open)
const details = (wrapper) =>
  Object.fromEntries(wrapper.findAll('.detail-layout dt').map((dt, i) => [dt.text(), wrapper.findAll('.detail-layout dd')[i].text()]))

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(shipmentService).forEach((fn) => fn.mockReset())
})

describe('StaffShipmentDetailView', () => {
  it('chờ xác nhận: thẻ Shop, Điều phối "Chưa phát sinh", nút Duyệt/Từ chối', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('h1').text()).toBe('YC000012')
    expect(wrapper.text()).toContain('Chưa có mã vận đơn (cấp khi duyệt)')
    const titles = wrapper.findAll('.card__title').map((h) => h.text())
    expect(titles[0]).toBe('Shop gửi hàng')
    expect(titles).toContain('Điều phối')
    const d = details(wrapper)
    expect(d['Tên Shop']).toBe('Shop Hoa')
    expect(d['Đang giữ hàng']).toBe('Shop')
    expect(d['Shipper phụ trách']).toBe('Chưa phát sinh')
    expect(d['Số lần giao']).toBe('0/3') // spec 007: kèm giới hạn từ meta
    expect(button(wrapper, 'Duyệt')).toBeDefined()
    expect(button(wrapper, 'Từ chối')).toBeDefined()
  })

  it('không có nút khi allowed_actions rỗng; Bị từ chối hiện lý do', async () => {
    const { wrapper } = await setup(REJECTED)
    expect(button(wrapper, 'Duyệt')).toBeUndefined()
    expect(button(wrapper, 'Từ chối')).toBeUndefined()
    expect(wrapper.text()).toContain('Lý do từ chối: Thiếu số nhà')
  })

  it('duyệt: hộp xác nhận nêu mã, Shop, COD; gửi updated_at đã tải; thành công hiện mã + tải lại lịch sử', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Duyệt').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('YC000012')
    expect(dialog.text()).toContain('Shop Hoa')
    expect(dialog.text()).toContain(formatVnd(350000))
    expect(dialog.text()).toContain('không hoàn tác')
    expect(shipmentService.approve).not.toHaveBeenCalled() // chưa xác nhận thì chưa duyệt
    shipmentService.approve.mockResolvedValue(APPROVED)
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.approve).toHaveBeenCalledWith('12', PENDING.updated_at)
    expect(openDialog(wrapper)).toBeUndefined()
    expect(wrapper.find('h1').text()).toBe('HTT261121K7Q2M')
    expect(wrapper.find('.alert--success').text()).toContain('HTT261121K7Q2M')
    expect(button(wrapper, 'Duyệt')).toBeUndefined()
    expect(shipmentService.events).toHaveBeenCalledTimes(2)
  })

  it('"Để sau": đóng hộp, không duyệt', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Duyệt').trigger('click')
    await flush()
    await openDialog(wrapper).findAll('button').find((b) => b.text() === 'Để sau').trigger('click')
    await flush()
    expect(openDialog(wrapper)).toBeUndefined()
    expect(shipmentService.approve).not.toHaveBeenCalled()
  })

  it('duyệt bị 409 (Shop vừa sửa): đóng hộp, cảnh báo, tải bản mới', async () => {
    const { wrapper } = await setup()
    shipmentService.approve.mockRejectedValue(new ApiError({
      status: 409, code: 'CONFLICT', message: 'Yêu cầu vừa được Shop thay đổi. Vui lòng tải lại để kiểm tra trước khi xử lý.',
    }))
    shipmentService.get.mockResolvedValue({ ...PENDING, cod_amount: 999000, updated_at: 'moi' })
    await button(wrapper, 'Duyệt').trigger('click')
    await flush()
    await openDialog(wrapper).find('form').trigger('submit')
    await flush()
    expect(openDialog(wrapper)).toBeUndefined()
    expect(wrapper.find('.alert--warning').text()).toContain('vừa được Shop thay đổi')
    expect(shipmentService.get).toHaveBeenCalledTimes(2)
    expect(details(wrapper).COD).toBe(formatVnd(999000))
    expect(button(wrapper, 'Duyệt')).toBeDefined() // xem lại xong vẫn duyệt được, lần này với bản mới
  })

  it('duyệt bị 409 (Shop vừa hủy): báo trạng thái mới, hết nút', async () => {
    const { wrapper } = await setup()
    shipmentService.approve.mockRejectedValue(new ApiError({
      status: 409, code: 'INVALID_TRANSITION', message: 'Yêu cầu đang ở trạng thái Đã hủy nên không duyệt được.',
    }))
    shipmentService.get.mockResolvedValue({ ...PENDING, status: 'CANCELLED', allowed_actions: [] })
    await button(wrapper, 'Duyệt').trigger('click')
    await flush()
    await openDialog(wrapper).find('form').trigger('submit')
    await flush()
    expect(wrapper.find('.alert--warning').text()).toContain('Đã hủy')
    expect(button(wrapper, 'Duyệt')).toBeUndefined()
  })

  it('từ chối: phải nhập lý do; gửi lý do đã cắt khoảng trắng; hiện lý do sau khi xong', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Từ chối').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    const submit = dialog.find('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined()
    await dialog.find('textarea').setValue('   ')
    expect(submit.attributes('disabled')).toBeDefined() // toàn khoảng trắng vẫn khóa
    expect(dialog.find('textarea').attributes('maxlength')).toBe(String(CHOICES.limits.reject_reason_max_length))
    await dialog.find('textarea').setValue('  Thiếu số nhà ')
    expect(submit.attributes('disabled')).toBeUndefined()
    shipmentService.reject.mockResolvedValue(REJECTED)
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.reject).toHaveBeenCalledWith('12', 'Thiếu số nhà', PENDING.updated_at)
    expect(wrapper.text()).toContain('Lý do từ chối: Thiếu số nhà')
    expect(wrapper.find('.alert--success').text()).toContain('Đã từ chối')
  })

  it('từ chối bị lỗi lý do từ backend: hiện dưới ô, hộp vẫn mở', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Từ chối').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    await dialog.find('textarea').setValue('x')
    shipmentService.reject.mockRejectedValue(new ApiError({
      status: 400, code: 'VALIDATION_ERROR', message: 'Dữ liệu chưa hợp lệ.', fields: { reason: ['Lý do quá dài.'] },
    }))
    await dialog.find('form').trigger('submit')
    await flush()
    expect(dialog.find('.field__error').text()).toBe('Lý do quá dài.')
    expect(dialog.element.open).toBe(true)
  })

  it('404: không tìm thấy', async () => {
    shipmentService.get.mockRejectedValue(new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' }))
    const { wrapper } = await mountView(StaffShipmentDetailView, { path: '/staff/shipments/999' })
    await flush()
    expect(wrapper.find('h1').text()).toBe('Không tìm thấy vận đơn')
  })

  // ---------------- Spec 006: điều phối lấy hàng
  const TASK = (extra = {}) => ({
    id: 31, type: 'PICKUP', status: 'ACTIVE', shipper: SHIPPER, assigned_by: { id: 1, username: 'nv', full_name: 'NV' },
    assigned_at: '2026-11-22T03:00:00Z', closed_at: null, needs_attention: false, result: null, ...extra,
  })
  const AWAITING = { ...APPROVED, status: 'AWAITING_PICKUP', allowed_actions: ['ASSIGN_PICKUP'], tasks: [] }

  it('Chờ lấy hàng: chỉ nút Phân công; hộp chọn Shipper chỉ tải khi mở; phân công gửi id + updated_at', async () => {
    dispatchService.shippers.mockResolvedValue([{ ...SHIPPER, open_task_count: 1 }])
    const { wrapper } = await setup(AWAITING)
    expect(wrapper.findAll('.page__actions button').map((b) => b.text())).toEqual(['Phân công lấy hàng'])
    expect(dispatchService.shippers).not.toHaveBeenCalled()
    await button(wrapper, 'Phân công lấy hàng').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('12 Trần Thái Tông')
    const submit = dialog.find('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined() // chưa chọn Shipper
    await dialog.find('.picker__item input').setValue(true)
    expect(submit.attributes('disabled')).toBeUndefined()
    shipmentService.assignPickup.mockResolvedValue({ ...AWAITING, status: 'PICKUP_ASSIGNED', allowed_actions: [],
      tasks: [TASK()] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.assignPickup).toHaveBeenCalledWith('12', 7, AWAITING.updated_at)
    expect(wrapper.find('.alert--success').text()).toContain('Nguyễn Văn Long')
    expect(details(wrapper)['Shipper phụ trách']).toContain('Nguyễn Văn Long')
  })

  it('Đã lấy hàng: xác nhận tiếp nhận kèm ghi chú sai lệch đã cắt khoảng trắng', async () => {
    const picked = { ...AWAITING, status: 'PICKED_UP', holder_type: 'SHIPPER', holder_shipper: SHIPPER,
      allowed_actions: ['RECEIVE_AT_HUB'], tasks: [TASK({ status: 'SUCCEEDED', closed_at: '2026-11-22T04:00:00Z' })] }
    const { wrapper } = await setup(picked)
    expect(details(wrapper)['Đang giữ hàng']).toBe('Shipper · Nguyễn Văn Long')
    await button(wrapper, 'Xác nhận tiếp nhận').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('Nguyễn Văn Long')
    expect(dialog.find('textarea').attributes('maxlength')).toBe('500')
    await dialog.find('textarea').setValue('  Thiếu 1 kiện ')
    shipmentService.receiveAtHub.mockResolvedValue({ ...picked, status: 'AT_HUB', holder_type: 'HUB',
      holder_shipper: null, allowed_actions: [] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.receiveAtHub).toHaveBeenCalledWith('12', 'Thiếu 1 kiện', picked.updated_at)
    expect(details(wrapper)['Đang giữ hàng']).toBe('Điểm tập kết')
  })

  it('Lấy thất bại: nút Lấy lại / Kết thúc dùng chung hộp lý do; lý do của Shipper hiện ở thẻ Điều phối', async () => {
    const failed = { ...AWAITING, status: 'PICKUP_FAILED', allowed_actions: ['ABANDON_PICKUP', 'RETRY_PICKUP'],
      tasks: [TASK({ status: 'FAILED', closed_at: '2026-11-22T04:00:00Z',
        result: { outcome: 'FAILED', reason_code: 'SHOP_ABSENT', note: 'Gọi 3 lần', recorded_at: '2026-11-22T04:00:00Z' } })] }
    const { wrapper } = await setup(failed)
    expect(wrapper.find('.tasks__item').text()).toContain('Lý do: Shop vắng mặt / không liên lạc được — Gọi 3 lần')
    expect(wrapper.findAll('.page__actions button').map((b) => b.text())).toEqual(['Kết thúc', 'Lấy lại'])
    await button(wrapper, 'Lấy lại').trigger('click')
    await flush()
    let dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('Chờ lấy hàng')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await dialog.find('textarea').setValue('  Shop hẹn chiều ')
    shipmentService.retryPickup.mockResolvedValue({ ...AWAITING, tasks: failed.tasks })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.retryPickup).toHaveBeenCalledWith('12', 'Shop hẹn chiều', failed.updated_at)
    expect(button(wrapper, 'Phân công lấy hàng')).toBeDefined() // lấy lại xong phân công được ngay (D7)

    shipmentService.get.mockResolvedValue(failed)
    const again = await setup(failed)
    await button(again.wrapper, 'Kết thúc').trigger('click')
    await flush()
    dialog = openDialog(again.wrapper)
    expect(dialog.text()).toContain('không hoàn tác')
    expect(dialog.find('button[type="submit"]').classes()).toContain('btn--danger')
    await dialog.find('textarea').setValue('Shop đóng cửa')
    shipmentService.abandonPickup.mockResolvedValue({ ...failed, status: 'PICKUP_ABANDONED', allowed_actions: [] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.abandonPickup).toHaveBeenCalledWith('12', 'Shop đóng cửa', failed.updated_at)
  })

  it('Shipper bị khóa khi nhiệm vụ còn mở: cảnh báo cần đổi Shipper (D9)', async () => {
    const { wrapper } = await setup({ ...AWAITING, status: 'PICKUP_ASSIGNED', allowed_actions: [],
      tasks: [TASK({ needs_attention: true })] })
    expect(wrapper.find('.attention').text()).toContain('bị khóa')
  })
})

// ---------------------------------------------------------------- Spec 007: giao hàng
describe('StaffShipmentDetailView — giao hàng, giao lại / hoàn (spec 007)', () => {
  const DTASK = (extra = {}) => ({
    id: 51, type: 'DELIVERY', status: 'FAILED', attempt_no: 1, shipper: SHIPPER, assigned_by: { id: 2, full_name: 'NV' },
    assigned_at: '2026-11-22T05:00:00Z', closed_at: '2026-11-22T06:00:00Z', needs_attention: false,
    result: { outcome: 'FAILED', reason_code: 'RECEIVER_UNREACHABLE', note: 'Gọi 3 lần', cod_expected: null,
      cod_collected: null, recorded_at: '2026-11-22T06:00:00Z' }, ...extra,
  })
  const AT_HUB = { ...APPROVED, status: 'AT_HUB', holder_type: 'HUB', holder_shipper: null, holder_locked: false,
    delivery_attempts: 0, allowed_actions: ['ASSIGN_DELIVERY'], tasks: [] }
  const FAILED = { ...AT_HUB, status: 'DELIVERY_FAILED', holder_type: 'SHIPPER', holder_shipper: SHIPPER,
    delivery_attempts: 1, allowed_actions: ['DECIDE_REDELIVERY', 'DECIDE_RETURN'], tasks: [DTASK()] }

  it('Đã nhập điểm tập kết: phân công giao cần chọn Shipper + tích "đã nhận hàng"; gửi id + updated_at', async () => {
    dispatchService.shippers.mockResolvedValue([{ ...SHIPPER, open_task_count: 0 }])
    const { wrapper } = await setup(AT_HUB)
    await button(wrapper, 'Phân công giao hàng').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('Lần giao1/3')
    expect(normalize(dialog.text())).toContain('350.000 ₫')
    const submit = dialog.find('button[type="submit"]')
    await dialog.find('.picker__item input').setValue(true)
    expect(submit.attributes('disabled')).toBeDefined() // D6: chưa tích bàn giao
    await dialog.find('.checkbox input').setValue(true)
    expect(submit.attributes('disabled')).toBeUndefined()
    shipmentService.assignDelivery.mockResolvedValue({ ...AT_HUB, status: 'OUT_FOR_DELIVERY', allowed_actions: [],
      holder_type: 'SHIPPER', holder_shipper: SHIPPER,
      tasks: [DTASK({ status: 'ACTIVE', closed_at: null, result: null })] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.assignDelivery).toHaveBeenCalledWith('12', 7, AT_HUB.updated_at)
    expect(wrapper.find('.alert--success').text()).toContain('Đã phân công giao lần 1 cho Nguyễn Văn Long')
  })

  it('Giao thất bại: hiện lý do lần gần nhất, lần N/3, nút Giao lại / Chuyển hoàn; Điều phối có lý do theo nhóm giao', async () => {
    const { wrapper } = await setup(FAILED)
    expect(wrapper.find('.alert--danger').text()).toContain('Giao lần 1/3 thất bại: Không liên hệ được người nhận — Gọi 3 lần')
    expect(wrapper.findAll('.page__actions button').map((b) => b.text())).toEqual(['Chuyển hoàn', 'Giao lại'])
    expect(details(wrapper)['Số lần giao']).toBe('1/3')
    expect(wrapper.find('.tasks__item').text()).toContain('Giao hàng · lần 1')
    expect(wrapper.find('.tasks__result').text()).toContain('Lý do: Không liên hệ được người nhận')
  })

  it('Giao lại: lý do bắt buộc, gửi lý do đã cắt khoảng trắng + updated_at', async () => {
    const { wrapper } = await setup(FAILED)
    await button(wrapper, 'Giao lại').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('đã giao 1/3 lần')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await dialog.find('textarea').setValue('  Khách hẹn sau 17h ')
    shipmentService.decideRedelivery.mockResolvedValue({ ...FAILED, status: 'AWAITING_REDELIVERY',
      allowed_actions: ['ASSIGN_DELIVERY'] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.decideRedelivery).toHaveBeenCalledWith('12', 'Khách hẹn sau 17h', FAILED.updated_at)
    expect(button(wrapper, 'Phân công giao hàng')).toBeDefined()
  })

  it('Chờ giao lại khi hàng ở Shipper (D7): hộp chỉ có người đang giữ, không tải danh sách', async () => {
    const waiting = { ...FAILED, status: 'AWAITING_REDELIVERY', allowed_actions: ['ASSIGN_DELIVERY'] }
    const { wrapper } = await setup(waiting)
    await button(wrapper, 'Phân công giao hàng').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('h2').text()).toBe('Phân công giao lại')
    expect(dispatchService.shippers).not.toHaveBeenCalled()
    expect(dialog.findAll('.picker__item')).toHaveLength(1)
    expect(dialog.text()).toContain('Lần giao2/3')
    await dialog.find('.checkbox input').setValue(true)
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('Shipper giữ hàng bị khóa (D7): cảnh báo ở Điều phối và trong hộp; không bấm phân công được', async () => {
    const locked = { ...FAILED, status: 'AWAITING_REDELIVERY', allowed_actions: ['ASSIGN_DELIVERY'], holder_locked: true }
    const { wrapper } = await setup(locked)
    expect(wrapper.find('.attention').text()).toContain('Shipper đang giữ hàng đã bị khóa')
    await button(wrapper, 'Phân công giao hàng').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('.alert--warning').exists()).toBe(true)
    expect(dialog.find('.picker').exists()).toBe(false)
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('đủ 3 lần (D8): chỉ nút Chuyển hoàn, ghi rõ chỉ được hoàn; hoàn gửi lý do', async () => {
    const third = { ...FAILED, delivery_attempts: 3, allowed_actions: ['DECIDE_RETURN'],
      tasks: [DTASK({ id: 53, attempt_no: 3 }), DTASK({ id: 52, attempt_no: 2 }), DTASK()] }
    const { wrapper } = await setup(third)
    expect(wrapper.findAll('.page__actions button').map((b) => b.text())).toEqual(['Chuyển hoàn'])
    expect(wrapper.find('.alert--danger').text()).toContain('đã đủ 3 lần nên chỉ được chuyển hoàn')
    await button(wrapper, 'Chuyển hoàn').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    await dialog.find('textarea').setValue('Không liên lạc được 3 lần')
    shipmentService.decideReturn.mockResolvedValue({ ...third, status: 'AWAITING_RETURN', allowed_actions: [] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.decideReturn).toHaveBeenCalledWith('12', 'Không liên lạc được 3 lần', third.updated_at)
  })

  it('Đã giao: thẻ "Kết quả giao" (thời gian, lần, COD đã thu); lịch sử hiện COD đã thu dạng tiền', async () => {
    const delivered = { ...AT_HUB, status: 'DELIVERED', holder_type: 'RECIPIENT', allowed_actions: [],
      delivery_attempts: 2, delivery: { delivered_at: '2026-11-22T06:00:00Z', cod_collected: 350000, attempt_no: 2 } }
    shipmentService.events.mockResolvedValue(page([{ id: 9, action: 'CONFIRM_DELIVERY', from_status: 'OUT_FOR_DELIVERY',
      to_status: 'DELIVERED', actor: SHIPPER, reason: '', created_at: '2026-11-22T06:00:00Z',
      changes: { cod_collected: { from: null, to: 350000 }, delivery_attempts: { from: 1, to: 2 } } }]))
    shipmentService.get.mockResolvedValue(delivered)
    const { wrapper } = await mountView(StaffShipmentDetailView, {
      path: '/staff/shipments/12', beforeMount: () => { useMetaStore().choices = CHOICES },
    })
    await flush()
    const d = details(wrapper)
    expect(d['Lần giao']).toBe('2')
    expect(normalize(d['COD đã thu'])).toBe('350.000 ₫')
    expect(normalize(wrapper.find('.events__changes').text())).toContain('COD đã thu: (trống) → 350.000 ₫')
    expect(wrapper.find('.events__changes').text()).toContain('Số lần đã giao: 1 → 2')
  })
})

// ---------------------------------------------------------------- Spec 008: hoàn hàng
describe('StaffShipmentDetailView — hoàn hàng (spec 008)', () => {
  const RTASK = (extra = {}) => ({
    id: 71, type: 'RETURN', status: 'ACTIVE', attempt_no: null, shipper: SHIPPER, assigned_by: { id: 2, full_name: 'NV' },
    assigned_at: '2026-11-23T02:00:00Z', closed_at: null, needs_attention: false, handover_reported_at: null, result: null,
    ...extra,
  })
  const AWAITING = { ...APPROVED, status: 'AWAITING_RETURN', holder_type: 'SHIPPER', holder_shipper: SHIPPER,
    holder_locked: false, delivery_attempts: 1, allowed_actions: ['ASSIGN_RETURN'], tasks: [] }
  const RETURNING = { ...AWAITING, status: 'RETURNING', allowed_actions: ['RECEIVE_RETURN', 'REPORT_RETURN_ISSUE'],
    tasks: [RTASK()] }
  const PICKUP_WAIT = { ...AWAITING, status: 'AWAITING_SHOP_PICKUP', holder_type: 'HUB', holder_shipper: null,
    allowed_actions: ['CONFIRM_SHOP_RECEIVED'], tasks: [RTASK({ status: 'SUCCEEDED', closed_at: '2026-11-23T04:00:00Z' })] }

  it('Chờ xử lý hoàn: phân công hoàn chỉ người đang giữ, không ô tích bàn giao; gửi id + updated_at', async () => {
    const { wrapper } = await setup(AWAITING)
    await button(wrapper, 'Phân công hoàn hàng').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dispatchService.shippers).not.toHaveBeenCalled()
    expect(dialog.findAll('.picker__item')).toHaveLength(1)
    expect(dialog.find('.checkbox').exists()).toBe(false)
    expect(dialog.text()).toContain('Điểm tập kết HTT EXPRESS')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    shipmentService.assignReturn.mockResolvedValue({ ...RETURNING })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.assignReturn).toHaveBeenCalledWith('12', 7, AWAITING.updated_at)
    expect(wrapper.find('.alert--success').text()).toContain('Đã phân công hoàn cho Nguyễn Văn Long')
  })

  it('Đang hoàn: Ghi sai lệch + Tiếp nhận; Shipper chưa báo → cảnh báo; tiếp nhận gửi ghi chú đã cắt', async () => {
    const { wrapper } = await setup(RETURNING)
    expect(wrapper.findAll('.page__actions button').map((b) => b.text())).toEqual(['Ghi sai lệch', 'Tiếp nhận hàng hoàn'])
    await button(wrapper, 'Tiếp nhận hàng hoàn').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('.alert--warning').text()).toContain('Shipper chưa báo đã đưa hàng về')
    await dialog.find('textarea').setValue('  Móp hộp  ')
    shipmentService.receiveReturn.mockResolvedValue({ ...PICKUP_WAIT })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.receiveReturn).toHaveBeenCalledWith('12', 'Móp hộp', RETURNING.updated_at)
    expect(button(wrapper, 'Xác nhận Shop đã nhận')).toBeDefined()
  })

  it('Shipper đã báo: không cảnh báo; Điều phối hiện thời điểm báo', async () => {
    const reported = { ...RETURNING, tasks: [RTASK({ handover_reported_at: '2026-11-23T03:00:00Z' })] }
    const { wrapper } = await setup(reported)
    expect(wrapper.find('.tasks__item').text()).toContain('Shipper đã báo đưa hàng về lúc')
    await button(wrapper, 'Tiếp nhận hàng hoàn').trigger('click')
    await flush()
    expect(openDialog(wrapper).find('.alert--warning').exists()).toBe(false)
  })

  it('"Có sai lệch, chưa nhận?" mở hộp ghi sai lệch; lý do bắt buộc; gửi lý do', async () => {
    const { wrapper } = await setup(RETURNING)
    await button(wrapper, 'Tiếp nhận hàng hoàn').trigger('click')
    await flush()
    await openDialog(wrapper).findAll('button').find((b) => b.text() === 'Có sai lệch, chưa nhận?').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('h2').text()).toBe('Ghi sai lệch hàng hoàn')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await dialog.find('textarea').setValue('Thiếu 1 kiện')
    shipmentService.reportReturnIssue.mockResolvedValue({ ...RETURNING })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.reportReturnIssue).toHaveBeenCalledWith('12', 'Thiếu 1 kiện', RETURNING.updated_at)
    expect(wrapper.find('.alert--success').text()).toContain('Đơn vẫn chờ tiếp nhận')
  })

  it('Chờ Shop đến lấy: tên người nhận điền sẵn tên Shop, phải tích kiểm tra; gửi tên đã cắt + ghi chú', async () => {
    const { wrapper } = await setup(PICKUP_WAIT)
    await button(wrapper, 'Xác nhận Shop đã nhận').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    const name = dialog.find('input[type="text"]')
    expect(name.element.value).toBe('Shop Hoa')
    expect(name.attributes('maxlength')).toBe('100')
    const submit = dialog.find('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined() // chưa tích (D7)
    await dialog.find('.checkbox input').setValue(true)
    expect(submit.attributes('disabled')).toBeUndefined()
    await name.setValue('   ')
    expect(submit.attributes('disabled')).toBeDefined() // tên trống
    await name.setValue('  Chị Hoa (ủy quyền) ')
    shipmentService.confirmShopReceived.mockResolvedValue({ ...PICKUP_WAIT, status: 'RETURNED_TO_SHOP', allowed_actions: [],
      return_result: { received_at: '2026-11-23T05:00:00Z', receiver_name: 'Chị Hoa (ủy quyền)' } })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(shipmentService.confirmShopReceived).toHaveBeenCalledWith('12', 'Chị Hoa (ủy quyền)', '', PICKUP_WAIT.updated_at)
    expect(details(wrapper)['Người nhận']).toBe('Chị Hoa (ủy quyền)')
  })
})

