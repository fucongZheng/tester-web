<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索需求名称/编号" clearable style="width:200px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:150px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:140px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.module_id" placeholder="模块" clearable filterable style="width:130px" @change="load">
          <el-option v-for="m in queryModules" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width:120px" @change="load">
          <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button :loading="syncing" @click="syncFromXuqiu">从 xuqiu 同步</el-button>
        <el-button type="primary" @click="openDialog()">新增需求</el-button>
      </div>
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
      <el-table-column label="附件" width="90">
        <template #default="{ row }">
          <span v-if="(row.attachments || []).length">{{ row.attachments.length }} 个</span>
          <span v-else style="color:#c0c4cc">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑需求' : '新增需求'" width="720px" top="6vh">
      <el-form :model="form" label-width="80px">
        <el-form-item label="需求名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="产品">
          <el-select v-model="form.product_name" filterable clearable style="width:100%" placeholder="选择用户">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
          </el-select>
        </el-form-item>
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
        <el-form-item label="需求内容">
          <RichEditor v-model="form.content" />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            action="/api/uploads"
            :headers="uploadHeaders"
            :on-success="onUploadSuccess"
            :on-remove="onUploadRemove"
            :file-list="fileList"
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip"
            multiple
          >
            <el-button type="primary" plain>上传附件</el-button>
            <template #tip><div class="el-upload__tip">图片/文档/压缩包，单文件不超过 20MB</div></template>
          </el-upload>
        </el-form-item>
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
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'
import RichEditor from '../../components/RichEditor.vue'

const { isAdmin } = useAdmin()
const route = useRoute()

const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const users = ref([]); const options = ref({ status: [], priority: [] })
const formVersions = ref([]); const formModules = ref([]); const queryModules = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', module_id: '', status: '' })
const form = ref({})
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
const fileList = ref([])

function prioType(p) { return { P0: 'danger', P1: 'warning', P2: 'primary', P3: 'info' }[p] || '' }

/* 从 xuqiu 需求系统同步：拉取全量需求，幂等 upsert（本地状态/优先级/模块不动） */
const syncing = ref(false)
async function syncFromXuqiu() {
  syncing.value = true
  try {
    const res = await request.post('/sync/run')
    const parts = [`新增 ${res.created_count}`, `更新 ${res.updated_count}`, `无变化 ${res.skipped_count}`]
    if (res.cases_count) parts.push(`AI 生成用例 ${res.cases_count} 条`)
    if (res.missing_count) parts.push(`源已删除 ${res.missing_count}`)
    if (res.failed_count) parts.push(`失败 ${res.failed_count}`)
    ElMessage.success(`同步完成：${parts.join('，')}`)
    load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '同步失败，请确认 xuqiu 服务已启动')
  } finally {
    syncing.value = false
  }
}
async function load() {
  loading.value = true
  try { const res = await request.get('/requirements', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''; query.value.module_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  queryModules.value = query.value.project_id ? await request.get('/modules/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function loadFormVersions() {
  form.value.version_id = ''; form.value.module_id = null
  formVersions.value = form.value.project_id
    ? await request.get('/versions/all', { params: { project_id: form.value.project_id } })
    : []
  formModules.value = []
}
async function loadFormModules() {
  form.value.module_id = null
  formModules.value = form.value.project_id
    ? await request.get('/modules/all', { params: { project_id: form.value.project_id } })
    : []
}
async function fillFormOptions() {
  if (!form.value.project_id) { formVersions.value = []; formModules.value = []; return }
  formVersions.value = await request.get('/versions/all', { params: { project_id: form.value.project_id } })
  formModules.value = await request.get('/modules/all', { params: { project_id: form.value.project_id } })
}
function toFileList(list) {
  return (list || []).map((f) => ({ name: f.name, url: f.url, response: f }))
}
function onUploadSuccess(res, file) {
  if (res && res.url) {
    form.value.attachments = [...(form.value.attachments || []), { name: res.name || file.name, url: res.url, size: res.size }]
  }
}
function onUploadRemove(file) {
  const url = file.response?.url || file.url
  form.value.attachments = (form.value.attachments || []).filter((a) => a.url !== url)
}
async function openDialog(row) {
  form.value = row
    ? { ...row, module_id: row.module_id || null, attachments: [...(row.attachments || [])] }
    : { name: '', content: '', product_name: '', project_id: '', version_id: '', module_id: null, priority: 'P2', status: '待开发', attachments: [] }
  fileList.value = toFileList(form.value.attachments)
  if (row) await fillFormOptions()
  else { formVersions.value = []; formModules.value = [] }
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
  users.value = await request.get('/users/all')
  options.value = await request.get('/requirements/options')
  const q = route.query || {}
  if (q.project_id) query.value.project_id = Number(q.project_id)
  if (q.version_id) query.value.version_id = Number(q.version_id)
  if (q.module_id) query.value.module_id = Number(q.module_id)
  if (q.keyword) query.value.keyword = q.keyword
  if (query.value.project_id) {
    versions.value = await request.get('/versions/all', { params: { project_id: query.value.project_id } })
    queryModules.value = await request.get('/modules/all', { params: { project_id: query.value.project_id } })
  }
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
