<template>
  <div class="home-page">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">
          <span class="title-gradient">发现你的下一部</span>
          <span class="title-highlight">最爱电影</span>
        </h1>
        <p class="banner-subtitle">基于AI的智能推荐，为你精选每一部佳作</p>
        <div class="banner-stats">
          <div class="stat-item">
            <div class="stat-number">{{ movies.length + recommendations.length }}</div>
            <div class="stat-label">精选电影</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-number">{{ recommendations.length }}</div>
            <div class="stat-label">为你推荐</div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-number">AI</div>
            <div class="stat-label">智能算法</div>
          </div>
        </div>
      </div>
      <div class="banner-decoration">
        <div class="decoration-circle circle-1"></div>
        <div class="decoration-circle circle-2"></div>
        <div class="decoration-circle circle-3"></div>
      </div>
    </div>

    <!-- 推荐给你 -->
    <section class="content-section" v-if="recommendations.length > 0">
      <div class="section-header">
        <div class="section-title-box">
          <h2 class="section-title">
            <span class="title-icon">✨</span>
            <span>为你推荐</span>
          </h2>
          <button class="refresh-btn" @click="reload">
            <span class="refresh-icon">🔄</span>
            <span>刷新</span>
          </button>
        </div>
        <p class="section-subtitle">基于你的兴趣和观影历史精心挑选</p>
      </div>
      
      <div class="movies-grid">
        <div 
          v-for="(m, index) in recommendations" 
          :key="m.id" 
          class="movie-item"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <MovieCard :movie="m" @open="openMovie" />
        </div>
      </div>
    </section>

    <!-- 热门电影 -->
    <section class="content-section">
      <div class="section-header">
        <div class="section-title-box">
          <h2 class="section-title">
            <span class="title-icon">🔥</span>
            <span>热门电影</span>
          </h2>
        </div>
        <p class="section-subtitle">大家都在看的精彩影片</p>
      </div>
      
      <div class="movies-grid">
        <div 
          v-for="(m, index) in movies" 
          :key="m.id" 
          class="movie-item"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <MovieCard :movie="m" @open="openMovie" />
        </div>
      </div>
    </section>

    <!-- 兴趣标签选择对话框 -->
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

<style scoped>
.home-page {
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

/* 欢迎横幅 */
.welcome-banner {
  background: var(--bg-secondary);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 60px 48px;
  margin-bottom: 48px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-strong);
  transition: all 0.3s ease;
}

.banner-content {
  position: relative;
  z-index: 2;
  text-align: center;
}

.banner-title {
  font-size: 48px;
  font-weight: 800;
  margin: 0 0 16px 0;
  line-height: 1.2;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-gradient {
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-highlight {
  color: var(--text-primary);
}

.banner-subtitle {
  font-size: 18px;
  color: var(--text-secondary);
  margin: 0 0 32px 0;
  font-weight: 500;
}

.banner-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 32px;
  margin-top: 32px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 36px;
  font-weight: 800;
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-light);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, var(--border-color), transparent);
}

/* 装饰元素 */
.banner-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.1;
}

.circle-1 {
  width: 300px;
  height: 300px;
  background: var(--primary-gradient);
  top: -150px;
  right: -100px;
  animation: float 6s ease-in-out infinite;
}

.circle-2 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -100px;
  left: -50px;
  animation: float 8s ease-in-out infinite reverse;
}

.circle-3 {
  width: 150px;
  height: 150px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  top: 50%;
  left: 10%;
  animation: float 7s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

/* 内容区块 */
.content-section {
  margin-bottom: 48px;
  animation: slideUp 0.6s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section-header {
  margin-bottom: 32px;
  padding: 0 8px;
}

.section-title-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-secondary);
  padding: 12px 20px;
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft);
  margin-bottom: 8px;
}

.section-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.title-icon {
  font-size: 36px;
  line-height: 1;
}

.section-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
  font-weight: 500;
  padding: 0 20px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--bg-hover);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  color: var(--primary-color);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
  margin-left: 20px;
}

.refresh-btn:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.refresh-icon {
  font-size: 18px;
  display: inline-block;
  transition: transform 0.6s ease;
}

.refresh-btn:hover .refresh-icon {
  transform: rotate(360deg);
}

/* 电影网格 */
.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 32px;
  padding: 8px;
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

/* 响应式设计 */
@media (max-width: 1200px) {
  .movies-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 24px;
  }
}

@media (max-width: 768px) {
  .welcome-banner {
    padding: 40px 24px;
    margin-bottom: 32px;
  }

  .banner-title {
    font-size: 32px;
  }

  .banner-subtitle {
    font-size: 16px;
  }

  .banner-stats {
    gap: 20px;
  }

  .stat-number {
    font-size: 28px;
  }

  .stat-label {
    font-size: 12px;
  }

  .section-title {
    font-size: 24px;
  }

  .title-icon {
    font-size: 28px;
  }

  .section-subtitle {
    font-size: 14px;
  }

  .movies-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .refresh-btn {
    align-self: stretch;
    justify-content: center;
  }
}
</style>








