<template>
  <div class="home-page">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">
          <span class="title-gradient">校园二手交易</span>
          <span class="title-highlight">智能推荐平台</span>
        </h1>
        <p class="banner-subtitle">基于AI的智能推荐，为你精选每一件好物</p>
        <div class="banner-stats">
          <div class="stat-item">
            <div class="stat-number">{{ products.length }}</div>
            <div class="stat-label">优质商品</div>
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
            <span>猜你喜欢</span>
          </h2>
          <button class="refresh-btn" @click="loadRecommendations">
            <span class="refresh-icon">🔄</span>
            <span>刷新</span>
          </button>
        </div>
        <p class="section-subtitle">基于你的兴趣和浏览历史精心挑选</p>
      </div>
      
      <div class="products-grid">
        <div 
          v-for="(p, index) in recommendations" 
          :key="p.id" 
          class="product-item"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <ProductCard :product="p" @open="openProduct" />
        </div>
      </div>
    </section>

    <!-- 热门商品 -->
    <section class="content-section">
      <div class="section-header">
        <div class="section-title-box">
          <h2 class="section-title">
            <span class="title-icon">🔥</span>
            <span>热门商品</span>
          </h2>
        </div>
        <p class="section-subtitle">大家都在看的优质好物</p>
      </div>
      
      <div class="products-grid">
        <div 
          v-for="(p, index) in products" 
          :key="p.id" 
          class="product-item"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <ProductCard :product="p" @open="openProduct" />
        </div>
      </div>
    </section>

    <!-- TODO: 兴趣标签选择对话框 -->
    <!-- <PreferenceDialog v-model="showPreferenceDialog" @saved="onPreferenceSaved" /> -->
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import ProductCard from "../components/ProductCard.vue";
import { apiListProducts } from "../api/products";
import { apiGetRecommendations } from "../api/behavior";
import { useUserStore } from "../stores/user";

const router = useRouter();
const userStore = useUserStore();

const products = ref([]);
const recommendations = ref([]);
const loading = ref(false);

// 加载热门商品
async function loadProducts() {
  try {
    loading.value = true;
    const res = await apiListProducts({ page: 1, page_size: 12, sort: "hot" });
    if (res.data.code === 0) {
      products.value = res.data.data.items || [];
    }
  } catch (error) {
    console.error("加载商品失败:", error);
    ElMessage.error("加载商品失败");
  } finally {
    loading.value = false;
  }
}

// 加载推荐商品
async function loadRecommendations() {
  if (!userStore.token) {
    return; // 未登录不加载推荐
  }
  
  try {
    const res = await apiGetRecommendations(6);
    if (res.data.code === 0) {
      recommendations.value = res.data.data.items || [];
      
      // 显示推荐策略信息（调试用）
      if (res.data.data.message) {
        console.log("推荐策略:", res.data.data.message);
      }
    }
  } catch (error) {
    console.error("加载推荐失败:", error);
  }
}

// 打开商品详情
function openProduct(product) {
  router.push(`/product/${product.id}`);
}

onMounted(() => {
  loadProducts();
  loadRecommendations();
});
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  padding-top: 60px;
  background: var(--bg-primary);
}

/* 欢迎横幅 */
.welcome-banner {
  position: relative;
  background: var(--primary-gradient);
  padding: 80px 24px;
  overflow: hidden;
  margin-bottom: 60px;
}

.banner-content {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.banner-title {
  font-size: 48px;
  font-weight: 800;
  line-height: 1.3;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-gradient {
  background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-highlight {
  color: #ffd700;
  text-shadow: 0 2px 20px rgba(255, 215, 0, 0.5);
}

.banner-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 40px;
  font-weight: 500;
}

.banner-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 40px;
  max-width: 600px;
  margin: 0 auto;
  padding: 30px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 36px;
  font-weight: 800;
  color: white;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.stat-divider {
  width: 1px;
  height: 50px;
  background: rgba(255, 255, 255, 0.3);
}

.banner-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  pointer-events: none;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.circle-1 {
  width: 300px;
  height: 300px;
  top: -100px;
  right: -100px;
  animation: float 20s ease-in-out infinite;
}

.circle-2 {
  width: 200px;
  height: 200px;
  bottom: -50px;
  left: 10%;
  animation: float 15s ease-in-out infinite reverse;
}

.circle-3 {
  width: 150px;
  height: 150px;
  top: 50%;
  left: -75px;
  animation: float 18s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-30px) rotate(180deg);
  }
}

/* 内容区域 */
.content-section {
  max-width: 1400px;
  margin: 0 auto 80px;
  padding: 0 24px;
}

.section-header {
  margin-bottom: 32px;
}

.section-title-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 36px;
}

.section-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--primary-gradient);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.refresh-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(88, 101, 242, 0.4);
}

.refresh-icon {
  font-size: 16px;
  display: inline-block;
  transition: transform 0.6s ease;
}

.refresh-btn:hover .refresh-icon {
  transform: rotate(360deg);
}

/* 商品网格 */
.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
}

.product-item {
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
@media (max-width: 768px) {
  .banner-title {
    font-size: 32px;
  }

  .banner-subtitle {
    font-size: 16px;
  }

  .banner-stats {
    gap: 20px;
    padding: 20px;
  }

  .stat-number {
    font-size: 24px;
  }

  .stat-label {
    font-size: 12px;
  }

  .section-title {
    font-size: 24px;
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }
}
</style>
