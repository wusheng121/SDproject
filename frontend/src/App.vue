<template>
  <el-container style="min-height: 100vh">
    <el-header style="display: flex; align-items: center; justify-content: space-between">
      <div style="font-weight: 700">电影推荐系统</div>
      <el-menu mode="horizontal" :default-active="activePath" @select="onSelect">
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/search">搜索</el-menu-item>
        <el-menu-item index="/favorites">收藏夹</el-menu-item>
        <el-menu-item index="/rate">评分</el-menu-item>
        <el-menu-item index="/login">登录</el-menu-item>
        <el-menu-item index="/register">注册</el-menu-item>
      </el-menu>
    </el-header>

    <el-main style="padding: 24px">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const activePath = computed(() => route.path);

function onSelect(path) {
  router.push(path);
}
</script>



