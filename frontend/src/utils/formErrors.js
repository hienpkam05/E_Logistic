// Tách lỗi API (ApiError) thành lỗi theo trường và thông điệp chung cho form.

/** { tenTruong: 'thông điệp 1 thông điệp 2' } từ err.fields của backend. */
export function fieldErrors(err) {
  const result = {}
  for (const [name, messages] of Object.entries(err?.fields ?? {})) {
    if (name === 'non_field_errors') continue
    result[name] = Array.isArray(messages) ? messages.join(' ') : String(messages)
  }
  return result
}

/**
 * Thông điệp hiển thị đầu form. Có lỗi theo trường thì trả thông điệp chung của backend
 * ("Dữ liệu chưa hợp lệ.") kèm non_field_errors nếu có.
 */
export function generalMessage(err) {
  if (!err) return ''
  const nonField = err.fields?.non_field_errors
  if (Array.isArray(nonField) && nonField.length) return nonField.join(' ')
  return err.message || ''
}
