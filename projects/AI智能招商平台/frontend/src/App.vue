<template>
  <el-container style="height: 100vh;">
    <el-aside width="220px" v-if="isLoggedIn"><AsideMenu /></el-aside>
    <el-container>
      <el-header height="60px"><HeaderBar /></el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from './store/auth'
import AsideMenu from '@/components/AsideMenu.vue'
import HeaderBar from '@/components/HeaderBar.vue'
const authStore = useAuthStore()
const isLoggedIn = computed(() => !!authStore.token)
</script>
