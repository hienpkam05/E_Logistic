import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  DELIVERY_FAIL_REASON, FAIL_REASON_GROUP, HOLDER_TYPE, PICKUP_FAIL_REASON, SHIPMENT_ACTION, SHIPMENT_ORDERING, TASK_TYPE, can,
} from '../shipmentActions'

// Mã hành động frontend dùng phải tồn tại trong ShipmentAction của backend (đọc thẳng constants.py).
const source = readFileSync(resolve(process.cwd(), '..', 'backend', 'apps', 'shipments', 'constants.py'), 'utf8')
const block = source.split('class ShipmentAction(models.TextChoices):')[1].split(/\n\S/)[0]
const backendCodes = [...block.matchAll(/^\s+([A-Z_]+) = "([A-Z_]+)"/gm)].map((m) => m[2])

describe('shipmentActions', () => {
  it('mọi mã có trong ShipmentAction backend, key = value', () => {
    expect(backendCodes.length).toBeGreaterThan(5)
    for (const [key, value] of Object.entries(SHIPMENT_ACTION)) {
      expect(key).toBe(value)
      expect(backendCodes).toContain(value)
    }
  })

  it('can() theo allowed_actions; thiếu dữ liệu → false', () => {
    const s = { allowed_actions: [SHIPMENT_ACTION.CANCEL_REQUEST] }
    expect(can(s, SHIPMENT_ACTION.CANCEL_REQUEST)).toBe(true)
    expect(can(s, SHIPMENT_ACTION.UPDATE_REQUEST)).toBe(false)
    expect(can(null, SHIPMENT_ACTION.UPDATE_REQUEST)).toBe(false)
    expect(can({}, SHIPMENT_ACTION.UPDATE_REQUEST)).toBe(false)
  })

  it('HOLDER_TYPE có trong HolderType của backend (key = value)', () => {
    const holderBlock = source.split('class HolderType(models.TextChoices):')[1].split(/\n\S/)[0]
    const codes = [...holderBlock.matchAll(/^\s+([A-Z_]+) = "([A-Z_]+)"/gm)].map((m) => m[2])
    expect(codes.length).toBe(4)
    for (const [key, value] of Object.entries(HOLDER_TYPE)) {
      expect(key).toBe(value)
      expect(codes).toContain(value)
    }
  })

  it('SHIPMENT_ORDERING đúng bằng các khóa SHIPMENT_LIST_ORDERINGS của backend', () => {
    const orderBlock = source.split('SHIPMENT_LIST_ORDERINGS = {')[1].split('}')[0]
    const backendKeys = [...orderBlock.matchAll(/^\s+"(-?[a-z_]+)":/gm)].map((m) => m[1])
    expect(backendKeys.length).toBe(2)
    expect(Object.values(SHIPMENT_ORDERING).sort()).toEqual([...backendKeys].sort())
  })

  // Mã của dispatch/constants.py — đọc thẳng file backend.
  const dispatch = readFileSync(resolve(process.cwd(), '..', 'backend', 'apps', 'dispatch', 'constants.py'), 'utf8')
  const codesOf = (className) => {
    const enumBlock = dispatch.split(`class ${className}(models.TextChoices):`)[1].split(/\n\S/)[0]
    return [...enumBlock.matchAll(/^\s+([A-Z_]+) = "([A-Z_]+)"/gm)].map((m) => m[2])
  }

  it('FAIL_REASON_GROUP khớp FAIL_REASONS_BY_TASK_TYPE (dispatch) + tên nhóm ở /meta/choices/ (core/choices.py)', () => {
    const mapBlock = dispatch.split('FAIL_REASONS_BY_TASK_TYPE = {')[1].split('}')[0]
    const typeToEnum = Object.fromEntries([...mapBlock.matchAll(/TaskType\.([A-Z_]+): (\w+)/g)].map((m) => [m[1], m[2]]))
    const choices = readFileSync(resolve(process.cwd(), '..', 'backend', 'apps', 'core', 'choices.py'), 'utf8')
    expect(Object.keys(FAIL_REASON_GROUP).sort()).toEqual(Object.keys(typeToEnum).sort())
    for (const [type, group] of Object.entries(FAIL_REASON_GROUP)) {
      expect(choices).toContain(`"${group}": (${typeToEnum[type]}, None)`)
    }
  })

  it.each([
    ['PICKUP_FAIL_REASON', 'PickupFailReason', PICKUP_FAIL_REASON, 6],
    ['DELIVERY_FAIL_REASON', 'DeliveryFailReason', DELIVERY_FAIL_REASON, 6],
    ['TASK_TYPE', 'TaskType', TASK_TYPE, 3],
  ])('%s có trong %s của backend (key = value)', (_name, className, constant, count) => {
    const codes = codesOf(className)
    expect(codes.length).toBe(count)
    for (const [key, value] of Object.entries(constant)) {
      expect(key).toBe(value)
      expect(codes).toContain(value)
    }
  })
})

