<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1>修改密码</h1>
      <p class="hint">首次登录需要修改初始密码。</p>
      <el-form @submit.prevent="submit">
        <el-form-item label="当前密码">
          <el-input v-model="currentPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="confirmPassword" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="submit" @click="submit">
          保存新密码
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { apiChangePassword } from "../api/user";
import { useUserStore } from "../stores/user";

const router = useRouter();
const userStore = useUserStore();
const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const loading = ref(false);

async function submit() {
  if (!currentPassword.value) {
    ElMessage.warning("请输入当前密码");
    return;
  }
  if (newPassword.value.length < 8 || !/[A-Za-z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
    ElMessage.warning("新密码至少 8 位，且必须包含字母和数字");
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }
  loading.value = true;
  try {
    await apiChangePassword(currentPassword.value, newPassword.value);
    if (userStore.profile) userStore.profile.must_change_password = false;
    ElMessage.success("密码已更新");
    router.replace(userStore.isAdmin ? "/admin" : "/");
  } catch (error) {
    ElMessage.error(error?.message || "修改密码失败");
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
</style>
