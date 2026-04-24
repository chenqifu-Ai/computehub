<template>
  <div class="stations">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>充电站管理</span>
          <el-button type="primary" @click="handleAdd">新增站点</el-button>
        </div>
      </template>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="城市">
          <el-input v-model="searchForm.city" placeholder="请输入城市" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable>
            <el-option label="正常" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="站点名称" />
        <el-table-column prop="city" label="城市" />
        <el-table-column prop="address" label="地址" />
        <el-table-column prop="totalPiles" label="充电桩数" />
        <el-table-column prop="availablePiles" label="可用数" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '停用' }}
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="站点名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入站点名称" />
        </el-form-item>
        <el-form-item label="省份" prop="province">
          <el-input v-model="form.province" placeholder="请输入省份" />
        </el-form-item>
        <el-form-item label="城市" prop="city">
          <el-input v-model="form.city" placeholder="请输入城市" />
        </el-form-item>
        <el-form-item label="区县" prop="district">
          <el-input v-model="form.district" placeholder="请输入区县" />
        </el-form-item>
        <el-form-item label="详细地址" prop="address">
          <el-input v-model="form.address" placeholder="请输入详细地址" />
        </el-form-item>
        <el-form-item label="经度" prop="longitude">
          <el-input v-model="form.longitude" placeholder="请输入经度" />
        </el-form-item>
        <el-form-item label="纬度" prop="latitude">
          <el-input v-model="form.latitude" placeholder="请输入纬度" />
        </el-form-item>
        <el-form-item label="停车费" prop="parkingFee">
          <el-input v-model="form.parkingFee" placeholder="元/小时" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const searchForm = reactive({ city: '', status: null })
const pagination = reactive({ page: 1, size: 20, total: 100 })
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref()

const tableData = ref([
  { id: 1, name: '朝阳充电站', city: '北京市', address: '朝阳区xxx路xxx号', totalPiles: 10, availablePiles: 5, status: 1 },
  { id: 2, name: '海淀充电站', city: '北京市', address: '海淀区xxx路xxx号', totalPiles: 8, availablePiles: 6, status: 1 },
  { id: 3, name: '西城充电站', city: '北京市', address: '西城区xxx路xxx号', totalPiles: 12, availablePiles: 10, status: 1 }
])

const form = ref({
  id: null,
  name: '',
  province: '',
  city: '',
  district: '',
  address: '',
  longitude: '',
  latitude: '',
  parkingFee: ''
})

const rules = {
  name: [{ required: true, message: '请输入站点名称', trigger: 'blur' }],
  city: [{ required: true, message: '请输入城市', trigger: 'blur' }],
  address: [{ required: true, message: '请输入详细地址', trigger: 'blur' }]
}

const handleSearch = () => {
  ElMessage.success('查询成功')
}

const handleReset = () => {
  searchForm.city = ''
  searchForm.status = null
}

const handleAdd = () => {
  dialogTitle.value = '新增站点'
  form.value = { id: null, name: '', province: '', city: '', district: '', address: '', longitude: '', latitude: '', parkingFee: '' }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑站点'
  form.value = { ...row }
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该站点吗？', '提示', { type: 'warning' })
    .then(() => {
      ElMessage.success('删除成功')
    })
}

const handleSubmit = async () => {
  await formRef.value.validate()
  dialogVisible.value = false
  ElMessage.success('保存成功')
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-form {
  margin-bottom: 20px;
}
</style>