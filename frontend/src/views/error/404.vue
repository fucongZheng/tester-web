<template>
  <div class="nf">
    <h1>404</h1>
    <p>页面不存在或没有访问权限</p>
    <el-button type="primary" @click="$router.replace('/dashboard')">返回首页</el-button>
  </div>
</template>

<style scoped>
.nf { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #909399; }
.nf h1 { font-size: 64px; color: #c0c4cc; margin: 0 0 12px; }
.nf p { margin-bottom: 24px; }
</style>
