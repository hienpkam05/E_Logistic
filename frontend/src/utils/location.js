import { TASK_STATUS } from './statusTones'
import { TASK_TYPE } from './shipmentActions'
import { MAP_DIRECTIONS_URL } from '../config'

export const LOCATION_SHARING_STATE = Object.freeze({
  IDLE: 'idle', STARTING: 'starting', WAITING: 'waiting', SHARING: 'sharing', STOPPED: 'stopped',
  DENIED: 'denied', UNAVAILABLE: 'unavailable', NETWORK_ERROR: 'network-error', ERROR: 'error', UNSUPPORTED: 'unsupported',
})
export const OPEN_LOCATION_TASK_STATUSES = new Set([TASK_STATUS.ACTIVE, TASK_STATUS.PENDING_SWAP_HANDOVER])
export const LOCATION_STOP_HTTP_STATUSES = new Set([401, 403, 404, 409])
export const GEO_PERMISSION_DENIED = 1 // GeolocationPositionError.PERMISSION_DENIED (Web API).

export const LOCATION_SHARING_LABEL = Object.freeze({
  idle: 'Chưa bật chia sẻ vị trí', starting: 'Đang kiểm tra nhiệm vụ và quyền vị trí…', waiting: 'Đang chờ điểm GPS…',
  sharing: 'Đang chia sẻ vị trí', stopped: 'Đã dừng chia sẻ vị trí', denied: 'Chưa cấp quyền vị trí',
  unavailable: 'Mất tín hiệu GPS', 'network-error': 'Mất kết nối mạng', error: 'Chưa thể cập nhật vị trí', unsupported: 'Chưa hỗ trợ vị trí',
})

export function taskDestination(task, hub) {
  if (!task || !OPEN_LOCATION_TASK_STATUSES.has(task.status)) return ''
  if (task.status === TASK_STATUS.PENDING_SWAP_HANDOVER || task.type === TASK_TYPE.RETURN) return hub?.address?.trim() || ''
  const shipment = task.shipment
  if (task.type === TASK_TYPE.PICKUP) return [shipment?.pickup_address, shipment?.pickup_ward?.name].filter(Boolean).join(', ')
  if (task.type === TASK_TYPE.DELIVERY) return [shipment?.delivery_address, shipment?.delivery_ward?.name].filter(Boolean).join(', ')
  return ''
}

export function directionsUrl(address) {
  if (!address?.trim()) return null
  const url = new URL(MAP_DIRECTIONS_URL)
  url.searchParams.set('api', '1')
  url.searchParams.set('destination', address.trim())
  return url.href
}

export function locationLimits(limits) {
  const result = {
    maxAge: limits.location_ping_max_age_seconds, maxFuture: limits.location_ping_max_future_seconds,
    minInterval: limits.location_ping_min_interval_seconds, maxAccuracy: limits.location_ping_max_accuracy_m,
    stale: limits.location_stale_seconds, poll: limits.location_poll_interval_seconds,
  }
  return Object.values(result).every((value) => Number.isFinite(value) && value > 0) ? result : null
}

export function validCoordinates(lat, lng) {
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180
}
