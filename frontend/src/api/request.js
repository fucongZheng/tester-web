import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  // 去掉空参数，避免 int 类型的 query 字段收到 '' 导致后端 422
  if (config.params) {
    const clean = {}
    for (const [k, v] of Object.entries(config.params)) {
      if (v !== '' && v !== null && v !== undefined) clean[k] = v
    }
    config.params = clean
  }
  return config
})

request.interceptors.response.use(
  // blob 下载保留完整 response（调用方需要 headers/filename），其余剥出 data
  (res) => (res.config.responseType === 'blob' ? res : res.data),
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail || '请求失败'
    if (status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      // 用整页跳转而不是 router.push，避免与动态路由形成循环依赖
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }
    return Promise.reject(err)
  }
)

/** 带鉴权的文件上传：token 每次现读，避免组件里缓存旧凭证；url 相对于 /api */
export function uploadFile(url, formData, config = {}) {
  const token = localStorage.getItem('token')
  return request.post(url, formData, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    ...config,
  })
}

/** 带鉴权的 blob 下载并触发浏览器保存：token 每次现读 */
export async function downloadBlob(url, filename = 'download', mime = '') {
  const token = localStorage.getItem('token')
  const res = await request.get(url, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const blob = new Blob([res.data], { type: mime || res.data?.type || '' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(a.href)
  return blob
}

export default request
