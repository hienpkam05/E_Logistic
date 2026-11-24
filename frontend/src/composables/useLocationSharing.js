// Chỉ thu thập sau start(). Không giữ hàng đợi offline, không gửi lại mẫu GPS như điểm mới.
import { onScopeDispose, ref, toValue, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useMetaStore } from '../stores/meta'
import { ROLES } from '../router/roles'
import * as taskService from '../services/taskService'
import * as trackingService from '../services/trackingService'
import {
  GEO_PERMISSION_DENIED, LOCATION_SHARING_STATE as S, LOCATION_STOP_HTTP_STATUSES,
  OPEN_LOCATION_TASK_STATUSES, locationLimits, validCoordinates,
} from '../utils/location'

export function useLocationSharing(taskId, { taskStatus, onTask } = {}) {
  const auth = useAuthStore()
  const meta = useMetaStore()
  const enabled = ref(false)
  const state = ref(S.IDLE)
  const message = ref('')
  const lastRecordedAt = ref(null)
  let session = null

  function stop(nextState = S.STOPPED, text = '') {
    const run = session
    session = null
    enabled.value = false
    state.value = nextState
    message.value = text
    if (!run) return
    run.controller.abort()
    if (run.watchId !== null) navigator.geolocation?.clearWatch(run.watchId)
    clearInterval(run.timer)
    run.permission?.removeEventListener('change', run.permissionChanged)
    if (run.offline) window.removeEventListener('offline', run.offline)
  }

  function reportApiError(run, error) {
    if (session !== run || error?.name === 'AbortError') return
    if (LOCATION_STOP_HTTP_STATUSES.has(error?.status)) {
      stop(S.STOPPED, error?.message || 'Nhiệm vụ hoặc phiên đăng nhập không còn cho phép chia sẻ.')
    } else {
      state.value = error?.status === 0 ? S.NETWORK_ERROR : S.ERROR
      message.value = error?.message || 'Chưa thể cập nhật vị trí.'
    }
  }

  async function refreshTask(run) {
    if (run.checking || session !== run) return
    run.checking = true
    try {
      const task = await taskService.get(run.taskId, { signal: run.controller.signal })
      if (session === run) onTask?.(task)
      if (session === run && !OPEN_LOCATION_TASK_STATUSES.has(task.status)) {
        stop(S.STOPPED, 'Nhiệm vụ đã kết thúc. Đã dừng chia sẻ vị trí.')
      }
    } catch (error) {
      reportApiError(run, error)
    } finally {
      run.checking = false
    }
  }

  async function position(run, fix) {
    if (session !== run) return
    const now = Date.now()
    const { latitude: lat, longitude: lng, accuracy } = fix.coords || {}
    const age = (now - fix.timestamp) / 1000
    if (!validCoordinates(lat, lng) || !Number.isFinite(fix.timestamp) || age > run.limits.maxAge ||
        age < -run.limits.maxFuture || (accuracy != null && (!Number.isFinite(accuracy) || accuracy < 0 || accuracy > run.limits.maxAccuracy))) {
      state.value = S.UNAVAILABLE
      message.value = 'Chưa có điểm GPS mới với độ chính xác phù hợp.'
      return
    }
    if (fix.timestamp <= run.lastTimestamp) return
    run.lastTimestamp = fix.timestamp
    run.lastFixAt = fix.timestamp
    if (navigator.onLine === false) {
      run.offline()
      return
    }
    // Bỏ mẫu trong lúc bận/quá dày; chỉ callback mới mới có thể gửi tiếp.
    if (run.sending || now - run.lastAttempt < run.limits.minInterval * 1000) return
    run.sending = true
    run.lastAttempt = now
    const recordedAt = new Date(fix.timestamp).toISOString()
    try {
      const result = await trackingService.sendLocation(run.taskId,
        { lat, lng, accuracy: accuracy ?? null, recorded_at: recordedAt }, { signal: run.controller.signal })
      if (session !== run) return
      if (result.stored) lastRecordedAt.value = recordedAt
      state.value = S.SHARING
      message.value = ''
    } catch (error) {
      reportApiError(run, error)
    } finally {
      run.sending = false
    }
  }

  async function start() {
    if (session) return
    if (!auth.isAuthenticated || auth.role !== ROLES.SHIPPER || auth.mustChangePassword || !toValue(taskId)) {
      stop(S.STOPPED, 'Chỉ Shipper phụ trách nhiệm vụ mở mới được chia sẻ vị trí.')
      return
    }
    if (taskStatus && !OPEN_LOCATION_TASK_STATUSES.has(toValue(taskStatus))) {
      stop(S.STOPPED, 'Nhiệm vụ đã kết thúc.')
      return
    }
    if (!navigator.geolocation || window.isSecureContext === false) {
      stop(S.UNSUPPORTED, 'Cần trình duyệt hỗ trợ vị trí trên HTTPS hoặc localhost.')
      return
    }
    const run = { taskId: toValue(taskId), controller: new AbortController(), watchId: null, timer: null,
      checking: false, sending: false, lastAttempt: -Infinity, lastTimestamp: -Infinity, lastFixAt: Date.now() }
    session = run
    enabled.value = true
    state.value = S.STARTING
    message.value = ''
    lastRecordedAt.value = null
    try {
      await meta.load()
      if (session !== run) return
      run.limits = locationLimits(meta.limits)
      if (!run.limits) throw new Error('Chưa tải được giới hạn GPS. Vui lòng thử lại.')
      // Xác minh nhiệm vụ trước khi yêu cầu trình duyệt thu thập vị trí.
      const task = await taskService.get(run.taskId, { signal: run.controller.signal })
      if (session !== run) return
      onTask?.(task)
      if (session !== run) return
      if (!OPEN_LOCATION_TASK_STATUSES.has(task.status)) {
        stop(S.STOPPED, 'Nhiệm vụ đã kết thúc.')
        return
      }
      run.permissionChanged = () => {
        if (session === run && run.permission.state === 'denied') stop(S.DENIED, 'Chưa cấp quyền vị trí. Đã dừng thu thập GPS.')
      }
      try {
        const permission = await navigator.permissions?.query({ name: 'geolocation' })
        if (session !== run) return
        run.permission = permission
        permission?.addEventListener('change', run.permissionChanged)
        if (permission?.state === 'denied') { run.permissionChanged(); return }
      } catch { /* Browser có thể không hỗ trợ Permissions API; callback geolocation vẫn kiểm quyền. */ }
      if (session !== run) return
      run.offline = () => {
        if (session !== run) return
        state.value = S.NETWORK_ERROR
        message.value = 'Mất mạng. Chỉ gửi điểm GPS mới khi kết nối lại.'
      }
      window.addEventListener('offline', run.offline)
      state.value = S.WAITING
      const watchId = navigator.geolocation.watchPosition((fix) => { void position(run, fix) }, (error) => {
        if (session !== run) return
        if (error.code === GEO_PERMISSION_DENIED) stop(S.DENIED, 'Chưa cấp quyền vị trí. Đã dừng thu thập GPS.')
        else { state.value = S.UNAVAILABLE; message.value = 'Mất tín hiệu GPS. Đang chờ điểm đo mới.' }
      }, { enableHighAccuracy: true, maximumAge: 0, timeout: run.limits.maxAge * 1000 })
      if (session !== run) { navigator.geolocation.clearWatch(watchId); return }
      run.watchId = watchId
      run.timer = setInterval(() => {
        void refreshTask(run)
        if (session === run && (Date.now() - run.lastFixAt) / 1000 > run.limits.maxAge && navigator.onLine !== false) {
          state.value = S.UNAVAILABLE
          message.value = 'Chưa nhận được điểm GPS mới. Không gửi lại vị trí cũ.'
        }
      }, run.limits.poll * 1000)
    } catch (error) {
      if (session === run) stop(error?.status === 0 ? S.NETWORK_ERROR : S.ERROR, error?.message || 'Chưa thể bật chia sẻ vị trí.')
    }
  }

  const unsubscribe = auth.$onAction(({ name }) => { if (name === 'logout') stop() })
  watch(() => [toValue(taskId), auth.user?.id, auth.role, auth.isAuthenticated, auth.mustChangePassword], () => {
    stop(S.IDLE)
    lastRecordedAt.value = null
  }, { flush: 'sync' })
  if (taskStatus) watch(() => toValue(taskStatus), (value) => {
    if (!OPEN_LOCATION_TASK_STATUSES.has(value)) stop(S.STOPPED, 'Nhiệm vụ đã kết thúc.')
  }, { flush: 'sync' })
  onScopeDispose(() => { stop(); unsubscribe() })
  return { enabled, state, message, lastRecordedAt, start, stop }
}
