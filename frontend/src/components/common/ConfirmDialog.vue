<script setup>
// Hộp xác nhận dùng <dialog> gốc: trình duyệt lo bẫy focus và phím Esc.
// Môi trường không có showModal() (vd jsdom khi test) thì mở bằng thuộc tính `open`.
import { nextTick, ref, useId, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  confirmLabel: { type: String, default: 'Xác nhận' },
  cancelLabel: { type: String, default: 'Hủy' },
  tone: { type: String, default: 'primary' }, // 'primary' | 'danger'
  busy: { type: Boolean, default: false },
  confirmDisabled: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])

const dialog = ref(null)
const titleId = useId()

function show() {
  const el = dialog.value
  if (!el || el.open) return
  if (typeof el.showModal === 'function') el.showModal()
  else el.setAttribute('open', '')
}

function hide() {
  const el = dialog.value
  if (!el || !el.open) return
  if (typeof el.close === 'function') el.close()
  else el.removeAttribute('open')
}

function cancel() {
  if (!props.busy) emit('cancel')
}

// Esc của trình duyệt: chặn đóng tự động, để component cha quyết định qua prop `open`.
function onNativeCancel(event) {
  event.preventDefault()
  cancel()
}

watch(() => props.open, async (value) => {
  await nextTick()
  value ? show() : hide()
}, { immediate: true })
</script>

<template>
  <dialog ref="dialog" class="confirm-dialog" :aria-labelledby="titleId" @cancel="onNativeCancel">
    <form method="dialog" class="confirm-dialog__body" @submit.prevent="emit('confirm')">
      <h2 :id="titleId">{{ title }}</h2>
      <div class="confirm-dialog__content"><slot /></div>
      <div class="form__actions confirm-dialog__actions">
        <button type="button" class="btn btn--ghost" :disabled="busy" @click="cancel">{{ cancelLabel }}</button>
        <button type="submit" class="btn" :class="tone === 'danger' ? 'btn--danger' : 'btn--primary'"
                :disabled="busy || confirmDisabled">
          {{ busy ? 'Đang xử lý…' : confirmLabel }}
        </button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.confirm-dialog {
  width: min(460px, calc(100vw - 32px)); padding: 0; border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text);
}
.confirm-dialog::backdrop { background: rgb(23 45 61 / 45%); }
.confirm-dialog__body { display: flex; flex-direction: column; gap: 16px; padding: 24px; }
.confirm-dialog__body h2 { margin: 0; }
.confirm-dialog__content { display: flex; flex-direction: column; gap: 12px; line-height: 1.6; }
.confirm-dialog__actions { justify-content: flex-end; }
</style>
