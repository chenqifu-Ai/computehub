<template>
  <div class="piles">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>充电桩管理</span>
          <el-button type="primary" @click="handleAdd">新增充电桩</el-button>
        </div>
      </template>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="站点">
          <el-select v-model="searchForm.stationId" placeholder="请选择站点" clearable>
            <el-option label="朝阳充电站" :value="1" />
            <el-option label="海淀充电站" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable>
            <el-option label="空闲" :value="1" />
            <el-option label="充电中" :value="2" />
            <el-option label="离线" :value="3" />
            <el-option label="故障" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="code" label="编号" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="stationName" label="所属站点" />
        <el-table-column prop="type" label="类型">
          <template #default="{ row }">
            <el-tag :type="row.type === 1 ? 'primary' : 'info'">
              {{ row.type === 1 ? '快充' : '慢充' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="power" label="功率(kW)" />
        <el-table-column prop="price" label="电价(元/度)" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status].type">
              {{ statusMap[row.status].label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
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
import { ElMessage, ElMessageBox } from 'element-plus'

const searchForm = reactive({ stationId: null, status: null })
const pagination = reactive({ page: 1, size: 20, total: 50 })

const statusMap = {
  1: { label: '空闲', type: 'success' },
  2: { label: '充电中', type: 'primary' },
  3: { label: '离线', type: 'info' },
  4: { label: '故障', type: 'danger' }
}

const tableData = ref([
  { id: 1, code: 'P001', name: '1号充电桩', stationName: '朝阳充电站', type: 1, power: 120, price: 1.20, status: 1 },
  { id: 2, code: 'P002', name: '2号充电桩', stationName: '朝阳充电站', type: 1, power: 120, price: 1.20, status: 2 },
  { id: 3, code: 'P003', name: '3号充电桩', stationName: '朝阳充电站', type: 2, power: 7, price: 0.60, status: 1 },
  { id: 4, code: 'P004', name: '4号充电桩', stationName: '海淀充电站', type: 1, power: 120, price: 1.20, status: 3 }
])

const handleSearch = () => ElMessage.success('查询成功')
const handleReset = () => { searchForm.stationId = null; searchForm.status = null }
const handleAdd = () => ElMessage.success('新增功能开发中')
const handleEdit = (row) => ElMessage.success('编辑功能开发中')
const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该充电桩吗？', '提示', { type: 'warning' })
    .then(() => ElMessage.success('删除成功'))
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.search-form { margin-bottom: 20px; }
</style>