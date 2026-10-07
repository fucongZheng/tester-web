<template>
  <el-dialog v-model="visible" title="导入用例" width="960px" top="5vh" :close-on-click-modal="false" @closed="reset">
    <el-steps :active="step - 1" simple style="margin-bottom:16px">
      <el-step title="上传文件" />
      <el-step title="字段映射" />
      <el-step title="导入结果" />
    </el-steps>

    <!-- Step1 上传与设置 -->
    <div v-if="step === 1">
      <el-form :model="form" label-width="90px">
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="项目" required>
            <el-select v-model="form.project_id" style="width:100%" filterable @change="onProjectChange">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="版本名称" required>
            <el-select v-model="form.version_id" style="width:100%" filterable placeholder="选择版本名称">
              <el-option v-for="v in versions" :key="v.id" :label="v.name || v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12"><el-form-item label="版本">
            <el-select v-model="form.version_id" disabled style="width:100%" placeholder="选版本名称后自动带出">
              <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="模块策略">
          <el-radio-group v-model="form.strategy">
            <el-radio value="all">指定模块</el-radio>
            <el-radio value="match">按Excel模块列匹配</el-radio>
            <el-radio value="create">匹配并新建缺失模块</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.strategy === 'all'" label="导入模块">
          <el-select v-model="form.module_id" style="width:100%" clearable filterable placeholder="不挂模块">
            <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" /></el-select>
        </el-form-item>
        <el-form-item v-else-if="form.strategy === 'match'" label="兜底模块">
          <el-select v-model="form.fallback_module_id" style="width:100%" clearable filterable
                     placeholder="Excel模块名匹配不到时挂到该模块，留空则不挂模块">
            <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" /></el-select>
        </el-form-item>
        <el-alert v-else type="info" :closable="false" show-icon
                  title="按Excel模块列匹配系统模块，匹配不到的自动新建（导入前会提示新建数量）" style="margin-bottom:18px" />
      </el-form>

      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx,.csv"
                 :on-change="onFileChange" :on-remove="onFileRemove">
        <el-icon style="font-size:40px;color:#c0c4cc;margin-top:24px"><UploadFilled /></el-icon>
        <div class="el-upload__text">将 .xlsx / .csv 文件拖到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持常见表头（用例标题/测试步骤/预期结果/所属模块 等），列顺序不限；
            <el-link type="primary" underline="never" @click="downloadTemplate">下载标准模板</el-link>
          </div>
        </template>
      </el-upload>
    </div>

    <!-- Step2 映射与预览 -->
    <div v-else-if="step === 2 && parseData">
      <div class="map-bar">
        <el-select v-model="sheetName" style="width:220px" @change="reparse">
          <el-option v-for="s in parseData.sheets" :key="s.name" :value="s.name"
                     :label="`${s.name}（${s.row_count}行）`" :disabled="!s.score && !s.selected" />
        </el-select>
        <div class="map-fields">
          <div v-for="f in FIELDS" :key="f.key" class="map-field">
            <span class="map-label">{{ f.label }}</span>
            <el-select v-model="fieldMapping[f.key]" size="small" style="width:130px"
                       :clearable="f.key !== 'title'" placeholder="不导入" @change="reparse">
              <el-option v-for="(h, i) in parseData.headers" :key="i" :value="i" :label="h || `第${i + 1}列`" />
            </el-select>
          </div>
        </div>
        <el-button size="small" :loading="aiMapping" @click="doAiMap">AI识别映射</el-button>
      </div>
      <el-alert :type="skipCount ? 'warning' : 'success'" :closable="false" show-icon style="margin:10px 0"
                :title="`共 ${stats.total_rows} 行：可导入 ${stats.valid} 行，跳过 ${stats.skipped} 行（空行/模块分割行/标题为空）${stats.truncated ? '，超出1000行已截断' : ''}`" />

      <el-table ref="tableRef" v-loading="parsing" :data="parseData.rows" border stripe max-height="380"
                :row-class-name="rowClass" @selection-change="onSelect">
        <el-table-column type="selection" width="42" :selectable="(row) => !row._skip" />
        <el-table-column prop="_row" label="#" width="52" />
        <el-table-column label="标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.title }}</span>
            <el-tooltip v-if="row._warn" :content="row._warn" placement="top">
              <el-icon color="#E6A23C" style="margin-left:4px;vertical-align:-2px"><WarningFilled /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="130" show-overflow-tooltip />
        <el-table-column label="优先级" width="70">
          <template #default="{ row }"><el-tag :type="prioType(row.priority)" size="small">{{ row.priority }}</el-tag></template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.case_type }}</el-tag>
            <el-tag v-if="row.case_type_raw" size="small" type="warning" style="margin-left:4px">{{ row.case_type_raw }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="precondition" label="前置条件" min-width="120" show-overflow-tooltip />
        <el-table-column prop="steps" label="步骤" min-width="160" show-overflow-tooltip />
        <el-table-column prop="expected" label="预期结果" min-width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <el-tag v-if="row._skip" size="small" type="danger">跳过：{{ row._skip_reason }}</el-tag>
            <el-tag v-else size="small" type="success">导入</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Step3 结果 -->
    <div v-else-if="step === 3">
      <el-result :icon="result.errors.length ? 'warning' : 'success'"
                 :title="`导入完成：成功 ${result.created_count} 条，跳过重复 ${result.skipped_count} 条，失败 ${result.errors.length} 条`">
        <template #extra>
          <div v-if="result.errors.length" class="err-list">
            <div v-for="(e, i) in result.errors.slice(0, 10)" :key="i">第 {{ e.index }} 条：{{ e.reason }}</div>
            <div v-if="result.errors.length > 10">… 共 {{ result.errors.length }} 条失败</div>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <template v-if="step === 1">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="parsing" :disabled="!form.project_id || !form.version_id || !file"
                   @click="doParse">解析文件</el-button>
      </template>
      <template v-else-if="step === 2">
        <el-button @click="step = 1">上一步</el-button>
        <el-button @click="selectAll">全选</el-button>
        <el-button type="primary" :loading="saving" :disabled="!selected.length" @click="doImport">
          导入所选（{{ selected.length }}）
        </el-button>
      </template>
      <template v-else>
        <el-button type="primary" @click="visible = false">完成</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, WarningFilled } from '@element-plus/icons-vue'
import request from '../../api/request'

const props = defineProps({ projects: { type: Array, default: () => [] } })
const emit = defineEmits(['imported'])

const CHUNK_SIZE = 200
const FIELDS = [
  { key: 'title', label: '标题*' },
  { key: 'precondition', label: '前置条件' },
  { key: 'steps', label: '步骤' },
  { key: 'expected', label: '预期结果' },
  { key: 'module', label: '模块' },
  { key: 'priority', label: '优先级' },
  { key: 'case_type', label: '类型' },
  { key: 'remark', label: '备注' },
  { key: 'origin_no', label: '原编号' },
]

const visible = ref(false)
const step = ref(1)
const parsing = ref(false)
const saving = ref(false)
const aiMapping = ref(false)
const file = ref(null)
const versions = ref([])
const modules = ref([])
const parseData = ref(null)
const sheetName = ref('')
const fieldMapping = ref({})
const selected = ref([])
const tableRef = ref()
const result = ref({ created_count: 0, skipped_count: 0, errors: [] })
const form = ref({ project_id: '', version_id: '', strategy: 'all', module_id: null, fallback_module_id: null })

const stats = computed(() => parseData.value?.stats || { total_rows: 0, valid: 0, skipped: 0 })
const skipCount = computed(() => stats.value.skipped)

function prioType(p) { return { P0: 'danger', P1: 'warning', P2: 'primary', P3: 'info' }[p] || '' }
function rowClass({ row }) { return row._skip ? 'skip-row' : '' }

async function open(pre = {}) {
  form.value = {
    project_id: pre.project_id || '', version_id: pre.version_id || '',
    strategy: 'all', module_id: null, fallback_module_id: null,
  }
  versions.value = []
  if (form.value.project_id) {
    await onProjectChange(true)
  }
  visible.value = true
}

async function onProjectChange(keepVersion = false) {
  if (!keepVersion) form.value.version_id = ''
  form.value.module_id = null
  form.value.fallback_module_id = null
  versions.value = form.value.project_id
    ? await request.get('/versions/all', { params: { project_id: form.value.project_id } }) : []
  modules.value = form.value.project_id
    ? await request.get('/modules/all', { params: { project_id: form.value.project_id } }) : []
}

function onFileChange(f) { file.value = f.raw || null }
function onFileRemove() { file.value = null }

async function doParse() {
  if (!file.value) return ElMessage.warning('请先选择文件')
  parsing.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    parseData.value = await request.post('/cases/import/parse', fd, { timeout: 60000 })
    sheetName.value = parseData.value.sheet
    fieldMapping.value = { ...parseData.value.mapping }
    step.value = 2
    await reselect()
  } finally { parsing.value = false }
}

async function reparse() {
  if (!file.value) return
  parsing.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('sheet', sheetName.value)
    fd.append('header_row', parseData.value.header_row)
    fd.append('mapping', JSON.stringify(fieldMapping.value))
    parseData.value = await request.post('/cases/import/parse', fd, { timeout: 60000 })
    await reselect()
  } catch (e) {
    // 拦截器已提示；保留当前预览数据
  } finally { parsing.value = false }
}

async function reselect() {
  selected.value = []
  await nextTick()
  tableRef.value?.toggleAllSelection()
}

async function doAiMap() {
  if (!parseData.value) return
  const raw = parseData.value.raw_rows.filter((r) => (r[0] ?? '').trim() !== '').slice(0, 3)
  aiMapping.value = true
  try {
    const res = await request.post('/cases/import/ai-map', {
      headers: parseData.value.headers, sample_rows: raw,
    }, { timeout: 90000 })
    fieldMapping.value = { ...fieldMapping.value, ...res.mapping }
    await reparse()
    ElMessage.success('已应用AI推荐的映射，请核对预览')
  } catch (e) {
    ElMessage.warning('AI识别映射失败，请手动选择列')
  } finally { aiMapping.value = false }
}

function onSelect(rows) { selected.value = rows }
function selectAll() { tableRef.value?.toggleAllSelection() }

async function resolveModuleId(row, nameMap) {
  if (form.value.strategy === 'all') return form.value.module_id
  if (form.value.strategy === 'match') {
    return nameMap.get((row.module || '').trim()) ?? form.value.fallback_module_id ?? null
  }
  // create：匹配不到的已在导入前新建，这里必然命中
  return nameMap.get((row.module || '').trim()) ?? null
}

async function prepareCreateStrategy(rows) {
  const existing = new Set((await request.get('/modules/all', { params: { project_id: form.value.project_id } }))
    .map((m) => (m.name || '').trim()))
  const missing = [...new Set(rows.map((r) => (r.module || '').trim()).filter((n) => n && !existing.has(n)))]
  if (!missing.length) return
  const preview = missing.slice(0, 5).join('、') + (missing.length > 5 ? ` 等 ${missing.length} 个` : '')
  await ElMessageBox.confirm(`检测到 ${missing.length} 个系统不存在的模块，将自动新建：${preview}`, '新建模块确认', { type: 'warning' })
  for (const name of missing) {
    await request.post('/modules', { name, project_id: form.value.project_id, parent_id: 0 })
  }
}

async function doImport() {
  if (!selected.value.length) return ElMessage.warning('请先勾选要导入的用例')
  saving.value = true
  try {
    if (form.value.strategy === 'create') await prepareCreateStrategy(selected.value)
    const list = await request.get('/modules/all', { params: { project_id: form.value.project_id } })
    const nameMap = new Map(list.map((m) => [(m.name || '').trim(), m.id]))

    const items = await Promise.all(selected.value.map(async (r) => ({
      title: r.title, precondition: r.precondition, steps: r.steps, expected: r.expected,
      case_type: r.case_type, priority: r.priority, remark: r.remark,
      module_id: await resolveModuleId(r, nameMap),
    })))

    const agg = { created_count: 0, skipped_count: 0, errors: [] }
    for (let i = 0; i < items.length; i += CHUNK_SIZE) {
      const chunk = items.slice(i, i + CHUNK_SIZE)
      const res = await request.post('/cases/batch', {
        project_id: form.value.project_id, version_id: form.value.version_id, items: chunk,
      }, { timeout: 120000 })
      agg.created_count += res.created_count
      agg.skipped_count += res.skipped_count
      agg.errors.push(...(res.errors || []).map((e) => ({ ...e, index: e.index + i })))
    }
    result.value = agg
    step.value = 3
    if (agg.created_count) emit('imported')
  } catch (e) {
    // 新建模块确认被取消 / 请求失败：拦截器已提示，停留预览页
  } finally { saving.value = false }
}

async function downloadTemplate() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await axios.get('/api/cases/import/template', {
      responseType: 'blob',
      headers: { Authorization: token ? `Bearer ${token}` : '' },
    })
    const url = URL.createObjectURL(new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }))
    const a = document.createElement('a')
    a.href = url
    a.download = '测试用例导入模板.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('模板下载失败')
  }
}

function reset() {
  step.value = 1
  file.value = null
  parseData.value = null
  sheetName.value = ''
  fieldMapping.value = {}
  selected.value = []
  result.value = { created_count: 0, skipped_count: 0, errors: [] }
}

defineExpose({ open })
</script>

<style scoped>
.map-bar { display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.map-fields { display: flex; flex-wrap: wrap; gap: 6px 14px; flex: 1; }
.map-field { display: flex; align-items: center; gap: 4px; }
.map-label { font-size: 12px; color: #606266; }
.err-list { text-align: left; color: #f56c6c; font-size: 13px; line-height: 1.8; }
:deep(.skip-row) { color: #909399; background: #fafafa !important; }
</style>
