<template>
  <div class="product-card" @click="$emit('open', product)">
    <div class="product-image">
      <img 
        v-if="product?.image_url" 
        :src="product.image_url" 
        :alt="product.name"
        class="image"
      />
      <div v-else class="image-placeholder">
        <span class="placeholder-icon">📦</span>
        <span class="placeholder-text">暂无图片</span>
      </div>
      
      <!-- 成色标签 -->
      <div v-if="product?.condition" class="condition-badge">
        {{ product.condition }}
      </div>

      <!-- 悬停遮罩 -->
      <div class="hover-overlay">
        <div class="overlay-content">
          <div class="overlay-icon">👁️</div>
          <div class="overlay-text">查看详情</div>
        </div>
      </div>
    </div>

    <div class="product-info">
      <h3 class="product-name" :title="product?.name">{{ product?.name || "-" }}</h3>
      
      <!-- 价格 -->
      <div class="product-price">
        <span class="price-symbol">¥</span>
        <span class="price-value">{{ product?.price?.toFixed(0) || "0" }}</span>
      </div>

      <div class="product-meta">
        <span v-if="product?.categories?.length" class="meta-item">
          <span class="meta-icon">🏷️</span>
          <span>{{ product.categories[0] }}</span>
        </span>
        <span v-if="product?.behavior_count" class="meta-item">
          <span class="meta-icon">❤️</span>
          <span>{{ product.behavior_count }}</span>
        </span>
      </div>

      <!-- 推荐理由（如果有） -->
      <div v-if="product?.reason" class="recommendation-reason">
        <span class="reason-icon">✨</span>
        <span class="reason-text">{{ product.reason }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  product: {
    type: Object,
    default: null
  }
});

defineEmits(["open"]);
</script>

<style scoped>
.product-card {
  background: var(--bg-card);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-soft);
  position: relative;
}

.product-card:hover {
  transform: translateY(-12px) scale(1.02);
  box-shadow: 0 20px 40px rgba(88, 101, 242, 0.3);
}

.product-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--primary-gradient);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
  z-index: 1;
}

.product-card:hover::before {
  opacity: 0.1;
}

/* 商品图片区域 */
.product-image {
  position: relative;
  width: 100%;
  padding-top: 100%; /* 1:1 宽高比 */
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  overflow: hidden;
}

.image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.product-card:hover .image {
  transform: scale(1.1);
}

.image-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--primary-gradient);
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.8;
}

.placeholder-text {
  color: white;
  font-size: 14px;
  font-weight: 500;
  opacity: 0.9;
}

/* 成色标签 */
.condition-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(10px);
  padding: 6px 12px;
  border-radius: 20px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  z-index: 2;
  animation: fadeInScale 0.5s ease;
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 悬停遮罩 */
.hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(88, 101, 242, 0.95) 0%, rgba(252, 70, 107, 0.95) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.4s ease;
  z-index: 2;
}

.product-card:hover .hover-overlay {
  opacity: 1;
}

.overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  transform: translateY(20px);
  transition: transform 0.4s ease;
}

.product-card:hover .overlay-content {
  transform: translateY(0);
}

.overlay-icon {
  font-size: 48px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.overlay-text {
  color: white;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* 商品信息区域 */
.product-info {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  z-index: 2;
}

.product-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  min-height: 44px;
  transition: color 0.3s ease;
}

.product-card:hover .product-name {
  color: var(--primary-color);
}

/* 价格 */
.product-price {
  display: flex;
  align-items: baseline;
  gap: 2px;
  color: #ff4d4f;
  font-weight: 700;
}

.price-symbol {
  font-size: 14px;
}

.price-value {
  font-size: 24px;
  line-height: 1;
}

.product-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-icon {
  font-size: 14px;
}

/* 推荐理由 */
.recommendation-reason {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--primary-gradient);
  border-radius: 20px;
  font-size: 12px;
  color: white;
  font-weight: 600;
  align-self: flex-start;
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0%, 100% {
    box-shadow: 0 0 10px rgba(88, 101, 242, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(88, 101, 242, 0.8);
  }
}

.reason-icon {
  font-size: 14px;
}

.reason-text {
  letter-spacing: 0.3px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .product-name {
    font-size: 14px;
    min-height: 40px;
  }

  .product-meta {
    font-size: 12px;
  }

  .price-value {
    font-size: 20px;
  }

  .condition-badge {
    padding: 4px 10px;
    font-size: 11px;
  }
}
</style>
