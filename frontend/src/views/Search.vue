<template>
  <div class="search-page">
    <div class="page-header">
      <h2 class="page-title">搜索商品</h2>
      <p class="page-subtitle">输入关键词，找到心仪的好物</p>
    </div>

    <el-card class="search-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="商品名称">
          <el-input 
            v-model="form.keyword" 
            placeholder="输入商品关键词" 
            style="width: 240px" 
            @keyup.enter="onSearch" 
          />
        </el-form-item>
        <el-form-item label="品类">
          <el-select
            v-model="form.category"
            clearable
            filterable
            placeholder="选择品类"
            style="width: 180px"
            @change="onSearch"
          >
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格范围">
          <el-input 
            v-model="form.min_price" 
            placeholder="最低价" 
            style="width: 100px" 
            type="number"
            @keyup.enter="onSearch" 
          />
          <span style="margin: 0 8px;">-</span>
          <el-input 
            v-model="form.max_price" 
            placeholder="最高价" 
            style="width: 100px" 
            type="number"
            @keyup.enter="onSearch" 
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSearch">搜索</el-button>
          <el-button @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="results-card">
      <div class="results-header">
        <span>搜索结果</span>
        <span v-if="total > 0" class="results-count">共 {{ total }} 件商品</span>
      </div>
      <el-empty v-if="results.length === 0" description="暂无结果，试试其他关键词" />
      <div v-else class="products-grid">
        <div v-for="p in results" :key="p.id" class="product-item">
          <ProductCard :product="p" @open="openProduct" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import ProductCard from "../components/ProductCard.vue";
import { apiListProducts, apiListCategories } from "../api/products";

const router = useRouter();
const results = ref([]);
const categories = ref([]);
const total = ref(0);

const form = reactive({
  keyword: "",
  category: "",
  min_price: "",
  max_price: ""
});

async function loadCategories() {
  try {
    const res = await apiListCategories();
    if (res.data.code === 0) {
      categories.value = res.data.data.items.map(c => c.name);
    }
  } catch (error) {
    console.error("加载品类失败:", error);
  }
}

async function onSearch() {
  try {
    const params = {
      page: 1,
      page_size: 20
    };
    
    if (form.keyword) params.keyword = form.keyword;
    if (form.category) params.category = form.category;
    if (form.min_price) params.min_price = parseFloat(form.min_price);
    if (form.max_price) params.max_price = parseFloat(form.max_price);
    
    const res = await apiListProducts(params);
    if (res.data.code === 0) {
      results.value = res.data.data.items || [];
      total.value = res.data.data.total || 0;
    }
  } catch (error) {
    console.error("搜索失败:", error);
    ElMessage.error("搜索失败，请重试");
  }
}

function onReset() {
  form.keyword = "";
  form.category = "";
  form.min_price = "";
  form.max_price = "";
  results.value = [];
  total.value = 0;
}

function openProduct(product) {
  router.push(`/product/${product.id}`);
}

onMounted(() => {
  loadCategories();
});
</script>

<style scoped>
.search-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
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

.search-card {
  margin-bottom: 24px;
}

.results-card {
  min-height: 400px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.results-count {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 400;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
  margin-top: 20px;
}

.product-item {
  animation: fadeIn 0.4s ease;
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
}
</style>
