<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1>邮箱验证</h1>
      <p class="hint">{{ message }}</p>
      <el-button v-if="done" type="primary" @click="router.push('/login')">去登录</el-button>
      <el-button v-else type="primary" :loading="loading" @click="verify">立即验证</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiVerifyEmail } from "../api/user";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const done = ref(false);
const message = ref("正在准备验证链接...");

async function verify() {
  const token = String(route.query.token || "");
  if (!token) {
    message.value = "验证链接无效或缺少 token";
    return;
  }
  loading.value = true;
  try {
    await apiVerifyEmail(token);
    done.value = true;
    message.value = "邮箱验证成功";
  } catch (error) {
    message.value = error?.message || "验证失败，链接可能已过期";
  } finally {
    loading.value = false;
  }
}

onMounted(verify);
</script>

<style scoped>
.auth-page { min-height: 60vh; display: flex; align-items: center; justify-content: center; padding: 40px 20px; }
.auth-card { width: min(460px, 100%); padding: 24px; text-align: center; }
h1 { margin: 0 0 12px; color: var(--text-primary); }
.hint { color: var(--text-secondary); line-height: 1.7; margin: 0 0 24px; }
</style>
