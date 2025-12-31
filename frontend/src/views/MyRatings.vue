<template>
  <div>
    <h2 style="margin: 0 0 12px">我的评分</h2>
    <el-card>
      <el-row justify="space-between" align="middle" style="margin-bottom: 12px">
        <el-col style="color: #666; font-size: 13px">展示你对电影打过的分（从数据库读取）</el-col>
        <el-col><el-button @click="reload">刷新</el-button></el-col>
      </el-row>

      <el-empty v-if="items.length === 0" description="暂无评分（去评分页提交一个试试）" />

      <el-table v-else :data="items" style="width: 100%">
        <el-table-column label="电影" min-width="220">
          <template #default="{ row }">
            <div style="font-weight: 600">{{ row.movie?.title }}</div>
            <div style="font-size: 12px; color: #666">年份：{{ row.movie?.release_year || "-" }}</div>
          </template>
        </el-table-column>
        <el-table-column label="评分" width="160">
          <template #default="{ row }">
            <el-rate :model-value="row.score" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="评论" />
        <el-table-column prop="updated_at" label="更新时间" width="220" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { apiUserRatings } from "../api/user";

const items = ref([]);

async function reload() {
  const resp = await apiUserRatings();
  items.value = resp?.data?.items || [];
}

onMounted(reload);
</script>



