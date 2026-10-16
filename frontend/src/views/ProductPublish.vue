<template>
  <div class="publish-page">
    <div class="publish-container">
      <h1 class="page-title">发布商品</h1>
      
      <!-- TODO: 完整的商品发布表单待实现 -->
      <div class="placeholder-content">
        <div class="placeholder-icon">📸</div>
        <h2>商品发布功能正在开发中</h2>
        <p class="placeholder-desc">即将支持以下功能：</p>
        <ul class="feature-list">
          <li>📷 AI 拍照识物 - 自动识别商品品类、品牌、成色</li>
          <li>✏️ 商品信息编辑 - 名称、描述、价格、成色</li>
          <li>🏷️ 品类选择 - 保温杯、运动鞋、手机等</li>
          <li>🖼️ 多图上传 - 支持上传多张商品图片</li>
          <li>✅ 提交审核 - 管理员审核后上架</li>
        </ul>
        
        <div class="todo-section">
          <h3>🔧 开发任务（TODO）</h3>
          <div class="todo-list">
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>后端：实现 POST /api/products 商品发布接口</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>后端：实现 POST /api/ai/recognize AI 识物接口（初期 Mock）</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：商品发布表单（名称、描述、价格、成色、品类）</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：图片上传组件</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>前端：AI 识物按钮和结果展示</span>
            </div>
            <div class="todo-item">
              <span class="todo-checkbox">☐</span>
              <span>管理员审核流程对接</span>
            </div>
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn-secondary" @click="$router.back()">返回</button>
          <button class="btn-primary" disabled>开始发布（开发中）</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// TODO: 商品发布逻辑待实现
</script>

<style scoped>
.publish-page {
  min-height: 100vh;
  padding: 80px 20px 40px;
  background: var(--bg-primary);
}

.publish-container {
  max-width: 800px;
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
  text-align: center;
  box-shadow: var(--shadow-soft);
}

.placeholder-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.placeholder-content h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.placeholder-desc {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 30px;
}

.feature-list {
  text-align: left;
  max-width: 500px;
  margin: 0 auto 40px;
  padding: 0;
  list-style: none;
}

.feature-list li {
  font-size: 15px;
  color: var(--text-primary);
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.feature-list li:last-child {
  border-bottom: none;
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
}

.todo-list {
  text-align: left;
  max-width: 600px;
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
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 40px;
}

.btn-primary,
.btn-secondary {
  padding: 12px 32px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.btn-primary {
  background: var(--primary-gradient);
  color: white;
}

.btn-primary:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(88, 101, 242, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 2px solid var(--border-color);
}

.btn-secondary:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

@media (max-width: 768px) {
  .publish-page {
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

  .action-buttons {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
