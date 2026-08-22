<template>
  <el-container style="height: 100%">
    <el-aside width="220px" class="aside">
      <div class="logo">🧪 测试管理系统</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#001529"
        text-color="#c0c4cc"
        active-text-color="#fff"
        style="border-right: none"
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
            <el-avatar :size="28" style="background:#409eff">{{ (userStore.user?.real_name || 'U')[0] }}</el-avatar>
            <span style="margin-left:8px">{{ userStore.user?.real_name || userStore.user?.username }}</span>
            <el-icon style="margin-left:4px"><ArrowDown /></el-icon>
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
.aside { background: #001529; }
.logo { height: 60px; line-height: 60px; color: #fff; font-size: 16px; font-weight: 600; text-align: center; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 4px rgba(0,21,41,.08); }
.page-title { font-size: 16px; font-weight: 600; color: #303133; }
.user { display: flex; align-items: center; cursor: pointer; color: #303133; }
.main { background: #f0f2f5; }
</style>
