import { describe, expect, it, vi } from 'vitest'

// Router THẬT (src/router/index.js), không phải bộ route giả trong views/__tests__/helpers.js.
// Bắt lỗi khai báo route như ':id(\d+)' trong chuỗi JS (mất dấu \ → chỉ khớp chữ "d") — lỗi đã gặp ở spec 005.
vi.mock('../../stores/auth', () => ({ useAuthStore: () => ({ restore: async () => {} }) }))

const { default: router } = await import('../index')

describe('router thật: đường dẫn chi tiết theo id', () => {
  it.each([
    ['/shop/shipments/12', 'shop-shipment-detail'],
    ['/staff/shipments/12', 'staff-shipment-detail'],
    ['/staff/accounts/12', 'staff-account-detail'],
    ['/shipper/tasks/12', 'shipper-task-detail'],
  ])('%s → %s, id là số', (path, name) => {
    const resolved = router.resolve(path)
    expect(resolved.name).toBe(name)
    expect(resolved.params.id).toBe('12')
  })

  it.each(['/shop/shipments/abc', '/staff/shipments/d', '/staff/accounts/x1', '/shipper/tasks/d'])('%s (id không phải số) → 404', (path) => {
    expect(router.resolve(path).name).toBe('not-found')
  })

  it('đường dẫn tĩnh không bị nuốt bởi route :id', () => {
    expect(router.resolve('/shop/shipments/new').name).toBe('shop-shipment-new')
    expect(router.resolve('/staff/accounts/new').name).toBe('staff-account-new')
    expect(router.resolve('/shipper/tasks').name).toBe('shipper-tasks')
  })
})

describe('notificationLinkFor: liên kết "Xem" theo vai trò', async () => {
  const { notificationLinkFor } = await import('../roles')

  it('Shop / Nhân viên mở vận đơn; Shipper mở nhiệm vụ', () => {
    const payload = { shipment_id: 12, task_id: 31 }
    expect(notificationLinkFor('SHOP', payload)).toEqual({ name: 'shop-shipment-detail', params: { id: '12' } })
    expect(notificationLinkFor('ADMIN', payload)).toEqual({ name: 'staff-shipment-detail', params: { id: '12' } })
    expect(notificationLinkFor('SHIPPER', payload)).toEqual({ name: 'shipper-task-detail', params: { id: '31' } })
  })

  it('thiếu id tương ứng → không có liên kết', () => {
    expect(notificationLinkFor('SHIPPER', { shipment_id: 12 })).toBeNull() // Shipper không có màn vận đơn
    expect(notificationLinkFor('SHOP', { task_id: 31 })).toBeNull()
    expect(notificationLinkFor('ADMIN', {})).toBeNull()
    expect(notificationLinkFor('SHOP', undefined)).toBeNull()
  })
})

