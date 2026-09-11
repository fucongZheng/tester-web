<template>
  <div class="share-page">
    <div class="share-header">
      <h2>🧪 {{ data.title || 'BUG 分享' }}</h2>
      <p class="meta">分享人 {{ data.created_by || '-' }} · {{ data.created_at }}{{ data.expires_at ? ' · 有效至 ' + data.expires_at : '' }} · 免登录，可改状态 / 修复人 / 备注</p>
    </div>
    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom:16px" />
    <el-table v-else :data="data.items" v-loading="loading" border stripe>
      <el-table-column prop="bug_no" label="编号" width="90" />
      <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
      <el-table-column label="复现步骤" min-width="240">
        <template #default="{ row }">
          <div class="steps-brief">{{ stepsBrief(row.steps) }}</div>
          <div class="steps-meta">
            <el-tag v-if="imgCount(row.steps)" size="small" type="info">{{ imgCount(row.steps) }} 张截图</el-tag>
            <el-button link type="primary" @click="openSteps(row)">查看详情</el-button>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="severity" label="严重等级" width="90">
        <template #default="{ row }"><el-tag :type="sevType(row.severity)" size="small">{{ row.severity }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="160">
        <template #default="{ row }">
          <el-select v-model="row.status" size="small" @change="save(row)">
            <el-option v-for="s in data.statuses" :key="s" :label="s" :value="s" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目" width="110" />
      <el-table-column prop="version_name" label="版本" width="80" />
      <el-table-column prop="assignee" label="经办人" width="80" />
      <el-table-column label="修复人" width="140">
        <template #default="{ row }">
          <el-select v-model="row.fixer" size="small" filterable clearable placeholder="选择" @change="save(row)">
            <el-option v-for="u in data.users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="备注" min-width="180">
        <template #default="{ row }">
          <div class="remark">{{ row.remark || '-' }}</div>
          <el-input v-model="row._note" size="small" placeholder="追加备注后回车保存" @keyup.enter="save(row)" />
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawer" :title="`复现步骤 · ${current.bug_no || ''} ${current.title || ''}`" size="720px">
      <div class="steps-full" v-html="safeSteps(current.steps)" @click="onImgClick" />
      <el-image-viewer v-if="preview" :url-list="previewList" :initial-index="previewIndex" @close="preview = false" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { sanitizeHtml } from '../../utils/sanitize'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const data = ref({ title: '', items: [], statuses: [], users: [] })
const drawer = ref(false)
const current = ref({})
const preview = ref(false)
const previewList = ref([])
const previewIndex = ref(0)

function sevType(s) { return { 致命: 'danger', 严重: 'warning', 一般: 'primary', 轻微: 'info', 建议: 'success' }[s] || '' }
function safeSteps(html) {
  const cleaned = sanitizeHtml(html || '')
  return cleaned || '<span style="color:#c0c4cc">无</span>'
}
function stripHtml(html) {
  const d = document.createElement('div')
  d.innerHTML = html || ''
  return (d.textContent || '').replace(/\s+/g, ' ').trim()
}
function stepsBrief(html) {
  const t = stripHtml(html)
  if (!t) return imgCount(html) ? '含截图，点击查看详情' : '无'
  return t.length > 80 ? `${t.slice(0, 80)}…` : t
}
function imgCount(html) {
  return (html || '').match(/<img\b/gi)?.length || 0
}
function openSteps(row) {
  current.value = row
  drawer.value = true
}
function onImgClick(e) {
  const img = e.target?.closest?.('img')
  if (!img) return
  const imgs = [...(e.currentTarget.querySelectorAll('img') || [])]
  previewList.value = imgs.map((i) => i.src).filter(Boolean)
  previewIndex.value = Math.max(0, imgs.indexOf(img))
  preview.value = true
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get(`/api/shares/public/${route.params.token}`)
    data.value = res.data
    ;(data.value.items || []).forEach(i => { i._note = '' })
  } catch (e) {
    error.value = e.response?.data?.detail || '分享链接无效'
  } finally { loading.value = false }
}
async function save(row) {
  try {
    const res = await axios.put(`/api/shares/public/${route.params.token}/bugs/${row.id}`, {
      status: row.status,
      fixer: row.fixer || '',
      note: row._note || '',
    })
    Object.assign(row, res.data)
    row._note = ''
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}
onMounted(load)
</script>

<style scoped>
.share-page { max-width: 1400px; margin: 0 auto; padding: 24px; }
.share-header h2 { margin-bottom: 6px; color: var(--c-text); }
.meta { color: var(--c-text-3); margin-bottom: 16px; font-size: 13px; }
.remark { white-space: pre-wrap; color: var(--c-text-2); font-size: 12px; margin-bottom: 6px; max-height: 80px; overflow: auto; }
.steps-brief { color: var(--c-text-2); font-size: 13px; line-height: 1.5; }
.steps-meta { margin-top: 4px; display: flex; align-items: center; gap: 8px; }
.steps-full { line-height: 1.7; color: var(--c-text); }
.steps-full :deep(img) { max-width: 100%; height: auto; display: block; margin: 10px 0; border: 1px solid var(--c-border); border-radius: var(--r-xs); cursor: zoom-in; }
.steps-full :deep(ul), .steps-full :deep(ol) { padding-left: 18px; }
.steps-full :deep(p) { margin: 0 0 8px; }
</style>
