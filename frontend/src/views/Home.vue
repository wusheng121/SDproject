<template>
  <div>
    <el-row justify="space-between" align="middle" style="margin-bottom: 16px">
      <el-col>
        <h2 style="margin: 0">首页</h2>
        <div style="color: #666; font-size: 13px">热门 / 推荐电影（当前为 mock 数据，后续可接数据库）</div>
      </el-col>
      <el-col>
        <el-button @click="reload">刷新</el-button>
      </el-col>
    </el-row>

    <el-card style="margin-bottom: 16px">
      <div style="font-weight: 600; margin-bottom: 8px">推荐给你</div>
      <el-row :gutter="12">
        <el-col v-for="m in recommendations" :key="m.id" :xs="12" :sm="8" :md="6" :lg="4" style="margin-bottom: 12px">
          <MovieCard :movie="m" @open="openMovie" />
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <div style="font-weight: 600; margin-bottom: 8px">电影列表</div>
      <el-row :gutter="12">
        <el-col v-for="m in movies" :key="m.id" :xs="12" :sm="8" :md="6" :lg="4" style="margin-bottom: 12px">
          <MovieCard :movie="m" @open="openMovie" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import MovieCard from "../components/MovieCard.vue";
import { apiListMovies } from "../api/movies";
import { apiRecommendations } from "../api/actions";

const router = useRouter();

const movies = ref([]);
const recommendations = ref([]);

async function reload() {
  const [mResp, rResp] = await Promise.all([apiListMovies({ page: 1, page_size: 12 }), apiRecommendations(8)]);
  movies.value = mResp?.data?.items || [];
  recommendations.value = rResp?.data?.items || [];
}

function openMovie(movie) {
  if (!movie?.id) return;
  router.push(`/movies/${movie.id}`);
}

onMounted(reload);
</script>



