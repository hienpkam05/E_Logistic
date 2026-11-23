<script setup>
// UC05.3 — danh sách vận đơn của Shop. Bộ lọc, từ khóa, trang nằm trên URL.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import PaginationBar from '../../components/common/PaginationBar.vue'
import StatusBadge from '../../components/common/StatusBadge.vue'
import { usePagedList } from '../../composables/usePagedList'
import * as shipmentService from '../../services/shipmentService'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatPhone, formatVnd } from '../../utils/format'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

// Trạng thái lạ trên URL được gửi nguyên cho backend kiểm tra (400 → báo lỗi + Bỏ lọc);
// không lọc bằng danh mục meta vì meta tải bất đồng bộ (bài học spec 003).
const status = computed(() => (typeof route.query.status === 'string' ? route.query.status : ''))
const q = computed(() => (typeof route.query.q === 'string' ? route.query.q : ''))
const page = computed(() => Math.max(1, Number.parseInt(route.query.page, 10) || 1))
const filtered = computed(() => Boolean(status.value || q.value))
const statusOptions = computed(() => meta.options('shipment_statuses'))

const searchText = ref(q.value)
const { items, total, hasNext, hasPrevious, loading, error: loadError, load } = usePagedList(() =>
  shipmentService.list({
    status: status.value ? [status.value] : undefined,
    q: q.value || undefined,
    page: page.value,
  }))

function setQuery(patch) {
  const next = { status: status.value, q: q.value, ...patch }
  router.push({ name: 'shop-shipments', query: Object.fromEntries(Object.entries(next).filter(([, v]) => v)) })
}

function goPage(next) {
  router.push({ name: 'shop-shipments', query: { ...route.query, page: next > 1 ? String(next) : undefined } })
}

function clearFilters() {
  searchText.value = ''
  router.push({ name: 'shop-shipments' })
}

watch(q, (value) => { searchText.value = value })
watch([status, q, page], load, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="shipments-title">
    <h1 id="shipments-title" class="sr-only">Vận đơn của tôi</h1>

    <div class="toolbar">
      <RouterLink :to="{ name: 'shop-shipment-new' }" class="btn btn--primary btn--split">
        <span class="btn__icon"><AppIcon name="plus" :size="20" /></span>
        <span class="btn__label">Tạo yêu cầu gửi hàng</span>
      </RouterLink>
      <span class="toolbar__spacer" />
      <form class="search" role="search" @submit.prevent="setQuery({ q: searchText.trim() })">
        <AppIcon name="search" :size="20" />
        <input v-model="searchText" type="search" :maxlength="meta.limits.search_query_max_length"
               aria-label="Từ khóa tìm kiếm" placeholder="Tìm mã yêu cầu, mã vận đơn, tên hoặc SĐT người nhận" />
      </form>
    </div>

    <div class="data-card">
      <div class="data-card__head">
        <div class="tabs" role="group" aria-label="Lọc nhanh">
          <button type="button" class="tabs__item" :aria-pressed="!status" @click="setQuery({ status: '' })">Tất cả</button>
        </div>
        <label class="filter-select">
          <AppIcon name="filter" :size="16" />
          <span class="sr-only">Lọc theo trạng thái</span>
          <select :value="status" @change="setQuery({ status: $event.target.value })">
            <option value="">Lọc theo trạng thái</option>
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </label>
        <span v-if="!loading && !loadError" class="data-card__count">{{ total }} vận đơn</span>
      </div>

      <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải danh sách…</p>

      <div v-else-if="loadError" class="empty-state" role="alert">
        <span class="empty-state__icon"><AppIcon name="alert" :size="26" /></span>
        <p class="empty-state__title">Chưa tải được danh sách</p>
        <p>{{ loadError }}</p>
        <div class="form__actions">
          <button type="button" class="btn btn--primary" @click="load"><AppIcon name="reload" :size="16" />Tải lại</button>
          <button v-if="filtered" type="button" class="btn btn--ghost" @click="clearFilters">Bỏ lọc</button>
        </div>
      </div>

      <div v-else-if="!items.length" class="empty-state">
        <span class="empty-state__icon"><AppIcon :name="filtered ? 'search' : 'inbox'" :size="26" /></span>
        <template v-if="filtered">
          <p class="empty-state__title">Không có vận đơn phù hợp với bộ lọc.</p>
          <p>Thử từ khóa khác hoặc bỏ bộ lọc trạng thái.</p>
          <button type="button" class="btn btn--ghost" @click="clearFilters">Bỏ lọc</button>
        </template>
        <template v-else>
          <p class="empty-state__title">Bạn chưa có yêu cầu gửi hàng nào.</p>
          <p>Tạo yêu cầu đầu tiên, Nhân viên sẽ duyệt và cấp mã vận đơn.</p>
          <RouterLink :to="{ name: 'shop-shipment-new' }" class="btn btn--primary">
            <AppIcon name="plus" :size="16" />Tạo yêu cầu đầu tiên
          </RouterLink>
        </template>
      </div>

      <template v-else>
        <div class="table-wrap">
          <table class="table table--stack">
            <thead>
              <tr>
                <th>Mã</th><th>Người nhận</th><th>Giao đến</th><th class="num">Thu hộ</th><th>Trạng thái</th>
                <th>Ngày tạo</th><th class="cell-actions">Xem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in items" :key="s.id">
                <td data-label="Mã">
                  <RouterLink :to="{ name: 'shop-shipment-detail', params: { id: s.id } }">{{ s.tracking_code || s.request_code }}</RouterLink>
                  <span v-if="!s.tracking_code" class="cell-sub">mã yêu cầu</span>
                </td>
                <td data-label="Người nhận">{{ s.receiver_name }}<span class="cell-sub">{{ formatPhone(s.receiver_phone) }}</span></td>
                <td data-label="Giao đến">{{ s.delivery_ward?.name }}</td>
                <td class="num" data-label="Thu hộ">{{ s.cod_amount ? formatVnd(s.cod_amount) : '—' }}</td>
                <td data-label="Trạng thái"><StatusBadge :value="s.status" /></td>
                <td data-label="Ngày tạo">{{ formatDateTime(s.created_at) }}</td>
                <td class="cell-actions" data-label="Xem">
                  <RouterLink :to="{ name: 'shop-shipment-detail', params: { id: s.id } }" class="row-action"
                              :aria-label="`Xem ${s.tracking_code || s.request_code}`">
                    <AppIcon name="eye" :size="18" />
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hasNext || hasPrevious" class="data-card__foot">
          <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total" unit="vận đơn"
                         @change="goPage" />
        </div>
      </template>
    </div>
  </section>
</template>
