<template>
  <div>
    <div class="toolbar">
      <el-select v-model="project_id" placeholder="项目" clearable filterable style="width:180px" @change="onProject">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="version_id" placeholder="版本" clearable filterable style="width:140px" @change="reload">
        <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
      </el-select>
      <el-select v-model="module_id" placeholder="模块" clearable filterable style="width:140px" @change="reload">
        <el-option v-for="m in modules" :key="m.id" :label="m.name" :value="m.id" />
      </el-select>
    </div>

    <el-row :gutter="16">
      <el-col :span="4" v-for="c in cards" :key="c.label">
        <el-card shadow="never" class="stat-card clickable" @click="goList(c.path, c.filter)">
          <div class="stat-label">
            <span class="stat-dot" :style="{ background: c.color }"></span>
            {{ c.label }}
          </div>
          <div class="stat-value">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="severityRef" class="chart"></div></el-card></el-col>
      <el-col :span="12"><el-card><div ref="statusRef" class="chart"></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="rankRef" class="chart"></div></el-card></el-col>
      <el-col :span="12"><el-card><div ref="moduleRef" class="chart"></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="projectRef" class="chart"></div></el-card></el-col>
      <el-col :span="12"><el-card><div ref="stageRef" class="chart"></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="trendRef" class="chart"></div></el-card></el-col>
      <el-col :span="12"><el-card><div ref="progressRef" class="chart"></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <el-card header="模块维度统计（点击数字下钻）">
          <el-table :data="moduleRows" size="small" max-height="300">
            <el-table-column prop="name" label="模块" min-width="120" />
            <el-table-column label="需求" width="70">
              <template #default="{ row }"><el-button link type="primary" @click="goList('/requirement', row.filter)">{{ row.requirement }}</el-button></template>
            </el-table-column>
            <el-table-column label="用例" width="70">
              <template #default="{ row }"><el-button link type="primary" @click="goList('/case', row.filter)">{{ row.case }}</el-button></template>
            </el-table-column>
            <el-table-column label="BUG" width="70">
              <template #default="{ row }"><el-button link type="primary" @click="goBug(row.filter)">{{ row.bug }}</el-button></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="测试流程看板">
          <el-table :data="flows" size="small" max-height="300" @row-click="goFlow">
            <el-table-column prop="project_name" label="项目" width="120" />
            <el-table-column prop="version_no" label="版本" width="90" />
            <el-table-column prop="current_stage_label" label="当前环节" />
            <el-table-column prop="current_round" label="轮次" width="60" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === '已完成' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '../../api/request'

const router = useRouter()
const projects = ref([]); const versions = ref([]); const modules = ref([])
const project_id = ref(''); const version_id = ref(''); const module_id = ref('')
const PALETTE = ['#F37021', '#3A6B8C', '#6B9B7A', '#D4A537', '#E8843C', '#7A848B']
const cards = ref([
  { label: '项目', value: 0, color: '#3A6B8C', path: '/project' },
  { label: '版本', value: 0, color: '#6B9B7A', path: '/version' },
  { label: '需求', value: 0, color: '#D4A537', path: '/requirement' },
  { label: '测试用例', value: 0, color: '#F37021', path: '/case' },
  { label: 'BUG', value: 0, color: '#E8843C', path: '/bug' },
  { label: '进行中流程', value: 0, color: '#3A6B8C', path: '/flow' },
])
const flows = ref([])
const moduleRows = ref([])
const charts = {}
const severityRef = ref(); const statusRef = ref(); const rankRef = ref()
const moduleRef = ref(); const projectRef = ref(); const stageRef = ref()
const trendRef = ref(); const progressRef = ref()

function scopeParams() {
  const p = {}
  if (project_id.value) p.project_id = project_id.value
  if (version_id.value) p.version_id = version_id.value
  if (module_id.value) p.module_id = module_id.value
  return p
}
function goList(path, extra) {
  const q = { ...scopeParams(), ...(extra || {}) }
  Object.keys(q).forEach((k) => { if (q[k] === '' || q[k] == null) delete q[k] })
  router.push({ path, query: q })
}
function goBug(extra) { goList('/bug', extra) }
function goFlow() {
  if (router.hasRoute('m-flow') || router.getRoutes().some((r) => r.path === '/flow')) {
    router.push('/flow')
    return
  }
  ElMessage.warning('当前角色没有测试流程权限')
}

function bindClick(chart, items) {
  chart.off('click')
  chart.on('click', (p) => {
    const hit = (items || [])[p.dataIndex]
    if (hit?.filter) goBug(hit.filter)
  })
}
function pie(el, data, title, key) {
  if (!el) return
  if (charts[key]) charts[key].dispose()
  const chart = echarts.init(el)
  charts[key] = chart
  chart.setOption({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    color: PALETTE,
    series: [{
      type: 'pie', radius: ['35%', '65%'],
      data: (data || []).map((d) => ({ name: d.name, value: d.value })),
      label: { formatter: '{b}: {c}' },
    }],
  })
  bindClick(chart, data)
}
function hbar(el, data, title, key) {
  if (!el) return
  if (charts[key]) charts[key].dispose()
  const list = (data || []).slice()
  const n = Math.max(list.length, 1)
  el.style.height = `${Math.min(Math.max(300, 48 + n * 28), 720)}px`
  const chart = echarts.init(el)
  charts[key] = chart
  const names = list.map((d) => d.name).reverse()
  const values = list.map((d) => d.value).reverse()
  chart.setOption({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params?.[0]
        if (!p) return ''
        return `${p.name}<br/>BUG：${p.value}`
      },
    },
    grid: { left: 12, right: 40, top: 40, bottom: n > 16 ? 36 : 16, containLabel: true },
    dataZoom: n > 16 ? [{ type: 'inside', yAxisIndex: 0, zoomOnMouseWheel: true, moveOnMouseMove: true }] : [],
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { width: 160, overflow: 'truncate', ellipsis: '…', interval: 0 },
      triggerEvent: true,
    },
    series: [{
      type: 'bar', data: values,
      itemStyle: { color: '#E8843C' }, barMaxWidth: 18,
      label: { show: true, position: 'right' },
    }],
  })
  bindClick(chart, [...list].reverse())
}
function line(el, dates, newData, closedData) {
  if (!el) return
  if (charts.trend) charts.trend.dispose()
  const chart = echarts.init(el)
  charts.trend = chart
  chart.setOption({
    title: { text: 'BUG 趋势（近7天）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增', '关闭'], bottom: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    color: ['#F37021', '#6B9B7A'],
    series: [
      { name: '新增', type: 'line', smooth: true, data: newData, areaStyle: { color: 'rgba(243,112,33,.12)' } },
      { name: '关闭', type: 'line', smooth: true, data: closedData },
    ],
  })
}
function bar(el, data) {
  if (!el) return
  if (charts.progress) charts.progress.dispose()
  const chart = echarts.init(el)
  charts.progress = chart
  chart.setOption({
    title: { text: '各版本用例通过率', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: data.map((d) => d.version) },
    yAxis: { type: 'value', max: 100 },
    series: [{ type: 'bar', data: data.map((d) => d.rate), itemStyle: { color: '#6B9B7A' }, barMaxWidth: 40 }],
  })
}

async function onProject() {
  version_id.value = ''; module_id.value = ''
  versions.value = project_id.value ? await request.get('/versions/all', { params: { project_id: project_id.value } }) : []
  modules.value = project_id.value ? await request.get('/modules/all', { params: { project_id: project_id.value } }) : []
  reload()
}
async function reload() {
  const p = scopeParams()
  const [summary, sev, status, rank, mods, proj, stage, trend, progress, board, mstats] = await Promise.all([
    request.get('/dashboard/summary'),
    request.get('/dashboard/bug-severity', { params: p }),
    request.get('/dashboard/bug-status', { params: p }),
    request.get('/dashboard/bug-rank', { params: { ...p, limit: 20 } }),
    request.get('/dashboard/bug-module', { params: p }),
    request.get('/dashboard/bug-project'),
    request.get('/dashboard/bug-stage', { params: p }),
    request.get('/dashboard/bug-trend', { params: { ...p, days: 7 } }),
    request.get('/dashboard/case-progress'),
    request.get('/dashboard/flow-board'),
    request.get('/dashboard/module-stats', { params: p }),
  ])
  cards.value[0].value = summary.project
  cards.value[1].value = summary.version
  cards.value[2].value = summary.requirement
  cards.value[3].value = summary.case
  cards.value[4].value = summary.bug
  cards.value[5].value = summary.flow
  cards.value[0].filter = p
  cards.value[1].filter = p
  cards.value[2].filter = p
  cards.value[3].filter = p
  cards.value[4].filter = p
  flows.value = board
  moduleRows.value = mstats
  await nextTick()
  pie(severityRef.value, sev, 'BUG 严重等级', 'sev')
  pie(statusRef.value, status, 'BUG 状态', 'status')
  hbar(rankRef.value, rank.slice(0, 6), '研发 BUG 数（考核）', 'rank')
  hbar(moduleRef.value, mods.slice(0, 6), 'BUG 按模块', 'mod')
  hbar(projectRef.value, proj.slice(0, 6), 'BUG 按项目', 'proj')
  pie(stageRef.value, stage, 'BUG 发现阶段', 'stage')
  line(trendRef.value, trend.dates, trend.new, trend.closed)
  bar(progressRef.value, progress)
}
onMounted(async () => {
  projects.value = await request.get('/projects/all')
  await reload()
})
</script>

<style scoped>
.stat-card { padding: 4px 0; }
.clickable { cursor: pointer; transition: box-shadow .15s; }
.clickable:hover { box-shadow: var(--sh-2); }
.stat-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--c-text-2);
  font-weight: 500;
}
.stat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 38px; margin-top: 8px; color: var(--c-text); }
.chart { height: 300px; }
</style>
