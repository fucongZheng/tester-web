<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索版本号/名称" clearable style="width:200px" @keyup.enter="load" />
        <el-select v-model="query.project_id" placeholder="所属项目" clearable filterable style="width:180px" @change="load">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增版本</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="version_no" label="版本号" width="120" />
      <el-table-column prop="name" label="版本名称" min-width="140" />
      <el-table-column prop="project_name" label="所属项目" width="150" />
      <el-table-column label="开始时间" width="180">
        <template #default="{ row }">{{ toDateTime(row.start_date) || '-' }}</template>
      </el-table-column>
      <el-table-column label="上线时间" width="180">
        <template #default="{ row }">{{ toDateTime(row.launch_date) || '-' }}</template>
      </el-table-column>
      <el-table-column label="超时" width="160">
        <template #default="{ row }">
          <el-tag v-if="row.overtime" type="danger" size="small">超时 {{ row.overtime }}</el-tag>
          <span v-else style="color:#c0c4cc">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="评审纪要" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.review_minutes || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑版本' : '新增版本'" width="620px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="版本号" required><el-input v-model="form.version_no" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="form.project_id" style="width:100%" filterable>
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_date" type="datetime" format="YYYY-MM-DD HH:mm:ss" value-format="YYYY-MM-DD HH:mm:ss" time-format="HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="上线时间" required>
          <el-date-picker v-model="form.launch_date" type="datetime" format="YYYY-MM-DD HH:mm:ss" value-format="YYYY-MM-DD HH:mm:ss" time-format="HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width:100%">
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" /></el-select></el-form-item>
        <el-form-item label="评审纪要" required>
          <el-input v-model="form.review_minutes" type="textarea" :rows="5" placeholder="必填。可手填，或从该版本已通过的需求评审记录生成" />
          <el-button v-if="form.id" link type="primary" :loading="drafting" @click="fillFromReviews">从需求评审生成</el-button>
          <div v-else class="hint">新建后可再点「从需求评审生成」；没有评审记录时请手填纪要。</div>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
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

const items = ref([])
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const projects = ref([])
const statuses = ref([])
const query = ref({ page: 1, size: 10, keyword: '', project_id: '' })
const form = ref({})
const drafting = ref(false)

function statusType(s) {
  return { 已上线: 'success', 已归档: 'info', 测试中: 'warning', 开发中: 'primary', 规划中: '' }[s] || ''
}
async function load() {
  loading.value = true
  try {
    const res = await request.get('/versions', { params: query.value })
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}
function toDateTime(v) {
  if (!v) return ''
  const s = String(v).trim().replace('T', ' ')
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return `${s} 00:00:00`
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(s)) return `${s}:00`
  return s
}
function openDialog(row) {
  form.value = row
    ? { ...row, start_date: toDateTime(row.start_date), launch_date: toDateTime(row.launch_date) }
    : { version_no: '', name: '', project_id: '', start_date: '', launch_date: '', status: '规划中', review_minutes: '', remark: '' }
  dialog.value = true
}
async function save() {
  if (!form.value.version_no || !form.value.project_id) return ElMessage.warning('版本号和项目必填')
  if (!form.value.launch_date) return ElMessage.warning('上线时间必填')
  if (!(form.value.review_minutes || '').trim()) return ElMessage.warning('需求评审纪要必填')
  if (form.value.id) await request.put(`/versions/${form.value.id}`, form.value)
  else await request.post('/versions', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function fillFromReviews() {
  if (!form.value.id) return ElMessage.warning('请先保存版本，再从评审记录生成')
  drafting.value = true
  try {
    const res = await request.get(`/versions/${form.value.id}/review-minutes-draft`)
    form.value.review_minutes = res.review_minutes
    ElMessage.success('已填入评审纪要，请核对后保存')
  } finally { drafting.value = false }
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除版本「${row.version_no}」？`, '提示', { type: 'warning' })
  await request.delete(`/versions/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  statuses.value = await request.get('/versions/statuses')
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.hint { color: var(--c-text-3); font-size: 12px; line-height: 1.4; margin-top: 4px; }
</style>
