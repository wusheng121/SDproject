<template>
  <div class="app-container">
    <!-- 导航栏 -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo-section" @click="router.push('/')">
          <div class="logo-icon">🎬</div>
          <div class="logo-text">
            <div class="logo-title">CineMatch</div>
            <div class="logo-subtitle">智能电影推荐</div>
          </div>
        </div>

        <nav class="nav-menu">
          <!-- 返回按钮 -->
          <a 
            v-if="canGoBack"
            class="nav-item back-btn"
            @click="goBack"
            title="返回上一页"
          >
            <span class="nav-icon">←</span>
            <span class="nav-label">返回</span>
          </a>

          <a 
            v-for="item in navItems" 
            :key="item.path"
            :class="['nav-item', { active: activePath === item.path }]"
            @click="router.push(item.path)"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </a>
        </nav>

        <div class="user-section">
          <!-- 主题切换按钮 -->
          <button class="theme-toggle" @click="toggleTheme" :title="isDarkMode ? '切换到日间模式' : '切换到夜间模式'">
            <span class="theme-icon">{{ isDarkMode ? '☀️' : '🌙' }}</span>
          </button>

          <div v-if="hasToken" class="user-info">
            <button class="username-btn" @click="router.push('/user-center')" title="进入用户中心">
              <span class="user-icon">👤</span>
              <span class="username-text">{{ userStore.username || '用户' }}</span>
            </button>
            <el-button class="logout-btn" @click="logout">
              <span>退出</span>
            </el-button>
          </div>
          <div v-else class="auth-buttons">
            <el-button class="login-btn" @click="router.push('/login')">登录</el-button>
            <el-button class="register-btn" type="primary" @click="router.push('/register')">注册</el-button>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="app-main">
      <div class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="app-footer">
      <div class="footer-content">
        <p>© 2026 CineMatch 智能电影推荐系统 | 数据库原理课程项目</p>
        <p class="footer-links">
          <a href="#">关于我们</a>
          <span>·</span>
          <a href="#">隐私政策</a>
          <span>·</span>
          <a href="#">使用条款</a>
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useUserStore } from "./stores/user";
import { currentTheme, toggleTheme, THEME_DARK } from "./composables/useTheme";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const activePath = computed(() => route.path);
const hasToken = computed(() => !!userStore.token);
const isDarkMode = computed(() => currentTheme.value === THEME_DARK);

// 判断是否可以返回
const canGoBack = computed(() => {
  // 如果在首页，不显示返回按钮
  if (route.path === '/') return false;
  // 检查是否有历史记录
  return window.history.length > 1;
});

const navItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/search', label: '搜索', icon: '🔍' },
  { path: '/favorites', label: '收藏夹', icon: '❤️' },
  { path: '/rate', label: '评分', icon: '⭐' },
  { path: '/my-ratings', label: '我的评分', icon: '📝' },
];

function goBack() {
  router.back();
}

function logout() {
  userStore.logout();
  router.push("/login");
}
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 应用容器 */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  position: relative;
  transition: background 0.3s ease;
}

.app-container::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3), transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(252, 70, 107, 0.3), transparent 50%);
  pointer-events: none;
  z-index: 0;
  transition: opacity 0.3s ease;
}

[data-theme="dark"] .app-container::before {
  opacity: 0.5;
}

/* 导航栏 */
.app-header {
  background: var(--bg-secondary);
  backdrop-filter: blur(20px);
  box-shadow: var(--shadow-soft);
  position: sticky;
  top: 0;
  z-index: 1000;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.3s ease;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 32px;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Logo区域 */
.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.logo-section:hover {
  transform: scale(1.05);
}

.logo-icon {
  font-size: 36px;
  line-height: 1;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 24px;
  font-weight: 800;
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 1px;
}

/* 导航菜单 */
.nav-menu {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 返回按钮特殊样式 */
.back-btn {
  background: var(--bg-hover);
  border: 2px solid var(--border-color);
  margin-right: 8px;
}

.back-btn:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  transform: translateY(-2px) translateX(-2px);
}

.back-btn .nav-icon {
  font-size: 20px;
  font-weight: bold;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 14px;
  text-decoration: none;
  position: relative;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--primary-color);
  transform: translateY(-2px);
}

.nav-item.active {
  background: var(--primary-gradient);
  color: white;
  box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4);
}

.nav-icon {
  font-size: 18px;
  line-height: 1;
}

.nav-label {
  font-size: 14px;
}

/* 用户区域 */
.user-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 主题切换按钮 */
.theme-toggle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-soft);
}

.theme-toggle:hover {
  transform: translateY(-2px) rotate(20deg);
  box-shadow: var(--shadow-medium);
  border-color: var(--primary-color);
}

.theme-icon {
  font-size: 22px;
  line-height: 1;
  transition: transform 0.3s ease;
}

.theme-toggle:active .theme-icon {
  transform: scale(0.9);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-hover);
  border: 2px solid var(--border-color);
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.username-btn:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: var(--shadow-soft);
}

.user-icon {
  font-size: 18px;
  line-height: 1;
}

.username-text {
  font-weight: 600;
}

.logout-btn {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border: none;
  color: white;
  padding: 10px 24px;
  border-radius: 20px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
}

.logout-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(245, 87, 108, 0.4);
}

.auth-buttons {
  display: flex;
  gap: 12px;
}

.login-btn {
  padding: 10px 24px;
  border-radius: 20px;
  border: 2px solid var(--primary-color);
  background: transparent;
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background: var(--primary-color);
  color: white;
  transform: translateY(-2px);
}

.register-btn {
  padding: 10px 24px;
  border-radius: 20px;
  background: var(--primary-gradient);
  border: none;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(88, 101, 242, 0.3);
}

.register-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(88, 101, 242, 0.4);
}

/* 主内容区 */
.app-main {
  flex: 1;
  position: relative;
  z-index: 1;
  padding: 40px 0;
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 32px;
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* 页脚 */
.app-footer {
  background: var(--bg-secondary);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--border-color);
  padding: 32px 0;
  position: relative;
  z-index: 1;
}

.footer-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 32px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}

.footer-content p {
  margin: 8px 0;
}

.footer-links {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
}

.footer-links a {
  color: var(--primary-color);
  text-decoration: none;
  transition: color 0.3s ease;
}

.footer-links a:hover {
  color: var(--primary-dark);
}

.footer-links span {
  color: var(--text-light);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    padding: 0 16px;
    height: auto;
    flex-wrap: wrap;
    padding-top: 12px;
    padding-bottom: 12px;
  }

  .nav-menu {
    order: 3;
    width: 100%;
    margin-top: 12px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .nav-item {
    padding: 8px 12px;
    font-size: 13px;
  }

  .nav-icon {
    font-size: 16px;
  }

  .logo-title {
    font-size: 20px;
  }

  .main-content {
    padding: 0 16px;
  }
}
</style>




