<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索标题/编号" clearable style="width:180px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:140px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="版本名称" clearable filterable style="width:140px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.name || v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="选版本名称后自动带出" disabled filterable style="width:140px">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.module_id" placeholder="模块" clearable filterable style="width:120px" @change="load">
          <el-option v-for="m in queryModules" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-select v-model="query.case_type" placeholder="类型" clearable style="width:110px" @change="load">
          <el-option v-for="s in options.case_type" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增用例</el-button>
        <el-button @click="openImportDialog">导入用例</el-button>
        <el-button @click="openAiDialog">AI生成用例</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="case_no" label="编号" width="90" />
      <el-table-column prop="title" label="用例标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="case_type" label="类型" width="80">
        <template #default="{ row }"><el-tag size="small" type="info">{{ row.case_type }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="80">
        <template #default="{ row }"><el-tag :type="prioType(row.priority)" size="small">{{ row.priority }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目" width="120" />
      <el-table-column prop="version_name" label="版本" width="80" />
      <el-table-column prop="version_label" label="版本名称" width="110" show-overflow-tooltip />
      <el-table-column prop="module_name" label="模块" width="90" />
      <el-table-column prop="status" label="状态" width="70">
        <template #default="{ row }"><el-tag :type="row.status ? 'success' : 'info'" size="small">{{ row.status ? '启用' : '停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" @click="openExec(row)">执行</el-button>
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <!-- AI 生成 -->
    <el-dialog v-model="aiDialog" :title="aiStep === 1 ? 'AI生成用例' : `预览用例（${aiCases.length}）`" width="920px" top="6vh" :close-on-click-modal="false" @closed="resetAi">
      <el-form v-if="aiStep === 1" :model="aiForm" label-width="90px">
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="项目" required>
            <el-select v-model="aiForm.project_id" style="width:100%" filterable @change="loadAiVersions">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="版本名称" required>
            <el-select v-model="aiForm.version_id" style="width:100%" filterable @change="loadAiRelated">
              <el-option v-for="v in aiVersions" :key="v.id" :label="v.name || v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="版本">
            <el-select v-model="aiForm.version_id" disabled style="width:100%" placeholder="选版本名称后自动带出">
              <el-option v-for="v in aiVersions" :key="v.id" :label="v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="模块">
            <el-select v-model="aiForm.module_id" style="width:100%" clearable filterable>
              <el-option v-for="m in aiModules" :key="m.id" :label="m.name" :value="m.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="关联需求">
            <el-select v-model="aiForm.requirement_id" style="width:100%" clearable filterable>
              <el-option v-for="r in aiReqs" :key="r.id" :label="r.name" :value="r.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="生成模式" required>
          <el-radio-group v-model="aiForm.mode">
            <el-radio value="loop">闭环用例（主链路端到端）</el-radio>
            <el-radio value="detail">细节用例（字段级加厚）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="需求内容" required>
          <el-input v-model="aiForm.requirement" type="textarea" :rows="6" placeholder="粘贴或填写需求说明、验收标准、接口约定等" />
        </el-form-item>
        <el-form-item label="附加要求">
          <el-input v-model="aiForm.prompt" type="textarea" :rows="3" placeholder="可选。补充侧重方向，如「重点覆盖支付链路」；主提示词已内置用例设计方法论" />
        </el-form-item>
      </el-form>

      <div v-else>
        <el-alert type="info" :closable="false" show-icon style="margin-bottom:10px"
          :title="`已生成 ${aiCases.length} 条，勾选后保存。同项目同版本下标题重复的会自动跳过。`" />
        <el-table ref="aiTableRef" :data="aiCases" border stripe max-height="460" @selection-change="onAiSelect">
          <el-table-column type="selection" width="42" />
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
          <el-table-column prop="case_type" label="类型" width="80" />
          <el-table-column prop="priority" label="优先级" width="80" />
          <el-table-column prop="precondition" label="前置条件" min-width="140" show-overflow-tooltip />
          <el-table-column prop="steps" label="步骤" min-width="180" show-overflow-tooltip />
          <el-table-column prop="expected" label="预期结果" min-width="140" show-overflow-tooltip />
        </el-table>
      </div>

      <template #footer>
        <template v-if="aiStep === 1">
          <el-button @click="aiDialog = false">取消</el-button>
          <el-button type="primary" :loading="aiGenerating" @click="doAiGenerate">生成</el-button>
        </template>
        <template v-else>
          <el-button @click="aiStep = 1">返回修改</el-button>
          <el-button @click="selectAllAi">全选</el-button>
          <el-button type="primary" :loading="aiSaving" :disabled="!aiSelected.length" @click="saveAiCases">
            保存已选（{{ aiSelected.length }}）
          </el-button>
        </template>
      </template>
    </el-dialog>

    <!-- 导入用例 -->
    <ImportDialog ref="importRef" :projects="projects" @imported="load" />

    <!-- 用例编辑 -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑用例' : '新增用例'" width="640px">
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
          <el-col :span="12"><el-form-item label="关联需求">
            <el-select v-model="form.requirement_id" style="width:100%" clearable filterable>
              <el-option v-for="r in formReqs" :key="r.id" :label="r.name" :value="r.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="类型"><el-select v-model="form.case_type" style="width:100%">
            <el-option v-for="s in options.case_type" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="优先级"><el-select v-model="form.priority" style="width:100%">
            <el-option v-for="s in options.priority" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="前置条件"><el-input v-model="form.precondition" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="操作步骤"><el-input v-model="form.steps" type="textarea" :rows="3" placeholder="每步一行" /></el-form-item>
        <el-form-item label="预期结果"><el-input v-model="form.expected" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.status" :active-value="1" :inactive-value="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 执行记录 -->
    <el-dialog v-model="execDialog" :title="`执行：${execCase.title || ''}`" width="700px">
      <el-descriptions :column="1" border size="small" class="case-info">
        <el-descriptions-item label="前置条件">
          <pre class="readonly-text">{{ execCase.precondition || '无' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="操作步骤">
          <pre class="readonly-text">{{ execCase.steps || '无' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="预期结果">
          <pre class="readonly-text">{{ execCase.expected || '无' }}</pre>
        </el-descriptions-item>
      </el-descriptions>
      <el-form :inline="true" class="exec-form">
        <el-form-item label="结果">
          <el-select v-model="execForm.result" style="width:120px">
            <el-option v-for="r in execResults" :key="r" :label="r" :value="r" /></el-select>
        </el-form-item>
        <el-form-item label="轮次">
          <el-input-number v-model="execForm.round_no" :min="1" style="width:120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveExec">提交执行</el-button>
        </el-form-item>
      </el-form>
      <el-form><el-form-item label="实际结果">
        <el-input v-model="execForm.actual" type="textarea" :rows="2" placeholder="填写实际结果，与预期是否一致" />
      </el-form-item></el-form>
      <el-table :data="executions" size="small" border max-height="260">
        <el-table-column prop="round_no" label="轮次" width="60" />
        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }"><el-tag :type="resultType(row.result)" size="small">{{ row.result }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="actual" label="实际结果" min-width="160" show-overflow-tooltip />
        <el-table-column prop="executor" label="执行人" width="90" />
        <el-table-column prop="executed_at" label="时间" width="150" />
        <el-table-column label="" width="60">
          <template #default="{ row }"><el-button v-if="isAdmin" link type="danger" @click="delExec(row)">删</el-button></template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import ImportDialog from './ImportDialog.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const route = useRoute()

const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const options = ref({ case_type: [], priority: [] })
const formVersions = ref([]); const formModules = ref([]); const formReqs = ref([]); const queryModules = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', module_id: '', case_type: '', suite_id: '' })
const form = ref({})
const execDialog = ref(false); const execCase = ref({}); const executions = ref([]); const execResults = ref([])
const execForm = ref({ result: '通过', round_no: 1, actual: '' })
const DEFAULT_AI_PROMPT = '' // 主提示词已内置双 skill 方法论，这里只放用户附加要求
const aiDialog = ref(false)
const aiStep = ref(1)
const aiGenerating = ref(false)
const aiSaving = ref(false)
const aiVersions = ref([])
const aiModules = ref([])
const aiReqs = ref([])
const aiCases = ref([])
const aiSelected = ref([])
const aiTableRef = ref()
const aiForm = ref({
  project_id: '', version_id: '', module_id: null, requirement_id: null,
  requirement: '', prompt: '', mode: 'loop',
})

function prioType(p) { return { P0: 'danger', P1: 'warning', P2: 'primary', P3: 'info' }[p] || '' }
function resultType(r) { return { 通过: 'success', 失败: 'danger', 阻塞: 'warning', 跳过: 'info', 未执行: 'info' }[r] || '' }
const importRef = ref()
function openImportDialog() {
  importRef.value?.open({ project_id: query.value.project_id || '', version_id: query.value.version_id || '' })
}
async function load() {
  loading.value = true
  try { const res = await request.get('/cases', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''; query.value.module_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  queryModules.value = query.value.project_id ? await request.get('/modules/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function loadFormVersions() {
  form.value.version_id = ''; form.value.module_id = null; form.value.requirement_id = null
  formVersions.value = form.value.project_id
    ? await request.get('/versions/all', { params: { project_id: form.value.project_id } })
    : []
  formModules.value = []; formReqs.value = []
}
async function loadFormModules() {
  form.value.module_id = null; form.value.requirement_id = null
  formModules.value = form.value.project_id
    ? await request.get('/modules/all', { params: { project_id: form.value.project_id } })
    : []
  formReqs.value = (form.value.project_id && form.value.version_id)
    ? (await request.get('/requirements', { params: { project_id: form.value.project_id, version_id: form.value.version_id, size: 500 } })).items
    : []
}
async function fillFormOptions() {
  if (!form.value.project_id) { formVersions.value = []; formModules.value = []; formReqs.value = []; return }
  formVersions.value = await request.get('/versions/all', { params: { project_id: form.value.project_id } })
  formModules.value = await request.get('/modules/all', { params: { project_id: form.value.project_id } })
  formReqs.value = form.value.version_id
    ? (await request.get('/requirements', { params: { project_id: form.value.project_id, version_id: form.value.version_id, size: 500 } })).items
    : []
}
async function openDialog(row) {
  form.value = row
    ? { ...row, module_id: row.module_id || null, requirement_id: row.requirement_id || null }
    : { title: '', precondition: '', steps: '', expected: '', case_type: '功能', priority: 'P2', status: 1, project_id: '', version_id: '', module_id: null, requirement_id: null, remark: '' }
  if (row) await fillFormOptions()
  else { formVersions.value = []; formModules.value = []; formReqs.value = [] }
  dialog.value = true
}
async function save() {
  if (!form.value.title || !form.value.project_id || !form.value.version_id) return ElMessage.warning('标题/项目/版本必填')
  if (form.value.id) await request.put(`/cases/${form.value.id}`, form.value)
  else await request.post('/cases', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除用例「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/cases/${row.id}`); ElMessage.success('已删除'); load()
}
async function openExec(row) {
  execCase.value = row
  execForm.value = { result: '通过', round_no: 1, actual: '' }
  const res = await request.get('/executions', { params: { case_id: row.id } })
  executions.value = res.items
  execDialog.value = true
}
async function saveExec() {
  await request.post('/executions', { case_id: execCase.value.id, ...execForm.value })
  ElMessage.success('执行已提交')
  const res = await request.get('/executions', { params: { case_id: execCase.value.id } })
  executions.value = res.items
  execForm.value = { result: '通过', round_no: 1, actual: '' }
}
async function delExec(row) {
  await request.delete(`/executions/${row.id}`)
  const res = await request.get('/executions', { params: { case_id: execCase.value.id } })
  executions.value = res.items
}
function resetAi() {
  aiStep.value = 1
  aiGenerating.value = false
  aiSaving.value = false
  aiCases.value = []
  aiSelected.value = []
}
async function openAiDialog() {
  resetAi()
  aiForm.value = {
    project_id: query.value.project_id || '',
    version_id: query.value.version_id || '',
    module_id: null,
    requirement_id: null,
    requirement: '',
    prompt: '',
    mode: 'loop',
  }
  aiVersions.value = []
  aiModules.value = []
  aiReqs.value = []
  if (aiForm.value.project_id) {
    aiVersions.value = await request.get('/versions/all', { params: { project_id: aiForm.value.project_id } })
    await loadAiRelated()
  }
  aiDialog.value = true
}
async function loadAiVersions() {
  aiForm.value.version_id = ''
  aiForm.value.module_id = null
  aiForm.value.requirement_id = null
  aiVersions.value = aiForm.value.project_id
    ? await request.get('/versions/all', { params: { project_id: aiForm.value.project_id } })
    : []
  aiModules.value = []
  aiReqs.value = []
}
async function loadAiRelated() {
  aiForm.value.module_id = null
  aiForm.value.requirement_id = null
  aiModules.value = aiForm.value.project_id
    ? await request.get('/modules/all', { params: { project_id: aiForm.value.project_id } })
    : []
  aiReqs.value = (aiForm.value.project_id && aiForm.value.version_id)
    ? (await request.get('/requirements', { params: { project_id: aiForm.value.project_id, version_id: aiForm.value.version_id, size: 500 } })).items
    : []
}
async function doAiGenerate() {
  if (!aiForm.value.requirement?.trim()) return ElMessage.warning('需求内容必填')
  if (!aiForm.value.project_id || !aiForm.value.version_id) return ElMessage.warning('请先选择项目和版本，生成后才能保存')
  aiGenerating.value = true
  try {
    const res = await request.post('/cases/ai-generate', aiForm.value, { timeout: 200000 })
    aiCases.value = res.items || []
    if (!aiCases.value.length) return ElMessage.warning('未生成到用例')
    aiStep.value = 2
    aiSelected.value = []
    await nextTick()
    aiTableRef.value?.toggleAllSelection()
  } finally { aiGenerating.value = false }
}
function onAiSelect(rows) { aiSelected.value = rows }
function selectAllAi() { aiTableRef.value?.toggleAllSelection() }
async function saveAiCases() {
  if (!aiSelected.value.length) return ElMessage.warning('请先勾选用例')
  aiSaving.value = true
  try {
    const res = await request.post('/cases/batch', {
      project_id: aiForm.value.project_id,
      version_id: aiForm.value.version_id,
      module_id: aiForm.value.module_id,
      requirement_id: aiForm.value.requirement_id,
      items: aiSelected.value,
    }, { timeout: 60000 })
    const parts = [`已保存 ${res.created_count} 条`]
    if (res.skipped_count) parts.push(`跳过重复 ${res.skipped_count} 条`)
    if (res.errors?.length) parts.push(`失败 ${res.errors.length} 条`)
    ElMessage.success(parts.join('，'))
    aiDialog.value = false
    load()
  } finally { aiSaving.value = false }
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  options.value = await request.get('/cases/options')
  execResults.value = await request.get('/executions/options')
  if (route.query.project_id) {
    query.value.project_id = Number(route.query.project_id)
    versions.value = await request.get('/versions/all', { params: { project_id: query.value.project_id } })
    queryModules.value = await request.get('/modules/all', { params: { project_id: query.value.project_id } })
  }
  if (route.query.version_id) query.value.version_id = Number(route.query.version_id)
  if (route.query.module_id) query.value.module_id = Number(route.query.module_id)
  if (route.query.suite_id) query.value.suite_id = Number(route.query.suite_id)
  if (route.query.keyword) query.value.keyword = route.query.keyword
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.exec-form { margin: 14px 0 8px; }
.case-info { margin-bottom: 8px; }
.readonly-text { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: inherit; color: #303133; line-height: 1.6; }
</style>
