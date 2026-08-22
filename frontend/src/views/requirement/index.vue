<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="搜索需求名称/编号" clearable style="width:200px" @keyup.enter="load" />
      <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:150px" @change="onProjectChange">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:140px" @change="load">
        <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
      </el-select>
      <el-select v-model="query.status" placeholder="状态" clearable style="width:120px" @change="load">
        <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openDialog()">新增需求</el-button>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="req_no" label="编号" width="100" />
      <el-table-column prop="name" label="需求名称" min-width="180" />
      <el-table-column prop="product_name" label="产品" width="90" />
      <el-table-column prop="project_name" label="项目" width="130" />
      <el-table-column prop="version_name" label="版本" width="90" />
      <el-table-column prop="module_name" label="模块" width="100" />
      <el-table-column prop="priority" label="优先级" width="80">
        <template #default="{ row }"><el-tag :type="prioType(row.priority)" size="small">{{ row.priority }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }"><el-tag size="small">{{ row.status }}</el-tag></template>
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

    <el-dialog v-model="dialog" :title="form.id ? '编辑需求' : '新增需求'" width="540px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="需求名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="产品姓名"><el-input v-model="form.product_name" /></el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable @change="loadFormVersions">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本" required>
          <el-select v-model="form.version_id" style="width:100%" filterable @change="loadFormModules">
            <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" style="width:100%" clearable filterable>
            <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级"><el-select v-model="form.priority" style="width:100%">
          <el-option v-for="s in options.priority" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width:100%">
          <el-option v-for="s in options.status" :key="s" :label="s" :value="s" /></el-select></el-form-item>
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

const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const options = ref({ status: [], priority: [] })
const formVersions = ref([]); const formModules = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', status: '' })
const form = ref({})

function prioType(p) { return { P0: 'danger', P1: 'warning', P2: 'primary', P3: 'info' }[p] || '' }
async function load() {
  loading.value = true
  try { const res = await request.get('/requirements', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function loadFormVersions() {
  form.value.version_id = ''; form.value.module_id = ''
  formVersions.value = await request.get('/versions/all', { params: { project_id: form.value.project_id } })
}
async function loadFormModules() {
  form.value.module_id = ''
  formModules.value = await request.get('/modules/all', { params: { project_id: form.value.project_id } })
}
async function openDialog(row) {
  form.value = row ? { ...row } : { name: '', product_name: '', project_id: '', version_id: '', module_id: null, priority: 'P2', status: '待开发' }
  if (row) { await loadFormVersions(); await loadFormModules() }
  dialog.value = true
}
async function save() {
  if (!form.value.name || !form.value.project_id || !form.value.version_id) return ElMessage.warning('名称/项目/版本必填')
  if (form.value.id) await request.put(`/requirements/${form.value.id}`, form.value)
  else await request.post('/requirements', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除需求「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/requirements/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  options.value = await request.get('/requirements/options')
  load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
