<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <div class="logo">
        <span class="logo-icon">⚡</span>
        <span class="logo-text">充电云</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1e3c72"
        text-color="#fff"
        active-text-color="#00d2ff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/stations">
          <el-icon><Location /></el-icon>
          <span>充电站管理</span>
        </el-menu-item>
        <el-menu-item index="/piles">
          <el-icon><Connection /></el-icon>
          <span>充电桩管理</span>
        </el-menu-item>
        <el-menu-item index="/orders">
          <el-icon><Document /></el-icon>
          <span>订单管理</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-right">
          <el-dropdown>
            <span class="el-dropdown-link">
              管理员 <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { DataAnalysis, Location, Connection, Document, User, ArrowDown } from '@element-plus/icons-vue'

const router = useRouter()

const logout = () => {
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100%;
}
.el-aside {
  background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: bold;
}
.logo-icon {
  font-size: 28px;
  margin-right: 8px;
}
.el-header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
}
.header-right {
  display: flex;
  align-items: center;
}
.el-dropdown-link {
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>