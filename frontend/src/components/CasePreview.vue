<template>
  <el-dialog
    :model-value="modelValue"
    :show-close="false"
    fullscreen
    class="case-preview-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
    @closed="onClosed"
  >
    <div class="pv">
      <!-- 顶栏：评审标题 / 进度 / 分组筛选 / 字号 / 关闭 -->
      <header class="pv-header">
        <div class="pv-left">
          <span class="pv-review">{{ title }}</span>
          <span class="pv-count">核心 {{ coreCount }} 例 · 常规 {{ normalCount }} 例</span>
        </div>
        <div class="pv-center">
          <el-radio-group v-model="groupFilter" size="default">
            <el-radio-button value="all">全部（{{ items.length }}）</el-radio-button>
            <el-radio-button value="core">核心（{{ coreCount }}）</el-radio-button>
            <el-radio-button value="normal">常规（{{ normalCount }}）</el-radio-button>
          </el-radio-group>
        </div>
        <div class="pv-right">
          <span v-if="current" class="pv-pos">{{ index + 1 }} / {{ list.length }}</span>
          <span class="pv-zoom">
            <el-button size="small" circle @click="zoom(-1)">A-</el-button>
            <b>{{ Math.round(scale * 100) }}%</b>
            <el-button size="small" circle @click="zoom(1)">A+</el-button>
          </span>
          <el-button size="small" circle :icon="Close" @click="$emit('update:modelValue', false)" />
        </div>
      </header>

      <!-- 正文：一屏一例，大字号投屏 -->
      <main v-if="current" class="pv-body" :style="{ '--pv-font': Math.round(20 * scale) + 'px' }">
        <div class="pv-card">
          <div class="pv-case-head">
            <span class="pv-case-no">{{ current.case.case_no }}</span>
            <h2 class="pv-case-title">{{ current.case.title }}</h2>
          </div>
          <div class="pv-tags">
            <el-tag :type="current.group === 'core' ? 'danger' : 'info'" effect="dark">
              {{ current.group === 'core' ? '核心用例' : '常规用例' }}
            </el-tag>
            <el-tag :type="prioType(current.case.priority)" effect="dark">{{ current.case.priority }}</el-tag>
            <el-tag effect="plain">{{ current.case.case_type }}</el-tag>
            <el-tag v-if="current.case.module_name" effect="plain" type="warning">{{ current.case.module_name }}</el-tag>
          </div>
          <section v-if="current.case.precondition">
            <label>前置条件</label>
            <div class="pv-text">{{ current.case.precondition }}</div>
          </section>
          <section v-if="current.case.steps">
            <label>操作步骤</label>
            <div class="pv-text pv-steps">{{ current.case.steps }}</div>
          </section>
          <section v-if="current.case.expected">
            <label>预期结果</label>
            <div class="pv-text pv-expected">{{ current.case.expected }}</div>
          </section>
        </div>
      </main>
      <main v-else class="pv-body pv-empty">
        <el-empty description="该评审没有选择用例" />
      </main>

      <!-- 底栏：翻页 -->
      <footer class="pv-footer">
        <el-button size="large" :disabled="index <= 0" @click="prev">← 上一例</el-button>
        <span class="pv-pos-lg" v-if="list.length">{{ index + 1 }} / {{ list.length }}</span>
        <el-button size="large" type="primary" :disabled="index >= list.length - 1" @click="next">下一例 →</el-button>
        <span class="pv-kbd-tip">键盘 ← → 翻页 · Home/End 跳到首末例</span>
      </footer>
    </div>
  </el-dialog>
</template>

<script setup>
/**
 * 用例评审投屏预览：全屏一屏一例，大字号，键盘翻页，
 * 支持核心/常规分组过滤与字号缩放，供评审现场投影。
 */
import { ref, computed, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },  // [{group:'core'|'normal', case:{...}}]
})
defineEmits(['update:modelValue'])

const BASE_FONT = 20
const index = ref(0)
const groupFilter = ref('all')
const scale = ref(1)

const coreCount = computed(() => props.items.filter(i => i.group === 'core').length)
const normalCount = computed(() => props.items.filter(i => i.group === 'normal').length)
const list = computed(() =>
  groupFilter.value === 'all' ? props.items : props.items.filter(i => i.group === groupFilter.value))
const current = computed(() => list.value[index.value])

watch(groupFilter, () => { index.value = 0 })
watch(() => props.modelValue, v => { if (v) { index.value = 0; groupFilter.value = 'all' } })

function prev() { if (index.value > 0) index.value -= 1 }
function next() { if (index.value < list.value.length - 1) index.value += 1 }
function zoom(dir) {
  scale.value = Math.min(1.8, Math.max(0.7, Math.round((scale.value + dir * 0.1) * 10) / 10))
}
function prioType(p) {
  return { P0: 'danger', P1: 'warning', P2: '', P3: 'info' }[p] || 'info'
}
function onKeydown(e) {
  if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return
  if (e.key === 'ArrowLeft') { e.preventDefault(); prev() }
  else if (e.key === 'ArrowRight') { e.preventDefault(); next() }
  else if (e.key === 'Home') { e.preventDefault(); index.value = 0 }
  else if (e.key === 'End') { e.preventDefault(); index.value = Math.max(0, list.value.length - 1) }
}
function onOpen() { document.addEventListener('keydown', onKeydown) }
function onClosed() { document.removeEventListener('keydown', onKeydown) }
</script>

<style scoped>
.pv { display: flex; flex-direction: column; height: calc(100vh - 24px); margin: -14px; }

.pv-header {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  padding: 10px 16px; border-bottom: 1px solid #dcdfe6; background: #fff;
}
.pv-left { min-width: 0; }
.pv-review { font-size: 16px; font-weight: 600; margin-right: 10px; }
.pv-count { font-size: 13px; color: #909399; }
.pv-center { flex: 1; display: flex; justify-content: center; }
.pv-right { display: flex; align-items: center; gap: 10px; }
.pv-pos { font-size: 15px; font-weight: 600; color: #e6720a; }
.pv-zoom { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; }

.pv-body { flex: 1; overflow-y: auto; background: #f2f3f5; font-size: var(--pv-font, 20px); }
.pv-card {
  max-width: 1080px; margin: 24px auto; background: #fff; border-radius: 10px;
  padding: 28px 36px 36px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.pv-case-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pv-case-no {
  font-size: 0.8em; font-weight: 600; color: #fff; background: #409eff;
  border-radius: 6px; padding: 2px 10px; white-space: nowrap;
}
.pv-case-title { margin: 0; font-size: 1.55em; line-height: 1.4; word-break: break-all; }
.pv-tags { display: flex; gap: 8px; margin: 14px 0 6px; }
.pv-tags .el-tag { font-size: 0.72em; }

.pv-card section { margin-top: 18px; }
.pv-card label {
  display: inline-block; font-size: 0.72em; font-weight: 600; color: #606266;
  background: #f4f4f5; border-left: 4px solid #909399; border-radius: 4px;
  padding: 3px 12px; margin-bottom: 8px;
}
.pv-text {
  line-height: 1.9; white-space: pre-line; word-break: break-word; color: #303133;
}
.pv-steps { background: #fafcff; border: 1px dashed #d9e2ef; border-radius: 8px; padding: 10px 16px; }
.pv-expected {
  background: #f0f9eb; border: 1px solid #e1f3d8; border-radius: 8px; padding: 10px 16px;
  color: #2f5e2f; font-weight: 500;
}

.pv-empty { display: flex; align-items: center; justify-content: center; }

.pv-footer {
  display: flex; align-items: center; justify-content: center; gap: 18px;
  padding: 12px 16px; border-top: 1px solid #dcdfe6; background: #fff;
}
.pv-pos-lg { font-size: 18px; font-weight: 700; color: #e6720a; min-width: 90px; text-align: center; }
.pv-kbd-tip { font-size: 13px; color: #c0c4cc; }
</style>

<style>
/* 投屏预览是全屏浮层，去掉 el-dialog 默认内边距，样式全局生效一次即可 */
.case-preview-dialog { padding: 12px; }
.case-preview-dialog .el-dialog { background: transparent; }
.case-preview-dialog .el-dialog__header { display: none; }
.case-preview-dialog .el-dialog__body { padding: 12px; }
</style>
