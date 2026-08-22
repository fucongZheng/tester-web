<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="搜索标题/编号" clearable style="width:170px" @keyup.enter="load" />
      <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:130px" @change="onProjectChange">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:120px" @change="load">
        <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
      </el-select>
      <el-select v-model="query.severity" placeholder="严重等级" clearable style="width:110px" @change="load">
        <el-option v-for="s in options.severity" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="query.status" placeholder="状态" clearable style="width:130px" @change="load">
        <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openDialog()">新增BUG</el-button>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="bug_no" label="编号" width="90" />
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="severity" label="严重等级" width="90">
        <template #default="{ row }"><el-tag :type="sevType(row.severity)" size="small">{{ row.severity }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="130">
        <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="module_name" label="模块" width="90" />
      <el-table-column prop="project_name" label="项目" width="120" />
      <el-table-column prop="version_name" label="版本" width="80" />
      <el-table-column prop="found_stage" label="发现阶段" width="100" />
      <el-table-column prop="submitter" label="提交人" width="80" />
      <el-table-column prop="assignee" label="经办人" width="80" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pager" background layout="total, prev, pager, next" :total="total"
      :page-size="query.size" :current-page="query.page" @current-change="(p) => { query.page = p; load() }" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑BUG' : '新增BUG'" width="640px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="项目" required>
            <el-select v-model="form.project_id" style="width:100%" filterable @change="loadFormVersions">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="版本" required>
            <el-select v-model="form.version_id" style="width:100%" filterable @change="loadFormModules">
              <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="模块">
            <el-select v-model="form.module_id" style="width:100%" clearable filterable>
              <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="发现阶段">
            <el-select v-model="form.found_stage" style="width:100%">
              <el-option v-for="s in options.stage" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="严重等级">
            <el-select v-model="form.severity" style="width:100%">
              <el-option v-for="s in options.severity" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%">
              <el-option v-for="s in options.status" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="经办人"><el-input v-model="form.assignee" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="修复人"><el-input v-model="form.fixer" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
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
const projects = ref([]); const versions = ref([]); const options = ref({ severity: [], status: [], stage: [] })
const formVersions = ref([]); const formModules = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', severity: '', status: '' })
const form = ref({})

function sevType(s) { return { 致命: 'danger', 严重: 'warning', 一般: 'primary', 轻微: 'info', 建议: 'success' }[s] || '' }
function statusType(s) {
  return { 待处理: 'danger', 处理中: 'warning', 已修复未发版: 'primary', 已修复已发版: 'success', 不是BUG: 'info', 测试验证通过关闭: 'success' }[s] || ''
}
async function load() {
  loading.value = true
  try { const res = await request.get('/bugs', { params: query.value }); items.value = res.items; total.value = res.total }
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
  form.value = row ? { ...row } : { title: '', severity: '一般', status: '待处理', found_stage: '第一轮测试', project_id: '', version_id: '', module_id: null, assignee: '', fixer: '', remark: '' }
  if (row) { await loadFormVersions(); await loadFormModules() }
  dialog.value = true
}
async function save() {
  if (!form.value.title || !form.value.project_id || !form.value.version_id) return ElMessage.warning('标题/项目/版本必填')
  if (form.value.id) await request.put(`/bugs/${form.value.id}`, form.value)
  else await request.post('/bugs', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除BUG「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/bugs/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  options.value = await request.get('/bugs/options')
  load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
