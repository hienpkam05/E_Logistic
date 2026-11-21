import { http } from './http'

// GET /api/v1/meta/choices/ — enum và giới hạn nghiệp vụ (specs/001-nen-tang/api.md).
export const getChoices = (options) => http.get('/meta/choices/', options)
