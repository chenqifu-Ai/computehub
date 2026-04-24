<template>
  <div class="users">
    <el-card>
      <template #header>用户管理</template>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="手机号">
          <el-input v-model="searchForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="searchForm.level" placeholder="请选择" clearable>
            <el-option label="普通用户" :value="1" />
            <el-option label="VIP用户" :value="2" />
            <el-option label="企业用户" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="nickname" label="昵称" />
        <el-table-column prop="balance" label="余额">
          <template #default="{ row }">¥{{ row.balance }}</template>
        </el-table-column>
        <el-table-column prop="level" label="等级">
          <template #default="{ row }">
            <el-tag :type="levelMap[row.level].type">{{ levelMap[row.level].label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="注册时间" />
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

const searchForm = reactive({ phone: '', level: null })
const pagination = reactive({ page: 1, size: 20, total: 1000 })

const levelMap = {
  1: { label: '普通用户', type: '' },
  2: { label: 'VIP用户', type: 'warning' },
  3: { label: '企业用户', type: 'success' }
}

const tableData = ref([
  { id: 1, phone: '138****8001', nickname: '用户1', balance: 100.00, level: 1, status: 1, createdAt: '2026-01-01' },
  { id: 2, phone: '138****8002', nickname: '用户2', balance: 500.00, level: 2, status: 1, createdAt: '2026-01-15' },
  { id: 3, phone: '138****8003', nickname: '用户3', balance: 1000.00, level: 3, status: 1, createdAt: '2026-02-01' }
])

const handleSearch = () => ElMessage.success('查询成功')
const handleReset = () => { searchForm.phone = ''; searchForm.level = null }
</script>

<style scoped>
.search-form { margin-bottom: 20px; }
</style>