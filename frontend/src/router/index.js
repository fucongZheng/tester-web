import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'
import request from '../api/request'

// 动态加载 views 下的所有组件
const modules = import.meta.glob('../views/**/*.vue')

function resolveComponent(path) {
  if (!path) return null
  const key = `../views/${path.replace(/^views\//, '').replace(/^\/+/, '')}.vue`
  return modules[key] || null
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/login/index.vue') },
    {
      path: '/',
      name: 'Layout',
      component: () => import('../layout/Layout.vue'),
      redirect: '/dashboard',
      children: [],
    },
    // 兜底路由必须指向一个「终点组件」，不能再 redirect 到动态路由，
    // 否则动态路由尚未注册时会无限重定向 → 栈溢出
    { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/error/404.vue') },
  ],
})

function buildRoutes(menus) {
  const routes = []
  const walk = (nodes) => {
    for (const m of nodes) {
      if (m.type === 'menu' && m.component) {
        routes.push({
          path: m.path,
          name: `m-${m.id}`,
          component: resolveComponent(m.component),
          meta: { title: m.name, icon: m.icon },
        })
      }
      if (m.children && m.children.length) walk(m.children)
    }
  }
  walk(menus)
  return routes
}

let loaded = false

export async function loadDynamicRoutes() {
  if (loaded) return
  const userStore = useUserStore()
  const menus = await request.get('/auth/menus')
  userStore.setMenus(menus)
  const routes = buildRoutes(menus)
  routes.forEach((r) => router.addRoute('Layout', r))
  loaded = true
}

// 重置（退出登录后再次登录时重新拉取）
export function resetRoutes() {
  loaded = false
}

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (to.path === '/login') return true
  if (!userStore.token) return '/login'
  // 兜底：动态路由尚未加载（如刷新时 bootstrap 未生效）则先加载
  if (!loaded) {
    try {
      await loadDynamicRoutes()
    } catch (e) {
      userStore.logout()
      return '/login'
    }
    // 加载后重新匹配一次目标路由
    return to.fullPath
  }
  return true
})

export default router
