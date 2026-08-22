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
  (res) => res.data,
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

export default request
