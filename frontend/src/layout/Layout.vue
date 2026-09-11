<template>
  <el-container class="app-shell">
    <el-aside width="240px" class="aside">
      <div class="brand">
        <span class="brand-mark">测</span>
        <div class="brand-text">
          <div class="brand-name">测试管理系统</div>
          <div class="brand-sub">Test Manager</div>
        </div>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="side-menu"
      >
        <template v-for="m in userStore.menus" :key="m.id">
          <el-sub-menu v-if="m.children && m.children.length" :index="m.path || String(m.id)">
            <template #title>
              <el-icon v-if="m.icon"><component :is="m.icon" /></el-icon>
              <span>{{ m.name }}</span>
            </template>
            <el-menu-item v-for="c in m.children" :key="c.id" :index="c.path">
              {{ c.name }}
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="m.path">
            <el-icon v-if="m.icon"><component :is="m.icon" /></el-icon>
            <span>{{ m.name }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="page-title">{{ $route.meta.title || '' }}</div>
        <el-dropdown @command="onCommand">
          <span class="user">
            <el-avatar :size="32" class="user-avatar">{{ (userStore.user?.real_name || 'U')[0] }}</el-avatar>
            <span class="user-name">{{ userStore.user?.real_name || userStore.user?.username }}</span>
            <el-icon class="user-caret"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../store/user'

const userStore = useUserStore()

async function onCommand(cmd) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确定退出登录？', '提示', { type: 'warning' })
    userStore.logout()
    window.location.href = '/login'
  }
}
</script>

<style scoped>
.app-shell { height: 100%; }
.aside {
  background: var(--c-bg-2);
  border-right: 1px solid var(--c-border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.brand {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}
.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--c-orange-500), var(--c-gold-400));
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.brand-name { font-size: 15px; font-weight: 600; color: var(--c-text); line-height: 1.2; }
.brand-sub { font-size: 11px; color: var(--c-text-3); margin-top: 2px; }

.side-menu {
  border-right: none;
  background: transparent;
  padding: 12px 8px 24px;
  flex: 1;
}
.side-menu :deep(.el-menu-item),
.side-menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  border-radius: var(--r-sm);
  margin: 2px 0;
  color: var(--c-text-2);
}
.side-menu :deep(.el-sub-menu__title) {
  color: var(--c-blue-400);
  font-weight: 600;
  font-size: 13px;
}
.side-menu :deep(.el-menu-item:hover),
.side-menu :deep(.el-sub-menu__title:hover) {
  background: var(--c-blue-50);
  color: var(--c-blue-400);
}
.side-menu :deep(.el-menu-item.is-active) {
  background: var(--c-blue-50);
  color: var(--c-blue-600);
  font-weight: 500;
  box-shadow: inset 3px 0 0 var(--c-blue-400);
}
.side-menu :deep(.el-sub-menu .el-menu) {
  background: transparent;
}
.side-menu :deep(.el-sub-menu .el-menu-item) {
  padding-left: 48px !important;
}

.header {
  height: 64px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--c-border);
}
.page-title { font-size: 18px; font-weight: 600; color: var(--c-text); }
.user { display: flex; align-items: center; cursor: pointer; color: var(--c-text); }
.user-avatar { background: var(--c-orange-500); font-weight: 600; }
.user-name { margin-left: 8px; font-size: 14px; }
.user-caret { margin-left: 4px; color: var(--c-text-3); }
.main { background: var(--c-bg); overflow: auto; padding: 20px 24px 40px; }
</style>
