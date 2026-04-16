import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Sessions
export const createSession  = (config)     => api.post('/sessions', { config })
export const listSessions   = ()           => api.get('/sessions')
export const getSession     = (id)         => api.get(`/sessions/${id}`)
export const deleteSession  = (id)         => api.delete(`/sessions/${id}`)
export const startSession   = (id)         => api.post(`/sessions/${id}/start`)
export const stopSession    = (id)         => api.post(`/sessions/${id}/stop`)

// Files
export const uploadFile = (sessionId, file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/sessions/${sessionId}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const removeFile = (sessionId, filename) =>
  api.delete(`/sessions/${sessionId}/files/${encodeURIComponent(filename)}`)

// Graph
export const getGraph   = (id) => api.get(`/sessions/${id}/graph`)
export const getMetrics = (id) => api.get(`/sessions/${id}/metrics`)

// Custom domain
export const advancePhase  = (id)          => api.post(`/sessions/${id}/advance`)
export const chatQuery     = (id, message) => api.post(`/sessions/${id}/chat`, { message })
export const aeroChatQuery = (id, message) => api.post(`/sessions/${id}/aero-chat`, { message })

// Status
export const getStatus  = () => api.get('/status')

export default api
