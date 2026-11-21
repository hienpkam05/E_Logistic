// API xác thực và hồ sơ (specs/002-xac-thuc/api.md).
import { http } from './http'

const session = { skipSessionHandlers: true }

export const fetchCsrf = () => http.get('/accounts/auth/csrf/', session)
export const login = (username, password) => http.post('/accounts/auth/login/', { username, password }, session)
export const logout = () => http.post('/accounts/auth/logout/', undefined, session)
export const getMe = () => http.get('/accounts/me/', session)
export const updateMe = (data) => http.patch('/accounts/me/', data)
export const changePassword = ({ currentPassword, newPassword, newPasswordConfirm }) =>
  http.post('/accounts/me/password/', {
    current_password: currentPassword,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
