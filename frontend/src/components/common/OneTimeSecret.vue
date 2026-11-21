<script setup>
// Hiện bí mật chỉ có một lần (mật khẩu tạm — spec 003 D3, D4): sao chép, cảnh báo, xác nhận đã ghi lại.
import { ref } from 'vue'

defineProps({
  secret: { type: String, required: true },
  label: { type: String, default: 'Mật khẩu tạm' },
  username: { type: String, default: '' },
})
const emit = defineEmits(['done'])

const copyState = ref('') // '' | 'copied' | 'failed'
const valueEl = ref(null)

async function copy(secret) {
  try {
    await navigator.clipboard.writeText(secret)
    copyState.value = 'copied'
  } catch {
    // Trình duyệt chặn clipboard (vd không phải HTTPS): chọn sẵn chữ để người dùng tự Ctrl+C.
    const selection = window.getSelection?.()
    if (selection && valueEl.value) {
      const range = document.createRange()
      range.selectNodeContents(valueEl.value)
      selection.removeAllRanges()
      selection.addRange(range)
    }
    copyState.value = 'failed'
  }
}
</script>

<template>
  <section class="one-time-secret card" aria-live="polite">
    <p class="alert alert--warning">
      <strong>Chỉ hiển thị một lần.</strong> Sau khi đóng sẽ không xem lại được. Hãy chuyển cho người dùng ngay
      (trực tiếp hoặc qua điện thoại đã xác minh) — không gửi qua kênh công khai.
    </p>
    <dl class="details">
      <template v-if="username">
        <dt>Tên đăng nhập</dt>
        <dd>{{ username }}</dd>
      </template>
      <dt>{{ label }}</dt>
      <dd><code ref="valueEl" class="one-time-secret__value">{{ secret }}</code></dd>
    </dl>
    <p class="muted">Người dùng sẽ phải đổi mật khẩu ngay lần đăng nhập đầu tiên.</p>
    <p v-if="copyState === 'copied'" class="alert alert--success" role="status">Đã sao chép vào bộ nhớ tạm.</p>
    <p v-else-if="copyState === 'failed'" class="alert alert--info" role="status">
      Trình duyệt không cho sao chép tự động — đã chọn sẵn, hãy nhấn Ctrl+C.
    </p>
    <div class="form__actions">
      <button type="button" class="btn btn--ghost" @click="copy(secret)">Sao chép</button>
      <button type="button" class="btn btn--primary" @click="emit('done')">Tôi đã ghi lại</button>
    </div>
  </section>
</template>

<style scoped>
.one-time-secret { display: flex; flex-direction: column; gap: 12px; }
.one-time-secret .details { margin: 0; }
.one-time-secret__value {
  font-size: 1.25rem; letter-spacing: .08em; padding: 4px 10px; border-radius: 6px;
  background: var(--tone-neutral-bg); user-select: all;
}
</style>
