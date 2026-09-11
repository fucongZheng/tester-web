<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索标题/编号" clearable style="width:180px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="项目" clearable filterable style="width:150px" @change="onProjectChange">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="query.version_id" placeholder="版本" clearable filterable style="width:130px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width:110px" @change="load">
          <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增上线申请</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="launch_no" label="编号" width="100" />
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目" width="130" />
      <el-table-column prop="version_name" label="版本" width="90" />
      <el-table-column prop="module_name" label="模块" width="100" />
      <el-table-column prop="plan_date" label="计划上线" width="110" />
      <el-table-column prop="applicant" label="申请人" width="90" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="{ 已通过: 'success', 已驳回: 'danger', 待审批: 'warning' }[row.status] || ''">{{ row.status }}</el-tag>
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

    <el-dialog v-model="dialog" :title="form.id ? '编辑上线申请' : '新增上线申请'" width="620px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="标题" required><el-input v-model="form.title" placeholder="如 V1.2.0 上线申请" /></el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable @change="onFormProject">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本" required>
          <el-select v-model="form.version_id" style="width:100%" filterable>
            <el-option v-for="v in formVersions" :key="v.id" :label="v.version_no" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" clearable filterable style="width:100%" placeholder="整版本上线可留空">
            <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划上线日"><el-date-picker v-model="form.plan_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="上线内容" required>
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="变更说明、影响范围、回滚方案" />
        </el-form-item>
        <el-form-item v-if="form.id" label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="s in options.status" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="审批人">
          <el-select v-model="form.reviewer" filterable clearable style="width:100%" placeholder="选择用户">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
          </el-select>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const versions = ref([]); const users = ref([])
const formVersions = ref([]); const formModules = ref([])
const options = ref({ status: [] })
const query = ref({ page: 1, size: 10, keyword: '', project_id: '', version_id: '', status: '' })
const form = ref({})

async function load() {
  loading.value = true
  try { const res = await request.get('/launches', { params: query.value }); items.value = res.items; total.value = res.total }
  finally { loading.value = false }
}
async function onProjectChange() {
  query.value.version_id = ''
  versions.value = query.value.project_id ? await request.get('/versions/all', { params: { project_id: query.value.project_id } }) : []
  load()
}
async function onFormProject() {
  form.value.version_id = ''; form.value.module_id = null
  formVersions.value = form.value.project_id ? await request.get('/versions/all', { params: { project_id: form.value.project_id } }) : []
  formModules.value = form.value.project_id ? await request.get('/modules/all', { params: { project_id: form.value.project_id } }) : []
}
async function openDialog(row) {
  if (row) {
    form.value = { ...row, module_id: row.module_id || null }
    formVersions.value = await request.get('/versions/all', { params: { project_id: row.project_id } })
    formModules.value = await request.get('/modules/all', { params: { project_id: row.project_id } })
  } else {
    form.value = { title: '', project_id: '', version_id: '', module_id: null, plan_date: '', content: '', reviewer: '', status: '待审批', remark: '' }
    formVersions.value = []; formModules.value = []
  }
  dialog.value = true
}
async function save() {
  if (!(form.value.title || '').trim()) return ElMessage.warning('标题必填')
  if (!form.value.project_id || !form.value.version_id) return ElMessage.warning('项目和版本必选')
  if (!(form.value.content || '').trim()) return ElMessage.warning('上线内容必填')
  if (form.value.id) await request.put(`/launches/${form.value.id}`, form.value)
  else await request.post('/launches', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除上线申请「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/launches/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  users.value = await request.get('/users/all')
  options.value = await request.get('/launches/options')
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
