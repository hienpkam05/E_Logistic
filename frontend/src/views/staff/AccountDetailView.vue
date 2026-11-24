<script setup>
// UC02.4 / UC06.3 / UC06.4 / UC01.3 A1 — chi tiết tài khoản: sửa, khóa/mở khóa, đặt lại mật khẩu, lịch sử.
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute } from 'vue-router'
import AppIcon from '../../components/common/AppIcon.vue'
import ConfirmDialog from '../../components/common/ConfirmDialog.vue'
import FormField from '../../components/common/FormField.vue'
import OneTimeSecret from '../../components/common/OneTimeSecret.vue'
import PaginationBar from '../../components/common/PaginationBar.vue'
import { ROLES } from '../../router/roles'
import * as accountService from '../../services/accountService'
import * as dispatchService from '../../services/dispatchService'
import StatusBadge from '../../components/common/StatusBadge.vue'
import { API_ERROR } from '../../services/http'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { accountStatus } from '../../utils/accountStatus'
import { formatDateTime, formatPhone, initials } from '../../utils/format'
import { fieldErrors, generalMessage } from '../../utils/formErrors'

const route = useRoute()
const auth = useAuthStore()
const meta = useMetaStore()

const account = ref(null)
const loading = ref(true)
const loadError = ref('')
const notFound = ref(false)
const success = ref('')

const id = computed(() => route.params.id)
const isSelf = computed(() => account.value && auth.user && account.value.id === auth.user.id)
const status = computed(() => accountStatus(account.value))
const isShipper = computed(() => account.value?.role === ROLES.SHIPPER)

const NOT_SET = 'Chưa cập nhật'
const rows = computed(() => {
  const a = account.value
  if (!a) return []
  return [
    ['Tên đăng nhập', a.username],
    ['Họ tên', a.full_name || NOT_SET],
    ['Số điện thoại', a.phone ? formatPhone(a.phone) : NOT_SET],
    ['Địa chỉ liên hệ', a.address || NOT_SET],
    ['Vai trò', meta.label('user_roles', a.role)],
    ['Đăng nhập gần nhất', a.last_login ? formatDateTime(a.last_login) : 'Chưa đăng nhập'],
    ['Ngày tạo', formatDateTime(a.date_joined)],
  ]
})

async function load() {
  loading.value = true
  loadError.value = ''
  notFound.value = false
  try {
    account.value = await accountService.get(id.value)
  } catch (err) {
    account.value = null
    if (err?.status === 404) notFound.value = true
    else loadError.value = err?.message || 'Chưa thể tải tài khoản.'
  } finally {
    loading.value = false
  }
}

// --- Sửa hồ sơ (UC06.3; E1: người khác vừa sửa -> 409) ---
const editing = ref(false)
const saving = ref(false)
const form = reactive({ full_name: '', phone: '', address: '' })
const errors = ref({})
const message = ref('')
const conflict = ref(false)

function startEdit() {
  Object.assign(form, { full_name: account.value.full_name, phone: account.value.phone, address: account.value.address })
  errors.value = {}
  message.value = ''
  conflict.value = false
  success.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  conflict.value = false
}

async function save() {
  if (saving.value) return
  saving.value = true
  errors.value = {}
  message.value = ''
  conflict.value = false
  try {
    account.value = await accountService.update(
      id.value,
      { full_name: form.full_name.trim(), phone: form.phone.trim(), address: form.address.trim() },
      account.value.updated_at,
    )
    editing.value = false
    success.value = 'Đã lưu thông tin tài khoản.'
    loadEvents()
  } catch (err) {
    errors.value = fieldErrors(err)
    message.value = generalMessage(err)
    conflict.value = err?.code === API_ERROR.CONFLICT
  } finally {
    saving.value = false
  }
}

// Tải bản mới nhất sau xung đột: form nhận dữ liệu mới, phần đang gõ dở bị bỏ (đã báo trước).
async function reloadAfterConflict() {
  await load()
  if (account.value) startEdit()
}

// --- Khóa / mở khóa (UC02.4 A2, UC06.4) / đặt lại mật khẩu (UC01.3 A1) ---
const dialog = ref('') // '' | 'lock' | 'unlock' | 'reset'
const dialogBusy = ref(false)
const dialogError = ref('')
const lockReason = ref('')
const identityVerified = ref(false)
const tempPassword = ref('')
const openTasks = ref([])
const tasksLoading = ref(false)
const tasksError = ref('')
let tasksRequest = 0

async function loadOpenTasks() {
  const request = ++tasksRequest
  const accountId = id.value
  tasksLoading.value = true
  tasksError.value = ''
  try {
    const data = await dispatchService.openTasks(accountId)
    if (request === tasksRequest && dialog.value === 'lock' && id.value === accountId) openTasks.value = data
  } catch (err) {
    if (request === tasksRequest && dialog.value === 'lock') tasksError.value = err?.message || 'Chưa tải được nhiệm vụ.'
  } finally {
    if (request === tasksRequest) tasksLoading.value = false
  }
}

function openDialog(name) {
  dialog.value = name
  dialogError.value = ''
  lockReason.value = ''
  identityVerified.value = false
  success.value = ''
  openTasks.value = []
  tasksError.value = ''
  if (name === 'lock' && isShipper.value) loadOpenTasks()
}

function closeDialog() {
  if (!dialogBusy.value) dialog.value = ''
}

async function runAction(action, successText) {
  dialogBusy.value = true
  dialogError.value = ''
  try {
    const result = await action()
    if (result?.temp_password) {
      account.value = result.user
      tempPassword.value = result.temp_password
    } else {
      account.value = result
      success.value = successText
    }
    dialog.value = ''
    loadEvents()
  } catch (err) {
    dialogError.value = err?.message || 'Chưa thực hiện được.'
  } finally {
    dialogBusy.value = false
  }
}

const confirmLock = () => {
  if (dialogBusy.value || (isShipper.value && (tasksLoading.value || tasksError.value))) return
  runAction(() => accountService.lock(id.value, lockReason.value.trim()), 'Đã khóa tài khoản.')
}
const confirmUnlock = () => runAction(() => accountService.unlock(id.value), 'Đã mở khóa tài khoản.')
const confirmReset = () => runAction(() => accountService.resetPassword(id.value))

onBeforeRouteLeave(() => {
  if (!tempPassword.value) return true
  return window.confirm('Mật khẩu tạm sẽ không xem lại được. Bạn chắc chắn đã ghi lại và muốn rời trang?')
})

// --- Lịch sử ---
const events = ref([])
const eventsPage = ref(1)
const eventsTotal = ref(0)
const eventsNext = ref(false)
const eventsPrev = ref(false)
const eventsError = ref('')

const FIELD_LABELS = { full_name: 'Họ tên', phone: 'Số điện thoại', address: 'Địa chỉ liên hệ' }
const shown = (value) => (value === '' || value === null || value === undefined ? '(trống)' : value)

function describe(event) {
  const c = event.changes || {}
  const lines = []
  if (c.role) lines.push(`Vai trò: ${meta.label('user_roles', c.role.to)}`)
  for (const [field, label] of Object.entries(FIELD_LABELS)) {
    if (c[field]) lines.push(`${label}: ${shown(c[field].from)} → ${shown(c[field].to)}`)
  }
  if (c.identity_verified) lines.push('Nhân viên đã xác minh danh tính')
  if (event.reason) lines.push(`Lý do: ${event.reason}`)
  return lines
}

async function loadEvents(pageNumber = eventsPage.value) {
  eventsError.value = ''
  try {
    const data = await accountService.events(id.value, { page: pageNumber })
    events.value = data.results
    eventsTotal.value = data.count
    eventsNext.value = Boolean(data.next)
    eventsPrev.value = Boolean(data.previous)
    eventsPage.value = pageNumber
  } catch (err) {
    eventsError.value = err?.message || 'Chưa thể tải lịch sử.'
  }
}

watch(id, () => {
  dialog.value = ''
  tasksRequest++
  tasksLoading.value = false
  editing.value = false
  tempPassword.value = ''
  success.value = ''
  load()
  loadEvents(1)
}, { immediate: true })
</script>

<template>
  <section class="page" aria-labelledby="account-title">
    <RouterLink :to="{ name: 'staff-accounts' }" class="back-link">
      <AppIcon name="arrow-left" :size="16" />Danh sách tài khoản
    </RouterLink>

    <p v-if="loading" class="loading" role="status"><span class="spinner" />Đang tải tài khoản…</p>

    <div v-else-if="notFound" class="card">
      <h1 id="account-title">Không tìm thấy tài khoản</h1>
      <p class="muted">Tài khoản không tồn tại.</p>
    </div>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost" @click="load">Tải lại</button>
    </div>

    <template v-else-if="account">
      <header class="detail-header">
        <div class="title-row">
          <span class="avatar-lg" aria-hidden="true">{{ initials(account.full_name || account.username) }}</span>
          <div>
            <div class="title-row">
              <h1 id="account-title">{{ account.full_name || account.username }}</h1>
              <span class="pill" :class="`pill--${status.tone}`">{{ status.label }}</span>
            </div>
            <p class="muted">@{{ account.username }} · {{ meta.label('user_roles', account.role) }}</p>
          </div>
        </div>
      </header>

      <p v-if="isSelf" class="alert alert--info">
        Đây là tài khoản của bạn. Dùng <RouterLink :to="{ name: 'profile' }">Thông tin cá nhân</RouterLink> và
        <RouterLink :to="{ name: 'change-password' }">Đổi mật khẩu</RouterLink> để thay đổi.
      </p>
      <p v-if="success" class="alert alert--success" role="status">{{ success }}</p>

      <OneTimeSecret v-if="tempPassword" :secret="tempPassword" :username="account.username" label="Mật khẩu tạm mới"
                     @done="tempPassword = ''" />

      <div class="detail-layout">
      <!-- Xem -->
      <div v-if="!editing" class="card">
        <h2 class="card__title"><span class="card__title-icon"><AppIcon name="user" /></span>Thông tin tài khoản</h2>
        <dl class="details">
          <template v-for="[label, value] in rows" :key="label">
            <dt>{{ label }}</dt>
            <dd :class="{ muted: value === NOT_SET }">{{ value }}</dd>
          </template>
        </dl>
        <div v-if="!isSelf" class="form__actions card__actions">
          <button type="button" class="btn btn--primary" @click="startEdit">Chỉnh sửa</button>
          <button v-if="account.is_active" type="button" class="btn btn--ghost" @click="openDialog('lock')">Khóa tài khoản</button>
          <button v-else type="button" class="btn btn--ghost" @click="openDialog('unlock')">Mở khóa</button>
          <button type="button" class="btn btn--ghost" @click="openDialog('reset')">Đặt lại mật khẩu</button>
        </div>
      </div>

      <!-- Sửa -->
      <form v-else class="form card" novalidate @submit.prevent="save">
        <div v-if="conflict" class="alert alert--warning" role="alert">
          <p class="alert__text">{{ message }}</p>
          <button type="button" class="btn btn--ghost" @click="reloadAfterConflict">Tải bản mới nhất</button>
        </div>
        <p v-else-if="message" class="alert alert--danger" role="alert">{{ message }}</p>
        <FormField v-model="form.full_name" label="Họ tên" required :error="errors.full_name" :disabled="saving" />
        <FormField v-model="form.phone" label="Số điện thoại" type="tel" required hint="10 chữ số, bắt đầu bằng 0."
                   :error="errors.phone" :disabled="saving" />
        <FormField v-model="form.address" label="Địa chỉ liên hệ" multiline :error="errors.address" :disabled="saving" />
        <p class="muted">Tên đăng nhập và vai trò không đổi được. Khóa/mở khóa dùng nút riêng.</p>
        <div class="form__actions">
          <button type="submit" class="btn btn--primary" :disabled="saving">{{ saving ? 'Đang lưu…' : 'Lưu' }}</button>
          <button type="button" class="btn btn--ghost" :disabled="saving" @click="cancelEdit">Hủy</button>
        </div>
      </form>

      <!-- Lịch sử -->
      <section class="card" aria-labelledby="events-title">
        <h2 id="events-title" class="card__title"><span class="card__title-icon"><AppIcon name="clock" /></span>Lịch sử thao tác</h2>
        <p v-if="eventsError" class="alert alert--danger" role="alert">{{ eventsError }}</p>
        <p v-else-if="!events.length" class="muted">Chưa có thao tác nào.</p>
        <ol v-else class="events">
          <li v-for="event in events" :key="event.id" class="events__item">
            <div class="events__head">
              <strong>{{ meta.label('account_actions', event.action) }}</strong>
              <time :datetime="event.created_at">{{ formatDateTime(event.created_at) }}</time>
            </div>
            <span class="muted">bởi {{ event.actor ? `${event.actor.full_name} (${event.actor.username})` : 'Hệ thống' }}</span>
            <ul v-if="describe(event).length" class="events__changes">
              <li v-for="line in describe(event)" :key="line">{{ line }}</li>
            </ul>
          </li>
        </ol>
        <PaginationBar :page="eventsPage" :has-previous="eventsPrev" :has-next="eventsNext" :total="eventsTotal"
                       unit="thao tác" @change="loadEvents" />
      </section>
      </div>

      <!-- Hộp xác nhận -->
      <ConfirmDialog :open="dialog === 'lock'" title="Khóa tài khoản?" confirm-label="Khóa" tone="danger"
                     :busy="dialogBusy" :confirm-disabled="isShipper && (tasksLoading || Boolean(tasksError))"
                     @confirm="confirmLock" @cancel="closeDialog">
        <p><strong>{{ account.username }}</strong> sẽ bị đăng xuất ngay trên mọi thiết bị và không đăng nhập được
          cho tới khi mở khóa. Khi mở khóa phải đăng nhập lại.</p>
        <p v-if="isShipper">Nhiệm vụ đang mở của Shipper vẫn được giữ và cần Nhân viên xử lý (bàn giao/đổi người).</p>
        <template v-if="isShipper && dialog === 'lock'">
          <p v-if="tasksLoading" class="loading" role="status">Đang tải nhiệm vụ đang mở…</p>
          <div v-else-if="tasksError" class="alert alert--danger" role="alert">
            <p>{{ tasksError }}</p><button type="button" class="btn btn--ghost btn--sm" @click="loadOpenTasks">Tải lại nhiệm vụ</button>
          </div>
          <template v-else>
            <p v-if="!openTasks.length" class="muted">Shipper không có nhiệm vụ đang mở.</p>
            <template v-else>
              <p class="alert alert--warning">Sau khi khóa, cần xử lý bàn giao/đổi Shipper cho {{ openTasks.length }} nhiệm vụ này.</p>
              <ul class="events">
                <li v-for="task in openTasks" :key="task.id" class="events__item">
                  <RouterLink :to="{ name: 'staff-shipment-detail', params: { id: task.shipment.id } }">
                    {{ task.shipment.tracking_code || `Đơn #${task.shipment.id}` }}
                  </RouterLink>
                  <span>{{ meta.label('task_types', task.type) }}</span>
                  <StatusBadge group="task_statuses" :value="task.status" />
                  <span v-if="task.needs_attention" class="muted">Cần Nhân viên xử lý</span>
                </li>
              </ul>
            </template>
          </template>
        </template>
        <FormField v-model="lockReason" label="Lý do (không bắt buộc)" multiline :disabled="dialogBusy" />
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'unlock'" title="Mở khóa tài khoản?" confirm-label="Mở khóa"
                     :busy="dialogBusy" @confirm="confirmUnlock" @cancel="closeDialog">
        <p><strong>{{ account.username }}</strong> sẽ đăng nhập lại được. Các phiên cũ không dùng lại được.</p>
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>

      <ConfirmDialog :open="dialog === 'reset'" title="Đặt lại mật khẩu?" confirm-label="Đặt lại" tone="danger"
                     :busy="dialogBusy" :confirm-disabled="!identityVerified" @confirm="confirmReset" @cancel="closeDialog">
        <p>Mật khẩu hiện tại của <strong>{{ account.username }}</strong> sẽ hết hiệu lực, mọi thiết bị bị đăng xuất.
          Hệ thống cấp một mật khẩu tạm, người dùng phải đổi khi đăng nhập.</p>
        <label class="checkbox">
          <input v-model="identityVerified" type="checkbox" :disabled="dialogBusy" />
          Tôi đã xác minh danh tính người yêu cầu (họ tên và số điện thoại đã đăng ký).
        </label>
        <p v-if="dialogError" class="alert alert--danger" role="alert">{{ dialogError }}</p>
      </ConfirmDialog>
    </template>
  </section>
</template>

