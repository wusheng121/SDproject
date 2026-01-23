<template>
  <div class="auth-page">
    <div class="auth-container">
      <!-- 左侧装饰区 -->
      <div class="auth-decoration">
        <div class="decoration-content">
          <div class="decoration-icon">🎬</div>
          <h2 class="decoration-title">加入 CineMatch</h2>
          <p class="decoration-text">开启你的智能观影之旅</p>
          <div class="decoration-features">
            <div class="feature-item">
              <span class="feature-icon">✨</span>
              <span>AI智能推荐</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🎯</span>
              <span>个性化定制</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">💎</span>
              <span>海量精选影片</span>
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
            <h1 class="form-title">创建账户</h1>
            <p class="form-subtitle">填写信息，开始你的电影探索之旅</p>
          </div>

          <form @submit.prevent="onSubmit" class="register-form">
            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">👤</span>
                <span>用户名</span>
              </label>
              <input 
                v-model="form.username" 
                type="text"
                class="form-input"
                placeholder="请输入用户名（3-20个字符）"
                required
              />
            </div>

            <div class="form-group">
              <label class="form-label">
                <span class="label-icon">📧</span>
                <span>邮箱地址</span>
              </label>
              <input 
                v-model="form.email" 
                type="email"
                class="form-input"
                placeholder="your@email.com"
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
                placeholder="请输入密码（至少6个字符）"
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

            <button 
              type="submit" 
              class="submit-btn"
              :disabled="loading"
            >
              <span v-if="!loading">立即注册</span>
              <span v-else class="loading-spinner">⏳ 注册中...</span>
            </button>
          </form>

          <div class="form-footer">
            <p class="footer-text">
              已有账户？
              <a @click="router.push('/login')" class="footer-link">立即登录</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";

import { apiRegister } from "../api/user";

const router = useRouter();
const loading = ref(false);
const showPassword = ref(false);

const form = reactive({
  username: "",
  email: "",
  password: ""
});

async function onSubmit() {
  // 简单验证
  if (form.username.length < 3) {
    ElMessage.warning("用户名至少3个字符");
    return;
  }
  if (form.password.length < 6) {
    ElMessage.warning("密码至少6个字符");
    return;
  }

  loading.value = true;
  try {
    const resp = await apiRegister(form);
    if (resp?.code === 0) {
      ElMessage.success("🎉 注册成功，请登录");
      setTimeout(() => {
        router.push("/login");
      }, 1000);
    } else {
      ElMessage.error(resp?.message || "注册失败");
    }
  } finally {
    loading.value = false;
  }
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

.register-form {
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






















