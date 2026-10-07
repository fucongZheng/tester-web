<template>
  <el-dialog
    :model-value="modelValue"
    title="选择用例"
    width="980px"
    top="6vh"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
  >
    <!-- 筛选区：项目 / 版本 / 类型 / 模块 / 编号标题 -->
    <div class="picker-filters">
      <el-select v-model="filters.project_id" placeholder="项目" clearable filterable style="width:170px" @change="onFilterProject">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filters.version_id" placeholder="版本" clearable filterable style="width:120px" @change="reload">
        <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
      </el-select>
      <el-select v-model="filters.case_type" placeholder="类型" clearable style="width:100px" @change="reload">
        <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
      </el-select>
      <el-select v-model="filters.module_id" placeholder="模块" clearable filterable style="width:140px" @change="reload">
        <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="编号/标题搜索" clearable style="width:200px"
                @keyup.enter="reload" @clear="reload" />
      <el-button type="primary" @click="reload">查询</el-button>
    </div>

    <div class="picker-meta">
      <span>已选 <b>{{ selected.length }}</b> 条</span>
      <span class="tip">切换筛选不会丢失已选；勾选表头复选框即全选当前筛选结果</span>
      <span>
        <el-button size="small" @click="selectAllVisible">全选当前结果</el-button>
        <el-button size="small" @click="clearAll">清空已选</el-button>
      </span>
    </div>

    <el-table ref="tableRef" :data="rows" v-loading="loading" border stripe max-height="430"
              row-key="id" @selection-change="onSelectionChange">
      <el-table-column type="selection" width="42" reserve-selection :selectable="isSelectable" />
      <el-table-column prop="case_no" label="编号" width="110" />
      <el-table-column label="标题" min-width="230" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.title }}</span>
          <el-tag v-if="!isSelectable(row)" size="small" type="info" style="margin-left:6px">已选为{{ otherLabel }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="case_type" label="类型" width="80" align="center" />
      <el-table-column prop="priority" label="优先级" width="80" align="center" />
      <el-table-column prop="module_name" label="模块" width="120" show-overflow-tooltip />
      <el-table-column prop="version_name" label="版本" width="90" align="center" />
    </el-table>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="confirm">确定（已选 {{ selected.length }} 条）</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * 通用用例选择弹窗：项目/版本/类型/模块/编号标题筛选 + 勾选（支持全选），
 * 切换筛选保留已选（reserve-selection），excludeIds 里的用例禁选（两组互斥）。
 * confirm(ids, metas)：ids 为选中顺序的用例 id，metas 为 [{id,no,name}] 供外层展示标签。
 */
import { ref, computed, nextTick } from 'vue'
import request from '../api/request'

const props = defineProps({
  modelValue: Boolean,
  selected: { type: Array, default: () => [] },      // 已选 id
  excludeIds: { type: Array, default: () => [] },     // 互斥：另一组已选 id，禁选
  otherLabel: { type: String, default: '另一组' },    // 禁选行的提示，如「核心用例」
  projectId: { type: [Number, String], default: '' }, // 初始项目
  versionId: { type: [Number, String], default: '' }, // 初始版本
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const projects = ref([]); const versions = ref([]); const modules = ref([]); const typeOptions = ref([])
const filters = ref({ project_id: '', version_id: '', case_type: '', module_id: '', keyword: '' })
const rows = ref([]); const loading = ref(false)
const selected = ref([])          // 有序 id 列表
const metaMap = ref({})           // id -> {id,no,name}
const tableRef = ref()
const syncing = ref(false)

const excludeSet = computed(() => new Set(props.excludeIds || []))
const isSelectable = row => !excludeSet.value.has(row.id)

function onOpen() {
  selected.value = (props.selected || []).slice()
  filters.value = { project_id: props.projectId || '', version_id: props.versionId || '',
                    case_type: '', module_id: '', keyword: '' }
  loadBase()
}
async function loadBase() {
  projects.value = await request.get('/projects/all')
  typeOptions.value = (await request.get('/cases/options')).case_type || []
  await loadVersionsAndModules()
  reload()
}
async function loadVersionsAndModules() {
  const pid = filters.value.project_id
  versions.value = pid ? await request.get('/versions/all', { params: { project_id: pid } }) : []
  modules.value = pid ? await request.get('/modules/all', { params: { project_id: pid } }) : []
  if (filters.value.version_id && !versions.value.some(v => v.id === filters.value.version_id)) {
    filters.value.version_id = ''
  }
}
async function onFilterProject() {
  filters.value.version_id = ''; filters.value.module_id = ''
  await loadVersionsAndModules()
  reload()
}
async function reload() {
  loading.value = true
  try {
    const params = { page: 1, size: 1000 }
    if (filters.value.project_id) params.project_id = filters.value.project_id
    if (filters.value.version_id) params.version_id = filters.value.version_id
    if (filters.value.case_type) params.case_type = filters.value.case_type
    if (filters.value.module_id) params.module_id = filters.value.module_id
    if (filters.value.keyword) params.keyword = filters.value.keyword
    const res = await request.get('/cases', { params })
    rows.value = res.items
    rows.value.forEach((c) => { metaMap.value[c.id] = { id: c.id, no: c.case_no, name: c.title } })
    await syncSelection()
  } finally { loading.value = false }
}
function onSelectionChange(selRows) {
  if (syncing.value) return
  selected.value = selRows.filter(isSelectable).map(r => r.id)
}
async function syncSelection() {
  await nextTick()
  const table = tableRef.value
  if (!table) return
  syncing.value = true
  const set = new Set(selected.value)
  rows.value.forEach((c) => table.toggleRowSelection(c, set.has(c.id)))
  await nextTick()
  syncing.value = false
}
async function selectAllVisible() {
  const add = rows.value.filter(isSelectable).map(r => r.id)
  selected.value = [...new Set([...selected.value, ...add])]
  await syncSelection()
}
async function clearAll() {
  selected.value = []
  tableRef.value?.clearSelection()
}
function confirm() {
  const metas = selected.value.map(id => metaMap.value[id]).filter(Boolean)
  emit('confirm', selected.value.slice(), metas)
  emit('update:modelValue', false)
}
</script>

<style scoped>
.picker-filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.picker-meta {
  display: flex; align-items: center; gap: 12px; margin-bottom: 8px; font-size: 13px;
  color: var(--c-text-2, #606266);
}
.picker-meta .tip { color: var(--c-text-3, #909399); font-size: 12px; flex: 1; }
.picker-meta b { color: var(--c-orange-500, #e6720a); }
</style>
