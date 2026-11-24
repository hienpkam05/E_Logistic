// GPS theo nhiệm vụ/đơn; session, CSRF và AbortSignal đi qua API client chung.
import { http } from './http'

export const sendLocation = (taskId, point, options = {}) =>
  http.post(`/dispatch/tasks/${encodeURIComponent(taskId)}/locations/`, point, options)
export const getLocation = (shipmentId, options = {}) =>
  http.get(`/shipments/${encodeURIComponent(shipmentId)}/location/`, options)
