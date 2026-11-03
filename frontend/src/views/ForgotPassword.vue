<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1>找回密码</h1>
      <p class="hint">输入注册邮箱，我们会发送密码重置链接。</p>
      <el-form @submit.prevent="submit">
        <el-form-item label="邮箱">
          <el-input v-model="email" placeholder="your@email.com" />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="submit" @click="submit">
          发送重置链接
        </el-button>
      </el-form>
      <div class="links">
        <el-button link @click="router.push('/login')">返回登录</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { apiForgotPassword } from "../api/user";

const router = useRouter();
const email = ref("");
const loading = ref(false);

async function submit() {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    ElMessage.warning("请输入正确的邮箱");
    return;
  }
  loading.value = true;
  try {
    await apiForgotPassword(email.value.trim());
    ElMessage.success("如果该邮箱已注册，重置链接已发送");
  } catch (error) {
    ElMessage.error(error?.message || "发送失败，请稍后重试");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page { min-height: 60vh; display: flex; align-items: center; justify-content: center; padding: 40px 20px; }
.auth-card { width: min(460px, 100%); padding: 12px; }
h1 { margin: 0 0 8px; color: var(--text-primary); }
.hint { color: var(--text-secondary); margin: 0 0 24px; line-height: 1.6; }
.submit { width: 100%; margin-top: 8px; }
.links { margin-top: 16px; text-align: center; }
</style>
