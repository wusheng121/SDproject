<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- 左侧装饰区 -->
      <div class="auth-decoration">
        <div class="decoration-content">
          <div class="decoration-icon">🎬</div>
          <h2 class="decoration-title">欢迎回来</h2>
          <p class="decoration-text">继续你的精彩观影之旅</p>
          <div class="decoration-features">
            <div class="feature-item">
              <span class="feature-icon">🎯</span>
              <span>个性化推荐</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">⭐</span>
              <span>收藏与评分</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🔥</span>
              <span>发现热门影片</span>
            </div>
          </div>
        </div>
        <div class="decoration-bg">
          <div class="bg-circle circle-1"></div>
          <div class="bg-circle circle-2"></div>
          <div class="bg-circle circle-3"></div>
        </div>
      </div>

      <!-- 右侧表单区 -->
      <div class="auth-form-wrapper">
        <div class="auth-form">
          <div class="form-header">
            <h1 class="form-title">登录账户</h1>
            <p class="form-subtitle">输入你的账户信息以继续</p>
          </div>

          <form @submit.prevent="onSubmit" class="login-form">
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">👤</span>
                <span>用户名或邮箱</span>
              </label>
              <input 
                v-model="form.identifier" 
                type="text"
                class="form-input"
                placeholder="请输入用户名或邮箱"
                required
              />
            </div>

            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">🔒</span>
                <span>密码</span>
              </label>
              <input 
                v-model="form.password" 
                :type="showPassword ? 'text' : 'password'"
                class="form-input"
                placeholder="请输入密码"
                required
              />
              <button 
                type="button"
                class="password-toggle"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>

            <div class="form-options">
              <label class="remember-me">
                <input type="checkbox" v-model="form.remember" />
                <span>记住我</span>
              </label>
              <a class="forgot-password" @click="handleForgotPassword">忘记密码？</a>
            </div>

            <button 
              type="submit" 
              class="submit-btn"
              :disabled="loading"
            >
              <span v-if="!loading">立即登录</span>
              <span v-else class="loading-spinner">⏳ 登录中...</span>
            </button>
          </form>

          <div class="form-footer">
            <p class="footer-text">
              还没有账户？
              <a @click="router.push('/register')" class="footer-link">立即注册</a>
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 兴趣标签选择对话框 -->
    <PreferenceDialog v-model="showPreferenceDialog" @saved="onPreferenceSaved" />
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";

import { useUserStore } from "../stores/user";
import { apiGetPreferences } from "../api/user";
import PreferenceDialog from "../components/PreferenceDialog.vue";

const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const showPassword = ref(false);
const showPreferenceDialog = ref(false);

const form = reactive({
  identifier: "",
  password: "",
  remember: false
});

async function onSubmit() {
  if (!form.identifier || !form.password) {
    ElMessage.warning("请填写完整信息");
    return;
  }

  loading.value = true;
  try {
    const resp = await userStore.login(form);
    if (resp?.code === 0) {
      ElMessage.success("🎉 登录成功");
      // 登录成功后检查用户是否设置了兴趣标签
      setTimeout(() => {
        checkPreferences();
        router.push("/");
      }, 500);
    } else {
      ElMessage.error(resp?.message || "登录失败");
    }
  } finally {
    loading.value = false;
  }
}

async function checkPreferences() {
  try {
    const resp = await apiGetPreferences();
    const hasPreference = resp?.data?.has_preference || false;
    // 如果用户没有设置兴趣标签，弹出对话框
    if (!hasPreference) {
      setTimeout(() => {
        showPreferenceDialog.value = true;
      }, 1000);
    }
  } catch (err) {
    console.error("检查兴趣标签失败", err);
  }
}

function onPreferenceSaved() {
  ElMessage.success("兴趣标签已更新，推荐内容将根据您的偏好调整");
}

function handleForgotPassword() {
  ElMessage.info("请联系管理员重置密码");
}
</script>

<style scoped>
.auth-page {
  min-height: calc(100vh - 70px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.auth-container {
  display: flex;
  max-width: 1100px;
  width: 100%;
  background: var(--bg-secondary);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: var(--shadow-strong);
  animation: slideIn 0.6s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 左侧装饰区 */
.auth-decoration {
  flex: 1;
  background: var(--primary-gradient);
  padding: 60px 40px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.decoration-content {
  position: relative;
  z-index: 2;
  color: white;
  text-align: center;
}

.decoration-icon {
  font-size: 80px;
  margin-bottom: 24px;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.decoration-title {
  font-size: 36px;
  font-weight: 800;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.decoration-text {
  font-size: 18px;
  opacity: 0.95;
  margin: 0 0 48px 0;
  font-weight: 500;
}

.decoration-features {
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: flex-start;
  max-width: 300px;
  margin: 0 auto;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  width: 100%;
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateX(10px);
}

.feature-icon {
  font-size: 24px;
}

.decoration-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -100px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: -50px;
  left: -50px;
  animation: float 6s ease-in-out infinite reverse;
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 50%;
  left: 20%;
  animation: float 7s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(20px, -20px);
  }
}

/* 右侧表单区 */
.auth-form-wrapper {
  flex: 1;
  padding: 60px 50px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-form {
  width: 100%;
  max-width: 400px;
}

.form-header {
  margin-bottom: 40px;
}

.form-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.form-subtitle {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
  font-weight: 500;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  position: relative;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.label-icon {
  font-size: 18px;
}

.form-input {
  width: 100%;
  padding: 14px 18px;
  border: 2px solid var(--border-color);
  border-radius: 12px;
  font-size: 15px;
  transition: all 0.3s ease;
  background: var(--bg-card);
  color: var(--text-primary);
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 4px var(--bg-hover);
}

.form-input::placeholder {
  color: var(--text-light);
}

.password-toggle {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  transition: transform 0.2s ease;
}

.password-toggle:hover {
  transform: translateY(-50%) scale(1.1);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: -8px;
}

.remember-me {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
}

.remember-me input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--primary-color);
}

.forgot-password {
  font-size: 14px;
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.3s ease;
}

.forgot-password:hover {
  color: var(--primary-dark);
  text-decoration: underline;
}

.submit-btn {
  width: 100%;
  padding: 16px;
  background: var(--primary-gradient);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4);
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(88, 101, 242, 0.5);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.form-footer {
  margin-top: 32px;
  text-align: center;
}

.footer-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.footer-link {
  color: var(--primary-color);
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.3s ease;
}

.footer-link:hover {
  color: var(--primary-dark);
  text-decoration: underline;
}

/* 响应式设计 */
@media (max-width: 968px) {
  .auth-decoration {
    display: none;
  }

  .auth-form-wrapper {
    padding: 40px 30px;
  }
}

@media (max-width: 480px) {
  .auth-form-wrapper {
    padding: 30px 20px;
  }

  .form-title {
    font-size: 28px;
  }

  .form-subtitle {
    font-size: 14px;
  }
}
</style>








