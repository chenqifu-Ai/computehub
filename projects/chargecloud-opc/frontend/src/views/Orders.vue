<template>
  <div class="orders">
    <el-card>
      <template #header>订单管理</template>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="订单号">
          <el-input v-model="searchForm.orderNo" placeholder="请输入订单号" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable>
            <el-option label="充电中" :value="1" />
            <el-option label="已完成" :value="2" />
            <el-option label="已取消" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="searchForm.date" type="daterange" range-separator="-" start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" style="width: 100%">
        <el-table-column prop="orderNo" label="订单号" width="150" />
        <el-table-column prop="userName" label="用户" />
        <el-table-column prop="stationName" label="站点" />
        <el-table-column prop="pileName" label="充电桩" />
        <el-table-column prop="energy" label="充电量(度)">
          <template #default="{ row }">{{ row.energy }}度</template>
        </el-table-column>
        <el-table-column prop="amount" label="金额">
          <template #default="{ row }">¥{{ row.amount }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status].type">{{ statusMap[row.status].label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="160" />
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const searchForm = reactive({ orderNo: '', status: null, date: [] })
const pagination = reactive({ page: 1, size: 20, total: 500 })

const statusMap = {
  1: { label: '充电中', type: 'primary' },
  2: { label: '已完成', type: 'success' },
  3: { label: '已取消', type: 'info' }
}

const tableData = ref([
  { orderNo: 'C202603210001', userName: '用户1', stationName: '朝阳充电站', pileName: '1号桩', energy: 45.5, amount: 91.00, status: 2, createdAt: '2026-03-21 10:00' },
  { orderNo: 'C202603210002', userName: '用户2', stationName: '海淀充电站', pileName: '2号桩', energy: 32.0, amount: 64.00, status: 2, createdAt: '2026-03-21 10:30' },
  { orderNo: 'C202603210003', userName: '用户3', stationName: '朝阳充电站', pileName: '3号桩', energy: 28.5, amount: 57.00, status: 1, createdAt: '2026-03-21 11:00' }
])

const handleSearch = () => ElMessage.success('查询成功')
const handleReset = () => { searchForm.orderNo = ''; searchForm.status = null; searchForm.date = [] }
</script>

<style scoped>
.search-form { margin-bottom: 20px; }
</style>