<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-select v-model="project_id" placeholder="项目" clearable filterable style="width:170px" @change="onProject">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="version_id" placeholder="版本" clearable filterable style="width:140px" @change="load">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="startDialog = true">启动测试流程</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      :data="items"
      v-loading="loading"
      border
      :scrollable="false"
      :height="tableHeight"
      style="width: 100%"
    >
      <el-table-column type="expand" width="50">
        <template #default="{ row }">
          <el-timeline style="padding: 12px 24px">
            <el-timeline-item v-for="s in row.stages" :key="s.id"
              :type="stageTimelineType(s.status)" :timestamp="s.started_at || ''">
              <div>
                <b>环节{{ s.stage_no }}：{{ s.stage_name }}</b>
                <el-tag size="small" :type="stageTagType(s.status)" style="margin-left:8px">{{ s.status }}</el-tag>
                <span v-if="s.operator" style="margin-left:8px;color:var(--c-text-3)">操作人：{{ s.operator }}</span>
                <div v-if="s.remark" style="color:var(--c-text-2);margin-top:4px">{{ s.remark }}</div>
                <div v-if="(s.attachments || []).length" style="margin-top:6px">
                  <a v-for="(f, i) in s.attachments" :key="i" :href="f.url" target="_blank" style="margin-right:10px">📎 {{ f.name }}</a>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </template>
      </el-table-column>

      <el-table-column prop="id" label="ID" width="60" align="center" />
      <el-table-column prop="project_name" label="项目" width="150" show-overflow-tooltip />
      <el-table-column prop="version_name" label="版本名称" width="150" show-overflow-tooltip />
      <el-table-column prop="version_no" label="版本" width="100" align="center" />
      <el-table-column prop="current_stage_label" label="当前环节" width="180" show-overflow-tooltip>
        <template #default="{ row }"><b style="color:var(--c-orange-500)">{{ row.current_stage_label }}</b></template>
      </el-table-column>
      <el-table-column prop="current_round" label="轮次" width="60" align="center" />
      <el-table-column prop="status" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="{ 已完成: 'success', 已挂起: 'info', 进行中: 'warning' }[row.status] || 'warning'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="started_at" label="开始时间" width="160" />

      <!-- 操作列（固定右侧） -->
      <el-table-column label="操作" min-width="220" fixed="right" align="center">
        <template #default="{ row }">
          <div class="action-buttons">
            <template v-if="row.status === '进行中'">
              <el-button size="small" type="primary" @click="openAction(row, 'pass')">通过</el-button>
              <el-button v-if="metaOf(row).skippable" size="small" @click="openAction(row, 'skip')">跳过</el-button>
              <el-button v-if="metaOf(row).rejectKind" size="small" type="danger" @click="openAction(row, 'reject')">驳回</el-button>
            </template>
            <span v-else style="color:#c0c4cc">{{ row.status === '已挂起' ? '已挂起' : '已结束' }}</span>
            <el-button v-if="isAdmin" size="small" type="danger" link @click="del(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页器 -->
    <Pager v-model:page="page" v-model:size="size" :total="allItems.length" />

    <!-- 启动流程 -->
    <el-dialog v-model="startDialog" title="启动测试流程" width="440px">
      <el-form label-width="80px">
        <el-form-item label="项目" required>
          <el-select v-model="startForm.project_id" style="width:100%" filterable @change="loadStartVersions">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" /></el-select>
        </el-form-item>
        <el-form-item label="版本" required>
          <el-select v-model="startForm.version_id" style="width:100%" filterable>
            <el-option v-for="v in startVersions" :key="v.id" :label="v.version_no" :value="v.id" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="startDialog = false">取消</el-button>
        <el-button type="primary" @click="doStart">启动</el-button>
      </template>
    </el-dialog>

    <!-- 流转操作 -->
    <el-dialog v-model="actionDialog" :title="actionTitle" width="520px">
      <el-form label-width="80px">
        <el-form-item label="备注">
          <el-input v-model="actionForm.remark" type="textarea" :rows="3" :placeholder="actionPlaceholder" />
        </el-form-item>
        <el-form-item label="佐证附件">
          <el-upload
            action="/api/uploads"
            :headers="uploadHeaders"
            :on-success="onUploadSuccess"
            :on-remove="onUploadRemove"
            :file-list="fileList"
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip"
            multiple
          >
            <el-button type="primary" plain>上传附件</el-button>
            <template #tip><div class="el-upload__tip">截图、日志等，单文件不超过 20MB</div></template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="actionDialog = false">取消</el-button>
        <el-button :type="actionType === 'reject' ? 'danger' : 'primary'" @click="doAction">确认</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const router = useRouter()

const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
const fileList = ref([])
const attachments = ref([])

const allItems = ref([]); const loading = ref(false)
const page = ref(1); const size = ref(10)
const items = computed(() => {
  const start = (page.value - 1) * size.value
  return allItems.value.slice(start, start + size.value)
})
const projects = ref([]); const versions = ref([])
const project_id = ref(''); const version_id = ref('')
const startDialog = ref(false); const startForm = ref({ project_id: '', version_id: '' }); const startVersions = ref([])
const actionDialog = ref(false); const actionForm = ref({ remark: '' })
const actionTarget = ref(null); const actionType = ref('pass')

// 环节 code → 界面行为（按钮显示、弹窗文案），与后端 flow_stages.py 对应。
// 后端调整环节时只需同步这份声明式配置，不写环节序号。
const STAGE_META = {
  case_writing: { passTitle: '完成用例编写，进入用例评审', passTip: '填写用例编写完成说明' },
  case_review: { passTitle: '用例评审通过，进入开发提测', passTip: '填写评审结论说明' },
  dev_handover: { rejectKind: 'handover', passTitle: '提测通过，进入 AI 接口测试', passTip: '填写提测验证说明' },
  ai_api: { skippable: true },
  ai_ui: { skippable: true },
  manual: {},
  regression: {},
  acceptance: { rejectKind: 'acceptance' },
  launch: {},
}
const metaOf = row => STAGE_META[row.current_stage_code] || {}

const actionTitle = computed(() => {
  const meta = metaOf(actionTarget.value || {})
  if (actionType.value === 'skip') return '跳过当前环节'
  if (actionType.value === 'reject') {
    return meta.rejectKind === 'handover' ? '驳回开发提测' : '产品验收驳回'
  }
  return meta.passTitle || '进入下一环节'
})
const actionPlaceholder = computed(() => {
  const meta = metaOf(actionTarget.value || {})
  if (actionType.value === 'skip') return '填写跳过原因'
  if (actionType.value === 'reject') {
    return meta.rejectKind === 'handover' ? '填写驳回提测原因（必填）' : '填写验收不通过的原因'
  }
  return meta.passTip || '填写本环节通过说明'
})

function stageTagType(s) { return { 通过: 'success', 驳回: 'danger', 跳过: 'info', 进行中: 'primary', 待开始: 'info' }[s] || '' }
function stageTimelineType(s) { return { 通过: 'success', 驳回: 'danger', 跳过: 'info', 进行中: 'primary' }[s] || '' }

const tableHeight = ref(600)   // 默认高度（可手动调整）

async function loadVersions() {
  versions.value = await request.get('/versions/all', { params: { project_id: project_id.value } })
}
async function onProject() {
  version_id.value = ''
  await loadVersions()
  load()
}
async function load() {
  loading.value = true
  try { allItems.value = await request.get('/flow', { params: { project_id: project_id.value, version_id: version_id.value } }); page.value = 1 }
  finally { loading.value = false }
}
async function loadStartVersions() {
  startForm.value.version_id = ''
  startVersions.value = await request.get('/versions/all', { params: { project_id: startForm.value.project_id } })
}
async function doStart() {
  if (!startForm.value.project_id || !startForm.value.version_id) return ElMessage.warning('项目和版本必填')
  await request.post('/flow/start', startForm.value)
  ElMessage.success('流程已启动')
  startDialog.value = false
  startForm.value = { project_id: '', version_id: '' }
  load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除「${row.project_name} ${row.version_no}」的测试流程？删除后不可恢复。`, '提示', { type: 'warning' })
  await request.delete(`/flow/${row.id}`)
  ElMessage.success('已删除')
  load()
}
async function maybeRemindReport(row) {
  if (row.current_stage_code !== 'acceptance') return true
  try {
    const res = await request.get('/reports', {
      params: { project_id: row.project_id, version_id: row.version_id, page: 1, size: 1 },
    })
    if (res.total) return true
  } catch (e) {
    return true
  }
  try {
    await ElMessageBox.confirm(
      '产品验收前必须先有测试报告。上一环节未完成，不能进入下一环节。',
      '尚未创建测试报告',
      { confirmButtonText: '去创建报告', cancelButtonText: '取消', type: 'warning' },
    )
    router.push('/report')
    return false
  } catch (e) {
    return false
  }
}
async function openAction(row, type) {
  const cont = await maybeRemindReport(row)
  if (!cont) return
  actionTarget.value = row
  actionType.value = type
  actionForm.value = { remark: '' }
  fileList.value = []
  attachments.value = []
  actionDialog.value = true
}
function onUploadSuccess(res, file) {
  if (res && res.url) {
    attachments.value.push({ name: res.name || file.name, url: res.url, size: res.size })
  }
}
function onUploadRemove(file) {
  const url = file.response?.url || file.url
  attachments.value = attachments.value.filter(a => a.url !== url)
}
async function doAction() {
  if (actionType.value === 'reject' && metaOf(actionTarget.value).rejectKind === 'handover' && !(actionForm.value.remark || '').trim()) {
    return ElMessage.warning('驳回提测必须填写备注')
  }
  const url = `/flow/${actionTarget.value.id}/${actionType.value}`
  await request.post(url, { ...actionForm.value, attachments: attachments.value })
  ElMessage.success('操作成功')
  actionDialog.value = false
  load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  await loadVersions()
  load()
})
</script>

<style scoped>
/* 解决操作列右侧空白问题 */
.el-table {
  width: 100% !important;
}

/* 固定列样式优化 */
.el-table__fixed-right {
  right: 0 !important;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.05) !important;
}

.el-table__fixed-right-wrapper {
  max-height: 100% !important;
}

/* 操作按钮容器 */
.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
}

/* 操作按钮在固定列中的样式优化 */
.action-buttons .el-button {
  margin: 2px 0;
  padding: 5px 10px;
  font-size: 12px;
}

.action-buttons .el-button.is-link {
  margin-left: 4px;
}

/* 当只有删除按钮时的对齐 */
.action-buttons:has(> span:only-child) {
  justify-content: center;
}

/* 分页器撑满右侧 */
.pager-wrapper {
  margin: 0 -12px;
  padding: 12px 12px 0;
  text-align: right;
}

/* 工具栏样式 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 表格展开图标样式 */
.el-table__expand-icon {
  font-size: 14px;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-filters {
    flex-wrap: wrap;
  }
  
  .toolbar-filters .el-select {
    flex: 1;
    min-width: 120px;
  }
  
  .action-buttons {
    flex-wrap: wrap;
    gap: 2px;
  }
  
  .action-buttons .el-button {
    padding: 4px 8px;
    font-size: 11px;
  }
}

/* 修复表格边框在固定列下的显示 */
.el-table--border .el-table__fixed-right {
  border-left: 1px solid #ebeef5;
}

/* 确保操作列内容不溢出 */
.el-table__body-wrapper .cell {
  overflow: visible !important;
}
</style>