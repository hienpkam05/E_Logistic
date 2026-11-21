<script setup>
// UC02.4 / UC06.1 — danh sách tài khoản. "Quản lý Shipper" = màn hình này với ?role=SHIPPER.
// Bộ lọc, từ khóa, trang nằm trên URL để Back/tải lại giữ nguyên.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import PaginationBar from '../../components/common/PaginationBar.vue'
import { isRole } from '../../router/roles'
import * as accountService from '../../services/accountService'
import { useMetaStore } from '../../stores/meta'
import { STATUS_FILTERS, accountStatus, isActiveFromFilter } from '../../utils/accountStatus'
import { formatPhone } from '../../utils/format'

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
    <div class="page__header">
      <h1 id="accounts-title">{{ title }}</h1>
      <RouterLink :to="createRoute" class="btn btn--primary">
        {{ role ? `Thêm ${meta.label('user_roles', role)}` : 'Thêm tài khoản' }}
      </RouterLink>
    </div>

    <div class="tabs" role="group" aria-label="Lọc theo vai trò">
      <button type="button" class="tabs__item" :aria-pressed="!role" @click="setQuery({ role: '' })">Tất cả</button>
      <button v-for="r in roles" :key="r.value" type="button" class="tabs__item" :aria-pressed="role === r.value"
              @click="setQuery({ role: r.value })">{{ r.label }}</button>
    </div>

    <form class="toolbar" role="search" @submit.prevent="setQuery({ q: searchText.trim() })">
      <input v-model="searchText" type="search" placeholder="Tìm tên đăng nhập, họ tên, số điện thoại"
             aria-label="Từ khóa tìm kiếm" maxlength="100" />
      <select :value="status" aria-label="Lọc theo trạng thái" @change="setQuery({ status: $event.target.value })">
        <option v-for="f in STATUS_FILTERS" :key="f.value" :value="f.value">{{ f.label }}</option>
      </select>
      <button type="submit" class="btn btn--ghost">Tìm</button>
    </form>

    <p v-if="loading" class="muted" role="status">Đang tải danh sách…</p>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost" @click="load">Tải lại</button>
    </div>

    <div v-else-if="!items.length" class="card empty">
      <p class="muted">{{ filtered ? 'Không có tài khoản phù hợp với bộ lọc.' : 'Chưa có tài khoản nào.' }}</p>
      <button v-if="filtered" type="button" class="btn btn--ghost" @click="clearFilters">Bỏ lọc</button>
    </div>

    <template v-else>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr><th>Tên đăng nhập</th><th>Họ tên</th><th>Số điện thoại</th><th>Vai trò</th><th>Trạng thái</th></tr>
          </thead>
          <tbody>
            <tr v-for="user in items" :key="user.id">
              <td><RouterLink :to="{ name: 'staff-account-detail', params: { id: user.id } }">{{ user.username }}</RouterLink></td>
              <td>{{ user.full_name }}</td>
              <td>{{ formatPhone(user.phone) }}</td>
              <td>{{ meta.label('user_roles', user.role) }}</td>
              <td><span class="pill" :class="`pill--${accountStatus(user).tone}`">{{ accountStatus(user).label }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar :page="page" :has-previous="hasPrevious" :has-next="hasNext" :total="total" unit="tài khoản"
                     @change="goPage" />
    </template>
  </section>
</template>

<style scoped>
.page__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.page__header h1 { margin: 0; }
.page__header .btn { text-decoration: none; }
.tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.tabs__item {
  font: inherit; cursor: pointer; padding: 6px 14px; border-radius: 999px;
  border: 1px solid var(--border); background: white; color: var(--text);
}
.tabs__item[aria-pressed='true'] { border-color: var(--brand); color: var(--brand); font-weight: 600; }
.empty { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.empty p { margin: 0; }
</style>
