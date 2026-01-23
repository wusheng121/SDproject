<template>
  <div class="search-page">
    <h2 class="page-title">搜索电影</h2>

    <el-card class="search-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="可空" style="width: 220px" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select
            v-model="form.genre"
            clearable
            filterable
            placeholder="可空，从下拉选择"
            style="width: 200px"
            @change="onSearch"
          >
            <el-option v-for="g in genres" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="演员">
          <el-input v-model="form.actor" placeholder="可空，例如 Tom Hanks" style="width: 180px" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="results-card">
      <div class="results-header">搜索结果</div>
      <el-empty v-if="results.length === 0" description="暂无结果（输入关键词后点击搜索）" />
      <div v-else class="movies-grid">
        <div v-for="m in results" :key="m.id" class="movie-item">
          <MovieCard :movie="m" @open="openMovie" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import MovieCard from "../components/MovieCard.vue";
import { apiListGenres, apiSearchMovies } from "../api/movies";

const router = useRouter();

const form = reactive({
  title: "",
  genre: "",
  actor: ""
});
const results = ref([]);
const genres = ref([]);

async function onSearch() {
  if (!form.title && !form.genre && !form.actor) {
    ElMessage.warning("至少填一项标题/类型/演员");
    return;
  }
  const resp = await apiSearchMovies({ title: form.title, genre: form.genre, actor: form.actor });
  results.value = resp?.data?.items || [];
}

async function loadGenres() {
  const resp = await apiListGenres();
  genres.value = resp?.data?.items || [];
}

onMounted(() => {
  loadGenres();
});

function openMovie(movie) {
  if (!movie?.id) return;
  router.push(`/movies/${movie.id}`);
}
</script>

<style scoped>
.search-page {
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

.page-title {
  margin: 0 0 24px 0;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
}

.search-card {
  margin-bottom: 24px;
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

.results-card {
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

.results-header {
  font-weight: 700;
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

.movie-item {
  animation: fadeInUp 0.6s ease both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .page-title {
    font-size: 24px;
  }

  .movies-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }
}
</style>
