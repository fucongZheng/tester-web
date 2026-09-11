<template>
  <el-card>
    <div class="toolbar">
      <span class="hint">可接 OpenAI / Azure / z.ai / 中转站。启用后用于测试报告润色。保存前可用「测试连接」验证 Key。</span>
      <div class="toolbar-actions">
        <el-button v-if="isAdmin" type="primary" @click="openDialog()">新增 API</el-button>
      </div>
    </div>
    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="name" label="名称" width="160" />
      <el-table-column prop="provider" label="类型" width="100" />
      <el-table-column prop="base_url" label="Base URL" min-width="220" show-overflow-tooltip />
      <el-table-column prop="model" label="模型" width="140" />
      <el-table-column prop="api_key_masked" label="Key" width="140" />
      <el-table-column prop="enabled" label="启用" width="80">
        <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '是' : '否' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="isAdmin" link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <Pager v-model:page="page" v-model:size="size" :total="allItems.length" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑 API' : '新增 API'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.provider" style="width:100%">
            <el-option v-for="p in providers" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL"><el-input v-model="form.base_url" placeholder="https://api.openai.com/v1、https://z.ai 或中转站地址" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" show-password :placeholder="form.id ? '留空则不修改' : ''" /></el-form-item>
        <el-form-item label="模型"><el-input v-model="form.model" placeholder="如 gpt-4o-mini / glm-4.5" /></el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
          <span class="hint">同时只能启用一条</span>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button :loading="testing" @click="testLink">测试连接</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const allItems = ref([]); const loading = ref(false); const dialog = ref(false)
const testing = ref(false)
const providers = ref([]); const form = ref({})
const page = ref(1); const size = ref(10)
const items = computed(() => {
  const start = (page.value - 1) * size.value
  return allItems.value.slice(start, start + size.value)
})

async function load() {
  loading.value = true
  try { const res = await request.get('/apiconfigs'); allItems.value = res.items; page.value = 1 }
  finally { loading.value = false }
}
function openDialog(row) {
  form.value = row ? { ...row, api_key: '' } : { name: '', provider: 'openai', base_url: '', api_key: '', model: '', enabled: 0, remark: '' }
  dialog.value = true
}
async function save() {
  if (!form.value.name) return ElMessage.warning('名称必填')
  if (form.value.id) await request.put(`/apiconfigs/${form.value.id}`, form.value)
  else await request.post('/apiconfigs', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function testLink() {
  if (!form.value.api_key && !form.value.id) return ElMessage.warning('请先填写 API Key')
  testing.value = true
  try {
    const res = await request.post('/apiconfigs/test', {
      id: form.value.id,
      base_url: form.value.base_url,
      api_key: form.value.api_key,
      model: form.value.model,
    })
    ElMessage.success(`${res.message}（${res.latency_ms}ms，${res.model || '默认模型'}）`)
  } finally {
    testing.value = false
  }
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/apiconfigs/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => {
  providers.value = (await request.get('/apiconfigs/options')).providers
  load()
})
</script>

<style scoped>
.hint { color: var(--c-text-3); font-size: 12px; }
</style>
