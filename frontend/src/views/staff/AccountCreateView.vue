<script setup>
// UC02.4 A1 / UC06.2 — tạo tài khoản. ?role=SHIPPER (từ "Quản lý Shipper") khóa sẵn vai trò (UC06.2 BR1).
// Thành công: mật khẩu tạm hiện MỘT lần (D3); rời trang trước khi xác nhận đã ghi lại thì hỏi lại.
import { computed, reactive, ref } from 'vue'
import { RouterLink, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import FormField from '../../components/common/FormField.vue'
import OneTimeSecret from '../../components/common/OneTimeSecret.vue'
import { isRole } from '../../router/roles'
import * as accountService from '../../services/accountService'
import { useMetaStore } from '../../stores/meta'
import { fieldErrors, generalMessage } from '../../utils/formErrors'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const roles = computed(() => meta.options('user_roles'))
// Kiểm tra bằng ROLES cục bộ (đồng bộ) — không để vai trò khóa sẵn phụ thuộc meta đã tải xong chưa.
const presetRole = computed(() => (isRole(route.query.role) ? route.query.role : ''))

const form = reactive({ username: '', full_name: '', phone: '', address: '', role: '' })
const errors = ref({})
const message = ref('')
const submitting = ref(false)
const created = ref(null) // { user, temp_password }

const backRoute = computed(() => ({ name: 'staff-accounts', query: presetRole.value ? { role: presetRole.value } : {} }))

async function onSubmit() {
  if (submitting.value) return
  submitting.value = true
  errors.value = {}
  message.value = ''
  try {
    created.value = await accountService.create({
      username: form.username.trim(),
      full_name: form.full_name.trim(),
      phone: form.phone.trim(),
      address: form.address.trim(),
      role: presetRole.value || form.role,
    })
  } catch (err) {
    errors.value = fieldErrors(err)
    message.value = generalMessage(err)
  } finally {
    submitting.value = false
  }
}

function acknowledge() {
  const id = created.value.user.id
  created.value = null
  router.replace({ name: 'staff-account-detail', params: { id } })
}

onBeforeRouteLeave(() => {
  if (!created.value) return true
  return window.confirm('Mật khẩu tạm sẽ không xem lại được. Bạn chắc chắn đã ghi lại và muốn rời trang?')
})
</script>

<template>
  <section class="page page--narrow" aria-labelledby="create-title">
    <h1 id="create-title">{{ presetRole ? `Thêm ${meta.label('user_roles', presetRole)}` : 'Thêm tài khoản' }}</h1>

    <template v-if="created">
      <p class="alert alert--success" role="status">Đã tạo tài khoản {{ created.user.username }}.</p>
      <OneTimeSecret :secret="created.temp_password" :username="created.user.username" @done="acknowledge" />
    </template>

    <form v-else class="form card" novalidate @submit.prevent="onSubmit">
      <p v-if="message" class="alert alert--danger" role="alert">{{ message }}</p>
      <FormField v-model="form.username" label="Tên đăng nhập" autocomplete="off" required
                 hint="3–150 ký tự: chữ không dấu, số, dấu chấm, gạch dưới, gạch ngang."
                 :error="errors.username" :disabled="submitting" />
      <FormField v-model="form.full_name" label="Họ tên" required :error="errors.full_name" :disabled="submitting" />
      <FormField v-model="form.phone" label="Số điện thoại" type="tel" required hint="10 chữ số, bắt đầu bằng 0."
                 :error="errors.phone" :disabled="submitting" />
      <FormField v-model="form.address" label="Địa chỉ liên hệ" multiline :error="errors.address" :disabled="submitting" />

      <div v-if="presetRole" class="field">
        <span class="field__label">Vai trò</span>
        <p class="field__static">{{ meta.label('user_roles', presetRole) }}</p>
      </div>
      <div v-else class="field" :class="{ 'field--invalid': errors.role }">
        <label for="create-role">Vai trò<span class="field__required" aria-hidden="true"> *</span></label>
        <select id="create-role" v-model="form.role" required :disabled="submitting"
                :aria-invalid="errors.role ? 'true' : undefined">
          <option value="" disabled>Chọn vai trò</option>
          <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
        <p v-if="errors.role" class="field__error">{{ errors.role }}</p>
      </div>

      <p class="muted">Hệ thống sẽ tạo mật khẩu tạm; người dùng phải đổi ở lần đăng nhập đầu. Vai trò không đổi được sau khi tạo.</p>
      <div class="form__actions">
        <button type="submit" class="btn btn--primary" :disabled="submitting">
          {{ submitting ? 'Đang tạo…' : 'Tạo tài khoản' }}
        </button>
        <RouterLink :to="backRoute">Hủy</RouterLink>
      </div>
    </form>
  </section>
</template>

<style scoped>
.field__label { font-weight: 600; font-size: .9375rem; }
.field__static { margin: 0; padding: 10px 0; }
</style>
