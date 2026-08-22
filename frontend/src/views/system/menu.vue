<template>
  <el-card>
    <div class="toolbar">
      <el-button type="success" @click="openDialog()">新增菜单</el-button>
    </div>

    <el-table :data="tree" v-loading="loading" border row-key="id" default-expand-all
      :tree-props="{ children: 'children' }">
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="type" label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="{ dir: 'warning', menu: 'primary', button: 'info' }[row.type]">{{ typeLabel(row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路由路径" width="140" />
      <el-table-column prop="component" label="组件" min-width="170" />
      <el-table-column prop="icon" label="图标" width="100" />
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(null, row)">加子级</el-button>
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="form.id ? '编辑菜单' : '新增菜单'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="上级菜单">
          <el-tree-select v-model="form.parent_id" :data="parentOptions" check-strictly
            :props="{ label: 'name', value: 'id', children: 'children' }" clearable style="width:100%" />
        </el-form-item>
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio value="dir">目录</el-radio><el-radio value="menu">菜单</el-radio><el-radio value="button">按钮</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="路由路径"><el-input v-model="form.path" /></el-form-item>
        <el-form-item label="组件"><el-input v-model="form.component" placeholder="如 views/project/index" /></el-form-item>
        <el-form-item label="图标"><el-input v-model="form.icon" placeholder="Element Plus 图标名" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" /></el-form-item>
        <el-form-item label="权限标识"><el-input v-model="form.permission" placeholder="按钮权限用" /></el-form-item>
        <el-form-item label="显示"><el-switch v-model="form.visible" :active-value="1" :inactive-value="0" /></el-form-item>
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

const tree = ref([]); const loading = ref(false); const dialog = ref(false)
const parentOptions = ref([]); const form = ref({})

function typeLabel(t) { return { dir: '目录', menu: '菜单', button: '按钮' }[t] || t }
async function load() {
  loading.value = true
  try {
    tree.value = await request.get('/menus')
    parentOptions.value = [{ id: 0, name: '顶级', children: [] }, ...tree.value]
  } finally { loading.value = false }
}
function openDialog(row, parent) {
  if (parent) form.value = { parent_id: parent.id, name: '', type: 'menu', path: '', component: '', icon: '', sort: 0, permission: '', visible: 1 }
  else form.value = row ? { ...row } : { parent_id: 0, name: '', type: 'menu', path: '', component: '', icon: '', sort: 0, permission: '', visible: 1 }
  dialog.value = true
}
async function save() {
  if (!form.value.name) return ElMessage.warning('请输入名称')
  if (form.value.id) await request.put(`/menus/${form.value.id}`, form.value)
  else await request.post('/menus', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除菜单「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/menus/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 14px; }
</style>
