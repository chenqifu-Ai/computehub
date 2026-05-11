import axios from 'axios'
import { useAuthStore } from '@/store/auth'

const http = axios.create({ baseURL: '/api/v1', timeout: 15000, headers: { 'Content-Type': 'application/json' } })

http.interceptors.request.use((config) => {
  const store = useAuthStore()
  if (store.token) config.headers.Authorization = `Bearer ${store.token}`
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) { useAuthStore().logout(); window.location.href = '/login' }
    return Promise.reject(error)
  }
)

export default http
