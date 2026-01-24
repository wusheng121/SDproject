<template>
  <div class="movie-info-page">
    <div class="page-header">
      <h2 class="page-title">电影详情</h2>
      <el-button class="refresh-btn" @click="reload">刷新</el-button>
    </div>

    <el-card v-if="movie" class="movie-detail-card">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="8" :md="6">
          <div class="poster-container">
            <img v-if="movie.poster_url" :src="movie.poster_url" alt="poster" class="poster-image" />
            <div v-else class="poster-placeholder">无海报</div>
          </div>
        </el-col>

        <el-col :xs="24" :sm="16" :md="18">
          <h1 class="movie-title">{{ movie.title }}</h1>
          <div class="movie-meta">
            <div class="meta-item">
              <span class="meta-label">年份：</span>
              <span class="meta-value">{{ movie.release_year || "-" }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">类型：</span>
              <span class="meta-value">{{ (movie.genres || []).join(" / ") || "-" }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">演员：</span>
              <span class="meta-value">{{ (movie.actors || []).join(" / ") || "-" }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">评分：</span>
              <span class="meta-value">{{ movie.rating_avg ?? "-" }}（{{ movie.rating_count ?? 0 }} 人）</span>
            </div>
            <div v-if="movie.is_favorited != null" class="meta-item">
              <span class="meta-label">收藏状态：</span>
              <span class="meta-value favorite-status">{{ movie.is_favorited ? "已收藏" : "未收藏" }}</span>
          </div>
            <div v-if="movie.my_rating" class="meta-item">
              <span class="meta-label">我的评分：</span>
            <el-rate :model-value="movie.my_rating.score" disabled style="vertical-align: middle" />
              <span class="rating-time">更新时间：{{ movie.my_rating.updated_at || "-" }}</span>
            </div>
          </div>

          <el-divider />
          <div class="movie-description">{{ movie.description || "暂无简介" }}</div>

          <el-divider />
          <el-space>
            <el-button type="primary" :disabled="movie.is_favorited === true" @click="favorite(true)">收藏</el-button>
            <el-button :disabled="movie.is_favorited === false" @click="favorite(false)">取消收藏</el-button>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <el-empty v-else description="加载中..." />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiMovieDetail } from "../api/movies";
import { apiToggleFavorite } from "../api/actions";

const route = useRoute();

const movie = ref(null);

async function reload() {
  const id = route.params.id;
  const resp = await apiMovieDetail(id);
  movie.value = resp?.data || null;
}

async function favorite(isFav) {
  if (!movie.value?.id) return;
  await apiToggleFavorite({ movie_id: movie.value.id, favorite: isFav });
  movie.value.is_favorited = isFav;
}

watch(
  () => route.params.id,
  () => reload()
);

onMounted(reload);
</script>

<style scoped>
.movie-info-page {
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
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
}

.refresh-btn {
  background: var(--bg-secondary);
  color: var(--primary-color);
  border: 2px solid var(--border-color);
  font-weight: 600;
}

.movie-detail-card {
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

.poster-container {
  height: 360px;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  overflow: hidden;
}

.poster-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.poster-placeholder {
  color: var(--text-light);
  font-size: 16px;
}

.movie-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.movie-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
}

.meta-label {
  color: var(--text-secondary);
  font-weight: 600;
}

.meta-value {
  color: var(--text-primary);
}

.favorite-status {
  font-weight: 700;
  color: var(--primary-color);
}

.rating-time {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-light);
}

.movie-description {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--text-primary);
  font-size: 15px;
  padding: 16px;
  background: var(--bg-hover);
  border-radius: 12px;
}

@media (max-width: 768px) {
  .page-title {
    font-size: 24px;
  }

  .movie-title {
    font-size: 20px;
  }

  .poster-container {
    height: 280px;
    margin-bottom: 16px;
  }
}
</style>
