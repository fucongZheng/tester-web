<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索标题/编号" clearable style="width:180px" @keyup.enter="load" />
        <el-select v-model="query.review_type" placeholder="评审类型" clearable style="width:130px" @change="load">
          <el-option v-for="s in options.types" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:150px" @change="load">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.result" placeholder="结论" clearable style="width:130px" @change="load">
          <el-option v-for="s in options.results" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增评审</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="review_no" label="编号" width="100" />
      <el-table-column prop="review_type" label="类型" width="100">
        <template #default="{ row }"><el-tag :type="row.review_type === '需求评审' ? '' : 'warning'" size="small">{{ row.review_type }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目" width="120" />
      <el-table-column prop="version_name" label="版本" width="80" />
      <el-table-column prop="module_name" label="模块" width="100" />
      <el-table-column label="评审对象" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ (row.targets || []).map(t => t.name).join('、') || '-' }}</template>
      </el-table-column>
      <el-table-column prop="reviewer" label="主审人" width="90" />
      <el-table-column prop="result" label="结论" width="110">
        <template #default="{ row }"><el-tag :type="resultType(row.result)" size="small">{{ row.result }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="review_date" label="评审日期" width="110" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑评审' : '新增评审'" width="640px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="评审类型" required>
          <el-radio-group v-model="form.review_type" @change="onTypeChange">
            <el-radio v-for="t in options.types" :key="t" :value="t">{{ t }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable @change="onFormProject">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本">
          <el-select v-model="form.version_id" style="width:100%" clearable filterable @change="loadTargets">
            <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" style="width:100%" clearable filterable @change="loadTargets">
            <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="form.review_type === '用例评审' ? '用例' : '需求'">
          <el-select v-model="form.target_ids" multiple filterable style="width:100%" :placeholder="form.review_type === '用例评审' ? '选择用例' : '选择需求'">
            <el-option v-for="t in formTargets" :key="t.id" :label="targetLabel(t)" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="主审人">
            <el-select v-model="form.reviewer" filterable clearable style="width:100%" placeholder="选择用户">
              <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="评审日期"><el-date-picker v-model="form.review_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="参与人">
          <el-select v-model="form.participantList" multiple filterable style="width:100%" placeholder="多选用户">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
          </el-select>
        </el-form-item>
        <el-form-item label="结论">
          <el-select v-model="form.result" style="width:100%">
            <el-option v-for="s in options.results" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="评审意见"><el-input v-model="form.comment" type="textarea" :rows="3" /></el-form-item>
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
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const users = ref([]); const formVersions = ref([]); const formModules = ref([]); const formTargets = ref([])
const options = ref({ types: [], results: [] })
const query = ref({ page: 1, size: 10, keyword: '', review_type: '', project_id: '', result: '' })
const form = ref({})

function resultType(r) {
  return { 通过: 'success', 有条件通过: 'warning', 不通过: 'danger', 待评审: 'info' }[r] || ''
}
function targetLabel(t) {
  return `${t.req_no || t.case_no || t.no || ''} ${t.name || t.title || ''}`.trim()
}
async function load() {
  loading.value = true
  try { const res = await request.get('/reviews', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onFormProject() {
  form.value.version_id = ''; form.value.module_id = null; form.value.target_ids = []
  formVersions.value = form.value.project_id ? await request.get('/versions/all', { params: { project_id: form.value.project_id } }) : []
  formModules.value = form.value.project_id ? await request.get('/modules/all', { params: { project_id: form.value.project_id } }) : []
  await loadTargets()
}
async function onTypeChange() {
  form.value.target_ids = []
  await loadTargets()
}
async function loadTargets() {
  if (!form.value.project_id) { formTargets.value = []; return }
  const params = { project_id: form.value.project_id }
  if (form.value.version_id) params.version_id = form.value.version_id
  if (form.value.module_id) params.module_id = form.value.module_id
  if (form.value.review_type === '用例评审') {
    formTargets.value = await request.get('/cases/all', { params })
  } else {
    formTargets.value = await request.get('/requirements/all', { params })
  }
}
async function openDialog(row) {
  if (row) {
    form.value = {
      ...row,
      target_ids: (row.target_ids || []).slice(),
      module_id: row.module_id || null,
      participantList: (row.participants || '').split(/[,，]/).map(s => s.trim()).filter(Boolean),
    }
    formVersions.value = await request.get('/versions/all', { params: { project_id: row.project_id } })
    formModules.value = await request.get('/modules/all', { params: { project_id: row.project_id } })
    await loadTargets()
  } else {
    form.value = { review_type: '需求评审', title: '', project_id: '', version_id: '', module_id: null, target_ids: [], reviewer: '', participants: '', participantList: [], result: '待评审', comment: '', review_date: '' }
    formVersions.value = []; formModules.value = []; formTargets.value = []
  }
  dialog.value = true
}
async function save() {
  if (!form.value.review_type) return ElMessage.warning('请选择评审类型')
  if (!(form.value.title || '').trim()) return ElMessage.warning('评审标题必填')
  if (!form.value.project_id) return ElMessage.warning('项目必选')
  const payload = { ...form.value, participants: (form.value.participantList || []).join(',') }
  if (form.value.id) await request.put(`/reviews/${form.value.id}`, payload)
  else await request.post('/reviews', payload)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除评审「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/reviews/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  users.value = await request.get('/users/all')
  options.value = await request.get('/reviews/options')
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
