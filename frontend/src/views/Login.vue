<template>
  <div>
    <h2 style="margin: 0 0 12px">用户登录页</h2>
    <el-card style="max-width: 520px">
      <el-form :model="form" label-width="110px" @submit.prevent>
        <el-form-item label="用户名/邮箱">
          <el-input v-model="form.identifier" placeholder="请输入用户名或邮箱" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="记住我">
          <el-switch v-model="form.remember" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">登录</el-button>
          <el-button @click="loadProfile">拉取个人信息（mock）</el-button>
        </el-form-item>
      </el-form>

      <el-divider />
      <div style="color: #666; font-size: 13px">当前登录态：</div>
      <pre style="background: #fafafa; padding: 12px; border-radius: 6px">{{ userStore.profile }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { useUserStore } from "../stores/user";

const userStore = useUserStore();
const loading = ref(false);

const form = reactive({
  identifier: "",
  password: "",
  remember: false
});

async function onSubmit() {
  loading.value = true;
  try {
    const resp = await userStore.login(form);
    if (resp?.code === 0) ElMessage.success("登录成功");
    else ElMessage.error(resp?.message || "登录失败");
  } finally {
    loading.value = false;
  }
}

async function loadProfile() {
  const resp = await userStore.fetchProfile();
  if (resp?.code === 0) ElMessage.success("已获取个人信息");
  else ElMessage.error(resp?.message || "获取失败");
}
</script>



