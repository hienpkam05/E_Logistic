import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/http'
import * as taskService from '../../services/taskService'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import ShipperHomeView from '../shipper/ShipperHomeView.vue'
import TaskDetailView from '../shipper/TaskDetailView.vue'
import TaskListView from '../shipper/TaskListView.vue'
import { flush, mountView } from './helpers'
import { DELIVERY_TASK, PICKUP_TASK, RETURN_TASK, SHIPMENT_CHOICES, page } from './shipmentFixtures'

vi.mock('../../services/taskService', () => ({
  list: vi.fn(), get: vi.fn(), confirmPickup: vi.fn(), failPickup: vi.fn(), confirmDelivery: vi.fn(),
  failDelivery: vi.fn(), reportReturnHandover: vi.fn(), reportSwapHandover: vi.fn(),
}))

const withChoices = () => { useMetaStore().choices = SHIPMENT_CHOICES }
const button = (wrapper, text) =>
  wrapper.findAll('button').find((b) => b.text() === text && !b.element.closest('dialog'))
const openDialog = (wrapper) => wrapper.findAll('dialog').find((d) => d.element.open)
// D3: Shipper đi lấy không được thấy những thông tin này (backend không gửi; màn hình cũng không có chỗ hiện).
const FORBIDDEN_TEXT = ['Người nhận', 'Giao đến', 'Thu hộ', 'COD']

afterEach(() => {
  document.body.innerHTML = ''
  Object.values(taskService).forEach((fn) => fn.mockReset())
})

describe('TaskListView (UC04.1)', () => {
  async function setup(path = '/shipper/tasks', data = page([PICKUP_TASK])) {
    taskService.list.mockResolvedValue(data)
    const result = await mountView(TaskListView, { path, beforeMount: withChoices })
    await flush()
    return result
  }

  it('mặc định Đang làm: thẻ có mã, Shop, địa chỉ lấy, số kiện, trạng thái; bấm mở chi tiết', async () => {
    const { wrapper } = await setup()
    expect(taskService.list).toHaveBeenCalledWith({ open: true, page: 1 })
    const card = wrapper.find('.task-card')
    expect(card.attributes('href')).toBe('/shipper/tasks/31')
    for (const text of ['HTT261122K7Q2M', 'Shop Hoa', '12 Trần Thái Tông, Phường Dịch Vọng', '2 kiện', 'Đang thực hiện']) {
      expect(card.text()).toContain(text)
    }
  })

  it('tab Đã xong ghi lên URL và gọi open=false', async () => {
    const { wrapper, router } = await setup()
    await button(wrapper, 'Đã xong').trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ done: '1' })
    expect(taskService.list).toHaveBeenLastCalledWith({ open: false, page: 1 })
  })

  it('chưa có nhiệm vụ: báo trống + gợi ý tải lại (A1); Tải lại gọi lại API', async () => {
    const { wrapper } = await setup('/shipper/tasks', page([]))
    expect(wrapper.text()).toContain('Chưa có nhiệm vụ.')
    await button(wrapper, 'Tải lại').trigger('click')
    expect(taskService.list).toHaveBeenCalledTimes(2)
  })

  it('lỗi tải: báo lỗi', async () => {
    taskService.list.mockRejectedValueOnce(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Mất mạng' }))
    const { wrapper } = await mountView(TaskListView, { path: '/shipper/tasks', beforeMount: withChoices })
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất mạng')
  })
})

describe('TaskDetailView (UC04.1–04.3)', () => {
  it('chờ đổi người: chỉ điểm tập kết và báo bàn giao; không người nhận, COD hoặc nút thất bại', async () => {
    const task = { ...DELIVERY_TASK, status: 'PENDING_SWAP_HANDOVER', allowed_actions: ['REPORT_SWAP_HANDOVER'] }
    taskService.get.mockResolvedValue(task)
    taskService.reportSwapHandover.mockResolvedValue({ ...task, allowed_actions: [], handover_reported_at: '2026-11-23T05:00:00Z' })
    const { wrapper } = await mountView(TaskDetailView, { path: '/shipper/tasks/41', beforeMount: withChoices })
    await flush()
    expect(wrapper.text()).toContain('Đưa hàng về để bàn giao')
    expect(wrapper.find('.cod-card').exists()).toBe(false)
    expect(button(wrapper, 'Giao thành công')).toBeUndefined()
    expect(button(wrapper, 'Giao thất bại')).toBeUndefined()
    await button(wrapper, 'Đã đưa hàng về điểm tập kết').trigger('click'); await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('input[type="number"]').exists()).toBe(false)
    expect(dialog.find('button[type="submit"]').element.disabled).toBe(false)
    await dialog.find('form').trigger('submit'); await flush()
    expect(taskService.reportSwapHandover).toHaveBeenCalledWith('41')
    expect(wrapper.text()).toContain('chờ Nhân viên điểm tập kết xác nhận')
    expect(button(wrapper, 'Đã đưa hàng về điểm tập kết')).toBeUndefined()
  })
  async function setup(task = PICKUP_TASK) {
    taskService.get.mockResolvedValue(task)
    const result = await mountView(TaskDetailView, { path: `/shipper/tasks/${task.id}`, beforeMount: withChoices })
    await flush()
    return result
  }

  it('thông tin để đi lấy + nút gọi; không có người nhận / COD (D3)', async () => {
    const { wrapper } = await setup()
    expect(wrapper.find('h1').text()).toBe('HTT261122K7Q2M')
    expect(wrapper.text()).toContain('12 Trần Thái Tông, Phường Dịch Vọng')
    expect(wrapper.find('a[href="tel:0912345678"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Gọi trước')
    for (const text of FORBIDDEN_TEXT) expect(wrapper.text()).not.toContain(text)
    expect(button(wrapper, 'Đã lấy hàng')).toBeDefined()
    expect(button(wrapper, 'Lấy hàng thất bại')).toBeDefined()
  })

  it('nhiệm vụ đã đóng: backend ẩn SĐT (spec 007 D3) → còn tên, không nút gọi, không "tel:null"', async () => {
    const { wrapper } = await setup({
      ...PICKUP_TASK, status: 'SUCCEEDED', allowed_actions: [],
      shipment: { ...PICKUP_TASK.shipment, sender_phone: null },
      result: { outcome: 'SUCCEEDED', reason_code: null, note: '', recorded_at: '2026-11-22T04:00:00Z' },
    })
    expect(wrapper.text()).toContain(PICKUP_TASK.shipment.sender_name)
    expect(wrapper.find('a[href^="tel:"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('null')
  })

  it('"Đã lấy hàng": hộp xác nhận nêu mã/Shop/số kiện; xong ẩn nút, báo mang về điểm tập kết', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Đã lấy hàng').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    for (const text of ['HTT261122K7Q2M', 'Shop Hoa', 'Áo len']) expect(dialog.text()).toContain(text)
    expect(taskService.confirmPickup).not.toHaveBeenCalled()
    taskService.confirmPickup.mockResolvedValue({
      ...PICKUP_TASK, status: 'SUCCEEDED', allowed_actions: [],
      result: { outcome: 'SUCCEEDED', reason_code: null, note: '', recorded_at: '2026-11-22T04:00:00Z' },
    })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(taskService.confirmPickup).toHaveBeenCalledWith('31')
    expect(wrapper.find('.alert--success').text()).toContain('điểm tập kết')
    expect(button(wrapper, 'Đã lấy hàng')).toBeUndefined()
    expect(wrapper.find('.alert--info').text()).toContain('Đã lấy hàng lúc')
  })

  it('"Lấy hàng thất bại": phải chọn lý do; Khác bắt buộc ghi chú; gửi ghi chú đã cắt khoảng trắng', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Lấy hàng thất bại').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    const submit = dialog.find('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined()
    expect(dialog.findAll('option').map((o) => o.text())).toContain('Hàng chưa sẵn sàng') // nhãn từ backend
    await dialog.find('select').setValue('OTHER')
    expect(submit.attributes('disabled')).toBeDefined() // Khác mà chưa ghi chú
    expect(dialog.text()).toContain('bắt buộc với lý do Khác')
    await dialog.find('textarea').setValue('   ')
    expect(submit.attributes('disabled')).toBeDefined()
    await dialog.find('textarea').setValue('  Cổng khóa  ')
    expect(submit.attributes('disabled')).toBeUndefined()
    taskService.failPickup.mockResolvedValue({
      ...PICKUP_TASK, status: 'FAILED', allowed_actions: [],
      result: { outcome: 'FAILED', reason_code: 'OTHER', note: 'Cổng khóa', recorded_at: '2026-11-22T04:00:00Z' },
    })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(taskService.failPickup).toHaveBeenCalledWith('31', 'OTHER', 'Cổng khóa')
    expect(wrapper.find('.alert--info').text()).toContain('Lấy thất bại: Khác — Cổng khóa')
  })

  it('lý do thường không cần ghi chú', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Lấy hàng thất bại').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    await dialog.find('select').setValue('SHOP_ABSENT')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('409 nhiệm vụ đã kết thúc (E1): đóng hộp, báo, tải trạng thái mới', async () => {
    const { wrapper } = await setup()
    taskService.confirmPickup.mockRejectedValue(new ApiError({
      status: 409, code: 'INVALID_TRANSITION', message: 'Nhiệm vụ đã kết thúc hoặc đã chuyển cho người khác.',
    }))
    taskService.get.mockResolvedValue({ ...PICKUP_TASK, status: 'FAILED', allowed_actions: [] })
    await button(wrapper, 'Đã lấy hàng').trigger('click')
    await flush()
    await openDialog(wrapper).find('form').trigger('submit')
    await flush()
    expect(openDialog(wrapper)).toBeUndefined()
    expect(wrapper.find('.alert--warning').text()).toContain('đã kết thúc')
    expect(taskService.get).toHaveBeenCalledTimes(2)
    expect(button(wrapper, 'Đã lấy hàng')).toBeUndefined()
  })

  it('404 (đã chuyển người khác): báo không tìm thấy', async () => {
    taskService.get.mockRejectedValue(new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' }))
    const { wrapper } = await mountView(TaskDetailView, { path: '/shipper/tasks/99', beforeMount: withChoices })
    await flush()
    expect(wrapper.find('h1').text()).toBe('Không tìm thấy nhiệm vụ')
  })
})

describe('ShipperHomeView', () => {
  it('3 ô đang làm theo loại (giao, lấy, hoàn — spec 007 D11, 008 D10): count nhiệm vụ mở, mở đúng loại', async () => {
    const COUNTS = { DELIVERY: 2, PICKUP: 3, RETURN: 1 }
    taskService.list.mockImplementation(async ({ type }) => page([], { count: COUNTS[type] }))
    const { wrapper } = await mountView(ShipperHomeView, {
      path: '/shipper',
      beforeMount: () => {
        withChoices()
        useAuthStore().setUser({ id: 7, username: 'sp', full_name: 'Shipper Long', role: 'SHIPPER', must_change_password: false })
      },
    })
    await flush()
    expect(taskService.list).toHaveBeenCalledWith({ type: 'DELIVERY', open: true })
    expect(taskService.list).toHaveBeenCalledWith({ type: 'PICKUP', open: true })
    const tiles = wrapper.findAll('.highlight').map((t) => [t.text().match(/\d+/)[0], t.attributes('href')])
    expect(tiles).toEqual([['2', '/shipper/tasks?type=DELIVERY'], ['3', '/shipper/tasks?type=PICKUP'],
      ['1', '/shipper/tasks?type=RETURN']])
    expect(wrapper.text()).not.toContain('Nhiệm vụ giao hàng, ghi nhận COD') // đã có, gỡ khỏi "Sắp có"
    expect(wrapper.text()).not.toContain('Nhiệm vụ hoàn hàng') // spec 008: đã có
    // menu chức năng: mục "Nhiệm vụ" (lấy + giao — spec 007 D11) trỏ tới danh sách
    const menu = wrapper.findAll('a').filter((a) => a.text().trim().startsWith('Nhiệm vụ'))
    expect(menu.map((a) => a.attributes('href'))).toContain('/shipper/tasks')
  })
})

// ---------------------------------------------------------------- Spec 007: nhiệm vụ GIAO
const normalize = (text) => text.replace(/\s+/g, ' ')

describe('TaskListView — lọc loại + thẻ giao (UC04.4)', () => {
  it('chip loại ghi ?type lên URL và gọi API theo loại; thẻ giao có người nhận, COD, lần N/3', async () => {
    taskService.list.mockResolvedValue(page([DELIVERY_TASK, PICKUP_TASK]))
    const { wrapper, router } = await mountView(TaskListView, { path: '/shipper/tasks', beforeMount: withChoices })
    await flush()
    expect(wrapper.findAll('.chip').map((c) => c.text())).toEqual(['Tất cả', 'Lấy hàng', 'Giao hàng', 'Hoàn hàng'])
    const [delivery, pickup] = wrapper.findAll('.task-card')
    for (const text of ['Giao hàng · lần 2/3', 'Trần Thị B', '5 Láng Hạ, Phường Láng']) expect(normalize(delivery.text())).toContain(text)
    expect(normalize(delivery.text())).toContain('COD 350.000 ₫')
    expect(delivery.text()).not.toContain('Shop Hoa') // D3: thẻ giao không cần thông tin đi lấy
    expect(pickup.text()).toContain('12 Trần Thái Tông')
    await wrapper.findAll('.chip')[2].trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ type: 'DELIVERY' })
    expect(taskService.list).toHaveBeenLastCalledWith({ type: 'DELIVERY', open: true, page: 1 })
    await button(wrapper, 'Đã xong').trigger('click')
    await flush()
    expect(router.currentRoute.value.query).toEqual({ type: 'DELIVERY', done: '1' }) // giữ bộ lọc loại
  })

  it('?type lạ → tất cả', async () => {
    taskService.list.mockResolvedValue(page([]))
    await mountView(TaskListView, { path: '/shipper/tasks?type=XYZ', beforeMount: withChoices })
    await flush()
    expect(taskService.list).toHaveBeenCalledWith({ type: undefined, open: true, page: 1 })
  })
})

describe('TaskDetailView — nhiệm vụ GIAO (UC04.4–04.7)', () => {
  async function setup(task = DELIVERY_TASK) {
    taskService.get.mockResolvedValue(task)
    const result = await mountView(TaskDetailView, { path: `/shipper/tasks/${task.id}`, beforeMount: withChoices })
    await flush()
    return result
  }
  const typeCod = async (dialog, value) => {
    await dialog.find('.cod__input').setValue(value)
    await flush()
  }

  it('hiện người nhận, nút gọi, COD, lần N/3; không có thông tin đi lấy (D3)', async () => {
    const { wrapper } = await setup()
    expect(normalize(wrapper.find('.task-type').text())).toContain('Giao hàng · lần 2/3')
    expect(wrapper.text()).toContain('5 Láng Hạ, Phường Láng')
    expect(wrapper.find('a[href="tel:0987654321"]').exists()).toBe(true)
    expect(normalize(wrapper.find('.cod-card__amount').text())).toBe('350.000 ₫')
    expect(wrapper.text()).not.toContain('Lấy hàng tại')
    expect(button(wrapper, 'Giao thành công')).toBeDefined()
    expect(button(wrapper, 'Giao thất bại')).toBeDefined()
  })

  it('"Giao thành công": phải tự gõ COD khớp mới bấm được; gửi số đã thu; xong báo đã giao', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Giao thành công').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('Trần Thị B')
    const submit = dialog.find('button[type="submit"]')
    expect(dialog.find('.cod__input').element.value).toBe('') // D5: không điền sẵn
    expect(submit.attributes('disabled')).toBeDefined()
    await typeCod(dialog, '330000')
    expect(submit.attributes('disabled')).toBeDefined() // thiếu → chưa cho xác nhận
    await typeCod(dialog, '350000')
    expect(submit.attributes('disabled')).toBeUndefined()
    taskService.confirmDelivery.mockResolvedValue({ ...DELIVERY_TASK, status: 'SUCCEEDED', allowed_actions: [],
      shipment: { ...DELIVERY_TASK.shipment, receiver_phone: null },
      result: { outcome: 'SUCCEEDED', reason_code: null, note: '', cod_expected: 350000, cod_collected: 350000,
        recorded_at: '2026-11-22T06:00:00Z' } })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(taskService.confirmDelivery).toHaveBeenCalledWith('41', 350000)
    expect(wrapper.find('.alert--success').text()).toContain('giao thành công')
    expect(normalize(wrapper.find('.alert--info').text())).toContain('đã thu COD 350.000 ₫')
    expect(button(wrapper, 'Giao thành công')).toBeUndefined()
    expect(wrapper.find('a[href^="tel:"]').exists()).toBe(false) // đã đóng: ẩn SĐT
  })

  it('backend báo lệch COD (E1.1): hiện ở ô COD, hộp vẫn mở', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Giao thành công').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    await typeCod(dialog, '350000')
    taskService.confirmDelivery.mockRejectedValue(new ApiError({ status: 400, code: 'VALIDATION_ERROR', message: 'x',
      fields: { cod_collected: ['Thiếu 20.000 ₫ so với COD phải thu 350.000 ₫.'] } }))
    await dialog.find('form').trigger('submit')
    await flush()
    expect(openDialog(wrapper)).toBeDefined()
    expect(openDialog(wrapper).find('.cod [role="alert"]').text()).toContain('Thiếu 20.000')
  })

  it('"Chưa thu đủ? Ghi giao thất bại" (E1.3): mở hộp thất bại chọn sẵn lý do chưa đủ tiền COD', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Giao thành công').trigger('click')
    await flush()
    await openDialog(wrapper).findAll('button').find((b) => b.text().startsWith('Chưa thu đủ')).trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('h2').text()).toBe('Giao hàng thất bại')
    expect(dialog.find('select').element.value).toBe('COD_NOT_READY')
    expect(dialog.text()).toContain('Lần giao 2/3')
    taskService.failDelivery.mockResolvedValue({ ...DELIVERY_TASK, status: 'FAILED', allowed_actions: [],
      result: { outcome: 'FAILED', reason_code: 'COD_NOT_READY', note: '', cod_expected: null, cod_collected: null,
        recorded_at: '2026-11-22T06:00:00Z' } })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(taskService.failDelivery).toHaveBeenCalledWith('41', 'COD_NOT_READY', '')
    expect(wrapper.find('.alert--success').text()).toContain('Hàng vẫn do bạn giữ')
    expect(wrapper.find('.alert--info').text()).toContain('Người nhận chưa đủ tiền COD')
  })

  it('"Giao thất bại": lý do theo danh mục giao; Khác bắt buộc ghi chú', async () => {
    const { wrapper } = await setup()
    await button(wrapper, 'Giao thất bại').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.findAll('option').map((o) => o.text())).toEqual(
      ['Chọn lý do', 'Không liên hệ được người nhận', 'Người nhận chưa đủ tiền COD', 'Khác'])
    await dialog.find('select').setValue('OTHER')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await dialog.find('textarea').setValue('  Cổng khóa ')
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('đơn không COD (A1): không có ô nhập, xác nhận được ngay, gửi 0', async () => {
    const noCod = { ...DELIVERY_TASK, shipment: { ...DELIVERY_TASK.shipment, cod_amount: 0 } }
    const { wrapper } = await setup(noCod)
    expect(wrapper.find('.cod-card__amount').text()).toBe('Không thu hộ')
    await button(wrapper, 'Giao thành công').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.find('.cod__input').exists()).toBe(false)
    expect(dialog.findAll('button').some((b) => b.text().startsWith('Chưa thu đủ'))).toBe(false)
    expect(dialog.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    taskService.confirmDelivery.mockResolvedValue({ ...noCod, status: 'SUCCEEDED', allowed_actions: [] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(taskService.confirmDelivery).toHaveBeenCalledWith('41', 0)
  })
})

// ---------------------------------------------------------------- Spec 008: nhiệm vụ HOÀN
describe('Nhiệm vụ HOÀN của Shipper (UC04.8, UC04.9 bước 1–3)', () => {
  async function detailOf(task = RETURN_TASK) {
    taskService.get.mockResolvedValue(task)
    const result = await mountView(TaskDetailView, { path: `/shipper/tasks/${task.id}`, beforeMount: withChoices })
    await flush()
    return result
  }

  it('thẻ danh sách: Shop, điểm tập kết; cờ "đã báo" khi chờ xác nhận', async () => {
    taskService.list.mockResolvedValue(page([{ ...RETURN_TASK, handover_reported_at: '2026-11-23T03:00:00Z' }]))
    const { wrapper } = await mountView(TaskListView, { path: '/shipper/tasks?type=RETURN', beforeMount: withChoices })
    await flush()
    const card = wrapper.find('.task-card')
    expect(normalize(card.text())).toContain('Hoàn hàng')
    expect(card.text()).toContain('Shop Hoa')
    expect(card.text()).toContain('Về Điểm tập kết HTT EXPRESS')
    expect(card.find('.task-card__flag').text()).toContain('chờ xác nhận')
    expect(card.text()).not.toContain('undefined')
  })

  it('chi tiết: thẻ "Đưa hàng về" (điểm tập kết + lý do hoàn), chỉ một nút, không người nhận / COD', async () => {
    const { wrapper } = await detailOf()
    expect(wrapper.text()).toContain('Đưa hàng về')
    expect(wrapper.text()).toContain('1 Tràng Tiền, Hoàn Kiếm')
    expect(wrapper.find('.return-reason').text()).toContain('Khách từ chối nhận')
    expect(wrapper.find('a[href="tel:0241234567"]').exists()).toBe(true)
    const actions = wrapper.findAll('.task-actions button').map((b) => b.text())
    expect(actions).toEqual(['Đã đưa hàng về điểm tập kết'])
    for (const text of ['Giao đến', 'Thu hộ', 'Lấy hàng tại', 'undefined']) expect(wrapper.text()).not.toContain(text)
  })

  it('"Đã đưa hàng về": hộp xác nhận → gọi API; sau đó báo chờ NV xác nhận, hết nút (A1, BR1)', async () => {
    const { wrapper } = await detailOf()
    await button(wrapper, 'Đã đưa hàng về điểm tập kết').trigger('click')
    await flush()
    const dialog = openDialog(wrapper)
    expect(dialog.text()).toContain('Chỉ bấm khi đã giao hàng tận tay')
    taskService.reportReturnHandover.mockResolvedValue({ ...RETURN_TASK, handover_reported_at: '2026-11-23T03:00:00Z',
      allowed_actions: [] })
    await dialog.find('form').trigger('submit')
    await flush()
    expect(taskService.reportReturnHandover).toHaveBeenCalledWith('61')
    expect(wrapper.find('.alert--success').text()).toContain('Nhân viên điểm tập kết sẽ kiểm tra')
    expect(wrapper.text()).toContain('chờ Nhân viên điểm tập kết xác nhận tiếp nhận')
    expect(wrapper.find('.task-actions').exists()).toBe(false)
  })

  it('đã tiếp nhận: hiện kết quả, không còn dòng chờ xác nhận', async () => {
    const { wrapper } = await detailOf({ ...RETURN_TASK, status: 'SUCCEEDED', closed_at: '2026-11-23T04:00:00Z',
      handover_reported_at: '2026-11-23T03:00:00Z', allowed_actions: [],
      result: { outcome: 'SUCCEEDED', reason_code: null, note: '', cod_expected: null, cod_collected: null,
        recorded_at: '2026-11-23T04:00:00Z' } })
    expect(wrapper.find('.alert--info').text()).toContain('Điểm tập kết đã tiếp nhận lúc')
    expect(wrapper.text()).not.toContain('chờ Nhân viên điểm tập kết xác nhận')
  })
})

