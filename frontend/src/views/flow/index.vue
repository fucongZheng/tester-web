<template>
  <el-card>
    <div class="toolbar">
      <el-select v-model="project_id" placeholder="项目" clearable filterable style="width:170px" @change="load">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="version_id" placeholder="版本" clearable filterable style="width:140px" @change="load">
        <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
      </el-select>
      <el-button type="success" @click="startDialog = true">启动测试流程</el-button>
    </div>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column type="expand">
        <template #default="{ row }">
          <el-timeline style="padding: 12px 24px">
            <el-timeline-item v-for="s in row.stages" :key="s.id"
              :type="stageTimelineType(s.status)" :timestamp="s.started_at || ''">
              <div>
                <b>环节{{ s.stage_no }}：{{ s.stage_name }}</b>
                <el-tag size="small" :type="stageTagType(s.status)" style="margin-left:8px">{{ s.status }}</el-tag>
                <span v-if="s.operator" style="margin-left:8px;color:#909399">操作人：{{ s.operator }}</span>
                <div v-if="s.remark" style="color:#606266;margin-top:4px">{{ s.remark }}</div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="project_name" label="项目" width="150" />
      <el-table-column prop="version_no" label="版本" width="100" />
      <el-table-column prop="current_stage_label" label="当前环节" width="150">
        <template #default="{ row }"><b style="color:#409eff">{{ row.current_stage_label }}</b></template>
      </el-table-column>
      <el-table-column prop="current_round" label="轮次" width="60" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === '已完成' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="started_at" label="开始时间" width="160" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === '进行中'">
            <el-button size="small" type="primary" @click="openAction(row, 'pass')">通过</el-button>
            <el-button v-if="[1, 2, 4].includes(row.current_stage)" size="small" @click="openAction(row, 'skip')">跳过</el-button>
            <el-button v-if="row.current_stage === 5" size="small" type="danger" @click="openAction(row, 'reject')">驳回</el-button>
          </template>
          <span v-else style="color:#c0c4cc">已结束</span>
        </template>
      </el-table-column>
    </el-table>

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
    <el-dialog v-model="actionDialog" :title="actionTitle" width="440px">
      <el-form label-width="80px">
        <el-form-item label="备注">
          <el-input v-model="actionForm.remark" type="textarea" :rows="3" :placeholder="actionPlaceholder" />
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
import { ElMessage } from 'element-plus'
import request from '../../api/request'

const items = ref([]); const loading = ref(false)
const projects = ref([]); const versions = ref([])
const project_id = ref(''); const version_id = ref('')
const startDialog = ref(false); const startForm = ref({ project_id: '', version_id: '' }); const startVersions = ref([])
const actionDialog = ref(false); const actionForm = ref({ remark: '' })
const actionTarget = ref(null); const actionType = ref('pass')

const actionTitle = computed(() => ({ pass: '进入下一环节', skip: '跳过当前环节', reject: '产品验收驳回' }[actionType.value]))
const actionPlaceholder = computed(() => ({ pass: '填写本环节通过说明', skip: '填写跳过原因', reject: '填写验收不通过的原因' }[actionType.value]))

function stageTagType(s) { return { 通过: 'success', 驳回: 'danger', 跳过: 'info', 进行中: 'primary', 待开始: 'info' }[s] || '' }
function stageTimelineType(s) { return { 通过: 'success', 驳回: 'danger', 跳过: 'info', 进行中: 'primary' }[s] || '' }

async function load() {
  loading.value = true
  try { items.value = await request.get('/flow', { params: { project_id: project_id.value, version_id: version_id.value } }) }
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
function openAction(row, type) {
  actionTarget.value = row
  actionType.value = type
  actionForm.value = { remark: '' }
  actionDialog.value = true
}
async function doAction() {
  const url = `/flow/${actionTarget.value.id}/${actionType.value}`
  await request.post(url, actionForm.value)
  ElMessage.success('操作成功')
  actionDialog.value = false
  load()
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  versions.value = await request.get('/versions/all')
  load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
</style>
