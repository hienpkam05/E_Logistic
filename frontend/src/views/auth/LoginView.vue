<script setup>
// UC01.1 Đăng nhập.
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import FormField from '../../components/common/FormField.vue'
import AuthLayout from '../../layouts/AuthLayout.vue'
import { CHANGE_PASSWORD_ROUTE, safeNext } from '../../router/guard'
import { homeRouteFor } from '../../router/roles'
import { useAuthStore } from '../../stores/auth'
import { fieldErrors, generalMessage } from '../../utils/formErrors'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const form = reactive({ username: '', password: '' })
const errors = ref({})
const message = ref('')
const submitting = ref(false)

const notice = computed(() => {
  if (route.query.logout === 'unconfirmed') {
    return 'Đã đăng xuất trên thiết bị này nhưng chưa xác nhận được với máy chủ. Hãy đăng xuất lại khi có kết nối.'
  }
  if (auth.restoreError) return auth.restoreError.message
  if (route.query.next) return 'Vui lòng đăng nhập để tiếp tục.'
  return ''
})

async function onSubmit() {
  if (submitting.value) return
  submitting.value = true
  errors.value = {}
  message.value = ''
  try {
    const user = await auth.login(form.username.trim(), form.password)
    if (user.must_change_password) {
      await router.replace({ name: CHANGE_PASSWORD_ROUTE })
    } else {
      await router.replace(safeNext(route.query.next) || homeRouteFor(user.role))
    }
  } catch (err) {
    errors.value = fieldErrors(err)
    message.value = generalMessage(err)
    form.password = ''
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthLayout>
    <section class="card auth-card" aria-labelledby="login-title">
      <div>
        <p class="eyebrow">Chào mừng trở lại</p>
        <h1 id="login-title">Đăng nhập</h1>
        <p class="muted auth-card__lead">Dùng tài khoản do HTT EXPRESS cấp.</p>
      </div>

      <p v-if="notice" class="alert alert--info" role="status">{{ notice }}</p>
      <p v-if="message" class="alert alert--danger" role="alert">{{ message }}</p>

      <form class="form" novalidate @submit.prevent="onSubmit">
        <FormField v-model="form.username" label="Tên đăng nhập" autocomplete="username" required
                   :error="errors.username" :disabled="submitting" />
        <FormField v-model="form.password" label="Mật khẩu" type="password" autocomplete="current-password" required
                   :error="errors.password" :disabled="submitting" />
        <button type="submit" class="btn btn--primary btn--block" :disabled="submitting">
          {{ submitting ? 'Đang đăng nhập…' : 'Đăng nhập' }}
        </button>
      </form>

      <RouterLink :to="{ name: 'forgot-password' }" class="auth-card__link">Quên mật khẩu?</RouterLink>
    </section>
  </AuthLayout>
</template>
