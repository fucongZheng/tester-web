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
      <el-table-column label="评审对象" min-width="200">
        <template #default="{ row }">
          <template v-if="row.review_type === '用例评审'">
            <div class="obj-line">
              <el-tag size="small" type="danger">核心{{ (row.targets || []).length }}</el-tag>
              <span class="obj-names">{{ (row.targets || []).map(t => t.name).join('、') || '-' }}</span>
            </div>
            <div v-if="(row.normal_targets || []).length" class="obj-line">
              <el-tag size="small" type="info">常规{{ row.normal_targets.length }}</el-tag>
              <span class="obj-names">{{ row.normal_targets.map(t => t.name).join('、') }}</span>
            </div>
          </template>
          <span v-else>{{ (row.targets || []).map(t => t.name).join('、') || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="reviewer" label="主审人" width="90" />
      <el-table-column prop="result" label="结论" width="110">
        <template #default="{ row }"><el-tag :type="resultType(row.result)" size="small">{{ row.result }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="review_date" label="评审日期" width="110" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.review_type === '用例评审'" link type="success" @click="openPreview(row)">预览用例</el-button>
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
          <el-select v-model="form.version_id" style="width:100%" clearable filterable @change="onFormVersion">
            <el-option v-for="v in formVersions" :key="v.id"
                       :label="v.name ? `${v.version_no} ${v.name}` : v.version_no" :value="v.id" />
          </el-select>
          <div v-if="form.review_type === '用例评审'" class="field-tip">选择版本后标题自动生成为「版本名称+版本号+测试用例评审」，可手动修改</div>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="form.module_id" style="width:100%" clearable filterable @change="loadTargets">
            <el-option v-for="m in formModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <!-- 需求评审：多选需求；用例评审：核心用例 + 常规用例（弹窗选择，互斥） -->
        <el-form-item v-if="form.review_type === '需求评审'" label="需求">
          <el-select v-model="form.target_ids" multiple filterable style="width:100%" placeholder="选择需求">
            <el-option v-for="t in formTargets" :key="t.id" :label="targetLabel(t)" :value="t.id" />
          </el-select>
        </el-form-item>
        <template v-else>
          <el-form-item label="核心用例">
            <div class="case-field">
              <div v-if="coreMetas.length" class="case-tags">
                <el-tag v-for="m in coreMetas" :key="m.id" closable type="danger" effect="light"
                        @close="removeCaseId('core', m.id)">{{ m.no }} {{ m.name }}</el-tag>
              </div>
              <el-button @click="openPicker('core')">
                {{ coreMetas.length ? '调整用例' : '选择用例' }}（已选 {{ (form.target_ids || []).length }} 条）
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="常规用例">
            <div class="case-field">
              <div v-if="normalMetas.length" class="case-tags">
                <el-tag v-for="m in normalMetas" :key="m.id" closable effect="light"
                        @close="removeCaseId('normal', m.id)">{{ m.no }} {{ m.name }}</el-tag>
              </div>
              <el-button @click="openPicker('normal')">
                {{ normalMetas.length ? '调整用例' : '选择用例' }}（已选 {{ (form.normal_ids || []).length }} 条）
              </el-button>
            </div>
          </el-form-item>
        </template>
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

    <!-- 用例选择弹窗（核心/常规共用，另一组已选的用例禁选） -->
    <CasePickerDialog v-model="pickerVisible" :selected="pickerSelected" :exclude-ids="pickerExclude"
                      :other-label="pickerMode === 'core' ? '常规用例' : '核心用例'"
                      :project-id="form.project_id" :version-id="form.version_id"
                      @confirm="onPickerConfirm" />

    <!-- 投屏预览：全屏一屏一例 -->
    <CasePreview v-model="previewVisible" :title="previewTitle" :items="previewItems" />
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import CasePickerDialog from '../../components/CasePickerDialog.vue'
import CasePreview from '../../components/CasePreview.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const items = ref([]); const total = ref(0); const loading = ref(false); const dialog = ref(false)
const projects = ref([]); const users = ref([]); const formVersions = ref([]); const formModules = ref([]); const formTargets = ref([])
const options = ref({ types: [], results: [] })
const query = ref({ page: 1, size: 10, keyword: '', review_type: '', project_id: '', result: '' })
const form = ref({})

// 用例评审：核心/常规两组用例 + 弹窗选择 + 投屏预览
const caseMeta = ref({})                 // id -> {id,no,name}，两组标签共用
const pickerVisible = ref(false); const pickerMode = ref('core')
const previewVisible = ref(false); const previewTitle = ref(''); const previewItems = ref([])
const autoTitle = ref('')                // 最近一次自动生成的标题，手动改过就不再覆盖

const coreMetas = computed(() => (form.value.target_ids || []).map(id => caseMeta.value[id]).filter(Boolean))
const normalMetas = computed(() => (form.value.normal_ids || []).map(id => caseMeta.value[id]).filter(Boolean))
const pickerSelected = computed(() => (pickerMode.value === 'core' ? form.value.target_ids : form.value.normal_ids) || [])
const pickerExclude = computed(() => (pickerMode.value === 'core' ? form.value.normal_ids : form.value.target_ids) || [])

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
  form.value.version_id = ''; form.value.module_id = null; form.value.target_ids = []; form.value.normal_ids = []
  formVersions.value = form.value.project_id ? await request.get('/versions/all', { params: { project_id: form.value.project_id } }) : []
  formModules.value = form.value.project_id ? await request.get('/modules/all', { params: { project_id: form.value.project_id } }) : []
  applyAutoTitle()
  await loadTargets()
}
function onFormVersion() {
  applyAutoTitle()
  loadTargets()
}
async function onTypeChange() {
  form.value.target_ids = []; form.value.normal_ids = []
  applyAutoTitle()
  await loadTargets()
}
function applyAutoTitle() {
  if (form.value.review_type !== '用例评审') return
  const v = formVersions.value.find(x => x.id === form.value.version_id)
  if (!v) {
    // 版本被清掉：若标题仍是自动生成的，一并清空
    if (form.value.title && form.value.title === autoTitle.value) { form.value.title = ''; autoTitle.value = '' }
    return
  }
  const t = `${v.name || ''}${v.version_no}测试用例评审`
  // 标题为空或仍是上次自动生成的 → 跟随版本更新；手动改过则不覆盖
  if (!form.value.title || form.value.title === autoTitle.value) {
    form.value.title = t
    autoTitle.value = t
  }
}
async function loadTargets() {
  // 需求评审才需要内联需求下拉；用例评审走 CasePickerDialog
  if (form.value.review_type === '用例评审' || !form.value.project_id) { formTargets.value = []; return }
  const params = { project_id: form.value.project_id }
  if (form.value.version_id) params.version_id = form.value.version_id
  if (form.value.module_id) params.module_id = form.value.module_id
  formTargets.value = await request.get('/requirements/all', { params })
}
function openPicker(mode) {
  if (!form.value.project_id) return ElMessage.warning('请先选择项目')
  pickerMode.value = mode
  pickerVisible.value = true
}
function onPickerConfirm(ids, metas) {
  metas.forEach((m) => { caseMeta.value[m.id] = m })
  if (pickerMode.value === 'core') form.value.target_ids = ids
  else form.value.normal_ids = ids
}
function removeCaseId(group, id) {
  const key = group === 'core' ? 'target_ids' : 'normal_ids'
  form.value[key] = (form.value[key] || []).filter(x => x !== id)
}
async function openPreview(row) {
  const res = await request.get(`/reviews/${row.id}/cases`)
  previewTitle.value = res.title
  previewItems.value = res.items
  previewVisible.value = true
}
async function openDialog(row) {
  if (row) {
    form.value = {
      ...row,
      target_ids: (row.target_ids || []).slice(),
      normal_ids: (row.normal_target_ids || []).slice(),
      module_id: row.module_id || null,
      participantList: (row.participants || '').split(/[,，]/).map(s => s.trim()).filter(Boolean),
    }
    caseMeta.value = {}
    ;[...(row.targets || []), ...(row.normal_targets || [])].forEach((t) => { caseMeta.value[t.id] = t })
    autoTitle.value = ''
    formVersions.value = await request.get('/versions/all', { params: { project_id: row.project_id } })
    formModules.value = await request.get('/modules/all', { params: { project_id: row.project_id } })
    await loadTargets()
  } else {
    form.value = { review_type: '需求评审', title: '', project_id: '', version_id: '', module_id: null, target_ids: [], normal_ids: [], reviewer: '', participants: '', participantList: [], result: '待评审', comment: '', review_date: '' }
    caseMeta.value = {}; autoTitle.value = ''
    formVersions.value = []; formModules.value = []; formTargets.value = []
  }
  dialog.value = true
}
async function save() {
  if (!form.value.review_type) return ElMessage.warning('请选择评审类型')
  if (!(form.value.title || '').trim()) return ElMessage.warning('评审标题必填')
  if (!form.value.project_id) return ElMessage.warning('项目必选')
  const isCaseReview = form.value.review_type === '用例评审'
  const payload = {
    ...form.value,
    participants: (form.value.participantList || []).join(','),
    // 需求评审不带用例分组；用例评审两组互斥兜底
    target_ids: isCaseReview ? (form.value.target_ids || []) : [],
    normal_ids: isCaseReview
      ? (form.value.normal_ids || []).filter(id => !(form.value.target_ids || []).includes(id))
      : [],
  }
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

.obj-line { display: flex; align-items: center; gap: 6px; line-height: 1.6; }
.obj-line + .obj-line { margin-top: 2px; }
.obj-line .el-tag { flex-shrink: 0; }
.obj-names {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; min-width: 0;
}

.field-tip { font-size: 12px; color: #909399; line-height: 1.5; margin-top: 2px; }

.case-field { width: 100%; }
.case-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; max-height: 96px; overflow-y: auto; }
.case-tags .el-tag { max-width: 100%; }
</style>
