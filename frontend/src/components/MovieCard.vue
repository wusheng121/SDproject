<template>
  <div class="movie-card" @click="$emit('open', movie)">
    <div class="movie-poster">
      <img 
        v-if="movie?.poster_url" 
        :src="movie.poster_url" 
        :alt="movie.title"
        class="poster-image"
      />
      <div v-else class="poster-placeholder">
        <span class="placeholder-icon">🎬</span>
        <span class="placeholder-text">暂无海报</span>
      </div>
      
      <!-- 评分徽章 -->
      <div v-if="movie?.rating_avg != null" class="rating-badge">
        <span class="rating-star">⭐</span>
        <span class="rating-value">{{ movie.rating_avg.toFixed(1) }}</span>
      </div>

      <!-- 悬停遮罩 -->
      <div class="hover-overlay">
        <div class="overlay-content">
          <div class="overlay-icon">👁️</div>
          <div class="overlay-text">查看详情</div>
        </div>
      </div>
      </div>

    <div class="movie-info">
      <h3 class="movie-title" :title="movie?.title">{{ movie?.title || "-" }}</h3>
      
      <div class="movie-meta">
        <span v-if="movie?.release_year" class="meta-item">
          <span class="meta-icon">📅</span>
          <span>{{ movie.release_year }}</span>
        </span>
        <span v-if="movie?.rating_count" class="meta-item">
          <span class="meta-icon">👥</span>
          <span>{{ movie.rating_count }} 评分</span>
        </span>
      </div>

      <!-- ML预测评分（如果有） -->
      <div v-if="movie?.ml_predicted_rating" class="ml-prediction">
        <span class="ml-icon">🤖</span>
        <span class="ml-text">为你推荐 {{ movie.ml_predicted_rating.toFixed(1) }}分</span>
      </div>
    </div>
    </div>
</template>

<script setup>
defineProps({
  movie: {
    type: Object,
    default: null
  }
});

defineEmits(["open"]);
</script>

<style scoped>
.movie-card {
  background: var(--bg-card);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-soft);
  position: relative;
}

.movie-card:hover {
  transform: translateY(-12px) scale(1.02);
  box-shadow: 0 20px 40px rgba(88, 101, 242, 0.3);
}

.movie-card::before {
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

.movie-card:hover::before {
  opacity: 0.1;
}

/* 海报区域 */
.movie-poster {
  position: relative;
  width: 100%;
  padding-top: 150%; /* 2:3 宽高比 */
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  overflow: hidden;
}

.poster-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.movie-card:hover .poster-image {
  transform: scale(1.1);
}

.poster-placeholder {
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

/* 评分徽章 */
.rating-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(10px);
  padding: 6px 12px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 4px;
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

.rating-star {
  font-size: 14px;
}

.rating-value {
  color: white;
  font-weight: 700;
  font-size: 14px;
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

.movie-card:hover .hover-overlay {
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

.movie-card:hover .overlay-content {
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

/* 电影信息区域 */
.movie-info {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  z-index: 2;
}

.movie-title {
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

.movie-card:hover .movie-title {
  color: var(--primary-color);
}

.movie-meta {
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

/* ML推荐标签 */
.ml-prediction {
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

.ml-icon {
  font-size: 14px;
}

.ml-text {
  letter-spacing: 0.3px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .movie-title {
    font-size: 14px;
    min-height: 40px;
  }

  .movie-meta {
    font-size: 12px;
  }

  .rating-badge {
    padding: 4px 10px;
  }

  .rating-value {
    font-size: 13px;
  }
}
</style>






















