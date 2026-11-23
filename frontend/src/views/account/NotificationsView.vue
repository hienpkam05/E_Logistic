<script setup>
// Thông báo nội bộ: danh sách, lọc chưa đọc, đánh dấu đã đọc (checklist mục 3).
// Bộ lọc và trang nằm trên URL (?unread=true&page=2) để Back/tải lại giữ nguyên chỗ đang xem.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import PaginationBar from '../../components/common/PaginationBar.vue'
import { notificationLinkFor } from '../../router/roles'
import { useAuthStore } from '../../stores/auth'
import * as notificationService from '../../services/notificationService'
import { useMetaStore } from '../../stores/meta'
import { useNotificationStore } from '../../stores/notifications'
import { formatDateTime } from '../../utils/format'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()
const store = useNotificationStore()
const auth = useAuthStore()

// Thông báo gắn vận đơn / nhiệm vụ → liên kết tới đúng màn của vai trò đang xem (spec 005 D6, 006 D8).
const shipmentLink = (item) => notificationLinkFor(auth.role, item.payload)

const items = ref([])
const total = ref(0)
const hasNext = ref(false)
const hasPrevious = ref(false)
const loading = ref(false)
const loadError = ref('')
const actionError = ref('')
const markingAll = ref(false)

const unreadOnly = computed(() => route.query.unread === 'true')
const page = computed(() => Math.max(1, Number.parseInt(route.query.page, 10) || 1))
const emptyText = computed(() => (unreadOnly.value ? 'Không có thông báo chưa đọc.' : 'Chưa có thông báo nào.'))

let requestId = 0
async function load() {
  const current = ++requestId // bỏ kết quả cũ nếu người dùng đổi bộ lọc/trang liên tục
  loading.value = true
  loadError.value = ''
  try {
    const data = await notificationService.list({ unread: unreadOnly.value || undefined, page: page.value })
    if (current !== requestId) return
    items.value = data.results
    total.value = data.count
    hasNext.value = Boolean(data.next)
    hasPrevious.value = Boolean(data.previous)
  } catch (err) {
    if (current !== requestId) return
    items.value = []
    loadError.value = err?.message || 'Chưa thể tải thông báo.'
  } finally {
    if (current === requestId) loading.value = false
  }
}

function go(query) {
  router.push({ name: 'notifications', query })
}

function setFilter(unread) {
  go(unread ? { unread: 'true' } : {})
}

function goPage(next) {
  go({ ...route.query, page: next > 1 ? String(next) : undefined })
}

async function open(item) {
  if (item.is_read) return
  actionError.value = ''
  try {
    const updated = await store.markRead(item)
    Object.assign(item, updated)
    if (unreadOnly.value) items.value = items.value.filter((n) => n.id !== item.id)
  } catch (err) {
    actionError.value = err?.message || 'Chưa đánh dấu được thông báo.'
  }
}

async function markAll() {
  markingAll.value = true
  actionError.value = ''
  try {
    await store.markAllRead()
    await load()
  } catch (err) {
    actionError.value = err?.message || 'Chưa đánh dấu được thông báo.'
  } finally {
    markingAll.value = false
  }
}

watch(() => [route.query.unread, route.query.page], () => {
  load()
  store.refreshCount()
}, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="notifications-title">
    <div class="page__header">
      <h1 id="notifications-title">Thông báo</h1>
      <button type="button" class="btn btn--ghost" :disabled="markingAll || store.unreadCount === 0" @click="markAll">
        {{ markingAll ? 'Đang cập nhật…' : 'Đánh dấu tất cả đã đọc' }}
      </button>
    </div>

    <div class="tabs" role="group" aria-label="Lọc thông báo">
      <button type="button" class="tabs__item" :aria-pressed="!unreadOnly" @click="setFilter(false)">Tất cả</button>
      <button type="button" class="tabs__item" :aria-pressed="unreadOnly" @click="setFilter(true)">
        Chưa đọc<span v-if="store.unreadCount"> ({{ store.unreadCount }})</span>
      </button>
    </div>

    <p v-if="actionError" class="alert alert--danger" role="alert">{{ actionError }}</p>

    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải thông báo…</p>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost" @click="load">Tải lại</button>
    </div>

    <p v-else-if="!items.length" class="card muted">{{ emptyText }}</p>

    <template v-else>
      <ul class="notification-list">
        <li v-for="item in items" :key="item.id">
          <button type="button" class="notification" :class="{ 'notification--unread': !item.is_read }"
                  :aria-label="item.is_read ? undefined : `${item.title} (chưa đọc, bấm để đánh dấu đã đọc)`"
                  @click="open(item)">
            <span class="notification__meta">
              <span>{{ meta.label('notification_kinds', item.kind) }}</span>
              <time :datetime="item.created_at">{{ formatDateTime(item.created_at) }}</time>
            </span>
            <strong class="notification__title">{{ item.title }}</strong>
            <span v-if="item.body" class="notification__body">{{ item.body }}</span>
          </button>
          <RouterLink v-if="shipmentLink(item)" :to="shipmentLink(item)" class="notification__link"
                      @click="open(item)">Xem vận đơn →</RouterLink>
        </li>
      </ul>

      <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total" unit="thông báo"
                     @change="goPage" />
    </template>
  </section>
</template>

<style scoped>
.notification-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.notification {
  width: 100%; text-align: left; font: inherit; color: inherit; cursor: pointer;
  display: flex; flex-direction: column; gap: 4px; padding: 14px 16px;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
}
.notification--unread { border-left: 4px solid var(--brand); background: var(--brand-softer); }
.notification:not(.notification--unread) { cursor: default; }
.notification:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.notification__meta { display: flex; justify-content: space-between; gap: 12px; font-size: .8125rem; color: var(--muted); }
.notification__body { color: var(--muted); }
.notification-list > li { display: flex; flex-direction: column; gap: 4px; }
.notification__link { align-self: flex-end; font-size: .875rem; font-weight: 600; }
</style>
