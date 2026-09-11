<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索套件名称/编号" clearable style="width:180px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:150px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:130px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.module_id" placeholder="模块" clearable filterable style="width:130px" @change="load">
          <el-option v-for="m in queryModules" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-select v-model="query.suite_type" placeholder="类型" clearable style="width:130px" @change="load">
          <el-option v-for="s in options.suite_type" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增套件</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="suite_no" label="编号" width="100" />
      <el-table-column prop="name" label="套件名称" min-width="160" />
      <el-table-column prop="suite_type" label="类型" width="110">
        <template #default="{ row }"><el-tag size="small">{{ row.suite_type }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目" width="130" />
      <el-table-column prop="version_name" label="版本" width="90" />
      <el-table-column prop="module_name" label="模块" width="100" />
      <el-table-column label="用例数" width="80">
        <template #default="{ row }">{{ row.case_count ?? (row.case_ids || []).length }}</template>
      </el-table-column>
      <el-table-column label="已执行" width="100">
        <template #default="{ row }">
          {{ row.executed_count ?? 0 }}/{{ row.case_count ?? (row.case_ids || []).length }}
        </template>
      </el-table-column>
      <el-table-column label="通过率" width="110">
        <template #default="{ row }">
          <el-tag v-if="(row.case_count || 0) === 0" size="small" type="info">-</el-tag>
          <el-tag v-else size="small" :type="passRateType(row)">{{ row.pass_rate || '0%' }}</el-tag>
        </template>
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

    <el-dialog v-model="dialog" :title="form.id ? '编辑套件' : '新增套件'" width="860px" top="6vh">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required><el-input v-model="form.name" placeholder="如 冒烟用例套件" /></el-form-item>
        <el-row :gutter="10">
          <el-col :span="8">
            <el-form-item label="类型">
              <el-select v-model="form.suite_type" style="width:100%">
                <el-option v-for="s in options.suite_type" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目" required>
              <el-select v-model="form.project_id" style="width:100%" filterable @change="onFormProject">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="版本" required>
              <el-select v-model="form.version_id" style="width:100%" filterable @change="loadFormCases">
                <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" clearable filterable style="width:100%" placeholder="按模块组套件，整版本可留空" @change="loadFormCases">
            <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用例">
          <div class="case-picker">
            <div class="case-picker-bar">
              <el-input v-model="caseKeyword" placeholder="搜索编号/标题" clearable style="width:180px" />
              <el-select v-model="caseTypeFilter" placeholder="类型" clearable style="width:110px">
                <el-option v-for="s in caseTypes" :key="s" :label="s" :value="s" />
              </el-select>
              <el-select v-model="caseModuleFilter" placeholder="模块" clearable filterable style="width:130px">
                <el-option v-for="m in caseModules" :key="m" :label="m" :value="m" />
              </el-select>
              <el-button @click="selectFiltered">全选当前筛选（{{ filteredCases.length }}）</el-button>
              <el-button @click="clearFiltered">取消当前筛选</el-button>
              <el-button type="primary" plain @click="selectAllCases">全选本版本（{{ formCases.length }}）</el-button>
              <el-button @click="clearAllCases">清空</el-button>
              <span class="picked">已选 {{ (form.case_ids || []).length }} 条</span>
            </div>
            <el-table
              ref="caseTableRef"
              :data="filteredCases"
              border
              size="small"
              max-height="360"
              row-key="id"
              @selection-change="onCaseSelect"
            >
              <el-table-column type="selection" width="42" reserve-selection />
              <el-table-column prop="case_no" label="编号" width="100" />
              <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
              <el-table-column prop="case_type" label="类型" width="80" />
              <el-table-column prop="priority" label="优先级" width="80" />
              <el-table-column prop="module_name" label="模块" width="110" show-overflow-tooltip />
            </el-table>
          </div>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="execDialog" :title="`执行套件：${execSuite.name || ''}`" width="780px">
      <el-table :data="execCases" border size="small" max-height="420">
        <el-table-column prop="case_no" label="编号" width="100" />
        <el-table-column prop="title" label="用例标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="case_type" label="类型" width="80" />
        <el-table-column label="最近结果" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.last_result" :type="resultType(row.last_result)" size="small">{{ row.last_result }}</el-tag>
            <span v-else style="color:#c0c4cc">未执行</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="warning" @click="openCaseExec(row)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="caseExecDialog" :title="`执行：${execCase.title || ''}`" width="700px">
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
            <el-option v-for="r in execResults" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="轮次">
          <el-input-number v-model="execForm.round_no" :min="1" style="width:120px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveExec">提交执行</el-button>
        </el-form-item>
      </el-form>
      <el-form>
        <el-form-item label="实际结果">
          <el-input v-model="execForm.actual" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <el-table :data="executions" size="small" border max-height="220">
        <el-table-column prop="round_no" label="轮次" width="60" />
        <el-table-column prop="result" label="结果" width="80">
          <template #default="{ row }"><el-tag :type="resultType(row.result)" size="small">{{ row.result }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="actual" label="实际结果" min-width="160" show-overflow-tooltip />
        <el-table-column prop="executor" label="执行人" width="90" />
        <el-table-column prop="executed_at" label="时间" width="150" />
      </el-table>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const route = useRoute()
const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const formVersions = ref([]); const formCases = ref([])
const queryModules = ref([]); const formModules = ref([])
const options = ref({ suite_type: [] })
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', module_id: '', suite_type: '' })
const form = ref({})
const caseTableRef = ref()
const caseKeyword = ref('')
const caseTypeFilter = ref('')
const caseModuleFilter = ref('')
const caseTypes = ref([])
const syncingSelection = ref(false)
const execDialog = ref(false); const execSuite = ref({})
const execCases = ref([])
const caseExecDialog = ref(false); const execCase = ref({})
const executions = ref([]); const execResults = ref([])
const execForm = ref({ result: '通过', round_no: 1, actual: '' })

function resultType(r) { return { 通过: 'success', 失败: 'danger', 阻塞: 'warning', 跳过: 'info', 未执行: 'info' }[r] || '' }
function passRateType(row) {
  if (!row.executed_count) return 'info'
  const n = parseFloat(row.pass_rate)
  if (n >= 100) return 'success'
  if (n >= 80) return ''
  if (n >= 50) return 'warning'
  return 'danger'
}
const caseModules = computed(() => {
  const set = new Set()
  formCases.value.forEach((c) => { if (c.module_name) set.add(c.module_name) })
  return [...set]
})
const filteredCases = computed(() => {
  const kw = (caseKeyword.value || '').trim().toLowerCase()
  return formCases.value.filter((c) => {
    if (caseTypeFilter.value && c.case_type !== caseTypeFilter.value) return false
    if (caseModuleFilter.value && c.module_name !== caseModuleFilter.value) return false
    if (kw) {
      const text = `${c.case_no || ''} ${c.title || ''}`.toLowerCase()
      if (!text.includes(kw)) return false
    }
    return true
  })
})
function resetCasePicker() {
  caseKeyword.value = ''
  caseTypeFilter.value = ''
  caseModuleFilter.value = ''
}
function onCaseSelect(rows) {
  if (syncingSelection.value) return
  const visible = new Set(filteredCases.value.map((c) => c.id))
  const keep = (form.value.case_ids || []).filter((id) => !visible.has(id))
  form.value.case_ids = [...keep, ...rows.map((r) => r.id)]
}
async function syncCaseSelection() {
  await nextTick()
  const table = caseTableRef.value
  if (!table) return
  syncingSelection.value = true
  const set = new Set(form.value.case_ids || [])
  filteredCases.value.forEach((c) => table.toggleRowSelection(c, set.has(c.id)))
  await nextTick()
  syncingSelection.value = false
}
function selectFiltered() {
  const extra = filteredCases.value.map((c) => c.id)
  form.value.case_ids = [...new Set([...(form.value.case_ids || []), ...extra])]
  syncCaseSelection()
}
function clearFiltered() {
  const drop = new Set(filteredCases.value.map((c) => c.id))
  form.value.case_ids = (form.value.case_ids || []).filter((id) => !drop.has(id))
  syncCaseSelection()
}
function selectAllCases() {
  form.value.case_ids = formCases.value.map((c) => c.id)
  syncCaseSelection()
}
function clearAllCases() {
  form.value.case_ids = []
  syncCaseSelection()
}
watch([filteredCases, dialog], () => {
  if (dialog.value) syncCaseSelection()
})

async function load() {
  loading.value = true
  try { const res = await request.get('/suites', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''; query.value.module_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  queryModules.value = query.value.project_id ? await request.get('/modules/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function onFormProject() {
  form.value.version_id = ''; form.value.module_id = null; form.value.case_ids = []
  resetCasePicker()
  formVersions.value = form.value.project_id ? await request.get('/versions/all', { params: { project_id: form.value.project_id } }) : []
  formModules.value = form.value.project_id ? await request.get('/modules/all', { params: { project_id: form.value.project_id } }) : []
  formCases.value = []
}
async function loadFormCases() {
  form.value.case_ids = []
  resetCasePicker()
  if (!form.value.project_id || !form.value.version_id) { formCases.value = []; return }
  const params = { project_id: form.value.project_id, version_id: form.value.version_id }
  if (form.value.module_id) params.module_id = form.value.module_id
  formCases.value = await request.get('/cases/all', { params })
  syncCaseSelection()
}
async function openDialog(row) {
  resetCasePicker()
  if (row) {
    form.value = { ...row, case_ids: (row.case_ids || []).slice(), module_id: row.module_id || null }
    formVersions.value = await request.get('/versions/all', { params: { project_id: row.project_id } })
    formModules.value = await request.get('/modules/all', { params: { project_id: row.project_id } })
    const params = { project_id: row.project_id, version_id: row.version_id }
    if (row.module_id) params.module_id = row.module_id
    formCases.value = await request.get('/cases/all', { params })
  } else {
    form.value = { name: '', suite_type: '冒烟', project_id: '', version_id: '', module_id: null, case_ids: [], remark: '' }
    formVersions.value = []; formModules.value = []; formCases.value = []
  }
  dialog.value = true
  syncCaseSelection()
}
async function save() {
  if (!(form.value.name || '').trim()) return ElMessage.warning('套件名称必填')
  if (!form.value.project_id || !form.value.version_id) return ElMessage.warning('项目和版本必选')
  if (form.value.id) await request.put(`/suites/${form.value.id}`, form.value)
  else await request.post('/suites', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除套件「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/suites/${row.id}`); ElMessage.success('已删除'); load()
}
async function openExec(row) {
  execSuite.value = row
  execCases.value = (row.cases || []).map(c => ({ ...c, last_result: '' }))
  execDialog.value = true
  for (const c of execCases.value) {
    const res = await request.get('/executions', { params: { case_id: c.id } })
    c.last_result = res.items?.[0]?.result || ''
  }
}
async function openCaseExec(row) {
  execCase.value = row
  if (!row.precondition && !row.steps && !row.expected) {
    const resCase = await request.get('/cases', { params: { keyword: row.case_no || row.title, size: 1 } })
    const hit = (resCase.items || []).find(c => c.id === row.id)
    if (hit) execCase.value = { ...row, ...hit }
  }
  execForm.value = { result: '通过', round_no: 1, actual: '' }
  const res = await request.get('/executions', { params: { case_id: row.id } })
  executions.value = res.items
  caseExecDialog.value = true
}
async function saveExec() {
  await request.post('/executions', { case_id: execCase.value.id, ...execForm.value })
  ElMessage.success('执行已提交')
  const res = await request.get('/executions', { params: { case_id: execCase.value.id } })
  executions.value = res.items
  execCase.value.last_result = execForm.value.result
  execForm.value = { result: '通过', round_no: 1, actual: '' }
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  options.value = await request.get('/suites/options')
  execResults.value = await request.get('/executions/options')
  try { caseTypes.value = (await request.get('/cases/options')).case_type || [] } catch (e) { caseTypes.value = [] }
  if (route.query.project_id) {
    query.value.project_id = Number(route.query.project_id)
    versions.value = await request.get('/versions/all', { params: { project_id: query.value.project_id } })
  }
  if (route.query.version_id) query.value.version_id = Number(route.query.version_id)
  if (route.query.suite_type) query.value.suite_type = route.query.suite_type
  await load()
  const sid = Number(route.query.suite_id || 0)
  if (sid) {
    const hit = items.value.find(s => s.id === sid)
    if (hit) openExec(hit)
    else {
      const one = await request.get(`/suites/${sid}`)
      openExec(one)
    }
  }
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.exec-form { margin: 14px 0 8px; }
.case-info { margin-bottom: 8px; }
.readonly-text { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: inherit; color: #303133; line-height: 1.6; }
.case-picker { width: 100%; }
.case-picker-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
.picked { color: var(--c-orange-500); font-size: 13px; margin-left: auto; }
</style>
