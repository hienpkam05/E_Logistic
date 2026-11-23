<script setup>
// Chọn phường/xã Hà Nội (spec 004 D1): ô gõ để lọc + danh sách. Giá trị là MÃ phường.
// Dùng lại cho mọi form địa chỉ (lấy hàng, giao hàng, spec sau).
import { computed, ref, useId } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  wards: { type: Array, default: () => [] }, // [{ code, name }]
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
const model = defineModel({ type: String, default: '' })

const id = useId()
const filter = ref('')

// So khớp không dấu, không phân biệt hoa thường: "hoan kiem" tìm được "Hoàn Kiếm".
const normalize = (text) =>
  text.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase()

const options = computed(() => {
  const term = normalize(filter.value.trim())
  const matched = term ? props.wards.filter((w) => normalize(w.name).includes(term)) : props.wards
  // Giữ phường đang chọn trong danh sách kể cả khi không khớp bộ lọc, để không "mất" lựa chọn.
  const selected = props.wards.find((w) => w.code === model.value)
  return selected && !matched.includes(selected) ? [selected, ...matched] : matched
})

const describedBy = computed(() => (props.error ? `${id}-error` : undefined))
</script>

<template>
  <div class="field ward-select" :class="{ 'field--invalid': error }">
    <label :for="id">{{ label }}<span v-if="required" class="field__required" aria-hidden="true"> *</span></label>
    <input
      v-model="filter"
      type="search"
      class="ward-select__filter"
      :placeholder="`Gõ để lọc ${wards.length} phường/xã`"
      :aria-label="`Lọc danh sách — ${label}`"
      :disabled="disabled"
    />
    <select
      :id="id"
      v-model="model"
      :required="required"
      :disabled="disabled"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="describedBy"
    >
      <option value="" disabled>{{ options.length ? 'Chọn phường/xã' : 'Không có phường/xã phù hợp' }}</option>
      <option v-for="w in options" :key="w.code" :value="w.code">{{ w.name }}</option>
    </select>
    <p v-if="error" :id="`${id}-error`" class="field__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.ward-select__filter { font: inherit; padding: 8px 10px; border: 1px solid var(--border-strong); border-radius: 8px; }
</style>
