<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="4" v-for="c in cards" :key="c.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" :style="{color:c.color}">{{ c.value }}</div>
          <div class="stat-label">{{ c.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="severityRef" class="chart"></div></el-card></el-col>
      <el-col :span="12"><el-card><div ref="statusRef" class="chart"></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="24"><el-card><div ref="trendRef" class="chart"></div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="progressRef" class="chart"></div></el-card></el-col>
      <el-col :span="12">
        <el-card header="测试流程看板">
          <el-table :data="flows" size="small" max-height="300">
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
import * as echarts from 'echarts'
import request from '../../api/request'

const cards = ref([
  { label: '项目', value: 0, color: '#409eff' },
  { label: '版本', value: 0, color: '#67c23a' },
  { label: '需求', value: 0, color: '#e6a23c' },
  { label: '测试用例', value: 0, color: '#909399' },
  { label: 'BUG', value: 0, color: '#f56c6c' },
  { label: '进行中流程', value: 0, color: '#8e44ad' },
])
const flows = ref([])
const severityRef = ref()
const statusRef = ref()
const trendRef = ref()
const progressRef = ref()

function pie(el, data, title) {
  if (!el) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['35%', '65%'],
      data, label: { formatter: '{b}: {c}' },
    }],
  })
}

function line(el, dates, newData, closedData) {
  if (!el) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: 'BUG 趋势（近30天）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增', '关闭'], bottom: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value' },
    series: [
      { name: '新增', type: 'line', smooth: true, data: newData, areaStyle: {} },
      { name: '关闭', type: 'line', smooth: true, data: closedData },
    ],
  })
}

function bar(el, data) {
  if (!el) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '各版本用例通过率', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: data.map((d) => d.version) },
    yAxis: { type: 'value', max: 100 },
    series: [{ type: 'bar', data: data.map((d) => d.rate), itemStyle: { color: '#67c23a' }, barMaxWidth: 40 }],
  })
}

onMounted(async () => {
  const [summary, sev, status, trend, progress, board] = await Promise.all([
    request.get('/dashboard/summary'),
    request.get('/dashboard/bug-severity'),
    request.get('/dashboard/bug-status'),
    request.get('/dashboard/bug-trend'),
    request.get('/dashboard/case-progress'),
    request.get('/dashboard/flow-board'),
  ])
  cards.value[0].value = summary.project
  cards.value[1].value = summary.version
  cards.value[2].value = summary.requirement
  cards.value[3].value = summary.case
  cards.value[4].value = summary.bug
  cards.value[5].value = summary.flow
  flows.value = board
  await nextTick()
  pie(severityRef.value, sev, 'BUG 严重等级分布')
  pie(statusRef.value, status, 'BUG 状态分布')
  line(trendRef.value, trend.dates, trend.new, trend.closed)
  bar(progressRef.value, progress)
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { color: #909399; font-size: 13px; margin-top: 6px; }
.chart { height: 300px; }
</style>
