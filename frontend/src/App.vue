<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <button class="brand" type="button" @click="router.push('/')">
          <span class="brand-mark">校</span>
          <span class="brand-copy">
            <strong>校园闲置</strong>
            <small>让好物继续流动</small>
          </span>
        </button>

        <nav class="nav-menu" aria-label="主导航">
          <button
            v-for="item in navItems"
            :key="item.path"
            type="button"
            :class="['nav-item', { active: activePath === item.path }]"
            @click="router.push(item.path)"
          >
            <span>{{ item.label }}</span>
          </button>
        </nav>

        <div class="user-section">
          <button
            class="theme-toggle"
            type="button"
            :title="isDarkMode ? '切换到日间模式' : '切换到夜间模式'"
            @click="toggleTheme"
          >
            {{ isDarkMode ? '日间' : '夜间' }}
          </button>
          <template v-if="hasToken">
            <button class="user-entry" type="button" @click="router.push('/user-center')">
              <span class="avatar">{{ (userStore.username || '用户').slice(0, 1) }}</span>
              <span class="username-text">{{ userStore.username || '用户' }}</span>
            </button>
            <button class="logout-btn" type="button" @click="logout">退出</button>
          </template>
          <template v-else>
            <button class="login-btn" type="button" @click="router.push('/login')">登录</button>
            <button class="register-btn" type="button" @click="router.push('/register')">注册</button>
          </template>
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <footer class="app-footer">
      <div class="footer-content">
        <strong>校园闲置</strong>
        <span>校内好物交换，让每件闲置都有下一站</span>
        <span>© 2026 Campus Market</span>
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

const navItems = computed(() => {
  const items = [
    { path: "/", label: "首页" },
    { path: "/search", label: "逛一逛" },
    { path: "/publish", label: "发布闲置" },
    { path: "/favorites", label: "我的收藏" }
  ];
  if (userStore.token) items.push({ path: "/assistant", label: "购物助手" });
  if (userStore.isAdmin) items.push({ path: "/admin", label: "管理后台" });
  return items;
});

async function logout() {
  await userStore.logout();
  router.push("/login");
}
</script>

<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--text-primary);
  background: var(--bg-primary);
}
button { font: inherit; }
.app-container { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg-primary); }
.app-header { position: sticky; top: 0; z-index: 10; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); }
.header-content { width: min(1240px, calc(100% - 40px)); height: 72px; margin: 0 auto; display: flex; align-items: center; gap: 42px; }
.brand { display: flex; align-items: center; gap: 10px; border: 0; padding: 0; color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.brand-mark { width: 38px; height: 38px; display: grid; place-items: center; color: white; background: var(--primary-color); border-radius: 10px; font-weight: 800; font-size: 20px; }
.brand-copy { display: flex; flex-direction: column; gap: 2px; white-space: nowrap; }
.brand-copy strong { font-size: 18px; letter-spacing: 0; }
.brand-copy small { color: var(--text-secondary); font-size: 11px; }
.nav-menu { display: flex; align-items: stretch; gap: 24px; height: 100%; flex: 1; }
.nav-item { position: relative; border: 0; padding: 0 2px; color: var(--text-secondary); background: transparent; cursor: pointer; font-size: 14px; }
.nav-item:hover, .nav-item.active { color: var(--primary-color); }
.nav-item.active::after { content: ""; position: absolute; right: 0; bottom: 0; left: 0; height: 3px; background: var(--primary-color); border-radius: 3px 3px 0 0; }
.user-section { display: flex; align-items: center; gap: 10px; white-space: nowrap; }
.theme-toggle, .login-btn, .logout-btn { border: 1px solid var(--border-color); padding: 8px 12px; color: var(--text-secondary); background: transparent; border-radius: 6px; cursor: pointer; font-size: 13px; }
.theme-toggle:hover, .login-btn:hover, .logout-btn:hover { color: var(--primary-color); border-color: var(--primary-color); }
.register-btn { border: 1px solid var(--primary-color); padding: 9px 16px; color: white; background: var(--primary-color); border-radius: 6px; cursor: pointer; font-size: 13px; }
.register-btn:hover { background: var(--primary-dark); }
.user-entry { display: flex; align-items: center; gap: 8px; border: 0; color: var(--text-primary); background: transparent; cursor: pointer; }
.avatar { width: 30px; height: 30px; display: grid; place-items: center; color: white; background: var(--primary-color); border-radius: 50%; font-size: 13px; font-weight: 700; }
.username-text { font-size: 13px; }
.app-main { flex: 1; }
.main-content { width: min(1240px, calc(100% - 40px)); margin: 0 auto; }
.app-footer { margin-top: 48px; border-top: 1px solid var(--border-color); background: var(--bg-secondary); }
.footer-content { width: min(1240px, calc(100% - 40px)); min-height: 68px; margin: 0 auto; display: flex; align-items: center; gap: 20px; color: var(--text-secondary); font-size: 12px; }
.footer-content strong { color: var(--text-primary); font-size: 14px; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s ease, transform .2s ease; }
.fade-enter-from { opacity: 0; transform: translateY(8px); }
.fade-leave-to { opacity: 0; transform: translateY(-8px); }
@media (max-width: 800px) {
  .header-content { width: calc(100% - 24px); height: auto; min-height: 64px; flex-wrap: wrap; gap: 12px; padding: 12px 0 0; }
  .nav-menu { order: 3; width: 100%; height: 42px; gap: 20px; overflow-x: auto; }
  .nav-item { flex: 0 0 auto; }
  .user-section { margin-left: auto; }
  .username-text, .theme-toggle { display: none; }
  .main-content, .footer-content { width: calc(100% - 24px); }
  .footer-content { flex-wrap: wrap; padding: 16px 0; gap: 8px 16px; }
}
</style>
