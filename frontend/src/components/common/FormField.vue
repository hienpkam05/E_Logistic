<script setup>
// Ô nhập có nhãn + lỗi theo trường; dùng chung cho mọi form.
import { computed, useId } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  type: { type: String, default: 'text' },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
  autocomplete: { type: String, default: undefined },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  multiline: { type: Boolean, default: false },
  // Độ dài tối đa — lấy từ meta.limits, không viết số ở màn hình.
  maxlength: { type: Number, default: undefined },
})
// Vue tự đổi giá trị <input type="number"> thành Number khi gõ — nhận cả hai kiểu.
const model = defineModel({ type: [String, Number], default: '' })

const id = useId()
const describedBy = computed(() =>
  [props.error && `${id}-error`, props.hint && `${id}-hint`].filter(Boolean).join(' ') || undefined,
)
</script>

<template>
  <div class="field" :class="{ 'field--invalid': error }">
    <label :for="id">{{ label }}<span v-if="required" class="field__required" aria-hidden="true"> *</span></label>
    <textarea
      v-if="multiline"
      :id="id"
      v-model="model"
      rows="2"
      :maxlength="maxlength"
      :required="required"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="describedBy"
    />
    <input
      v-else
      :id="id"
      v-model="model"
      :type="type"
      :autocomplete="autocomplete"
      :maxlength="maxlength"
      :required="required"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="describedBy"
    />
    <p v-if="hint" :id="`${id}-hint`" class="field__hint">{{ hint }}</p>
    <p v-if="error" :id="`${id}-error`" class="field__error">{{ error }}</p>
  </div>
</template>
