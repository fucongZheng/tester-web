<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="搜索版本号/名称" clearable style="width:200px" @keyup.enter="load" />
      <el-select v-model="query.project_id" placeholder="所属项目" clearable filterable style="width:180px" @change="load">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openDialog()">新增版本</el-button>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="version_no" label="版本号" width="120" />
      <el-table-column prop="name" label="版本名称" min-width="140" />
      <el-table-column prop="project_name" label="所属项目" width="150" />
      <el-table-column prop="start_date" label="开始时间" width="110" />
      <el-table-column prop="launch_date" label="上线时间" width="110" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pager" background layout="total, prev, pager, next" :total="total"
      :page-size="query.size" :current-page="query.page" @current-change="(p) => { query.page = p; load() }" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑版本' : '新增版本'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="版本号" required><el-input v-model="form.version_no" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable>
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间"><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="上线时间"><el-date-picker v-model="form.launch_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width:100%">
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const projects = ref([])
const statuses = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '' })
const form = ref({})

function statusType(s) {
  return { 已上线: 'success', 已归档: 'info', 测试中: 'warning', 开发中: 'primary', 规划中: '' }[s] || ''
}
async function load() {
  loading.value = true
  try {
    const res = await request.get('/versions', { params: query.value })
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}
function openDialog(row) {
  form.value = row ? { ...row } : { version_no: '', name: '', project_id: '', start_date: '', launch_date: '', status: '规划中', remark: '' }
  dialog.value = true
}
async function save() {
  if (!form.value.version_no || !form.value.project_id) return ElMessage.warning('版本号和项目必填')
  if (form.value.id) await request.put(`/versions/${form.value.id}`, form.value)
  else await request.post('/versions', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除版本「${row.version_no}」？`, '提示', { type: 'warning' })
  await request.delete(`/versions/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  statuses.value = await request.get('/versions/statuses')
  load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
