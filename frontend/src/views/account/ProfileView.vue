<script setup>
// UC02.1 Xem thông tin tài khoản, UC02.2 Cập nhật thông tin cá nhân.
import { computed, onMounted, reactive, ref } from 'vue'
import FormField from '../../components/common/FormField.vue'
import * as authService from '../../services/authService'
import { useAuthStore } from '../../stores/auth'
import { useMetaStore } from '../../stores/meta'
import { formatDateTime, formatPhone } from '../../utils/format'
import { fieldErrors, generalMessage } from '../../utils/formErrors'

const auth = useAuthStore()
const meta = useMetaStore()

const profile = ref(null)
const loading = ref(true)
const loadError = ref('')
const editing = ref(false)
const saving = ref(false)
const form = reactive({ full_name: '', phone: '', address: '' })
const errors = ref({})
const message = ref('')
const success = ref('')

const NOT_SET = 'Chưa cập nhật'
const rows = computed(() => {
  const p = profile.value
  if (!p) return []
  return [
    ['Tên đăng nhập', p.username],
    ['Họ tên', p.full_name || NOT_SET],
    ['Số điện thoại', p.phone ? formatPhone(p.phone) : NOT_SET],
    ['Địa chỉ liên hệ', p.address || NOT_SET],
    ['Vai trò', meta.label('user_roles', p.role)],
    ['Ngày tạo tài khoản', formatDateTime(p.date_joined)],
  ]
})

// Luôn lấy hồ sơ mới từ máy chủ (UC02.1); lỗi thì không hiển thị dữ liệu thay thế (E1).
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    profile.value = await authService.getMe()
    auth.setUser(profile.value)
  } catch (err) {
    profile.value = null
    loadError.value = err?.message || 'Chưa thể tải thông tin.'
  } finally {
    loading.value = false
  }
}

function startEdit() {
  Object.assign(form, {
    full_name: profile.value.full_name,
    phone: profile.value.phone,
    address: profile.value.address,
  })
  errors.value = {}
  message.value = ''
  success.value = ''
  editing.value = true
}

// UC02.2 A1: Hủy bỏ thay đổi chưa lưu, không gọi máy chủ.
function cancelEdit() {
  editing.value = false
  errors.value = {}
  message.value = ''
}

async function save() {
  if (saving.value) return
  saving.value = true
  errors.value = {}
  message.value = ''
  try {
    const data = await authService.updateMe({
      full_name: form.full_name.trim(),
      phone: form.phone.trim(),
      address: form.address.trim(),
    })
    profile.value = data
    auth.setUser(data)
    editing.value = false
    success.value = 'Đã lưu thông tin cá nhân.'
  } catch (err) {
    errors.value = fieldErrors(err)
    message.value = generalMessage(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="page page--narrow" aria-labelledby="profile-title">
    <h1 id="profile-title">Thông tin cá nhân</h1>

    <p v-if="loading" class="muted" role="status">Đang tải thông tin…</p>

    <div v-else-if="loadError" class="alert alert--danger" role="alert">
      <p class="alert__text">{{ loadError }}</p>
      <button type="button" class="btn btn--ghost" @click="load">Tải lại</button>
    </div>

    <template v-else-if="profile">
      <p v-if="success" class="alert alert--success" role="status">{{ success }}</p>

      <div v-if="!editing" class="card">
        <dl class="details">
          <template v-for="[label, value] in rows" :key="label">
            <dt>{{ label }}</dt>
            <dd :class="{ muted: value === NOT_SET }">{{ value }}</dd>
          </template>
        </dl>
        <button type="button" class="btn btn--primary" @click="startEdit">Chỉnh sửa</button>
      </div>

      <form v-else class="form card" novalidate @submit.prevent="save">
        <p v-if="message" class="alert alert--danger" role="alert">{{ message }}</p>
        <FormField v-model="form.full_name" label="Họ tên" autocomplete="name" required
                   :error="errors.full_name" :disabled="saving" />
        <FormField v-model="form.phone" label="Số điện thoại" type="tel" autocomplete="tel" required
                   hint="10 chữ số, bắt đầu bằng 0." :error="errors.phone" :disabled="saving" />
        <FormField v-model="form.address" label="Địa chỉ liên hệ" multiline
                   :error="errors.address" :disabled="saving" />
        <p class="muted">Tên đăng nhập và vai trò do Nhân viên quản lý, không tự sửa được.</p>
        <div class="form__actions">
          <button type="submit" class="btn btn--primary" :disabled="saving">{{ saving ? 'Đang lưu…' : 'Lưu' }}</button>
          <button type="button" class="btn btn--ghost" :disabled="saving" @click="cancelEdit">Hủy</button>
        </div>
      </form>
    </template>
  </section>
</template>
