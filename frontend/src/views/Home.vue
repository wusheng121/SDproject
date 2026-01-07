<template>
  <div>
    <el-row justify="space-between" align="middle" style="margin-bottom: 16px">
      <el-col>
        <h2 style="margin: 0">首页</h2>
        <div style="color: #666; font-size: 13px">热门 / 推荐电影</div>
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

    <!-- 兴趣标签选择对话框（首次访问引导） -->
    <PreferenceDialog v-model="showPreferenceDialog" @saved="onPreferenceSaved" />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import MovieCard from "../components/MovieCard.vue";
import PreferenceDialog from "../components/PreferenceDialog.vue";
import { apiListMovies } from "../api/movies";
import { apiRecommendations } from "../api/actions";
import { apiGetPreferences } from "../api/user";
import { useUserStore } from "../stores/user";

const router = useRouter();
const userStore = useUserStore();

const movies = ref([]);
const recommendations = ref([]);
const showPreferenceDialog = ref(false);

// 从 sessionStorage 获取本次会话是否已检查过偏好（避免页面刷新时重复弹窗）
const getPreferenceChecked = () => {
  return sessionStorage.getItem('preferenceChecked') === 'true';
};
const setPreferenceChecked = () => {
  sessionStorage.setItem('preferenceChecked', 'true');
};

async function reload() {
  const [mResp, rResp] = await Promise.all([apiListMovies({ page: 1, page_size: 12 }), apiRecommendations(8)]);
  movies.value = mResp?.data?.items || [];
  recommendations.value = rResp?.data?.items || [];
}

function openMovie(movie) {
  if (!movie?.id) return;
  router.push(`/movies/${movie.id}`);
}

async function checkPreferences() {
  // 本次会话已检查过，不再重复检查
  if (getPreferenceChecked()) return;
  setPreferenceChecked();

  // 如果用户已登录，检查是否设置了兴趣标签
  if (userStore.token) {
    try {
      const resp = await apiGetPreferences();
      const hasPreference = resp?.data?.has_preference || false;
      console.log('用户偏好状态:', { hasPreference, preferred_genres: resp?.data?.preferred_genres });
      
      if (!hasPreference) {
        // 延迟弹出，避免页面刚加载就弹窗（用户体验更好）
        setTimeout(() => {
          showPreferenceDialog.value = true;
        }, 1000);
      }
    } catch (err) {
      console.error("检查兴趣标签失败", err);
    }
  }
}

function onPreferenceSaved() {
  ElMessage.success("兴趣标签已更新，推荐内容将根据您的偏好调整");
  setPreferenceChecked(); // 标记为已设置，避免刷新页面时再次弹出
  reload(); // 重新加载推荐
}

onMounted(() => {
  reload();
  checkPreferences();
});
</script>








