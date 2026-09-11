<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索编号/分支" clearable style="width:180px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:150px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:130px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.module_id" placeholder="模块" clearable filterable style="width:130px" @change="load">
          <el-option v-for="m in queryModules" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width:110px" @change="load">
          <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增提测</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="handover_no" label="编号" width="100" />
      <el-table-column prop="project_name" label="项目" width="130" />
      <el-table-column prop="version_name" label="版本" width="90" />
      <el-table-column prop="module_name" label="模块" width="100" />
      <el-table-column label="需求" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ (row.requirements || []).map(r => r.name).join('、') || '-' }}</template>
      </el-table-column>
      <el-table-column prop="branch" label="提测分支" min-width="160" show-overflow-tooltip>
        <template #default="{ row }"><span class="branch-text">{{ row.branch }}</span></template>
      </el-table-column>
      <el-table-column prop="suite_name" label="冒烟套件" width="120" show-overflow-tooltip />
      <el-table-column prop="smoke_executed" label="冒烟用例" width="130">
        <template #default="{ row }">
          <el-tag :type="row.smoke_executed === '已执行' ? 'success' : 'warning'" size="small">{{ row.smoke_executed }}</el-tag>
          <el-button v-if="row.smoke_executed !== '已执行'" link type="primary" @click="goSmoke(row)">去执行</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="tester_name" label="测试人员" width="90" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="{ 待测试: 'warning', 测试中: 'primary', 已完成: 'success', 已驳回: 'danger' }[row.status] || ''">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="submitter" label="提交人" width="80" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑提测' : '新增提测'" width="620px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable @change="onFormProject">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本" required>
          <el-select v-model="form.version_id" style="width:100%" filterable @change="onFormVersion">
            <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" clearable filterable style="width:100%" placeholder="按模块提测时选择，整版本可留空" @change="onFormModule">
            <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="需求">
          <el-select v-model="form.requirement_ids" multiple filterable style="width:100%" placeholder="根据项目/版本/模块带出">
            <el-option v-for="r in formReqs" :key="r.id" :label="`${r.req_no || ''} ${r.name}`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="提测分支" required>
          <el-input v-model="form.branch" type="textarea" :rows="3" placeholder="可填多个分支，每行一个，如 release/1.2.0" />
        </el-form-item>
        <el-form-item label="冒烟套件">
          <el-select v-model="form.suite_id" clearable filterable style="width:100%" placeholder="选择该版本下的冒烟套件">
            <el-option v-for="s in formSuites" :key="s.id" :label="`${s.name}（${(s.case_ids || []).length}条）`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="冒烟用例">
          <el-radio-group v-model="form.smoke_executed">
            <el-radio value="未执行">未执行</el-radio>
            <el-radio value="已执行">已执行</el-radio>
          </el-radio-group>
          <el-button v-if="form.smoke_executed === '未执行'" link type="primary" @click="goSmoke()">去执行</el-button>
        </el-form-item>
        <el-form-item label="测试人员" required>
          <el-select v-model="form.tester_id" filterable style="width:100%" placeholder="请选择测试人员">
            <el-option v-for="u in testers" :key="u.id" :label="u.real_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.id" label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button v-if="!form.id" :loading="sharing" @click="shareForm">分享给开发填写</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const router = useRouter()
const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const testers = ref([])
const queryModules = ref([]); const formModules = ref([])
const formVersions = ref([]); const formReqs = ref([]); const formSuites = ref([])
const options = ref({ smoke: [], status: [] })
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', module_id: '', status: '' })
const form = ref({})
const sharing = ref(false)

async function load() {
  loading.value = true
  try { const res = await request.get('/handovers', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''; query.value.module_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  queryModules.value = query.value.project_id ? await request.get('/modules/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function loadFormRelated() {
  if (!form.value.project_id || !form.value.version_id) { formReqs.value = []; formSuites.value = []; return }
  const params = { project_id: form.value.project_id, version_id: form.value.version_id }
  if (form.value.module_id) params.module_id = form.value.module_id
  formReqs.value = await request.get('/requirements/all', { params })
  formSuites.value = await request.get('/suites/all', { params: { ...params, suite_type: '冒烟' } })
}
async function onFormProject() {
  form.value.version_id = ''; form.value.module_id = null; form.value.requirement_ids = []; form.value.suite_id = null
  formVersions.value = form.value.project_id ? await request.get('/versions/all', { params: { project_id: form.value.project_id } }) : []
  formModules.value = form.value.project_id ? await request.get('/modules/all', { params: { project_id: form.value.project_id } }) : []
  formReqs.value = []; formSuites.value = []
}
async function onFormVersion() {
  form.value.requirement_ids = []; form.value.suite_id = null
  if (!form.value.project_id || !form.value.version_id) { formReqs.value = []; formSuites.value = []; return }
  await loadFormRelated()
  form.value.requirement_ids = formReqs.value.map(r => r.id)
}
async function onFormModule() {
  form.value.requirement_ids = []; form.value.suite_id = null
  await loadFormRelated()
  form.value.requirement_ids = formReqs.value.map(r => r.id)
}
async function openDialog(row) {
  if (row) {
    form.value = { ...row, requirement_ids: (row.requirement_ids || []).slice(), suite_id: row.suite_id || null, module_id: row.module_id || null }
    formVersions.value = await request.get('/versions/all', { params: { project_id: row.project_id } })
    formModules.value = await request.get('/modules/all', { params: { project_id: row.project_id } })
    await loadFormRelated()
  } else {
    form.value = { project_id: '', version_id: '', module_id: null, requirement_ids: [], branch: '', smoke_executed: '未执行', suite_id: null, tester_id: '', remark: '', status: '待测试' }
    formVersions.value = []; formModules.value = []; formReqs.value = []; formSuites.value = []
  }
  dialog.value = true
}
async function save() {
  if (!form.value.project_id || !form.value.version_id) return ElMessage.warning('项目和版本必选')
  if (!(form.value.branch || '').trim()) return ElMessage.warning('提测分支必填')
  if (!form.value.tester_id) return ElMessage.warning('测试人员必选')
  if (form.value.id) {
    await request.put(`/handovers/${form.value.id}`, form.value)
    ElMessage.success('保存成功')
  } else {
    await request.post('/handovers', form.value)
    ElMessage.success('已提交提测，并启动测试流程（环节0：验证开发提测）')
  }
  dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除提测单「${row.handover_no}」？`, '提示', { type: 'warning' })
  await request.delete(`/handovers/${row.id}`); ElMessage.success('已删除'); load()
}
async function shareForm() {
  if (!form.value.project_id) return ElMessage.warning('请先选择项目再分享')
  sharing.value = true
  try {
    const res = await request.post('/handovers/share', {
      project_id: form.value.project_id || null,
      version_id: form.value.version_id || null,
    })
    const url = `${window.location.origin}/handover/share/${res.token}`
    try {
      await navigator.clipboard.writeText(url)
      ElMessage.success(res.expires_at ? `分享链接已复制，有效至 ${res.expires_at}` : '分享链接已复制，发给开发即可免登录填写')
    } catch (e) {
      await ElMessageBox.alert(url, '请复制分享链接', { confirmButtonText: '确定' })
    }
  } finally { sharing.value = false }
}
function goSmoke(row) {
  const src = row || form.value
  if (!src.suite_id) return ElMessage.warning('请先选择冒烟套件')
  const q = new URLSearchParams()
  if (src.project_id) q.set('project_id', src.project_id)
  if (src.version_id) q.set('version_id', src.version_id)
  q.set('suite_id', src.suite_id)
  router.push('/suite?' + q.toString())
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  testers.value = await request.get('/users/all')
  options.value = await request.get('/handovers/options')
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.branch-text { white-space: pre-line; }
</style>
