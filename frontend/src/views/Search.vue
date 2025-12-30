<template>
  <div>
    <h2 style="margin: 0 0 12px">搜索页</h2>

    <el-card style="margin-bottom: 16px">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="q" placeholder="可按标题/类型/演员搜索（mock）" style="width: 360px" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <div style="font-weight: 600; margin-bottom: 8px">结果</div>
      <el-empty v-if="results.length === 0" description="暂无结果（输入关键词后点击搜索）" />
      <el-row v-else :gutter="12">
        <el-col v-for="m in results" :key="m.id" :xs="12" :sm="8" :md="6" :lg="4" style="margin-bottom: 12px">
          <MovieCard :movie="m" @open="openMovie" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import MovieCard from "../components/MovieCard.vue";
import { apiSearchMovies } from "../api/movies";

const router = useRouter();

const q = ref("");
const results = ref([]);

async function onSearch() {
  const resp = await apiSearchMovies(q.value);
  results.value = resp?.data?.items || [];
}

function openMovie(movie) {
  if (!movie?.id) return;
  router.push(`/movies/${movie.id}`);
}
</script>



