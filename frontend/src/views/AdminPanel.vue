<template>
  <div class="admin-page">
    <div class="admin-container">
      <h1 class="page-title">管理后台</h1>
      
      <!-- TODO: 完整的管理后台待实现 -->
      <div class="placeholder-content">
        <div class="placeholder-icon">⚙️</div>
        <h2>管理后台功能正在开发中</h2>
        <p class="placeholder-desc">即将支持以下管理功能：</p>
        
        <div class="feature-grid">
          <div class="feature-card">
            <div class="feature-icon">👥</div>
            <h3>用户管理</h3>
            <p>查看用户列表、封禁违规用户</p>
          </div>
          
          <div class="feature-card">
            <div class="feature-icon">📦</div>
            <h3>商品审核</h3>
            <p>审核待上架商品、下架违规商品</p>
          </div>
          
          <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h3>数据统计</h3>
            <p>用户数、商品数、交易数据统计</p>
          </div>
          
          <div class="feature-card">
            <div class="feature-icon">📝</div>
            <h3>操作日志</h3>
            <p>查看平台操作日志、审计记录</p>
          </div>
        </div>
        
        <div class="todo-section">
          <h3>🔧 开发任务（TODO）</h3>
          <div class="todo-list">
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>后端：实现 RBAC 权限检查装饰器</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>后端：完善 /api/admin/* 系列接口</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>后端：创建操作日志表和记录机制</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：用户管理页面（列表、搜索、封禁）</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：商品审核页面（待审核列表、通过/拒绝）</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：统计数据展示（图表、数据看板）</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：操作日志查询页面</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>路由守卫：验证管理员权限</span>
            </div>
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn-secondary" @click="$router.push('/')">返回首页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// TODO: 管理后台逻辑待实现
// 需要检查当前用户是否为管理员
import { useUserStore } from "../stores/user";

const userStore = useUserStore();

// TODO: 添加权限检查
// if (userStore.user?.user_type !== 'admin') {
//   router.push('/');
// }
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding: 80px 20px 40px;
  background: var(--bg-primary);
}

.admin-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 40px;
  text-align: center;
}

.placeholder-content {
  background: var(--bg-card);
  border-radius: 24px;
  padding: 60px 40px;
  box-shadow: var(--shadow-soft);
}

.placeholder-icon {
  font-size: 80px;
  margin-bottom: 20px;
  text-align: center;
}

.placeholder-content h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
  text-align: center;
}

.placeholder-desc {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 40px;
  text-align: center;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}

.feature-card {
  background: var(--bg-primary);
  border-radius: 16px;
  padding: 30px 24px;
  text-align: center;
  transition: all 0.3s ease;
  border: 2px solid var(--border-color);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(88, 101, 242, 0.2);
  border-color: var(--primary-color);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.feature-card p {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.todo-section {
  margin-top: 40px;
  padding-top: 40px;
  border-top: 2px dashed var(--border-color);
}

.todo-section h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 20px;
  text-align: center;
}

.todo-list {
  max-width: 700px;
  margin: 0 auto;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.todo-checkbox {
  font-size: 18px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 40px;
}

.btn-secondary {
  padding: 12px 32px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  background: transparent;
  color: var(--text-primary);
  border: 2px solid var(--border-color);
}

.btn-secondary:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

@media (max-width: 768px) {
  .admin-page {
    padding: 60px 16px 30px;
  }

  .page-title {
    font-size: 24px;
  }

  .placeholder-content {
    padding: 40px 24px;
  }

  .placeholder-icon {
    font-size: 60px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>
