<script setup>
// Khối nền dùng chung Shop/NV; Phase 4 gắn vào màn chi tiết. active=false dừng toàn bộ polling/map.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import 'leaflet/dist/leaflet.css'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { ROLES } from '../../router/roles'
import * as trackingService from '../../services/trackingService'
import { formatDateTime } from '../../utils/format'
import { locationLimits, validCoordinates } from '../../utils/location'
import { MAP_INITIAL_ZOOM, MAP_MAX_ZOOM, MAP_TILE_ATTRIBUTION, MAP_TILE_URL } from '../../config'

const props = defineProps({ shipmentId: { type: [Number, String], required: true }, active: { type: Boolean, default: true },
  onlyWhenOpen: { type: Boolean, default: false } })
const emit = defineEmits(['ended'])
const auth = useAuthStore()
const meta = useMetaStore()
const host = ref(null)
const location = ref(null)
const task = ref(null)
const loading = ref(false)
const error = ref('')
const mapError = ref('')
const ended = ref(false)
const clock = ref(Date.now())
const visible = ref(document.visibilityState !== 'hidden')
const stale = computed(() => location.value && (location.value.stale ||
  (clock.value - Date.parse(location.value.recorded_at)) / 1000 > (locationLimits(meta.limits)?.stale ?? 0)))
const allowed = computed(() => auth.isAuthenticated && [ROLES.SHOP, ROLES.ADMIN].includes(auth.role) && !auth.mustChangePassword)
let session = null
let map = null
let marker = null
let resizeObserver = null
let renderVersion = 0

function destroyMap() {
  renderVersion++
  resizeObserver?.disconnect()
  resizeObserver = null
  map?.remove()
  map = marker = null
}

async function renderMap(run) {
  const version = ++renderVersion
  try {
    await nextTick()
    const L = await import('leaflet')
    if (session !== run || version !== renderVersion || !location.value || !host.value) return
    if (!MAP_TILE_URL || !MAP_TILE_ATTRIBUTION) throw new Error('Chưa cấu hình nguồn và ghi công bản đồ.')
    const coordinates = [location.value.lat, location.value.lng]
    if (!map) {
      map = L.map(host.value, { scrollWheelZoom: false }).setView(coordinates, MAP_INITIAL_ZOOM)
      const instance = map
      L.tileLayer(MAP_TILE_URL, { maxZoom: MAP_MAX_ZOOM, attribution: MAP_TILE_ATTRIBUTION,
        referrerPolicy: 'strict-origin-when-cross-origin',
        // Không tải bù vùng ngoài màn hình; không prefetch/offline tiles.
        keepBuffer: 0,
      }).on('tileerror', () => {
        if (session === run && map === instance) mapError.value = 'Chưa tải được nền bản đồ. Tọa độ và thời điểm vẫn được giữ.'
      }).addTo(map)
      const color = getComputedStyle(host.value).getPropertyValue('--brand').trim() || 'currentColor'
      marker = L.circleMarker(coordinates, { radius: 7, color, fillColor: color, fillOpacity: 0.8 }).addTo(map)
      if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(() => { if (map === instance) instance.invalidateSize() })
        resizeObserver.observe(host.value)
      }
    } else {
      marker.setLatLng(coordinates)
      map.panTo(coordinates, { animate: false })
    }
  } catch (cause) {
    if (session === run && version === renderVersion) mapError.value = cause?.message || 'Chưa tải được bản đồ.'
  }
}

function cancel() {
  const run = session
  session = null
  if (run) { run.controller.abort(); clearTimeout(run.timer); clearInterval(run.clockTimer) }
  destroyMap()
}

function schedule(run) {
  if (session !== run || ended.value) return
  run.timer = setTimeout(() => { void load(run) }, run.limits.poll * 1000)
}

async function load(run) {
  if (session !== run) return
  clock.value = Date.now()
  try {
    const data = await trackingService.getLocation(run.shipmentId, { signal: run.controller.signal })
    if (session !== run) return
    if (!data.task) {
      task.value = location.value = null
      ended.value = true
      clearInterval(run.clockTimer)
      error.value = ''
      destroyMap()
      emit('ended')
      return
    }
    if (task.value?.id !== data.task.id) {
      destroyMap()
      location.value = null
      mapError.value = ''
    }
    task.value = data.task
    if (data.location && (!validCoordinates(data.location.lat, data.location.lng) ||
        !Number.isFinite(Date.parse(data.location.recorded_at)))) throw new Error('Dữ liệu vị trí chưa hợp lệ.')
    location.value = data.location
    error.value = ''
    if (location.value) void renderMap(run)
    else { destroyMap(); mapError.value = '' }
  } catch (cause) {
    if (session !== run || cause?.name === 'AbortError') return
    error.value = cause?.message || 'Chưa thể tải vị trí.'
    if ([401, 403, 404].includes(cause?.status)) {
      task.value = location.value = null
      ended.value = true
      clearInterval(run.clockTimer)
      destroyMap()
    }
  } finally {
    if (session === run) { loading.value = false; clock.value = Date.now(); schedule(run) }
  }
}

async function restart() {
  cancel()
  task.value = location.value = null
  error.value = mapError.value = ''
  ended.value = false
  loading.value = false
  if (!props.active || !props.shipmentId || !visible.value || !allowed.value) return
  const run = { shipmentId: props.shipmentId, controller: new AbortController(), timer: null, clockTimer: null, limits: null }
  session = run
  loading.value = true
  try {
    await meta.load()
    if (session !== run) return
    run.limits = locationLimits(meta.limits)
    if (!run.limits) throw new Error('Chưa tải được giới hạn GPS. Vui lòng thử lại.')
    run.clockTimer = setInterval(() => { clock.value = Date.now() }, run.limits.poll * 1000)
    await load(run)
  } catch (cause) {
    if (session === run) { error.value = cause?.message || 'Chưa thể tải vị trí.'; loading.value = false }
  }
}

function retryMap() {
  destroyMap()
  mapError.value = ''
  if (session && location.value) void renderMap(session)
}
function visibilityChanged() { visible.value = document.visibilityState !== 'hidden' }
document.addEventListener('visibilitychange', visibilityChanged)
watch(() => [props.shipmentId, props.active, visible.value, auth.user?.id, auth.role, auth.isAuthenticated, auth.mustChangePassword],
  () => { void restart() }, { immediate: true, flush: 'sync' })
onBeforeUnmount(() => { cancel(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<template>
  <section v-show="!onlyWhenOpen || task || error" class="live-map" aria-label="Theo dõi vị trí Shipper">
    <slot />
    <p v-if="!active || !visible || !allowed" class="muted">Theo dõi vị trí đang tạm dừng.</p>
    <p v-else-if="loading" class="loading" role="status">Đang tải vị trí…</p>
    <div v-if="error" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ error }}<template v-if="location"> Vị trí bên dưới là dữ liệu lần trước.</template></p>
      <button type="button" class="btn btn--ghost btn--sm" @click="restart">Thử lại</button>
    </div>
    <p v-else-if="ended" class="alert alert--info" role="status">Không còn nhiệm vụ mở để theo dõi vị trí.</p>
    <p v-else-if="!loading && task && !location" class="muted" role="status">Chưa có vị trí được chia sẻ.</p>
    <template v-if="location">
      <p :class="stale ? 'alert alert--warning' : 'muted'" role="status">
        {{ stale ? 'Vị trí đã cũ — không phải vị trí hiện tại.' : (error ? 'Điểm được ghi nhận gần nhất.' : 'Đang cập nhật vị trí.') }}
      </p>
      <p class="muted">Thời điểm đo: {{ formatDateTime(location.recorded_at) }} · Nhận lúc: {{ formatDateTime(location.received_at) }}</p>
      <p class="muted">Tọa độ: {{ location.lat }}, {{ location.lng }}<template v-if="location.accuracy != null"> · Sai số: {{ location.accuracy }} m</template></p>
    </template>
    <div v-show="location" ref="host" class="live-map__canvas" role="region" aria-label="Bản đồ vị trí được chia sẻ" />
    <div v-if="mapError && location" class="alert alert--warning" role="alert">
      <p class="alert__text">{{ mapError }}</p>
      <button type="button" class="btn btn--ghost btn--sm" @click="retryMap">Tải lại bản đồ</button>
    </div>
    <!-- Attribution là cấu hình build tin cậy, không lấy từ dữ liệu người dùng/API. -->
    <p v-if="location && MAP_TILE_ATTRIBUTION" class="live-map__source" v-html="MAP_TILE_ATTRIBUTION" />
  </section>
</template>

<style scoped>
.live-map { display: grid; gap: 12px; min-width: 0; }
.live-map p { margin: 0; }
.live-map__canvas { height: clamp(260px, 40vh, 360px); width: 100%; min-width: 0; border-radius: var(--radius); isolation: isolate; z-index: 0; }
.live-map__source { font-size: 0.75rem; color: var(--muted); }
.live-map__source :deep(a) { color: var(--brand); }
</style>
