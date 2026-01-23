<template>
  <div class="user-center-page">
    <div class="page-header">
      <h2 class="page-title">用户中心</h2>
    </div>

    <el-card class="user-profile-card">
      <div class="profile-header">
        <div class="avatar">
          <span class="avatar-icon">👤</span>
        </div>
        <div class="profile-info">
          <h3 class="username">{{ userStore.username || '未登录' }}</h3>
          <p class="user-email">{{ userStore.email || '暂无邮箱' }}</p>
        </div>
      </div>

      <el-divider />

      <div class="stats-section">
        <h4 class="section-title">我的统计</h4>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">❤️</div>
            <div class="stat-value">{{ stats.favorites }}</div>
            <div class="stat-label">收藏电影</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">⭐</div>
            <div class="stat-value">{{ stats.ratings }}</div>
            <div class="stat-label">评分数量</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-value">{{ stats.avgRating }}</div>
            <div class="stat-label">平均评分</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🎯</div>
            <div class="stat-value">{{ stats.genres }}</div>
            <div class="stat-label">偏好类型</div>
          </div>
        </div>
      </div>

      <el-divider />

      <div class="preferences-section">
        <h4 class="section-title">兴趣偏好</h4>
        <div v-if="preferences.length > 0" class="preferences-tags">
          <el-tag 
            v-for="genre in preferences" 
            :key="genre" 
            type="primary"
            effect="plain"
            class="preference-tag"
          >
            {{ genre }}
          </el-tag>
        </div>
        <div v-else class="no-preferences">
          <p>暂未设置兴趣偏好</p>
          <el-button type="primary" @click="showPreferenceDialog = true">设置偏好</el-button>
        </div>
        <el-button 
          v-if="preferences.length > 0" 
          class="edit-btn" 
          @click="showPreferenceDialog = true"
        >
          编辑偏好
        </el-button>
      </div>

      <el-divider />

      <div class="actions-section">
        <h4 class="section-title">快捷操作</h4>
        <div class="action-buttons">
          <el-button @click="router.push('/favorites')">
            <span class="btn-icon">❤️</span>
            <span>我的收藏</span>
          </el-button>
          <el-button @click="router.push('/my-ratings')">
            <span class="btn-icon">⭐</span>
            <span>我的评分</span>
          </el-button>
          <el-button @click="router.push('/rate')">
            <span class="btn-icon">📝</span>
            <span>去评分</span>
          </el-button>
          <el-button type="danger" @click="handleLogout">
            <span class="btn-icon">🚪</span>
            <span>退出登录</span>
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 兴趣标签选择对话框 -->
    <PreferenceDialog v-model="showPreferenceDialog" @saved="onPreferenceSaved" />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useUserStore } from "../stores/user";
import { apiGetPreferences } from "../api/user";
import { apiUserFavorites } from "../api/user";
import { apiGetMyRatings } from "../api/actions";
import PreferenceDialog from "../components/PreferenceDialog.vue";

const router = useRouter();
const userStore = useUserStore();

const showPreferenceDialog = ref(false);
const preferences = ref([]);
const stats = ref({
  favorites: 0,
  ratings: 0,
  avgRating: 0,
  genres: 0
});

async function loadUserData() {
  try {
    // 加载偏好
    const prefResp = await apiGetPreferences();
    preferences.value = prefResp?.data?.preferred_genres || [];
    stats.value.genres = preferences.value.length;

    // 加载收藏数量
    const favResp = await apiUserFavorites();
    stats.value.favorites = favResp?.data?.items?.length || 0;

    // 加载评分数据
    const ratingsResp = await apiGetMyRatings();
    const ratings = ratingsResp?.data?.items || [];
    stats.value.ratings = ratings.length;
    
    if (ratings.length > 0) {
      const sum = ratings.reduce((acc, r) => acc + r.score, 0);
      stats.value.avgRating = (sum / ratings.length).toFixed(1);
    }
  } catch (err) {
    console.error("加载用户数据失败", err);
  }
}

function onPreferenceSaved() {
  ElMessage.success("兴趣偏好已更新");
  loadUserData();
}

function handleLogout() {
  userStore.logout();
  ElMessage.success("已退出登录");
  router.push("/login");
}

onMounted(() => {
  if (!userStore.token) {
    ElMessage.warning("请先登录");
    router.push("/login");
    return;
  }
  loadUserData();
});
</script>

<style scoped>
.user-center-page {
  animation: fadeIn 0.6s ease;
  max-width: 900px;
  margin: 0 auto;
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
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
}

.user-profile-card {
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

/* 个人资料头部 */
.profile-header {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--primary-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-medium);
}

.avatar-icon {
  font-size: 40px;
}

.profile-info {
  flex: 1;
}

.username {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.user-email {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

/* 统计区域 */
.stats-section {
  margin: 24px 0;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.stat-card {
  padding: 20px;
  background: var(--bg-hover);
  border-radius: 12px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-soft);
}

.stat-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--primary-color);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
}

/* 偏好区域 */
.preferences-section {
  margin: 24px 0;
}

.preferences-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.preference-tag {
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 20px;
}

.no-preferences {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.no-preferences p {
  margin: 0 0 16px 0;
  font-size: 15px;
}

.edit-btn {
  background: var(--bg-hover);
  color: var(--primary-color);
  border: 2px solid var(--border-color);
  font-weight: 600;
}

/* 操作区域 */
.actions-section {
  margin: 24px 0;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.action-buttons .el-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 12px;
}

.btn-icon {
  font-size: 20px;
}

@media (max-width: 768px) {
  .page-title {
    font-size: 28px;
  }

  .profile-header {
    flex-direction: column;
    text-align: center;
  }

  .username {
    font-size: 20px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    grid-template-columns: 1fr;
  }
}
</style>

