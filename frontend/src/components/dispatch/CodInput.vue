<script setup>
// Ô COD thực thu khi giao thành công (UC04.5 bước 3, UC04.7; spec 007 D5).
// - Hiện COD phải thu thật to; Shipper TỰ GÕ số đã thu (ô để trống, không điền sẵn) để buộc đếm tiền.
// - Báo khớp / thiếu / thừa ngay khi gõ (backend vẫn kiểm lại — nguồn sự thật).
// - Đơn không COD (A1): không có ô nhập, giá trị luôn 0.
// v-model = số nguyên VND hoặc null (chưa nhập).
import { computed, useId, watch } from 'vue'
import { formatNumber, formatVnd } from '../../utils/format'

const props = defineProps({
  expected: { type: Number, required: true },
  max: { type: Number, default: undefined }, // meta.limits.cod_max_vnd
  error: { type: String, default: '' }, // lỗi từ backend (fields.cod_collected)
  disabled: { type: Boolean, default: false },
})
const model = defineModel({ type: Number, default: null })

const id = useId()
const hasCod = computed(() => props.expected > 0)
watch(hasCod, (value) => { if (!value) model.value = 0 }, { immediate: true })

const display = computed(() => formatNumber(model.value))

function onInput(event) {
  const digits = event.target.value.replace(/\D/g, '')
  let value = digits ? Number(digits) : null
  if (value !== null && props.max !== undefined && value > props.max) value = props.max
  model.value = value
  event.target.value = formatNumber(value) // giữ hiển thị có dấu chấm ngăn cách
}

// Trạng thái so với phải thu: dùng cho chữ hiển thị và để màn cha biết đã khớp chưa.
const status = computed(() => {
  if (model.value === null) return { tone: 'muted', text: 'Nhập số tiền đã thu của người nhận.' }
  const diff = model.value - props.expected
  if (diff === 0) return { tone: 'success', text: 'Khớp COD phải thu.' }
  return diff < 0
    ? { tone: 'danger', text: `Thiếu ${formatVnd(-diff)} — chưa thu đủ thì ghi giao thất bại, không thu một phần.` }
    : { tone: 'danger', text: `Thừa ${formatVnd(diff)} so với COD phải thu.` }
})
const matches = computed(() => model.value === props.expected)
defineExpose({ matches })
</script>

<template>
  <div class="cod" :class="{ 'cod--invalid': error }">
    <p class="cod__expected">
      <span class="cod__label">COD phải thu</span>
      <strong class="cod__amount">{{ formatVnd(expected) }}</strong>
    </p>

    <p v-if="!hasCod" class="cod__none" role="status">Đơn không thu COD.</p>
    <template v-else>
      <label :for="id" class="cod__input-label">Số tiền đã thu (VND)<span aria-hidden="true"> *</span></label>
      <input
        :id="id"
        class="cod__input"
        type="text"
        inputmode="numeric"
        autocomplete="off"
        placeholder="Nhập số tiền"
        :value="display"
        :disabled="disabled"
        :aria-invalid="error || status.tone === 'danger' ? 'true' : undefined"
        :aria-describedby="`${id}-status`"
        @input="onInput"
      />
      <p :id="`${id}-status`" class="cod__status" :class="`cod__status--${status.tone}`" role="status" aria-live="polite">
        {{ status.text }}
      </p>
      <p v-if="error" class="field__error" role="alert">{{ error }}</p>
    </template>
  </div>
</template>

<style scoped>
.cod { display: flex; flex-direction: column; gap: 8px; }
.cod__expected {
  display: flex; flex-direction: column; gap: 2px; margin: 0; padding: 12px 16px;
  border-radius: var(--radius-sm); background: var(--brand-softer);
}
.cod__label { font-size: .8125rem; color: var(--muted); }
.cod__amount { font-size: 1.75rem; line-height: 1.2; color: var(--brand); }
.cod__none { margin: 0; color: var(--muted); }
.cod__input-label { font-weight: 600; font-size: .875rem; }
.cod__input {
  padding: 12px 14px; font-size: 1.25rem; font-weight: 600; letter-spacing: .02em;
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface);
}
.cod__input:focus { outline: none; border-color: var(--brand); box-shadow: var(--focus-ring); }
.cod--invalid .cod__input, .cod__input[aria-invalid='true'] { border-color: var(--tone-danger-fg); }
.cod__status { margin: 0; font-size: .875rem; }
.cod__status--muted { color: var(--muted); }
.cod__status--success { color: var(--tone-success-fg); }
.cod__status--danger { color: var(--tone-danger-fg); }
</style>
