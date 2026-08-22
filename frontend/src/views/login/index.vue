<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">测试管理系统</h2>
      <p class="sub">Test Management System</p>
      <el-form :model="form" @keyup.enter="onLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="onLogin">
          登录
        </el-button>
      </el-form>
      <p class="hint">默认账号 admin / admin123</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../api/request'
import { useUserStore } from '../../store/user'
import { loadDynamicRoutes } from '../../router'

const router = useRouter()
const userStore = useUserStore()
const form = ref({ username: 'admin', password: '' })
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
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1f3b73 0%, #2d6cdf 100%); }
.login-card { width: 380px; padding: 20px 10px; }
.title { text-align: center; margin-bottom: 4px; }
.sub { text-align: center; color: #909399; margin-bottom: 24px; font-size: 13px; }
.hint { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 16px; }
</style>
