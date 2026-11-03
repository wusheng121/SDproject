<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1>重置密码</h1>
      <p class="hint">请输入新密码。重置后其他设备上的登录会失效。</p>
      <el-form @submit.prevent="submit">
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="confirmPassword" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="submit" @click="submit">
          确认重置
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
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { apiResetPassword } from "../api/user";

const route = useRoute();
const router = useRouter();
const newPassword = ref("");
const confirmPassword = ref("");
const loading = ref(false);

async function submit() {
  const token = String(route.query.token || "");
  if (!token) {
    ElMessage.error("重置链接无效");
    return;
  }
  if (newPassword.value.length < 8 || !/[A-Za-z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
    ElMessage.warning("密码至少 8 位，且必须包含字母和数字");
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.warning("两次输入的密码不一致");
    return;
  }
  loading.value = true;
  try {
    await apiResetPassword(token, newPassword.value);
    ElMessage.success("密码已重置，请重新登录");
    router.replace("/login");
  } catch (error) {
    ElMessage.error(error?.message || "重置失败，链接可能已过期");
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
