import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as dispatchService from '../../../services/dispatchService'
import { mountWithModel } from '../../../test-utils'
import ShipperPicker from '../ShipperPicker.vue'

vi.mock('../../../services/dispatchService', () => ({ shippers: vi.fn() }))

const LONG = { id: 7, username: 'sp_long', full_name: 'Nguyễn Văn Long', phone: '0912345678', open_task_count: 0 }
const BINH = { id: 8, username: 'sp_binh', full_name: 'Trần Bình', phone: '0987654321', open_task_count: 3 }
const flush = () => new Promise((r) => setTimeout(r, 0))

beforeEach(() => dispatchService.shippers.mockReset())
afterEach(() => vi.useRealTimers())

describe('ShipperPicker', () => {
  it('hiện Shipper đang hoạt động kèm khối lượng việc; chọn → v-model là id', async () => {
    dispatchService.shippers.mockResolvedValue([LONG, BINH])
    const wrapper = mount(ShipperPicker, { props: { modelValue: null, 'onUpdate:modelValue': (v) => wrapper.setProps({ modelValue: v }) } })
    await flush()
    expect(dispatchService.shippers).toHaveBeenCalledWith({ q: undefined })
    const items = wrapper.findAll('.picker__item')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('Nguyễn Văn Long')
    expect(items[0].text()).toContain('0912 345 678')
    expect(items[0].find('.picker__load').text()).toBe('Đang rảnh')
    expect(items[1].find('.picker__load').text()).toBe('3 nhiệm vụ đang mở')
    await items[1].find('input').setValue(true)
    expect(wrapper.emitted('update:modelValue').at(-1)).toEqual([8])
    expect(wrapper.find('.picker__item.is-selected').text()).toContain('Trần Bình')
  })

  it('tìm: chỉ gọi API khi ngừng gõ; không thấy → báo không tìm thấy', async () => {
    vi.useFakeTimers()
    dispatchService.shippers.mockResolvedValue([LONG])
    const wrapper = mount(ShipperPicker)
    await vi.runAllTimersAsync()
    dispatchService.shippers.mockResolvedValue([])
    const input = wrapper.find('input[type="search"]')
    await input.setValue('b')
    await input.setValue('bi')
    await input.setValue(' bình ')
    expect(dispatchService.shippers).toHaveBeenCalledTimes(1) // chưa gọi khi đang gõ
    await vi.runAllTimersAsync()
    expect(dispatchService.shippers).toHaveBeenCalledTimes(2)
    expect(dispatchService.shippers).toHaveBeenLastCalledWith({ q: 'bình' })
    expect(wrapper.find('.picker__empty').text()).toBe('Không tìm thấy Shipper phù hợp.')
  })

  it('không có Shipper hoạt động: hướng dẫn giữ đơn và phân công sau (UC06.5 A1)', async () => {
    dispatchService.shippers.mockResolvedValue([])
    const wrapper = mount(ShipperPicker)
    await flush()
    expect(wrapper.find('.picker__empty').text()).toContain('Giữ đơn ở Chờ lấy hàng và phân công sau')
  })

  it('lỗi tải: báo lỗi + Tải lại', async () => {
    dispatchService.shippers.mockRejectedValueOnce(new Error('Mất mạng'))
    const wrapper = mount(ShipperPicker)
    await flush()
    expect(wrapper.find('[role="alert"]').text()).toContain('Mất mạng')
    dispatchService.shippers.mockResolvedValue([LONG])
    await wrapper.find('[role="alert"] button').trigger('click')
    await flush()
    expect(wrapper.findAll('.picker__item')).toHaveLength(1)
  })

  it('kết quả tìm cũ về muộn không đè kết quả mới', async () => {
    vi.useFakeTimers()
    let resolveOld
    dispatchService.shippers.mockResolvedValueOnce([LONG, BINH])
    const wrapper = mount(ShipperPicker)
    await vi.runAllTimersAsync()
    dispatchService.shippers.mockReturnValueOnce(new Promise((r) => { resolveOld = r }))
    await wrapper.find('input[type="search"]').setValue('lo')
    await vi.runAllTimersAsync()
    dispatchService.shippers.mockResolvedValueOnce([BINH])
    await wrapper.find('input[type="search"]').setValue('bình')
    await vi.runAllTimersAsync()
    resolveOld([LONG])
    await vi.runAllTimersAsync()
    expect(wrapper.findAll('.picker__item').map((i) => i.find('strong').text())).toEqual(['Trần Bình'])
  })
})

describe('ShipperPicker — giao lại khi hàng đang ở Shipper (D7)', () => {
  const HOLDER = { id: 7, username: 'sp_long', full_name: 'Shipper Long', phone: '0912345678' }

  it('chỉ người đang giữ hàng, chọn sẵn, không tải danh sách, có giải thích', async () => {
    const wrapper = mountWithModel(ShipperPicker, { holder: HOLDER })
    await flush()
    expect(dispatchService.shippers).not.toHaveBeenCalled()
    expect(wrapper.props('modelValue')).toBe(7)
    expect(wrapper.findAll('input[type="radio"]')).toHaveLength(1)
    expect(wrapper.find('input[type="search"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Shipper Long')
    expect(wrapper.text()).toContain('đổi Shipper')
  })

  it('không có holder: vẫn tải danh sách như spec 006', async () => {
    dispatchService.shippers.mockResolvedValue([{ ...HOLDER, open_task_count: 0 }])
    const wrapper = mount(ShipperPicker, { props: { modelValue: null } })
    await flush()
    expect(dispatchService.shippers).toHaveBeenCalledTimes(1)
    expect(wrapper.find('input[type="search"]').exists()).toBe(true)
  })
})
