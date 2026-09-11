<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="query.keyword" placeholder="搜索项目名称" clearable style="width:220px" @keyup.enter="load" />
        <el-select v-model="query.type" placeholder="类型" clearable style="width:140px" @change="load">
          <el-option v-for="t in types" :key="t" :label="t" :value="t" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="openDialog()">新增项目</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="项目名称" min-width="160" />
      <el-table-column prop="type" label="类型" width="110">
        <template #default="{ row }"><el-tag>{{ row.type }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="owner" label="负责人" width="110" />
      <el-table-column prop="members" label="参与成员" min-width="140" />
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pager v-model:page="query.page" v-model:size="query.size" :total="total" @update:page="load" @update:size="load" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑项目' : '新增项目'" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="form.type" style="width:100%">
          <el-option v-for="t in types" :key="t" :label="t" :value="t" /></el-select></el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="form.owner" filterable clearable style="width:100%" placeholder="选择用户">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
          </el-select>
        </el-form-item>
        <el-form-item label="参与成员">
          <el-select v-model="form.memberList" multiple filterable style="width:100%" placeholder="多选用户">
            <el-option v-for="u in users" :key="u.id" :label="u.real_name || u.username" :value="u.real_name || u.username" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()

const items = ref([])
const total = ref(0)
const loading = ref(false)
const dialog = ref(false)
const types = ref([])
const users = ref([])
const query = ref({ page: 1, size: 10, keyword: '', type: '' })
const form = ref({})

async function load() {
  loading.value = true
  try {
    const res = await request.get('/projects', { params: query.value })
    items.value = res.items
    total.value = res.total
  } finally { loading.value = false }
}
function openDialog(row) {
  if (row) {
    const memberList = (row.members || '').split(/[,，]/).map(s => s.trim()).filter(Boolean)
    form.value = { ...row, memberList }
  } else {
    form.value = { name: '', type: '其他', owner: '', members: '', memberList: [] }
  }
  dialog.value = true
}
async function save() {
  if (!form.value.name) return ElMessage.warning('请输入项目名称')
  const payload = { ...form.value, members: (form.value.memberList || []).join(',') }
  if (form.value.id) await request.put(`/projects/${form.value.id}`, payload)
  else await request.post('/projects', payload)
  ElMessage.success('保存成功')
  dialog.value = false
  load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除项目「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/projects/${row.id}`)
  ElMessage.success('已删除')
  load()
}
onMounted(async () => {
  types.value = await request.get('/projects/types')
  users.value = await request.get('/users/all')
  load()
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
</style>
