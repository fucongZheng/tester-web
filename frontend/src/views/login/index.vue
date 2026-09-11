<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="never">
      <div class="brand">
        <span class="brand-mark">测</span>
        <div>
          <h2 class="title">测试管理系统</h2>
          <p class="sub">登录后进入工作台</p>
        </div>
      </div>
      <el-form :model="form" label-position="top" @keyup.enter="onLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="onLogin">
          登录系统
        </el-button>
      </el-form>
      <p class="hint">请使用管理员分配的账号登录</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../api/request'
import { useUserStore } from '../../store/user'
import { loadDynamicRoutes, firstMenuPath } from '../../router'

const router = useRouter()
const userStore = useUserStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)

async function onLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await request.post('/auth/login', form.value)
    userStore.setLogin(res.token, res.user)
    await loadDynamicRoutes()
    ElMessage.success('登录成功')
    router.push(firstMenuPath(userStore.menus) || '/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(1200px 480px at 12% -10%, var(--c-orange-100), transparent 60%),
    radial-gradient(900px 420px at 110% 110%, var(--c-blue-100), transparent 55%),
    var(--c-bg);
}
.login-card {
  width: 440px;
  padding: 12px 16px 8px;
  border-radius: var(--r-md);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--c-orange-500), var(--c-gold-400));
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.title { font-size: 22px; font-weight: 700; line-height: 1.3; margin: 0; color: var(--c-text); }
.sub { color: var(--c-text-3); margin-top: 2px; font-size: 13px; }
.login-btn { width: 100%; margin-top: 8px; height: 44px; font-size: 16px; font-weight: 600; }
.hint { text-align: center; color: var(--c-text-4); font-size: 12px; margin-top: 16px; }
:deep(.el-form-item__label) { color: var(--c-text-2); font-weight: 500; }
</style>
