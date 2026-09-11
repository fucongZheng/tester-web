import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/tokens.css'
import './styles/element-override.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router, { loadDynamicRoutes } from './router'

async function bootstrap() {
  const app = createApp(App)
  app.use(createPinia())

  // 已登录则先加载动态路由，避免刷新时命中兜底路由
  if (localStorage.getItem('token')) {
    await loadDynamicRoutes().catch(() => {})
  }

  app.use(router)
  app.use(ElementPlus, { locale: zhCn })

  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.mount('#app')
}

bootstrap()
