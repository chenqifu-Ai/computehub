<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>AI智能招商平台</h2>
      <p class="subtitle">管理后台登录</p>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width:100%" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
async function handleLogin() {
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/dashboard')
  } finally { loading.value = false }
}
</script>
<style scoped>
.login-container { display:flex; justify-content:center; align-items:center; height:100vh; background:linear-gradient(135deg,#667eea,#764ba2) }
.login-card { width:400px; text-align:center; padding:20px }
.login-card h2 { color:#333; margin-bottom:5px }
.subtitle { color:#999; margin-bottom:20px }
</style>
