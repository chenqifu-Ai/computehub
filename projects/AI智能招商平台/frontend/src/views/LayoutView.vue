<template>
  <el-container>
    <el-aside width="220px">
      <div class="logo">🤖 AI招商平台</div>
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon><span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/brand">
          <el-icon><Memo /></el-icon><span>品牌管理</span>
        </el-menu-item>
        <el-menu-item index="/product">
          <el-icon><Goods /></el-icon><span>产品管理</span>
        </el-menu-item>
        <el-menu-item index="/qa">
          <el-icon><ChatDotRound /></el-icon><span>问答管理</span>
        </el-menu-item>
        <el-menu-item index="/device">
          <el-icon><Monitor /></el-icon><span>设备管理</span>
        </el-menu-item>
        <el-menu-item index="/user">
          <el-icon><User /></el-icon><span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="page-title">{{ pageTitle }}</span>
        <span class="user-info">{{ authStore.userInfo?.real_name || '管理员' }}</span>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
const route = useRoute()
const authStore = useAuthStore()
const pageTitle = computed(() => {
  const map: Record<string, string> = { '/dashboard':'数据看板', '/brand':'品牌管理', '/product':'产品管理', '/qa':'问答管理', '/device':'设备管理', '/user':'用户管理' }
  return map[route.path] || 'AI招商平台'
})
</script>
<style scoped>
.logo { height:60px; line-height:60px; text-align:center; font-size:18px; background:#001529; color:#fff }
.header { display:flex; align-items:center; justify-content:space-between; background:#fff; border-bottom:1px solid #eee }
.page-title { font-size:16px; font-weight:bold }
.user-info { color:#666 }
</style>
