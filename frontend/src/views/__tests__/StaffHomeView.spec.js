import { afterEach, describe, expect, it, vi } from 'vitest'
import * as shipmentService from '../../services/shipmentService'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { CHOICES } from '../../test-utils'
import StaffHomeView from '../staff/StaffHomeView.vue'
import { flush, mountView } from './helpers'
import { page } from './shipmentFixtures'

vi.mock('../../services/shipmentService', () => ({ list: vi.fn() }))

const ADMIN = { id: 1, username: 'nv_a', full_name: 'Nhân viên A', role: 'ADMIN', must_change_password: false }

async function setup() {
  const result = await mountView(StaffHomeView, {
    path: '/staff',
    beforeMount: () => {
      useMetaStore().choices = CHOICES
      useAuthStore().setUser(ADMIN)
    },
  })
  await flush()
  return result
}

afterEach(() => {
  document.body.innerHTML = ''
  shipmentService.list.mockReset()
})

describe('StaffHomeView', () => {
  it('ô "yêu cầu chờ duyệt" lấy count của danh sách Chờ xác nhận, bấm mở danh sách (D8)', async () => {
    shipmentService.list.mockResolvedValue(page([], { count: 7 }))
    const { wrapper } = await setup()
    expect(shipmentService.list).toHaveBeenCalledWith({ status: ['PENDING_APPROVAL'] })
    const tile = wrapper.find('.highlight')
    expect(tile.text()).toContain('7')
    expect(tile.text()).toContain('yêu cầu chờ duyệt')
    expect(tile.classes()).toContain('highlight--attention')
    expect(tile.attributes('href')).toBe('/staff/shipments')
    expect(wrapper.text()).toContain('Quản lý vận đơn') // menu chức năng có mục mới
  })

  it('không còn yêu cầu: "Đã xử lý hết", không tô cảnh báo', async () => {
    shipmentService.list.mockResolvedValue(page([], { count: 0 }))
    const { wrapper } = await setup()
    expect(wrapper.find('.highlight').text()).toContain('Đã xử lý hết')
    expect(wrapper.find('.highlight').classes()).not.toContain('highlight--attention')
  })

  it('lỗi tải số liệu: hiện "—", ô vẫn bấm được', async () => {
    shipmentService.list.mockRejectedValue(new Error('Mất mạng'))
    const { wrapper } = await setup()
    expect(wrapper.find('.highlight__value').text()).toBe('—')
    expect(wrapper.find('.highlight').attributes('href')).toBe('/staff/shipments')
  })
})
