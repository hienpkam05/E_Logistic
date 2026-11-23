<script setup>
// UC02.4 / UC06.1 — danh sách tài khoản. "Quản lý Shipper" = màn hình này với ?role=SHIPPER.
// Bộ lọc, từ khóa, trang nằm trên URL để Back/tải lại giữ nguyên.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import PaginationBar from '../../components/common/PaginationBar.vue'
import { isRole } from '../../router/roles'
import * as accountService from '../../services/accountService'
import { useMetaStore } from '../../stores/meta'
import { STATUS_FILTERS, accountStatus, isActiveFromFilter } from '../../utils/accountStatus'
import { formatPhone, initials } from '../../utils/format'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

// Nhãn tab lấy từ backend; còn kiểm tra ?role= dùng ROLES cục bộ — không phụ thuộc meta tải bất đồng bộ,
// nếu không lần tải đầu (meta chưa về) sẽ bỏ qua bộ lọc vai trò.
const roles = computed(() => meta.options('user_roles'))
const role = computed(() => (isRole(route.query.role) ? route.query.role : ''))
const status = computed(() => (STATUS_FILTERS.some((f) => f.value === route.query.status) ? route.query.status : ''))
const q = computed(() => (typeof route.query.q === 'string' ? route.query.q : ''))
const page = computed(() => Math.max(1, Number.parseInt(route.query.page, 10) || 1))
const filtered = computed(() => Boolean(role.value || status.value || q.value))
const title = computed(() => (role.value ? `Quản lý ${meta.label('user_roles', role.value)}` : 'Quản lý tài khoản'))

const searchText = ref(q.value)
const items = ref([])
const total = ref(0)
const hasNext = ref(false)
const hasPrevious = ref(false)
const loading = ref(false)
const loadError = ref('')

let requestId = 0
async function load() {
  const current = ++requestId
  loading.value = true
  loadError.value = ''
  try {
    const data = await accountService.list({
      role: role.value || undefined,
      isActive: isActiveFromFilter(status.value),
      q: q.value || undefined,
      page: page.value,
    })
    if (current !== requestId) return
    items.value = data.results
    total.value = data.count
    hasNext.value = Boolean(data.next)
    hasPrevious.value = Boolean(data.previous)
  } catch (err) {
    if (current !== requestId) return
    items.value = []
    loadError.value = err?.message || 'Chưa thể tải danh sách.'
  } finally {
    if (current === requestId) loading.value = false
  }
}

// Đổi bộ lọc luôn về trang 1; bỏ tham số rỗng khỏi URL.
function setQuery(patch) {
  const next = { role: role.value, status: status.value, q: q.value, ...patch }
  const query = Object.fromEntries(Object.entries(next).filter(([, v]) => v))
  router.push({ name: 'staff-accounts', query })
}

function goPage(next) {
  router.push({ name: 'staff-accounts', query: { ...route.query, page: next > 1 ? String(next) : undefined } })
}

function clearFilters() {
  searchText.value = ''
  router.push({ name: 'staff-accounts' })
}

const createRoute = computed(() => ({ name: 'staff-account-new', query: role.value ? { role: role.value } : {} }))

watch(q, (value) => { searchText.value = value })
watch([role, status, q, page], load, { immediate: true })

</script>

<template>
  <section class="page" aria-labelledby="accounts-title">
    <h1 id="accounts-title" class="sr-only">{{ title }}</h1>

    <div class="toolbar">
      <RouterLink :to="createRoute" class="btn btn--primary btn--split">
        <span class="btn__icon"><AppIcon name="user-plus" :size="20" /></span>
        <span class="btn__label">{{ role ? `Thêm ${meta.label('user_roles', role)}` : 'Thêm tài khoản' }}</span>
      </RouterLink>
      <span class="toolbar__spacer" />
      <form class="search" role="search" @submit.prevent="setQuery({ q: searchText.trim() })">
        <AppIcon name="search" :size="20" />
        <input v-model="searchText" type="search" placeholder="Tìm tên đăng nhập, họ tên, số điện thoại"
               aria-label="Từ khóa tìm kiếm" :maxlength="meta.limits.search_query_max_length" />
      </form>
    </div>

    <div class="data-card">
      <div class="data-card__head">
        <div class="tabs" role="group" aria-label="Lọc theo vai trò">
          <button type="button" class="tabs__item" :aria-pressed="!role" @click="setQuery({ role: '' })">Tất cả</button>
          <button v-for="r in roles" :key="r.value" type="button" class="tabs__item" :aria-pressed="role === r.value"
                  @click="setQuery({ role: r.value })">{{ r.label }}</button>
        </div>
        <label class="filter-select">
          <AppIcon name="filter" :size="16" />
          <span class="sr-only">Lọc theo trạng thái</span>
          <select :value="status" @change="setQuery({ status: $event.target.value })">
            <option v-for="f in STATUS_FILTERS" :key="f.value" :value="f.value">{{ f.label }}</option>
          </select>
        </label>
        <span v-if="!loading && !loadError" class="data-card__count">{{ total }} tài khoản</span>
      </div>

      <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải danh sách…</p>

      <div v-else-if="loadError" class="empty-state" role="alert">
        <span class="empty-state__icon"><AppIcon name="alert" :size="26" /></span>
        <p class="empty-state__title">Chưa tải được danh sách</p>
        <p>{{ loadError }}</p>
        <button type="button" class="btn btn--primary" @click="load"><AppIcon name="reload" :size="16" />Tải lại</button>
      </div>

      <div v-else-if="!items.length" class="empty-state">
        <span class="empty-state__icon"><AppIcon :name="filtered ? 'search' : 'users'" :size="26" /></span>
        <p class="empty-state__title">{{ filtered ? 'Không có tài khoản phù hợp với bộ lọc.' : 'Chưa có tài khoản nào.' }}</p>
        <button v-if="filtered" type="button" class="btn btn--ghost" @click="clearFilters">Bỏ lọc</button>
      </div>

      <template v-else>
        <div class="table-wrap">
          <table class="table table--stack">
            <thead>
              <tr>
                <th>Tên đăng nhập</th><th>Họ tên</th><th>Số điện thoại</th><th>Vai trò</th><th>Trạng thái</th>
                <th class="cell-actions">Xem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in items" :key="user.id">
                <td data-label="Tên đăng nhập"><RouterLink :to="{ name: 'staff-account-detail', params: { id: user.id } }">{{ user.username }}</RouterLink></td>
                <td data-label="Họ tên">
                  <span class="person">
                    <span class="person__avatar" aria-hidden="true">{{ initials(user.full_name || user.username) }}</span>{{ user.full_name }}
                  </span>
                </td>
                <td data-label="Số điện thoại">{{ formatPhone(user.phone) }}</td>
                <td data-label="Vai trò">{{ meta.label('user_roles', user.role) }}</td>
                <td data-label="Trạng thái"><span class="pill" :class="`pill--${accountStatus(user).tone}`">{{ accountStatus(user).label }}</span></td>
                <td class="cell-actions" data-label="Xem">
                  <RouterLink :to="{ name: 'staff-account-detail', params: { id: user.id } }" class="row-action"
                              :aria-label="`Xem ${user.username}`">
                    <AppIcon name="eye" :size="18" />
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hasNext || hasPrevious" class="data-card__foot">
          <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total" unit="tài khoản"
                         @change="goPage" />
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.person { display: inline-flex; align-items: center; gap: 10px; }
.person__avatar {
  display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 50%;
  font-size: .75rem; font-weight: 700; color: var(--brand); background: var(--brand-soft);
}
</style>
