<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-select v-model="project_id" placeholder="项目" clearable filterable style="width:170px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="genDialog = true">一键生成报告</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="report_no" label="编号" width="100" />
      <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目" width="150" />
      <el-table-column prop="version_no" label="版本" width="90" />
      <el-table-column prop="method" label="方式" width="70">
        <template #default="{ row }"><el-tag size="small" type="primary">{{ row.method }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="generator" label="生成人" width="90" />
      <el-table-column prop="created_at" label="生成时间" width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="view(row)">查看</el-button>
          <el-button link type="success" @click="exportDocx(row)">导出</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="page" v-model:size="size" :total="total" @update:page="load" @update:size="load" />

    <!-- 生成 -->
    <el-dialog v-model="genDialog" title="一键生成测试报告" width="460px">
      <el-form label-width="80px">
        <el-form-item label="项目" required>
          <el-select v-model="genForm.project_id" style="width:100%" filterable @change="loadGenVersions">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select>
        </el-form-item>
        <el-form-item label="版本名称" required>
          <el-select v-model="genForm.version_id" style="width:100%" filterable placeholder="选择版本名称" @change="loadGenModules">
            <el-option v-for="v in genVersions" :key="v.id" :label="v.name || v.version_no" :value="v.id" /></el-select>
        </el-form-item>
        <el-form-item label="版本">
          <el-select v-model="genForm.version_id" disabled style="width:100%" placeholder="选版本名称后自动带出">
            <el-option v-for="v in genVersions" :key="v.id" :label="v.version_no" :value="v.id" /></el-select>
        </el-form-item>
        <el-form-item label="模块" required>
          <el-select v-model="genForm.module_ids" multiple filterable style="width:100%" placeholder="根据版本带出，可多选">
            <el-option v-for="m in genModules" :key="m.id" :label="m.name" :value="m.id" /></el-select>
        </el-form-item>
        <el-form-item label="标题"><el-input v-model="genForm.title" placeholder="留空自动生成" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="genDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="doGenerate">生成</el-button>
      </template>
    </el-dialog>

    <!-- 预览 -->
    <el-dialog v-model="viewDialog" :title="viewReport.title" width="820px" top="5vh">
      <div class="md-preview" v-html="rendered"></div>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import request from '../../api/request'
import { renderMarkdown } from '../../utils/sanitize'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const items = ref([]); const total = ref(0); const loading = ref(false)
const projects = ref([]); const project_id = ref('')
const page = ref(1); const size = ref(10)
const genDialog = ref(false); const generating = ref(false)
const genForm = ref({ project_id: '', version_id: '', module_ids: [], title: '' })
const genVersions = ref([]); const genModules = ref([])
const viewDialog = ref(false); const viewReport = ref({}); const rendered = ref('')

async function load() {
  loading.value = true
  try {
    const res = await request.get('/reports', { params: { project_id: project_id.value, page: page.value, size: size.value } })
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}
async function onProjectChange() { load() }
async function loadGenVersions() {
  genForm.value.version_id = ''
  genForm.value.module_ids = []
  genVersions.value = await request.get('/versions/all', { params: { project_id: genForm.value.project_id } })
  genModules.value = []
}
async function loadGenModules() {
  genForm.value.module_ids = []
  genModules.value = genForm.value.project_id
    ? await request.get('/modules/all', { params: { project_id: genForm.value.project_id } })
    : []
}
async function doGenerate() {
  if (!genForm.value.project_id || !genForm.value.version_id) return ElMessage.warning('项目和版本必填')
  if (!genForm.value.module_ids?.length) return ElMessage.warning('模块必填')
  generating.value = true
  try {
    await request.post('/reports/generate', genForm.value)
    ElMessage.success('报告已根据系统数据生成')
    genDialog.value = false
    genForm.value = { project_id: '', version_id: '', module_ids: [], title: '' }
    genVersions.value = []; genModules.value = []
    load()
  } finally { generating.value = false }
}
async function view(row) {
  const res = await request.get(`/reports/${row.id}`)
  viewReport.value = res
  rendered.value = renderMarkdown(res.content || '')
  viewDialog.value = true
}
async function exportDocx(row) {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await axios.get(`/api/reports/${row.id}/export`, {
      responseType: 'blob',
      headers: { Authorization: token ? `Bearer ${token}` : '' },
    })
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.title || row.report_no || '测试报告'}.docx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导出失败')
  }
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除报告「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/reports/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => { projects.value = await request.get('/projects/all'); load() })
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.md-preview { max-height: 70vh; overflow: auto; padding: 8px; line-height: 1.7; }
.md-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
.md-preview :deep(th), .md-preview :deep(td) { border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; }
.md-preview :deep(th) { background: #f5f7fa; }
.md-preview :deep(h2) { margin: 16px 0 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
</style>
