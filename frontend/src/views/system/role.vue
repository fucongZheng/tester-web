<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-actions">
        <el-button v-if="isAdmin" type="primary" @click="openDialog()">新增角色</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="角色名" width="140" />
      <el-table-column prop="code" label="编码" width="140" />
      <el-table-column prop="description" label="描述" min-width="200" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status ? 'success' : 'danger'" size="small">{{ row.status ? '启用' : '禁用' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="isAdmin" link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <Pager v-model:page="page" v-model:size="size" :total="allItems.length" />

    <el-dialog v-model="dialog" :title="form.id ? '编辑角色' : '新增角色'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="编码" required><el-input v-model="form.code" :disabled="!!form.id" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status"><el-radio :value="1">启用</el-radio><el-radio :value="0">禁用</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item label="菜单权限">
          <el-tree ref="treeRef" :data="menuTree" show-checkbox node-key="id"
            :default-checked-keys="form.menu_ids" :props="{ label: 'name', children: 'children' }" />
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
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const allItems = ref([]); const loading = ref(false); const dialog = ref(false)
const menuTree = ref([]); const treeRef = ref()
const form = ref({})
const page = ref(1); const size = ref(10)
const items = computed(() => {
  const start = (page.value - 1) * size.value
  return allItems.value.slice(start, start + size.value)
})

async function load() {
  loading.value = true
  try { const res = await request.get('/roles'); allItems.value = res.items; page.value = 1 }
  finally { loading.value = false }
}
async function openDialog(row) {
  form.value = row ? { ...row } : { name: '', code: '', description: '', status: 1, menu_ids: [] }
  menuTree.value = await request.get('/menus')
  dialog.value = true
  await nextTick()
  treeRef.value?.setCheckedKeys(form.value.menu_ids || [])
}
async function save() {
  if (!form.value.name || !form.value.code) return ElMessage.warning('角色名和编码必填')
  const keys = treeRef.value?.getCheckedKeys() || []
  const payload = { ...form.value, menu_ids: keys }
  if (form.value.id) await request.put(`/roles/${form.value.id}`, payload)
  else await request.post('/roles', payload)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除角色「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/roles/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(load)
</script>
