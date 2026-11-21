<script setup>
// UC02.3 Đổi mật khẩu; cũng là bước bắt buộc sau khi nhận mật khẩu tạm (UC01.3).
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import FormField from '../../components/common/FormField.vue'
import { homeRouteFor } from '../../router/roles'
import * as authService from '../../services/authService'
import { useAuthStore } from '../../stores/auth'
import { fieldErrors, generalMessage } from '../../utils/formErrors'

const auth = useAuthStore()
const router = useRouter()

const empty = () => ({ currentPassword: '', newPassword: '', newPasswordConfirm: '' })
const form = reactive(empty())
const errors = ref({})
const message = ref('')
const success = ref('')
const submitting = ref(false)

async function onSubmit() {
  if (submitting.value) return
  const wasForced = auth.mustChangePassword
  submitting.value = true
  errors.value = {}
  message.value = ''
  success.value = ''
  try {
    await authService.changePassword({ ...form })
    auth.setUser(await authService.getMe())
    Object.assign(form, empty())
    if (wasForced) {
      await router.replace(homeRouteFor(auth.role))
    } else {
      success.value = 'Đã đổi mật khẩu. Các thiết bị khác đang đăng nhập tài khoản này sẽ phải đăng nhập lại.'
    }
  } catch (err) {
    errors.value = fieldErrors(err)
    message.value = generalMessage(err)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="page page--narrow" aria-labelledby="change-password-title">
    <h1 id="change-password-title">Đổi mật khẩu</h1>

    <p v-if="auth.mustChangePassword" class="alert alert--warning" role="status">
      Bạn đang dùng mật khẩu tạm. Hãy đặt mật khẩu mới để tiếp tục sử dụng hệ thống.
    </p>
    <p v-if="success" class="alert alert--success" role="status">{{ success }}</p>
    <p v-if="message" class="alert alert--danger" role="alert">{{ message }}</p>

    <form class="form card" novalidate @submit.prevent="onSubmit">
      <FormField v-model="form.currentPassword" label="Mật khẩu hiện tại" type="password"
                 autocomplete="current-password" required :error="errors.current_password" :disabled="submitting" />
      <FormField v-model="form.newPassword" label="Mật khẩu mới" type="password" autocomplete="new-password" required
                 hint="Ít nhất 8 ký tự, không quá giống tên đăng nhập, không chỉ gồm số."
                 :error="errors.new_password" :disabled="submitting" />
      <FormField v-model="form.newPasswordConfirm" label="Nhập lại mật khẩu mới" type="password"
                 autocomplete="new-password" required :error="errors.new_password_confirm" :disabled="submitting" />
      <div class="form__actions">
        <button type="submit" class="btn btn--primary" :disabled="submitting">
          {{ submitting ? 'Đang lưu…' : 'Đổi mật khẩu' }}
        </button>
        <RouterLink :to="{ name: 'forgot-password' }">Quên mật khẩu hiện tại?</RouterLink>
      </div>
    </form>
  </section>
</template>
