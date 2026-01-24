<template>
  <div class="favorites-page">
    <div class="page-header">
  <div>
        <h2 class="page-title">个人收藏夹</h2>
        <p class="page-subtitle">需要登录后才能看到你的收藏</p>
      </div>
      <el-button class="refresh-btn" @click="reload">刷新</el-button>
    </div>

    <el-card class="favorites-card">
      <el-empty v-if="items.length === 0" description="暂无收藏（先去电影详情页点收藏试试）" />
      <el-table v-else :data="items" class="favorites-table">
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

<style scoped>
.favorites-page {
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

.favorites-card {
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

.favorites-table {
  color: var(--text-primary);
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
