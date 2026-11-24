<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import FormField from '../../components/common/FormField.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import { ROLES, shipmentRouteFor } from '../../router/roles'
import * as shipmentService from '../../services/shipmentService'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime } from '../../utils/format'
import { fieldErrors } from '../../utils/formErrors'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const code = ref('')
const shipment = ref(null)
const loading = ref(false)
const error = ref('')
const codeError = ref('')
const notFound = ref(false)
let requestId = 0
const detail = computed(() => shipmentRouteFor(auth.role, shipment.value?.id))
const history = computed(() => detail.value ? { ...detail.value, hash: '#shipment-history' } : null)
const isStaff = computed(() => auth.role === ROLES.ADMIN)

async function search(value) {
  const current = ++requestId
  shipment.value = null
  error.value = ''
  codeError.value = ''
  notFound.value = false
  loading.value = true
  try {
    const result = await shipmentService.lookup(value)
    if (current === requestId) shipment.value = result
  } catch (err) {
    if (current !== requestId) return
    if (err?.status === 404) notFound.value = true
    else {
      codeError.value = fieldErrors(err).code || ''
      error.value = codeError.value ? '' : err?.message || 'Chưa thể tra cứu vận đơn. Vui lòng thử lại.'
    }
  } finally {
    if (current === requestId) loading.value = false
  }
}

async function submit() {
  const normalized = code.value.trim().toUpperCase()
  if (!normalized) {
    requestId++; loading.value = false; shipment.value = null; notFound.value = false; error.value = ''
    codeError.value = 'Vui lòng nhập mã yêu cầu hoặc mã vận đơn.'; return
  }
  if (meta.limits.search_query_max_length && normalized.length > meta.limits.search_query_max_length) {
    requestId++; loading.value = false; shipment.value = null; notFound.value = false; error.value = ''
    codeError.value = `Mã tối đa ${meta.limits.search_query_max_length} ký tự.`
    return
  }
  code.value = normalized
  if (route.query.code === normalized) await search(normalized)
  else await router.push({ name: 'tracking', query: { code: normalized } })
}

watch(() => route.query.code, (value) => {
  const text = typeof value === 'string' ? value : ''
  code.value = text
  if (text.trim()) search(text)
  else {
    requestId++
    loading.value = false
    shipment.value = null
    error.value = ''
    codeError.value = ''
    notFound.value = false
  }
}, { immediate: true })
onBeforeUnmount(() => { requestId++ })
</script>

<template>
  <section class="page page--narrow" aria-labelledby="tracking-title">
    <header class="page__header">
      <h1 id="tracking-title">Tra cứu vận đơn</h1>
      <p class="page__subtitle">Nhập đúng mã vận đơn hoặc mã yêu cầu để xem trạng thái và lịch sử.</p>
    </header>
    <form class="card form" novalidate @submit.prevent="submit">
      <FormField v-model="code" label="Mã vận đơn hoặc mã yêu cầu" required :error="codeError"
                 :maxlength="meta.limits.search_query_max_length" hint="Ví dụ: HTT… hoặc YC…" />
      <div class="form__actions">
        <button class="btn btn--primary" type="submit" :disabled="loading">
          <AppIcon name="search" :size="16" />{{ loading ? 'Đang tra cứu…' : 'Tra cứu' }}
        </button>
      </div>
    </form>
    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tra cứu vận đơn…</p>
    <div v-else-if="error" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ error }}</p>
      <button type="button" class="btn btn--ghost btn--sm" @click="submit">Thử lại</button>
    </div>
    <div v-else-if="notFound" class="card empty-state" role="status">
      <h2 class="empty-state__title">Không tìm thấy vận đơn phù hợp</h2>
      <p>Kiểm tra mã và tra cứu lại trong phạm vi được xem.</p>
    </div>
    <article v-else-if="shipment" class="card" aria-labelledby="lookup-result-title">
      <div class="title-row">
        <h2 id="lookup-result-title">{{ shipment.tracking_code || shipment.request_code }}</h2>
        <StatusBadge :value="shipment.status" />
      </div>
      <dl class="details">
        <dt>Mã yêu cầu</dt><dd>{{ shipment.request_code }}</dd>
        <template v-if="isStaff"><dt>Shop</dt><dd>{{ shipment.shop?.full_name }}</dd></template>
        <dt>Người nhận</dt><dd>{{ shipment.receiver_name }}</dd>
        <dt>Ngày tạo</dt><dd>{{ formatDateTime(shipment.created_at) }}</dd>
        <dt>Cập nhật gần nhất</dt><dd>{{ formatDateTime(shipment.updated_at) }}</dd>
      </dl>
      <div class="form__actions">
        <RouterLink v-if="detail" :to="detail" class="btn btn--primary">Xem chi tiết</RouterLink>
        <RouterLink v-if="history" :to="history" class="btn btn--outline">Lịch sử vận chuyển</RouterLink>
      </div>
    </article>
    <p v-else-if="!codeError" class="muted">Kết quả tra cứu sẽ hiển thị tại đây.</p>
  </section>
</template>
