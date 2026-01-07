<template>
  <div>
    <h2 style="margin: 0 0 12px">搜索页</h2>

    <el-card style="margin-bottom: 16px">
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







