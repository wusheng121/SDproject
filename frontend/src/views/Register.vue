<template>
  <div>
    <h2 style="margin: 0 0 12px">用户注册页</h2>
    <el-card style="max-width: 520px">
      <el-form :model="form" label-width="90px" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">注册</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";

import { apiRegister } from "../api/user";

const router = useRouter();
const loading = ref(false);

const form = reactive({
  username: "",
  email: "",
  password: ""
});

async function onSubmit() {
  loading.value = true;
  try {
    const resp = await apiRegister(form);
    if (resp?.code === 0) {
      ElMessage.success("注册成功，请登录");
      router.push("/login");
    } else {
      ElMessage.error(resp?.message || "注册失败");
    }
  } finally {
    loading.value = false;
  }
}
</script>





