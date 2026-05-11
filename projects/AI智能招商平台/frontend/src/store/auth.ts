import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('')
  const userInfo = ref<any>(null)
  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    return res
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  function init() {
    const saved = localStorage.getItem('token')
    if (saved) token.value = saved
  }

  return { token, userInfo, isLoggedIn, login, logout, init }
})
