<template>
  <div class="search-page">
    <div class="page-heading">
      <div><p class="eyebrow">CAMPUS MARKETPLACE</p><h1>逛一逛</h1><p>按关键词、品类和预算，找到合适的校园好物。</p></div>
    </div>

    <section class="search-tools">
      <el-form class="filter-form" @submit.prevent="onSearch">
        <div class="search-input-row">
          <el-input v-model="form.keyword" class="keyword-input" clearable placeholder="搜索商品名称" @keyup.enter="onSearch">
            <template #append><el-button type="primary" @click="onSearch">搜索</el-button></template>
          </el-input>
          <input ref="imageInput" type="file" accept="image/*" hidden @change="recognizeForSearch" />
          <el-button class="image-search-button" plain :loading="recognizing" @click="imageInput?.click()">拍照识物找同类</el-button>
        </div>
        <p v-if="recognizedHint" class="assist-hint">{{ recognizedHint }}</p>
        <div class="filter-row">
          <el-select v-model="form.category" clearable filterable placeholder="全部品类" @change="onSearch">
            <el-option v-for="category in categories" :key="category" :label="category" :value="category" />
          </el-select>
          <el-select v-model="form.min_condition" clearable placeholder="最低可接受成色" @change="onSearch">
            <el-option v-for="condition in conditions" :key="condition.value" :label="condition.label" :value="condition.value" />
          </el-select>
          <div class="price-range"><el-input v-model="form.min_price" type="number" min="0" placeholder="最低价" @keyup.enter="onSearch" /><span>至</span><el-input v-model="form.max_price" type="number" min="0" placeholder="最高价" @keyup.enter="onSearch" /><span>元</span></div>
          <el-select v-model="form.sort" placeholder="排序方式" @change="onSearch">
            <el-option label="综合热门" value="hot" /><el-option label="最新发布" value="new" /><el-option label="价格从低到高" value="price_asc" /><el-option label="价格从高到低" value="price_desc" />
          </el-select>
          <el-button @click="onReset">重置筛选</el-button>
        </div>
      </el-form>
    </section>

    <section class="results-section">
      <div class="results-heading"><div><h2>全部商品</h2><span>共 {{ total }} 件</span></div><span v-if="hasFilters" class="filter-note">已应用筛选条件</span></div>
      <div v-if="loading" class="loading-state">正在查找商品...</div>
      <div v-else-if="results.length" class="products-grid"><ProductCard v-for="product in results" :key="product.id" :product="product" @open="openProduct" /></div>
      <el-empty v-else description="没有找到符合条件的商品" />
      <div v-if="total > pageSize" class="pagination-row"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="loadResults" /></div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import ProductCard from "../components/ProductCard.vue";
import { apiListCategories, apiListProducts, apiRecognizeProduct, apiSearchProducts } from "../api/products";

const router = useRouter();
const route = useRoute();
const results = ref([]);
const categories = ref([]);
const total = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = 20;
const imageInput = ref(null);
const recognizing = ref(false);
const recognizedHint = ref("");
const conditions = [
  { label: "全新", value: "全新" },
  { label: "九成新及以上", value: "九成新" },
  { label: "八成新及以上", value: "八成新" },
  { label: "七成新及以上", value: "七成新" }
];
const form = reactive({ keyword: "", category: "", min_condition: "", min_price: "", max_price: "", sort: "hot" });
const hasFilters = computed(() => Object.values(form).some((value) => value && value !== "hot"));

async function recognizeForSearch(event) {
  const image = event.target.files?.[0];
  event.target.value = "";
  if (!image) return;
  recognizing.value = true;
  try {
    const response = await apiRecognizeProduct(image);
    const recognition = response.data.data.recognition;
    form.category = categories.value.includes(recognition.category) ? recognition.category : "";
    form.keyword = recognition.name && recognition.name !== "二手商品" ? recognition.name : recognition.keywords?.[0] || "";
    recognizedHint.value = `识别到${recognition.category}，可编辑关键词或品类后搜索`;
    onSearch();
  } catch (error) {
    ElMessage.error(error.message || "图片识别失败");
  } finally {
    recognizing.value = false;
  }
}

async function loadCategories() {
  try {
    const response = await apiListCategories();
    if (response.data.code === 0) categories.value = response.data.data.items || [];
  } catch (error) {
    console.error("加载品类失败:", error);
  }
}

async function loadResults() {
  loading.value = true;
  try {
    let response;
    if (form.keyword.trim()) {
      response = await apiSearchProducts({ q: form.keyword.trim(), category: form.category || undefined, min_condition: form.min_condition || undefined, min_price: form.min_price || undefined, max_price: form.max_price || undefined, sort: form.sort });
      const items = response.data.code === 0 ? response.data.data.items || [] : [];
      results.value = items.slice((page.value - 1) * pageSize, page.value * pageSize);
      total.value = response.data.data.total || 0;
    } else {
      response = await apiListProducts({ page: page.value, page_size: pageSize, category: form.category || undefined, min_condition: form.min_condition || undefined, min_price: form.min_price || undefined, max_price: form.max_price || undefined, sort: form.sort });
      if (response.data.code === 0) {
        results.value = response.data.data.items || [];
        total.value = response.data.data.total || 0;
      }
    }
    router.replace({ query: { ...route.query, ...(form.keyword ? { q: form.keyword } : {}), ...(form.category ? { category: form.category } : {}) } });
  } catch (error) {
    console.error("搜索失败:", error);
    ElMessage.error("搜索失败，请重试");
  } finally {
    loading.value = false;
  }
}

function onSearch() { page.value = 1; loadResults(); }
function onReset() {
  Object.assign(form, { keyword: "", category: "", min_condition: "", min_price: "", max_price: "", sort: "hot" });
  page.value = 1;
  router.replace({ query: {} });
  loadResults();
}
function openProduct(product) { router.push(`/product/${product.id}`); }

watch(() => route.query, (query) => {
  form.keyword = typeof query.q === "string" ? query.q : "";
  form.category = typeof query.category === "string" ? query.category : "";
}, { immediate: true });

onMounted(() => {
  loadCategories();
  loadResults();
});
</script>

<style scoped>
.search-page { padding: 36px 0 20px; }
.page-heading { margin-bottom: 28px; }
.eyebrow { margin: 0 0 8px; color: var(--primary-color); font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.page-heading h1 { margin: 0; color: var(--text-primary); font-size: 32px; }
.page-heading p:last-child { margin: 8px 0 0; color: var(--text-secondary); font-size: 14px; }
.search-tools { padding: 20px; border: 1px solid var(--border-color); background: var(--bg-card); }
.search-input-row { display: flex; align-items: center; gap: 10px; }
.keyword-input { flex: 1; min-width: 240px; max-width: 620px; }
.image-search-button { flex: 0 0 auto; min-height: 40px; }
.assist-hint { margin: 8px 0 0; color: var(--text-secondary); font-size: 12px; }
.filter-row { display: flex; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
.filter-row > .el-select { width: 160px; }
.price-range { display: flex; align-items: center; gap: 7px; color: var(--text-secondary); }
.price-range .el-input { width: 110px; }
.results-section { margin-top: 32px; }
.results-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.results-heading > div { display: flex; align-items: baseline; gap: 12px; }
.results-heading h2 { margin: 0; color: var(--text-primary); font-size: 21px; }
.results-heading span, .filter-note { color: var(--text-secondary); font-size: 12px; }
.products-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }
.loading-state, .pagination-row { padding: 28px 0; text-align: center; }
.pagination-row { display: flex; justify-content: center; }
@media (max-width: 850px) { .products-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 600px) { .search-page { padding-top: 24px; } .search-tools { padding: 14px; } .search-input-row { align-items: stretch; flex-direction: column; } .keyword-input { min-width: 0; max-width: none; width: 100%; } .image-search-button { width: 100%; margin-left: 0 !important; } .filter-row { align-items: stretch; } .filter-row > .el-select { width: calc(50% - 5px); } .price-range { width: 100%; } .price-range .el-input { flex: 1; width: 0; } .products-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } .results-heading { align-items: flex-start; } }
</style>
