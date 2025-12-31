<template>
  <div>
    <h2 style="margin: 0 0 12px">个人收藏夹 / 列表页</h2>

    <el-card>
      <el-row justify="space-between" align="middle" style="margin-bottom: 12px">
        <el-col style="color: #666; font-size: 13px">需要登录后才能看到你的收藏</el-col>
        <el-col><el-button @click="reload">刷新</el-button></el-col>
      </el-row>
      <el-empty v-if="items.length === 0" description="暂无收藏（先去电影详情页点收藏试试）" />
      <el-table v-else :data="items" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="release_year" label="年份" width="120" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="remove(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { apiUserFavorites } from "../api/user";
import { apiToggleFavorite } from "../api/actions";

const items = ref([]);

async function reload() {
  const resp = await apiUserFavorites();
  items.value = resp?.data?.items || [];
}

async function remove(id) {
  await apiToggleFavorite({ movie_id: id, favorite: false });
  ElMessage.success("已移除");
  await reload();
}

onMounted(reload);
</script>




