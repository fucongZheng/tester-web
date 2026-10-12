// 列表页公共样板：分页查询状态 + 竞态守卫 + 项目级联。
// 各页差异部分（表单字段、校验、保存动作）仍留在页面内，不强行抽象。
import { ref } from 'vue'
import request from '../api/request'

/**
 * 列表查询：items/total/loading/query/load。
 * 模板直接 v-model="query.xxx" 绑定筛选；endpoint 如 '/cases'，extraQuery 为页面特有筛选项初始值。
 * load 内置序号守卫：快速切换筛选时丢弃过期响应，防旧数据覆盖新筛选。
 */
export function useCrudList(endpoint, extraQuery = {}) {
  const items = ref([])
  const total = ref(0)
  const loading = ref(false)
  const dialog = ref(false)
  const query = ref({ page: 1, size: 10, keyword: '', ...extraQuery })

  let seq = 0
  async function load() {
    const my = ++seq
    loading.value = true
    try {
      const res = await request.get(endpoint, { params: query.value })
      if (my !== seq) return
      items.value = res.items
      total.value = res.total
    } finally {
      if (my === seq) loading.value = false
    }
  }
  return { items, total, loading, dialog, query, load }
}

/**
 * 查询区的项目→版本/模块级联：切项目时清空版本/模块并并行重拉两级选项。
 * versions/modules 返回给查询区下拉使用；表单区自己的级联各页有差异，不在此收编。
 */
export function useProjectCascade(query, afterChange) {
  const versions = ref([])
  const modules = ref([])
  async function onProjectChange() {
    query.value.version_id = ''
    query.value.module_id = ''
    if (query.value.project_id) {
      const pid = query.value.project_id
      const [vs, ms] = await Promise.all([
        request.get('/versions/all', { params: { project_id: pid } }),
        request.get('/modules/all', { params: { project_id: pid } }),
      ])
      versions.value = vs
      modules.value = ms
    } else {
      versions.value = []
      modules.value = []
    }
    if (afterChange) afterChange()
  }
  return { versions, modules, onProjectChange }
}
