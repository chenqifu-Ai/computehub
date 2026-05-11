<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6" v-for="card in statCards" :key="card.title">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" :style="{ background: card.color }">{{ icon }}</div>
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.title }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card><h3>设备在线分布</h3><div class="placeholder-chart">图表区域</div></el-card>
      </el-col>
      <el-col :span="12">
        <el-card><h3>查询热度TOP10</h3><div class="placeholder-chart">图表区域</div></el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup lang="ts">
const statCards = [
  { title: '在线设备', value: '128', color: '#409EFF' },
  { title: '今日查询', value: '2,456', color: '#67C23A' },
  { title: '今日发布', value: '3', color: '#E6A23C' },
  { title: '活跃门店', value: '89', color: '#F56C6C' },
]
</script>
<style scoped>
.stat-card { text-align:center; padding:10px }
.stat-icon { width:48px; height:48px; border-radius:50%; margin:0 auto 10px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:20px }
.stat-value { font-size:28px; font-weight:bold; color:#333 }
.stat-label { color:#999; margin-top:5px }
.placeholder-chart { height:250px; background:#f5f7fa; display:flex; align-items:center; justify-content:center; color:#ccc; border-radius:4px }
</style>
