<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-select v-model="project_id" placeholder="选择项目" filterable style="width:220px" @change="load">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </div>
      <div class="toolbar-actions">
        <el-button type="primary" :disabled="!project_id" @click="openDialog()">新增模块</el-button>
      </div>
    </div>

    <el-table :data="tree" v-loading="loading" border row-key="id" default-expand-all
      :tree-props="{ children: 'children' }">
      <el-table-column prop="name" label="模块名称" min-width="220" />
      <el-table-column prop="sort" label="排序" width="80" />
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(null, row)">加子模块</el-button>
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="form.id ? '编辑模块' : (form.parent_id ? '新增子模块' : '新增模块')" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="父模块">
          <el-tree-select v-model="form.parent_id" :data="parentOptions" check-strictly
            :props="{ label: 'name', value: 'id' }" clearable style="width:100%" />
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
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
import { useAdmin } from '../../composables/useAdmin'

const { isAdmin } = useAdmin()
const projects = ref([])
const tree = ref([])
const loading = ref(false)
const project_id = ref('')
const dialog = ref(false)
const form = ref({})
const parentOptions = ref([])

async function load() {
  if (!project_id.value) return
  loading.value = true
  try { tree.value = await request.get('/modules', { params: { project_id: project_id.value } }) }
  finally { loading.value = false }
}
async function loadParents() {
  const flat = await request.get('/modules/all', { params: { project_id: project_id.value } })
  parentOptions.value = [{ id: 0, name: '无（顶级）' }, ...flat]
}
function openDialog(row, parent) {
  if (parent) form.value = { name: '', parent_id: parent.id, sort: 0, remark: '', project_id: project_id.value }
  else form.value = row ? { ...row } : { name: '', parent_id: 0, sort: 0, remark: '', project_id: project_id.value }
  dialog.value = true
}
async function save() {
  if (!form.value.name) return ElMessage.warning('请输入模块名称')
  if (form.value.id) await request.put(`/modules/${form.value.id}`, form.value)
  else await request.post('/modules', form.value)
  ElMessage.success('保存成功'); dialog.value = false; load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除模块「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/modules/${row.id}`); ElMessage.success('已删除'); load()
}
onMounted(async () => { projects.value = await request.get('/projects/all') })
</script>
