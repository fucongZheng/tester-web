<template>
  <div class="qa-page">
    <el-card class="qa-side" shadow="never">
      <div class="side-head">
        <span>历史会话</span>
        <el-button type="primary" size="small" @click="newSession">新会话</el-button>
      </div>
      <el-scrollbar class="side-scroll">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="sess"
          :class="{ active: sessionId === s.id }"
          @click="openSession(s.id)"
        >
          <div class="sess-title">{{ s.title || '新会话' }}</div>
          <div class="sess-meta">
            <el-tag v-if="s.risk_level" size="small" :type="riskType(s.risk_level)" effect="plain">{{ riskLabel(s.risk_level) }}</el-tag>
            <span>{{ s.project_name || '全库' }}{{ s.version_no ? ' / ' + s.version_no : '' }}</span>
          </div>
          <el-button class="sess-del" link type="danger" @click.stop="delSession(s)">删除</el-button>
        </div>
        <el-empty v-if="!sessions.length" description="还没有问过" :image-size="64" />
      </el-scrollbar>
    </el-card>

    <el-card class="qa-main" shadow="never">
      <div class="toolbar">
        <el-select v-model="projectId" placeholder="项目（可空=全库）" clearable filterable style="width:200px" @change="onProject">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-select v-model="versionId" placeholder="版本（建议选择）" clearable filterable style="width:160px" @change="onScope">
          <el-option v-for="v in versions" :key="v.id" :label="v.version_no" :value="v.id" />
        </el-select>
        <el-button @click="loadSnapshot">刷新快照</el-button>
        <span class="hint">只根据系统数据回答，不编编号。选版本后判断更准。</span>
      </div>

      <div class="chat" ref="chatRef" v-loading="asking">
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-title">AI 问质</div>
          <div class="welcome-sub">问上线风险、覆盖缺口、未关闭缺陷、流程卡点。右侧是本次依据，可点进去核对。</div>
          <div class="quick">
            <el-tag v-for="q in quick" :key="q" class="qtag" effect="plain" @click="ask(q)">{{ q }}</el-tag>
          </div>
        </div>
        <div v-for="m in messages" :key="m.id || m._tmp" :class="['bubble', m.role]">
          <div class="who">{{ m.role === 'user' ? '管理员' : '质量参谋' }}</div>
          <div v-if="m.role === 'user'" class="text">{{ m.content }}</div>
          <div v-else class="md" v-html="renderMarkdown(m.content)"></div>
        </div>
      </div>

      <div class="composer">
        <div class="quick slim" v-if="messages.length">
          <el-tag v-for="q in quick" :key="q" class="qtag" effect="plain" @click="ask(q)">{{ q }}</el-tag>
        </div>
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="例如：这个版本能不能上线？未覆盖需求有哪些？（Ctrl+Enter 发送）"
          @keydown="onKey"
        />
        <div class="send-row">
          <span class="hint">依据来自当前项目/版本快照，AI 不能改数据。</span>
          <el-button type="primary" :loading="asking" :disabled="!question.trim()" @click="ask()">发送</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="qa-evidence" shadow="never">
      <template #header>
        <div class="ev-head">
          <span>本次依据</span>
          <el-tag v-if="snap.risk_level" :type="riskType(snap.risk_level)" size="small">{{ riskLabel(snap.risk_level) }}</el-tag>
        </div>
      </template>
      <el-scrollbar class="ev-scroll">
        <div v-if="!snap.scope" class="hint">选择范围或提问后，这里展示数字与可跳转清单。</div>
        <template v-else>
          <div class="ev-scope">{{ snap.scope.project_name }}{{ snap.scope.version_no ? ' / ' + snap.scope.version_no : '' }}</div>
          <div class="reasons">
            <div v-for="r in snap.risk_reasons || []" :key="r" class="reason">{{ r }}</div>
          </div>
          <el-descriptions :column="2" size="small" border class="ev-desc">
            <el-descriptions-item label="需求">
              <el-button link type="primary" @click="go(snap.links.requirement)">{{ snap.counts.requirement }}</el-button>
            </el-descriptions-item>
            <el-descriptions-item label="用例">
              <el-button link type="primary" @click="go(snap.links.case)">{{ snap.counts.case }}</el-button>
            </el-descriptions-item>
            <el-descriptions-item label="覆盖率">{{ snap.coverage.coverage_rate }}%</el-descriptions-item>
            <el-descriptions-item label="通过率">{{ snap.coverage.pass_rate }}%</el-descriptions-item>
            <el-descriptions-item label="未关闭BUG">
              <el-button link type="primary" @click="go(snap.links.bug)">{{ snap.counts.bug_open }}</el-button>
            </el-descriptions-item>
            <el-descriptions-item label="致命/严重">{{ snap.counts.bug_fatal_open }} / {{ snap.counts.bug_severe_open }}</el-descriptions-item>
            <el-descriptions-item label="线上溢出">{{ snap.counts.bug_online_overflow }}</el-descriptions-item>
            <el-descriptions-item label="流程">
              <el-button link type="primary" @click="go(snap.links.flow)">{{ snap.flow.stage || snap.flow.status }}</el-button>
            </el-descriptions-item>
          </el-descriptions>

          <h4>未关闭致命/严重</h4>
          <el-empty v-if="!(snap.bugs.open_critical || []).length" description="无" :image-size="40" />
          <div v-for="b in snap.bugs.open_critical || []" :key="b.no" class="ev-item" @click="go(b.link)">
            <el-tag size="small" :type="b.severity === '致命' ? 'danger' : 'warning'">{{ b.severity }}</el-tag>
            <span class="ev-no">{{ b.no }}</span>
            <span class="ev-name">{{ b.name }}</span>
          </div>

          <h4>无用例需求</h4>
          <el-empty v-if="!(snap.coverage.req_without_case || []).length" description="无" :image-size="40" />
          <div v-for="r in snap.coverage.req_without_case || []" :key="r.no" class="ev-item" @click="go(r.link)">
            <span class="ev-no">{{ r.no }}</span>
            <span class="ev-name">{{ r.name }}</span>
          </div>

          <h4>未执行用例</h4>
          <el-empty v-if="!(snap.coverage.case_not_executed || []).length" description="无" :image-size="40" />
          <div v-for="c in (snap.coverage.case_not_executed || []).slice(0, 8)" :key="c.no" class="ev-item" @click="go(c.link)">
            <span class="ev-no">{{ c.no }}</span>
            <span class="ev-name">{{ c.name }}</span>
          </div>

          <h4>BUG 最多的模块</h4>
          <el-empty v-if="!(snap.bugs.by_module || []).length" description="无" :image-size="40" />
          <div v-for="m in snap.bugs.by_module || []" :key="m.name" class="ev-item" @click="go(snap.links.bug)">
            <span class="ev-name">{{ m.name }}</span>
            <span class="ev-no">未关闭 {{ m.open }} / 共 {{ m.total }}</span>
          </div>

          <template v-if="(snap.stuck_flows || []).length">
            <h4>卡住超过 7 天</h4>
            <div v-for="f in snap.stuck_flows" :key="f.version + f.stage" class="ev-item" @click="go(f.link)">
              <span class="ev-name">{{ f.project }} / {{ f.version }}</span>
              <span class="ev-no">{{ f.stage }} · {{ f.stuck_days }}天</span>
            </div>
          </template>

          <template v-if="snap.compare">
            <h4>上一版本 {{ snap.compare.version_no }}</h4>
            <div class="hint">未关闭 BUG {{ snap.compare.bug_open }}，无用例需求 {{ snap.compare.uncovered }}，用例 {{ snap.compare.case_total }}</div>
          </template>
        </template>
      </el-scrollbar>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import { renderMarkdown } from '../../utils/sanitize'

const router = useRouter()
const projects = ref([])
const versions = ref([])
const projectId = ref('')
const versionId = ref('')
const sessions = ref([])
const sessionId = ref(0)
const messages = ref([])
const question = ref('')
const quick = ref([])
const snap = ref({})
const asking = ref(false)
const chatRef = ref()

function riskType(l) {
  return { red: 'danger', yellow: 'warning', green: 'success' }[l] || 'info'
}
function riskLabel(l) {
  return { red: '红 · 不建议上', yellow: '黄 · 带风险', green: '绿 · 未见阻断' }[l] || l
}
function go(link) {
  if (!link) return
  const [path, qs] = String(link).split('?')
  const query = {}
  if (qs) new URLSearchParams(qs).forEach((v, k) => { query[k] = v })
  router.push({ path, query })
}
function onKey(e) {
  if (e.key === 'Enter' && e.ctrlKey) {
    e.preventDefault()
    ask()
  }
}
async function scrollChat() {
  await nextTick()
  const el = chatRef.value
  if (el) el.scrollTop = el.scrollHeight
}
async function loadProjects() {
  projects.value = await request.get('/projects/all')
}
async function loadVersions() {
  if (!projectId.value) { versions.value = []; return }
  versions.value = await request.get('/versions/all', { params: { project_id: projectId.value } })
}
async function loadSessions() {
  const res = await request.get('/aiqa/sessions', { params: { page: 1, size: 50 } })
  sessions.value = res.items || []
}
async function loadQuick() {
  const res = await request.get('/aiqa/quick', { params: scopeParams() })
  quick.value = res.items || []
}
function scopeParams() {
  const p = {}
  if (projectId.value) p.project_id = projectId.value
  if (versionId.value) p.version_id = versionId.value
  return p
}
async function loadSnapshot() {
  snap.value = await request.get('/aiqa/snapshot', { params: scopeParams() })
  loadQuick()
}
async function onProject() {
  versionId.value = ''
  await loadVersions()
  onScope()
}
function onScope() {
  loadSnapshot()
}
function newSession() {
  sessionId.value = 0
  messages.value = []
}
async function openSession(id) {
  const s = await request.get(`/aiqa/sessions/${id}`)
  sessionId.value = s.id
  messages.value = s.messages || []
  projectId.value = s.project_id || ''
  await loadVersions()
  versionId.value = s.version_id || ''
  const last = [...messages.value].reverse().find((m) => m.role === 'assistant' && m.snapshot)
  snap.value = last?.snapshot || {}
  loadQuick()
  scrollChat()
}
async function delSession(s) {
  await ElMessageBox.confirm(`删除会话「${s.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/aiqa/sessions/${s.id}`)
  if (sessionId.value === s.id) newSession()
  ElMessage.success('已删除')
  loadSessions()
}
async function ask(text) {
  const q = (text || question.value || '').trim()
  if (!q || asking.value) return
  asking.value = true
  messages.value = [...messages.value, { _tmp: Date.now(), role: 'user', content: q }]
  question.value = ''
  scrollChat()
  try {
    const res = await request.post('/aiqa/ask', {
      question: q,
      session_id: sessionId.value || 0,
      ...scopeParams(),
    }, { timeout: 120000 })
    sessionId.value = res.session_id
    snap.value = res.snapshot || {}
    messages.value = res.session?.messages || []
    await loadSessions()
  } catch (e) {
    messages.value = messages.value.filter((m) => !m._tmp)
  } finally {
    asking.value = false
    scrollChat()
  }
}
onMounted(async () => {
  await loadProjects()
  await Promise.all([loadSessions(), loadSnapshot(), loadQuick()])
})
</script>

<style scoped>
.qa-page { display: flex; gap: 12px; height: calc(100vh - 120px); min-height: 520px; }
.qa-side { width: 240px; flex-shrink: 0; }
.qa-main { flex: 1; min-width: 0; }
.qa-evidence { width: 340px; flex-shrink: 0; }
.qa-page :deep(.el-card) { height: 100%; display: flex; flex-direction: column; }
.qa-side :deep(.el-card__body),
.qa-main :deep(.el-card__body),
.qa-evidence :deep(.el-card__body) { display: flex; flex-direction: column; flex: 1; padding: 12px; overflow: hidden; }
.qa-evidence :deep(.el-card__header) { padding: 10px 12px; }
.side-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-weight: 600; }
.side-scroll { flex: 1; }
.sess { position: relative; padding: 10px 8px; border-radius: var(--r-sm); cursor: pointer; margin-bottom: 6px; background: var(--c-bg); }
.sess.active { background: var(--c-orange-50); }
.sess-title { font-size: 13px; color: var(--c-text); padding-right: 36px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sess-meta { margin-top: 4px; font-size: 12px; color: var(--c-text-3); display: flex; gap: 6px; align-items: center; }
.sess-del { position: absolute; right: 4px; top: 8px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.hint { color: var(--c-text-3); font-size: 12px; }
.chat { flex: 1; overflow: auto; background: var(--c-bg); border-radius: var(--r-sm); padding: 12px; }
.welcome { padding: 24px 12px; }
.welcome-title { font-size: 20px; font-weight: 600; margin-bottom: 8px; }
.welcome-sub { color: var(--c-text-2); font-size: 13px; line-height: 1.6; margin-bottom: 16px; }
.quick { display: flex; flex-wrap: wrap; gap: 8px; }
.quick.slim { margin-bottom: 8px; }
.qtag { cursor: pointer; }
.bubble { max-width: 86%; margin-bottom: 14px; }
.bubble.user { margin-left: auto; }
.who { font-size: 12px; color: var(--c-text-3); margin-bottom: 4px; }
.bubble.user .who { text-align: right; }
.text, .md { background: #fff; border-radius: var(--r-md); padding: 10px 12px; line-height: 1.7; font-size: 13px; }
.bubble.user .text { background: var(--c-orange-500); color: #fff; }
.md :deep(p) { margin: 0 0 8px; }
.md :deep(ul), .md :deep(ol) { padding-left: 18px; margin: 0 0 8px; }
.md :deep(h1), .md :deep(h2), .md :deep(h3), .md :deep(h4) { font-size: 14px; margin: 8px 0 6px; }
.md :deep(blockquote) { margin: 0 0 8px; color: var(--c-text-3); padding-left: 8px; border-left: 3px solid var(--c-border-2); }
.composer { margin-top: 10px; }
.send-row { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.ev-head { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.ev-scroll { flex: 1; }
.ev-scope { font-weight: 600; margin-bottom: 8px; }
.reasons { margin-bottom: 10px; }
.reason { font-size: 12px; color: var(--c-text-2); line-height: 1.6; }
.ev-desc { margin-bottom: 12px; }
h4 { margin: 14px 0 8px; font-size: 13px; color: var(--c-text); }
.ev-item { display: flex; gap: 6px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--c-border); cursor: pointer; font-size: 12px; }
.ev-item:hover { color: var(--c-orange-500); }
.ev-no { color: var(--c-text-3); flex-shrink: 0; }
.ev-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
