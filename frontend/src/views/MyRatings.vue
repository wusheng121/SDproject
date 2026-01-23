<template>
  <div class="my-ratings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">我的评分</h2>
        <p class="page-subtitle">展示你对电影打过的分</p>
      </div>
      <el-button class="refresh-btn" @click="reload">刷新</el-button>
    </div>

    <el-card class="ratings-card">
      <el-empty v-if="items.length === 0" description="暂无评分（去评分页提交一个试试）" />

      <el-table v-else :data="items" class="ratings-table">
        <el-table-column label="电影" min-width="220">
          <template #default="{ row }">
            <div class="movie-title">{{ row.movie?.title }}</div>
            <div class="movie-year">年份：{{ row.movie?.release_year || "-" }}</div>
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

<style scoped>
.my-ratings-page {
  animation: fadeIn 0.6s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.refresh-btn {
  background: var(--bg-secondary);
  color: var(--primary-color);
  border: 2px solid var(--border-color);
  font-weight: 600;
}

.ratings-card {
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

.ratings-table {
  color: var(--text-primary);
}

.movie-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.movie-year {
  font-size: 12px;
  color: var(--text-secondary);
}

:deep(.el-table) {
  background: var(--bg-card);
  color: var(--text-primary);
}

:deep(.el-table th) {
  background: var(--bg-hover);
  color: var(--text-primary);
}

:deep(.el-table tr) {
  background: var(--bg-card);
}

:deep(.el-table td) {
  border-color: var(--border-color);
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .page-title {
    font-size: 24px;
  }

  .refresh-btn {
    align-self: stretch;
  }
}
</style>
