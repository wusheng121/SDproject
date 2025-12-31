<template>
  <div>
    <el-row justify="space-between" align="middle" style="margin-bottom: 12px">
      <el-col><h2 style="margin: 0">电影详情页</h2></el-col>
      <el-col>
        <el-button @click="reload">刷新</el-button>
      </el-col>
    </el-row>

    <el-card v-if="movie">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="8" :md="6">
          <div
            style="
              height: 360px;
              background: #f2f2f2;
              display: flex;
              align-items: center;
              justify-content: center;
              border-radius: 6px;
              overflow: hidden;
            "
          >
            <img v-if="movie.poster_url" :src="movie.poster_url" alt="poster" style="width: 100%; height: 100%; object-fit: cover" />
            <div v-else style="color: #999">无海报</div>
          </div>
        </el-col>

        <el-col :xs="24" :sm="16" :md="18">
          <div style="font-size: 20px; font-weight: 700">{{ movie.title }}</div>
          <div style="margin-top: 6px; color: #666">年份：{{ movie.release_year || "-" }}</div>
          <div style="margin-top: 6px; color: #666">类型：{{ (movie.genres || []).join(" / ") || "-" }}</div>
          <div style="margin-top: 6px; color: #666">演员：{{ (movie.actors || []).join(" / ") || "-" }}</div>
          <div style="margin-top: 6px; color: #666">评分：{{ movie.rating_avg ?? "-" }}（{{ movie.rating_count ?? 0 }} 人）</div>
          <div v-if="movie.is_favorited != null" style="margin-top: 6px; color: #666">
            收藏状态：<b>{{ movie.is_favorited ? "已收藏" : "未收藏" }}</b>
          </div>
          <div v-if="movie.my_rating" style="margin-top: 6px; color: #666">
            我的评分：
            <el-rate :model-value="movie.my_rating.score" disabled style="vertical-align: middle" />
            <span style="margin-left: 8px; font-size: 12px; color: #888">更新时间：{{ movie.my_rating.updated_at || "-" }}</span>
          </div>

          <el-divider />
          <div style="white-space: pre-wrap; line-height: 1.6">{{ movie.description || "暂无简介" }}</div>

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




