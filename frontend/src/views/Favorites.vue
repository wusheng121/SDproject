<template>
  <div class="favorites-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">我的收藏</h2>
        <p class="page-subtitle">收藏的商品都在这里</p>
      </div>
      <el-button type="primary" @click="reload">
        <span class="refresh-icon">🔄</span>
        刷新
      </el-button>
    </div>

    <el-card class="favorites-card">
      <el-empty v-if="items.length === 0" description="暂无收藏，去商品详情页收藏试试吧" />
      <div v-else class="products-grid">
        <div v-for="p in items" :key="p.id" class="product-item">
          <ProductCard :product="p" @open="openProduct" />
          <el-button 
            class="remove-btn" 
            size="small" 
            type="danger" 
            @click.stop="removeFavorite(p.id)"
          >
            移除收藏
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";

import ProductCard from "../components/ProductCard.vue";
import { apiGetUserBehaviors, apiAddBehavior } from "../api/behavior";

const router = useRouter();
const items = ref([]);

async function reload() {
  try {
    const res = await apiGetUserBehaviors({ behavior_type: "favorite" });
    if (res.data.code === 0) {
      // 提取商品信息
      items.value = res.data.data.items.map(b => b.product);
    }
  } catch (error) {
    console.error("加载收藏失败:", error);
    ElMessage.error("加载收藏失败");
  }
}

async function removeFavorite(productId) {
  try {
    await ElMessageBox.confirm('确定要移除这件商品吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    // TODO: 需要后端提供删除收藏的接口
    // 暂时使用添加收藏接口，传 favorite: false
    await apiAddBehavior({
      product_id: productId,
      behavior_type: "favorite",
      value: 0  // 0表示取消收藏
    });
    
    ElMessage.success("已移除收藏");
    await reload();
  } catch (error) {
    if (error !== 'cancel') {
      console.error("移除收藏失败:", error);
      ElMessage.error("移除收藏失败");
    }
  }
}

function openProduct(product) {
  router.push(`/product/${product.id}`);
}

onMounted(reload);
</script>

<style scoped>
.favorites-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.refresh-icon {
  margin-right: 4px;
}

.favorites-card {
  min-height: 400px;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

.product-item {
  position: relative;
  animation: fadeIn 0.4s ease;
}

.remove-btn {
  margin-top: 12px;
  width: 100%;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
