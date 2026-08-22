<template>
  <el-card>
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="搜索标题/编号" clearable style="width:180px" @keyup.enter="load" />
      <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:140px" @change="onProjectChange">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:120px" @change="load">
        <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
      </el-select>
      <el-select v-model="query.case_type" placeholder="类型" clearable style="width:110px" @change="load">
        <el-option v-for="s in options.case_type" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openDialog()">新增用例</el-button>
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
      <el-table-column prop="module_name" label="模块" width="90" />
      <el-table-column prop="status" label="状态" width="70">
        <template #default="{ row }"><el-tag :type="row.status ? 'success' : 'info'" size="small">{{ row.status ? '启用' : '停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" @click="openExec(row)">执行</el-button>
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pager" background layout="total, prev, pager, next" :total="total"
      :page-size="query.size" :current-page="query.page" @current-change="(p) => { query.page = p; load() }" />

    <!-- 用例编辑 -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑用例' : '新增用例'" width="640px">
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
          <el-col :span="12"><el-form-item label="关联需求">
            <el-select v-model="form.requirement_id" style="width:100%" clearable filterable>
              <el-option v-for="r in formReqs" :key="r.id" :label="r.name" :value="r.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="类型"><el-select v-model="form.case_type" style="width:100%">
            <el-option v-for="s in options.case_type" :key="s" :label="s" :value="s" /></el-select></el-form-item></el-col>
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
          <template #default="{ row }"><el-button link type="danger" @click="delExec(row)">删</el-button></template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'

const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const options = ref({ case_type: [], priority: [] })
const formVersions = ref([]); const formModules = ref([]); const formReqs = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', case_type: '' })
const form = ref({})
const execDialog = ref(false); const execCase = ref({}); const executions = ref([]); const execResults = ref([])
const execForm = ref({ result: '通过', round_no: 1, actual: '' })

function prioType(p) { return { P0: 'danger', P1: 'warning', P2: 'primary', P3: 'info' }[p] || '' }
function resultType(r) { return { 通过: 'success', 失败: 'danger', 阻塞: 'warning', 跳过: 'info', 未执行: 'info' }[r] || '' }
async function load() {
  loading.value = true
  try { const res = await request.get('/cases', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function loadFormVersions() {
  form.value.version_id = ''; form.value.module_id = ''; form.value.requirement_id = ''
  formVersions.value = await request.get('/versions/all', { params: { project_id: form.value.project_id } })
}
async function loadFormModules() {
  form.value.module_id = ''; form.value.requirement_id = ''
  formModules.value = await request.get('/modules/all', { params: { project_id: form.value.project_id } })
  formReqs.value = await request.get('/requirements', { params: { project_id: form.value.project_id, version_id: form.value.version_id, size: 500 } }).then(r => r.items)
}
async function openDialog(row) {
  form.value = row ? { ...row } : { title: '', precondition: '', steps: '', expected: '', case_type: '功能', priority: 'P2', status: 1, project_id: '', version_id: '', module_id: null, requirement_id: null, remark: '' }
  if (row) { await loadFormVersions(); await loadFormModules() }
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
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  options.value = await request.get('/cases/options')
  execResults.value = await request.get('/executions/options')
  load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.pager { margin-top: 14px; justify-content: flex-end; }
.exec-form { margin-bottom: 8px; }
</style>
