<template>
  <el-card>
    <div class="toolbar">
      <div class="toolbar-filters">
        <el-input v-model="keyword" placeholder="搜索用户名/路径" clearable style="width:220px" @keyup.enter="load" />
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </div>
    <el-table :data="items" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户" width="110" />
      <el-table-column prop="method" label="方法" width="80" />
      <el-table-column prop="path" label="路径" min-width="240" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="170" />
    </el-table>
    <Pager v-model:page="page" v-model:size="size" :total="total" @update:page="load" @update:size="load" />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../../api/request'
import Pager from '../../components/Pager.vue'

const items = ref([]); const total = ref(0); const loading = ref(false)
const keyword = ref(''); const page = ref(1); const size = ref(10)

async function load() {
  loading.value = true
  try {
    const res = await request.get('/logs', { params: { keyword: keyword.value, page: page.value, size: size.value } })
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}
onMounted(load)
</script>
