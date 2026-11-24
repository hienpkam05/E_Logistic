import { afterEach, describe, expect, it, vi } from 'vitest'
import * as shipmentService from '../../services/shipmentService'
import { ApiError } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import TrackingView from '../common/TrackingView.vue'
import { flush, mountView } from './helpers'
import { SHIPMENT, SHIPMENT_CHOICES } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({ lookup: vi.fn() }))
const RESULT = { ...SHIPMENT, tracking_code: 'HTT261123ABCDE', shop: { full_name: 'Shop Hoa' } }
async function setup(path = '/tracking', role = 'SHOP') {
  const result = await mountView(TrackingView, { path, beforeMount: () => {
    useAuthStore().setUser({ id: 3, role })
    useMetaStore().choices = SHIPMENT_CHOICES
  } })
  await flush()
  return result
}
afterEach(() => { shipmentService.lookup.mockReset(); document.body.innerHTML = '' })

describe('TrackingView', () => {
  it('ban đầu không gọi API; mã rỗng báo lỗi, không tra cứu', async () => {
    const { wrapper } = await setup()
    expect(shipmentService.lookup).not.toHaveBeenCalled()
    await wrapper.find('input').setValue('   ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('Vui lòng nhập mã')
    expect(shipmentService.lookup).not.toHaveBeenCalled()
  })

  it.each(['SHOP', 'ADMIN'])('tra cứu, lưu mã trên URL và link đúng vai trò %s', async role => {
    shipmentService.lookup.mockResolvedValue(RESULT)
    const { wrapper, router } = await setup('/tracking', role)
    await wrapper.find('input').setValue('  htt261123abcde ')
    await wrapper.find('form').trigger('submit'); await flush(); await flush()
    expect(router.currentRoute.value.query.code).toBe('HTT261123ABCDE')
    expect(shipmentService.lookup).toHaveBeenCalledWith('HTT261123ABCDE')
    expect(wrapper.text()).toContain('Cập nhật gần nhất')
    const detail = wrapper.findAll('a').find(a => a.text() === 'Xem chi tiết')
    expect(detail.attributes('href')).toBe(`/${role === 'SHOP' ? 'shop' : 'staff'}/shipments/12`)
    expect(wrapper.findAll('a').find(a => a.text() === 'Lịch sử vận chuyển').attributes('href')).toContain('#shipment-history')
    expect(wrapper.findAll('dt').some(dt => dt.text() === 'Shop')).toBe(role === 'ADMIN')
  })

  it('mở URL có code tự tra cứu; back/forward bỏ dữ liệu cũ và khôi phục mã', async () => {
    shipmentService.lookup.mockResolvedValue(RESULT)
    const { wrapper, router } = await setup('/tracking?code=YC000012')
    expect(shipmentService.lookup).toHaveBeenCalledWith('YC000012')
    await router.push('/tracking'); await flush()
    expect(wrapper.find('input').element.value).toBe('')
    expect(wrapper.find('#lookup-result-title').exists()).toBe(false)
    await router.push('/tracking?code=YC000012'); await flush()
    expect(shipmentService.lookup).toHaveBeenCalledTimes(2)
  })

  it('404 và mất mạng giữ mã để thử lại cùng URL', async () => {
    shipmentService.lookup.mockRejectedValueOnce(new ApiError({ status: 404, code: 'NOT_FOUND' }))
    const { wrapper } = await setup('/tracking?code=HTT261123ABCDE')
    expect(wrapper.text()).toContain('Không tìm thấy vận đơn phù hợp')
    shipmentService.lookup.mockRejectedValueOnce(new Error('Mất mạng'))
    await wrapper.find('form').trigger('submit'); await flush()
    expect(wrapper.text()).toContain('Mất mạng')
    expect(wrapper.find('input').element.value).toBe('HTT261123ABCDE')
    shipmentService.lookup.mockResolvedValue(RESULT)
    await wrapper.find('[role="alert"] button').trigger('click'); await flush()
    expect(wrapper.find('#lookup-result-title').text()).toBe(RESULT.tracking_code)
  })

  it('response cũ không đè kết quả mã mới, kể cả khi lỗi đến muộn', async () => {
    let rejectOld
    shipmentService.lookup.mockReturnValueOnce(new Promise((_, reject) => { rejectOld = reject }))
    const { wrapper, router } = await setup('/tracking?code=OLD')
    shipmentService.lookup.mockResolvedValue(RESULT)
    await router.push('/tracking?code=NEW'); await flush()
    rejectOld(new Error('Lỗi cũ')); await flush()
    expect(wrapper.text()).not.toContain('Lỗi cũ')
    expect(wrapper.find('#lookup-result-title').text()).toBe(RESULT.tracking_code)
  })
})
