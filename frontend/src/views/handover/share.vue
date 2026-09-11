<template>
  <div class="share-wrap">
    <el-card class="share-card" v-loading="loading">
      <h2 class="title">开发提测填写</h2>
      <p class="sub">免登录填写 · 由 {{ meta.created_by || '-' }} 分享{{ meta.expires_at ? ' · 有效至 ' + meta.expires_at : '' }}</p>
      <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom:16px" />
      <el-form v-else :model="form" label-width="110px">
        <el-form-item label="提交人" required>
          <el-select v-model="form.submitter_id" filterable style="width:100%" placeholder="请选择系统用户">
            <el-option v-for="u in meta.testers" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable @change="onProject">
            <el-option v-for="p in meta.projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本" required>
          <el-select v-model="form.version_id" style="width:100%" filterable @change="onVersion">
            <el-option v-for="v in meta.versions" :key="v.id" :label="v.version_no" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" clearable filterable style="width:100%" placeholder="按模块提测时选择" @change="onModule">
            <el-option v-for="m in meta.modules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="需求">
          <el-select v-model="form.requirement_ids" multiple filterable style="width:100%" placeholder="根据项目/版本/模块带出">
            <el-option v-for="r in meta.requirements" :key="r.id" :label="`${r.req_no || ''} ${r.name}`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="提测分支" required>
          <el-input v-model="form.branch" type="textarea" :rows="3" placeholder="可填多个分支，每行一个" />
        </el-form-item>
        <el-form-item label="冒烟套件">
          <el-select v-model="form.suite_id" clearable filterable style="width:100%" placeholder="选择该版本下的冒烟套件">
            <el-option v-for="s in meta.suites" :key="s.id" :label="`${s.name}（${(s.case_ids || []).length}条）`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="冒烟用例">
          <el-radio-group v-model="form.smoke_executed">
            <el-radio value="未执行">未执行</el-radio>
            <el-radio value="已执行">已执行</el-radio>
          </el-radio-group>
          <el-button v-if="form.smoke_executed === '未执行'" link type="primary" @click="openSmoke">去执行</el-button>
        </el-form-item>
        <el-form-item label="测试人员" required>
          <el-select v-model="form.tester_id" filterable style="width:100%" placeholder="请选择测试人员">
            <el-option v-for="u in meta.testers" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="saving" @click="submit">提交提测</el-button>
      </el-form>
    </el-card>

    <el-dialog v-model="smokeDialog" :title="`执行冒烟：${smokeSuite.name || ''}`" width="780px" append-to-body>
      <el-table :data="smokeCases" v-loading="smokeLoading" border size="small" max-height="420">
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

    <el-dialog v-model="caseExecDialog" :title="`执行：${execCase.title || ''}`" width="700px" append-to-body>
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
          <el-button type="primary" :loading="execSaving" @click="saveExec">提交执行</el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const meta = ref({ created_by: '', projects: [], versions: [], modules: [], requirements: [], suites: [], testers: [] })
const form = ref({
  submitter_id: '', project_id: '', version_id: '', module_id: null, requirement_ids: [],
  branch: '', smoke_executed: '未执行', suite_id: null, tester_id: '', remark: '',
})
const smokeDialog = ref(false)
const smokeLoading = ref(false)
const smokeSuite = ref({})
const smokeCases = ref([])
const caseExecDialog = ref(false)
const execCase = ref({})
const executions = ref([])
const execSaving = ref(false)
const execResults = ref(['通过', '失败', '阻塞', '跳过', '未执行'])
const execForm = ref({ result: '通过', round_no: 1, actual: '' })

function resultType(r) { return { 通过: 'success', 失败: 'danger', 阻塞: 'warning', 跳过: 'info', 未执行: 'info' }[r] || '' }

async function loadMeta() {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get(`/api/handovers/public/${route.params.token}`, {
      params: {
        project_id: form.value.project_id || undefined,
        version_id: form.value.version_id || undefined,
        module_id: form.value.module_id || undefined,
      },
    })
    meta.value = res.data
    if (!form.value.project_id && res.data.project_id) form.value.project_id = res.data.project_id
    if (!form.value.version_id && res.data.version_id) form.value.version_id = res.data.version_id
    if (form.value.project_id && form.value.version_id && !(form.value.requirement_ids || []).length) {
      form.value.requirement_ids = (res.data.requirements || []).map((r) => r.id)
    }
    if (res.data.options?.exec_results?.length) execResults.value = res.data.options.exec_results
  } catch (e) {
    error.value = e.response?.data?.detail || '分享链接无效'
  } finally { loading.value = false }
}
async function onProject() {
  form.value.version_id = ''
  form.value.module_id = null
  form.value.requirement_ids = []
  form.value.suite_id = null
  await loadMeta()
}
async function onVersion() {
  form.value.requirement_ids = []
  form.value.suite_id = null
  await loadMeta()
}
async function onModule() {
  form.value.requirement_ids = []
  form.value.suite_id = null
  await loadMeta()
}
async function openSmoke() {
  if (!form.value.submitter_id) return ElMessage.warning('请先选择提交人，执行记录会记在该人名下')
  if (!form.value.suite_id) return ElMessage.warning('请先选择冒烟套件')
  smokeLoading.value = true
  smokeDialog.value = true
  try {
    const res = await axios.get(`/api/handovers/public/${route.params.token}/suites/${form.value.suite_id}`)
    smokeSuite.value = res.data
    smokeCases.value = res.data.cases || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载冒烟用例失败')
    smokeDialog.value = false
  } finally { smokeLoading.value = false }
}
async function openCaseExec(row) {
  execCase.value = row
  execForm.value = { result: '通过', round_no: 1, actual: '' }
  try {
    const res = await axios.get(`/api/handovers/public/${route.params.token}/cases/${row.id}/executions`, {
      params: { suite_id: form.value.suite_id },
    })
    executions.value = res.data.items || []
  } catch (e) {
    executions.value = []
  }
  caseExecDialog.value = true
}
async function saveExec() {
  execSaving.value = true
  try {
    const res = await axios.post(`/api/handovers/public/${route.params.token}/executions`, {
      suite_id: form.value.suite_id,
      case_id: execCase.value.id,
      submitter_id: form.value.submitter_id,
      ...execForm.value,
    })
    ElMessage.success('执行已提交')
    execCase.value.last_result = res.data.last_result || execForm.value.result
    const hist = await axios.get(`/api/handovers/public/${route.params.token}/cases/${execCase.value.id}/executions`, {
      params: { suite_id: form.value.suite_id },
    })
    executions.value = hist.data.items || []
    execForm.value = { result: '通过', round_no: 1, actual: '' }
    if (smokeCases.value.length && smokeCases.value.every((c) => c.last_result && c.last_result !== '未执行')) {
      form.value.smoke_executed = '已执行'
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交执行失败')
  } finally { execSaving.value = false }
}
async function submit() {
  if (!form.value.submitter_id) return ElMessage.warning('提交人必填')
  if (!form.value.project_id || !form.value.version_id) return ElMessage.warning('项目和版本必选')
  if (!(form.value.branch || '').trim()) return ElMessage.warning('提测分支必填')
  if (!form.value.tester_id) return ElMessage.warning('测试人员必选')
  saving.value = true
  try {
    const res = await axios.post(`/api/handovers/public/${route.params.token}`, form.value)
    ElMessage.success(`提交成功，单号 ${res.data.handover_no}，已启动测试流程`)
    form.value = {
      submitter_id: form.value.submitter_id, project_id: form.value.project_id, version_id: '',
      module_id: null, requirement_ids: [], branch: '', smoke_executed: '未执行', suite_id: null, tester_id: '', remark: '',
    }
    await loadMeta()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally { saving.value = false }
}
onMounted(loadMeta)
</script>

<style scoped>
.share-wrap {
  min-height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background:
    radial-gradient(1200px 480px at 12% -10%, var(--c-orange-100), transparent 60%),
    radial-gradient(900px 420px at 110% 110%, var(--c-blue-100), transparent 55%),
    var(--c-bg);
  padding: 40px 16px;
}
.share-card { width: 640px; padding: 10px 6px 20px; border-radius: var(--r-md); }
.title { text-align: center; margin-bottom: 4px; color: var(--c-text); }
.sub { text-align: center; color: var(--c-text-3); margin-bottom: 20px; font-size: 13px; }
.exec-form { margin: 14px 0 8px; }
.case-info { margin-bottom: 8px; }
.readonly-text { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: inherit; color: var(--c-text); line-height: 1.6; }
</style>
