<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索标题/编号" clearable style="width:170px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:130px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:120px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.module_id" placeholder="模块" clearable filterable style="width:120px" @change="load">
          <el-option v-for="m in queryModules" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-select v-model="query.severity" placeholder="严重等级" clearable style="width:110px" @change="load">
          <el-option v-for="s in options.severity" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width:130px" @change="load">
          <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增BUG</el-button>
        <el-button :disabled="!selected.length" @click="shareBugs">分享选中</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe @selection-change="onSelect">
      <el-table-column type="selection" width="42" />
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
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑BUG' : '新增BUG'" width="780px" top="6vh">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="项目" required>
            <el-select v-model="form.project_id" style="width:100%" filterable @change="loadFormVersions">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="版本名称" required>
            <el-select v-model="form.version_id" style="width:100%" filterable placeholder="选择版本名称" @change="loadFormModules">
              <el-option v-for="v in formVersions" :key="v.id" :label="v.name || v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="版本">
            <el-select v-model="form.version_id" disabled style="width:100%" placeholder="选版本名称后自动带出">
              <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="模块">
            <el-select v-model="form.module_id" style="width:100%" clearable filterable>
              <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="发现阶段">
            <el-select v-model="form.found_stage" style="width:100%">
              <el-option v-for="s in options.stage" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="严重等级">
            <el-select v-model="form.severity" style="width:100%">
              <el-option v-for="s in options.severity" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%">
              <el-option v-for="s in options.status" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="经办人">
            <el-select v-model="form.assignee" filterable clearable style="width:100%" placeholder="选择用户">
              <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="修复人">
            <el-select v-model="form.fixer" filterable clearable style="width:100%" placeholder="选择用户">
              <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="复现步骤">
          <RichEditor v-model="form.steps" />
        </el-form-item>
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
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'
import RichEditor from '../../components/RichEditor.vue'

const route = useRoute()

const { isAdmin } = useAdmin()
const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const users = ref([]); const options = ref({ severity: [], status: [], stage: [] })
const formVersions = ref([]); const formModules = ref([]); const queryModules = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', module_id: '', severity: '', status: '', found_stage: '', assignee: '' })
const form = ref({})
const selected = ref([])

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
async function openDialog(row) {
  form.value = row
    ? { ...row, module_id: row.module_id || null }
    : { title: '', severity: '一般', status: '待处理', found_stage: '第一轮测试', project_id: '', version_id: '', module_id: null, assignee: '', fixer: '', steps: '', remark: '' }
  if (row) await fillFormOptions()
  else { formVersions.value = []; formModules.value = [] }
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
function onSelect(rows) { selected.value = rows }
async function shareBugs() {
  if (!selected.value.length) return ElMessage.warning('请先勾选要分享的 BUG')
  const res = await request.post('/shares', { bug_ids: selected.value.map(b => b.id) })
  const url = `${window.location.origin}/share/${res.token}`
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success(res.expires_at ? `分享链接已复制，有效至 ${res.expires_at}` : '分享链接已复制到剪贴板')
  } catch {
    await ElMessageBox.alert(url, '分享链接（请手动复制）', { confirmButtonText: '知道了' })
  }
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  users.value = await request.get('/users/all')
  options.value = await request.get('/bugs/options')
  const q = route.query || {}
  const keys = ['project_id', 'version_id', 'module_id']
  keys.forEach((k) => { if (q[k]) query.value[k] = Number(q[k]) })
  ;['severity', 'status', 'found_stage', 'assignee', 'keyword'].forEach((k) => { if (q[k]) query.value[k] = q[k] })
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
