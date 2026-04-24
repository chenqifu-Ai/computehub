<template>
  <div class="dashboard">
    <h2>数据看板</h2>
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.todayIncome }}</div>
          <div class="stat-label">今日收入（元）</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.todayOrders }}</div>
          <div class="stat-label">今日订单</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.totalStations }}</div>
          <div class="stat-label">充电站</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.onlinePiles }}/{{ stats.totalPiles }}</div>
          <div class="stat-label">在线充电桩</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>最近订单</template>
          <el-table :data="recentOrders" style="width: 100%">
            <el-table-column prop="orderNo" label="订单号" width="150" />
            <el-table-column prop="stationName" label="站点" />
            <el-table-column prop="energy" label="充电量(度)" />
            <el-table-column prop="amount" label="金额(元)" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="row.status === 2 ? 'success' : 'primary'">
                  {{ row.status === 1 ? '充电中' : '已完成' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>站点状态</template>
          <el-table :data="stations" style="width: 100%">
            <el-table-column prop="name" label="站点名称" />
            <el-table-column prop="totalPiles" label="充电桩" />
            <el-table-column prop="availablePiles" label="可用" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'danger'">
                  {{ row.status === 1 ? '正常' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref({
  todayIncome: '5,280',
  todayOrders: 128,
  totalStations: 15,
  totalPiles: 150,
  onlinePiles: 142
})

const recentOrders = ref([
  { orderNo: 'C202603210001', stationName: '朝阳充电站', energy: 45.5, amount: 91.00, status: 2 },
  { orderNo: 'C202603210002', stationName: '海淀充电站', energy: 32.0, amount: 64.00, status: 2 },
  { orderNo: 'C202603210003', stationName: '朝阳充电站', energy: 28.5, amount: 57.00, status: 1 },
  { orderNo: 'C202603210004', stationName: '西城充电站', energy: 50.0, amount: 100.00, status: 2 },
  { orderNo: 'C202603210005', stationName: '东城充电站', energy: 15.5, amount: 31.00, status: 2 }
])

const stations = ref([
  { name: '朝阳充电站', totalPiles: 10, availablePiles: 5, status: 1 },
  { name: '海淀充电站', totalPiles: 8, availablePiles: 6, status: 1 },
  { name: '西城充电站', totalPiles: 12, availablePiles: 10, status: 1 },
  { name: '东城充电站', totalPiles: 15, availablePiles: 12, status: 1 }
])
</script>

<style scoped>
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  text-align: center;
  padding: 20px;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #1e3c72;
}
.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 10px;
}
</style>