<template>
  <div class="product-detail-page">
    <el-card v-if="product" class="detail-card">
      <div class="product-container">
        <!-- 左侧：商品图片 -->
        <div class="product-image-section">
          <div class="main-image">
            <img 
              v-if="product.image_url" 
              :src="product.image_url" 
              :alt="product.name"
            />
            <div v-else class="image-placeholder">
              <span class="placeholder-icon">📦</span>
              <span class="placeholder-text">暂无图片</span>
            </div>
          </div>
        </div>

        <!-- 右侧：商品信息 -->
        <div class="product-info-section">
          <h1 class="product-title">{{ product.name }}</h1>
          
          <div class="product-price">
            <span class="price-label">价格：</span>
            <span class="price-value">¥{{ product.price }}</span>
          </div>

          <div class="product-meta">
            <div class="meta-item">
              <span class="meta-label">成色：</span>
              <el-tag type="success">{{ product.condition }}</el-tag>
            </div>
            <div class="meta-item">
              <span class="meta-label">品类：</span>
              <el-tag v-for="cat in product.categories" :key="cat" type="info">
                {{ cat }}
              </el-tag>
            </div>
            <div class="meta-item">
              <span class="meta-label">状态：</span>
              <el-tag :type="statusType(product.status)">
                {{ statusText(product.status) }}
              </el-tag>
            </div>
            <div class="meta-item">
              <span class="meta-label">卖家：</span>
              <span>{{ product.seller?.username || '未知' }}</span>
            </div>
          </div>

          <el-divider />

          <div class="product-description">
            <h3>商品描述</h3>
            <p>{{ product.description || '暂无描述' }}</p>
          </div>

          <div class="action-buttons">
            <el-button type="primary" size="large" @click="handleContact">
              联系卖家
            </el-button>
            <el-button 
              :type="isFavorited ? 'danger' : 'default'" 
              size="large" 
              @click="toggleFavorite"
            >
              <span v-if="isFavorited">💔 取消收藏</span>
              <span v-else>❤️ 收藏</span>
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 相似商品推荐 -->
    <el-card v-if="similarProducts.length > 0" class="similar-card">
      <h2 class="section-title">相似商品推荐</h2>
      <div class="products-grid">
        <div v-for="p in similarProducts" :key="p.id" class="product-item">
          <ProductCard :product="p" @open="openProduct" />
        </div>
      </div>
    </el-card>

    <el-empty v-if="!product && !loading" description="商品不存在" />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import ProductCard from "../components/ProductCard.vue";
import { apiProductDetail, apiListProducts } from "../api/products";
import { apiAddBehavior } from "../api/behavior";
import { useUserStore } from "../stores/user";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const product = ref(null);
const similarProducts = ref([]);
const loading = ref(false);
const isFavorited = ref(false);

async function loadProduct() {
  loading.value = true;
  try {
    const id = route.params.id;
    const res = await apiProductDetail(id);
    
    if (res.data.code === 0) {
      product.value = res.data.data;
      
      // 记录浏览行为
      if (userStore.token) {
        recordView(id);
      }
      
      // 加载相似商品
      loadSimilarProducts();
    }
  } catch (error) {
    console.error("加载商品失败:", error);
    ElMessage.error("加载商品失败");
  } finally {
    loading.value = false;
  }
}

async function recordView(productId) {
  try {
    await apiAddBehavior({
      product_id: productId,
      behavior_type: "view",
      value: 1
    });
  } catch (error) {
    console.error("记录浏览失败:", error);
  }
}

async function loadSimilarProducts() {
  try {
    // TODO: 后续可以调用专门的相似推荐接口
    // 暂时获取同品类的商品
    const category = product.value.categories?.[0];
    if (category) {
      const res = await apiListProducts({ 
        category, 
        page_size: 4 
      });
      if (res.data.code === 0) {
        similarProducts.value = res.data.data.items.filter(
          p => p.id !== product.value.id
        );
      }
    }
  } catch (error) {
    console.error("加载相似商品失败:", error);
  }
}

async function toggleFavorite() {
  if (!userStore.token) {
    ElMessage.warning("请先登录");
    router.push("/login");
    return;
  }

  try {
    await apiAddBehavior({
      product_id: product.value.id,
      behavior_type: "favorite",
      value: isFavorited.value ? 0 : 1
    });
    
    isFavorited.value = !isFavorited.value;
    ElMessage.success(isFavorited.value ? "收藏成功" : "取消收藏");
  } catch (error) {
    console.error("收藏操作失败:", error);
    ElMessage.error("操作失败，请重试");
  }
}

function handleContact() {
  // TODO: 实现联系卖家功能
  ElMessage.info("联系卖家功能开发中...");
}

function openProduct(p) {
  router.push(`/product/${p.id}`);
  loadProduct();
}

function statusType(status) {
  const map = {
    'pending': 'warning',
    'approved': 'success',
    'rejected': 'danger',
    'sold': 'info'
  };
  return map[status] || 'info';
}

function statusText(status) {
  const map = {
    'pending': '待审核',
    'approved': '在售',
    'rejected': '已拒绝',
    'sold': '已售出'
  };
  return map[status] || status;
}

onMounted(() => {
  loadProduct();
});
</script>

<style scoped>
.product-detail-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.detail-card {
  margin-bottom: 24px;
}

.product-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
}

.product-image-section {
  position: sticky;
  top: 24px;
  height: fit-content;
}

.main-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 16px;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.main-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.placeholder-icon {
  font-size: 64px;
  opacity: 0.5;
}

.placeholder-text {
  color: #999;
  font-size: 16px;
}

.product-info-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.product-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.3;
}

.product-price {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.price-label {
  font-size: 16px;
  color: var(--text-secondary);
}

.price-value {
  font-size: 42px;
  font-weight: 800;
  color: #ff4d4f;
}

.product-meta {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
}

.meta-label {
  color: var(--text-secondary);
  min-width: 80px;
}

.product-description h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.product-description p {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-wrap;
}

.action-buttons {
  display: flex;
  gap: 16px;
  margin-top: 24px;
}

.action-buttons .el-button {
  flex: 1;
}

.similar-card {
  margin-bottom: 24px;
}

.section-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 24px 0;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

@media (max-width: 1024px) {
  .product-container {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .product-image-section {
    position: static;
  }

  .products-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .product-title {
    font-size: 24px;
  }

  .price-value {
    font-size: 32px;
  }

  .action-buttons {
    flex-direction: column;
  }

  .products-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}
</style>
