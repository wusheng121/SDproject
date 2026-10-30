<template>
  <div class="home-page">
    <section class="marketplace-hero">
      <div class="hero-copy">
        <p class="eyebrow">CAMPUS MARKETPLACE</p>
        <h1>在校园里，找到<br /><span>下一件需要的好物</span></h1>
        <p class="hero-description">教材、数码、宿舍用品和运动装备，校内交易更近、更快，也更放心。</p>
        <div class="hero-actions">
          <button class="primary-action" type="button" @click="router.push('/search')">开始逛商品</button>
          <button class="secondary-action" type="button" @click="router.push('/publish')">发布我的闲置</button>
        </div>
      </div>
      <div class="hero-panel">
        <div class="panel-label">今日校园集市</div>
        <div class="panel-number">{{ totalProducts || products.length }}</div>
        <div class="panel-caption">件商品正在寻找新主人</div>
        <div class="panel-divider"></div>
        <div class="panel-row"><span>热门品类</span><strong>教材 · 数码 · 宿舍</strong></div>
        <div class="panel-row"><span>交易方式</span><strong>校内当面 · 方便可靠</strong></div>
      </div>
    </section>

    <section class="category-strip" aria-label="商品分类">
      <div class="section-heading compact-heading">
        <div><p class="eyebrow">BROWSE BY CATEGORY</p><h2>按品类逛逛</h2></div>
        <button class="text-action" type="button" @click="router.push('/search')">查看全部</button>
      </div>
      <div class="category-list">
        <button v-for="category in quickCategories" :key="category.name" class="category-item" type="button" @click="goToCategory(category.name)">
          <span class="category-icon">{{ category.short }}</span>
          <span>{{ category.name }}</span>
          <small>{{ category.note }}</small>
        </button>
      </div>
    </section>

    <section class="product-section recommendation-section">
      <div class="section-heading">
        <div><p class="eyebrow">PERSONAL PICKS</p><h2>为你推荐</h2><p>{{ recommendationMeta.message || "登录后根据兴趣和浏览行为，为你挑选校园好物。" }}</p></div>
        <div class="recommendation-actions">
          <button v-if="userStore.token" class="text-action" type="button" :disabled="recommendationLoading" @click="refreshRecommendations">{{ recommendationLoading ? "加载中..." : "换一批" }}</button>
          <button v-else class="text-action" type="button" @click="router.push('/login')">登录查看个性化推荐</button>
        </div>
      </div>
      <div v-if="recommendationLoading" class="loading-line">正在生成推荐...</div>
      <div v-else-if="recommendations.length" class="products-grid featured-grid">
        <ProductCard v-for="p in recommendations" :key="p.id" :product="p" @open="openProduct" />
      </div>
      <el-empty v-else-if="userStore.token" description="暂时没有可推荐的商品，请稍后再试" />
    </section>

    <section class="product-section">
      <div class="section-heading">
        <div><p class="eyebrow">TRENDING NOW</p><h2>校园热门好物</h2><p>同学们最近正在关注的商品，先到先得。</p></div>
        <button class="text-action" type="button" @click="router.push('/search')">进入集市</button>
      </div>
      <div v-if="loading" class="loading-line">正在加载商品...</div>
      <div v-else-if="products.length" class="products-grid">
        <ProductCard v-for="p in products" :key="p.id" :product="p" @open="openProduct" />
      </div>
      <el-empty v-else description="暂时没有商品，去发布第一件闲置吧" />
    </section>

    <section class="trust-strip">
      <div><strong>校内交易</strong><span>沟通距离更近，交付更方便</span></div>
      <div><strong>信息透明</strong><span>价格、成色和品类清晰展示</span></div>
      <div><strong>智能推荐</strong><span>从热门到个性化，帮你少走弯路</span></div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import ProductCard from "../components/ProductCard.vue";
import { apiListCategories, apiListProducts } from "../api/products";
import { apiGetRecommendations } from "../api/behavior";
import { useUserStore } from "../stores/user";

const router = useRouter();
const userStore = useUserStore();
const products = ref([]);
const recommendations = ref([]);
const recommendationMeta = ref({});
const recommendationOffset = ref(0);
const recommendationLoading = ref(false);
const categories = ref([]);
const totalProducts = ref(0);
const loading = ref(false);

const categoryDefaults = [
  { name: "教材书籍", short: "书", note: "课程资料" },
  { name: "数码产品", short: "数", note: "手机电脑" },
  { name: "宿舍用品", short: "宿", note: "生活好物" },
  { name: "运动户外", short: "动", note: "装备器材" },
  { name: "服饰鞋包", short: "衣", note: "穿搭配件" },
  { name: "其他闲置", short: "闲", note: "更多发现" }
];

const quickCategories = ref(categoryDefaults);

async function loadProducts() {
  try {
    loading.value = true;
    const res = await apiListProducts({ page: 1, page_size: 12, sort: "hot" });
    if (res.data.code === 0) {
      products.value = res.data.data.items || [];
      totalProducts.value = res.data.data.total || products.value.length;
    }
  } catch (error) {
    console.error("加载商品失败:", error);
    ElMessage.error("商品加载失败，请稍后重试");
  } finally {
    loading.value = false;
  }
}

async function loadRecommendations(offset = 0) {
  if (!userStore.token) {
    recommendations.value = [];
    return;
  }
  try {
    recommendationLoading.value = true;
    const res = await apiGetRecommendations(6, offset);
    const payload = res.data.data || {};
    recommendations.value = payload.items || [];
    recommendationMeta.value = payload;
    recommendationOffset.value = offset;
  } catch (error) {
    console.error("加载推荐失败:", error);
  } finally {
    recommendationLoading.value = false;
  }
}

async function refreshRecommendations() {
  const nextOffset = recommendationOffset.value + 6;
  await loadRecommendations(nextOffset >= (recommendationMeta.value.candidate_count || 0) ? 0 : nextOffset);
}

async function loadCategories() {
  try {
    const res = await apiListCategories();
    if (res.data.code === 0 && res.data.data.items?.length) {
      categories.value = res.data.data.items;
      quickCategories.value = categories.value.slice(0, 6).map((name, index) => ({
        name,
        short: categoryDefaults[index]?.short || "品",
        note: "校园好物"
      }));
    }
  } catch (error) {
    console.error("加载品类失败:", error);
  }
}

function goToCategory(category) {
  router.push({ path: "/search", query: { category } });
}

function openProduct(product) {
  router.push(`/product/${product.id}`);
}

onMounted(() => {
  loadProducts();
  loadRecommendations();
  loadCategories();
});
</script>

<style scoped>
.home-page { padding: 28px 0 0; }
.marketplace-hero { min-height: 330px; display: grid; grid-template-columns: 1.35fr .65fr; gap: 48px; align-items: center; padding: 52px 64px; color: #fff; background: #263b35; border-radius: 4px; }
.eyebrow { margin: 0 0 10px; color: var(--primary-color); font-size: 11px; font-weight: 800; letter-spacing: 1.2px; }
.marketplace-hero .eyebrow { color: #b8d8c8; }
.hero-copy h1 { margin: 0; font-size: clamp(34px, 4vw, 54px); line-height: 1.15; font-weight: 800; letter-spacing: 0; }
.hero-copy h1 span { color: #b8d8c8; }
.hero-description { max-width: 500px; margin: 20px 0 26px; color: rgba(255,255,255,.75); line-height: 1.8; font-size: 15px; }
.hero-actions { display: flex; gap: 12px; }
.primary-action, .secondary-action { border-radius: 4px; padding: 11px 18px; cursor: pointer; font-size: 14px; }
.primary-action { border: 1px solid #b8d8c8; color: #263b35; background: #b8d8c8; }
.secondary-action { border: 1px solid rgba(255,255,255,.45); color: white; background: transparent; }
.primary-action:hover, .secondary-action:hover { opacity: .86; }
.hero-panel { padding: 26px; border: 1px solid rgba(255,255,255,.2); background: rgba(255,255,255,.07); }
.panel-label { color: #b8d8c8; font-size: 13px; }
.panel-number { margin-top: 8px; font-size: 48px; line-height: 1; font-weight: 800; }
.panel-caption { margin-top: 8px; color: rgba(255,255,255,.65); font-size: 13px; }
.panel-divider { height: 1px; margin: 24px 0 14px; background: rgba(255,255,255,.2); }
.panel-row { display: flex; justify-content: space-between; gap: 12px; margin-top: 10px; color: rgba(255,255,255,.6); font-size: 12px; }
.panel-row strong { color: white; font-weight: 500; text-align: right; }
.category-strip, .product-section { margin-top: 48px; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 22px; }
.compact-heading { align-items: center; margin-bottom: 18px; }
.section-heading h2 { margin: 0; color: var(--text-primary); font-size: 25px; letter-spacing: 0; }
.section-heading p:not(.eyebrow) { margin: 8px 0 0; color: var(--text-secondary); font-size: 13px; }
.text-action { border: 0; padding: 4px 0; color: var(--primary-color); background: transparent; cursor: pointer; font-size: 13px; }
.text-action:hover { color: var(--primary-dark); text-decoration: underline; }
.category-list { display: grid; grid-template-columns: repeat(6, 1fr); border: 1px solid var(--border-color); background: var(--bg-card); }
.category-item { display: flex; flex-direction: column; align-items: flex-start; gap: 7px; min-height: 118px; padding: 18px; border: 0; border-right: 1px solid var(--border-color); color: var(--text-primary); background: transparent; cursor: pointer; text-align: left; }
.category-item:last-child { border-right: 0; }
.category-item:hover { background: var(--bg-hover); }
.category-icon { display: grid; place-items: center; width: 32px; height: 32px; color: var(--primary-color); border: 1px solid currentColor; border-radius: 50%; font-weight: 700; }
.category-item small { color: var(--text-secondary); font-size: 11px; }
.products-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }
.featured-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.loading-line { padding: 44px 0; color: var(--text-secondary); text-align: center; }
.trust-strip { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin: 56px 0 18px; padding: 24px 0; border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); }
.trust-strip div { display: flex; flex-direction: column; gap: 7px; }
.trust-strip strong { color: var(--text-primary); font-size: 14px; }
.trust-strip span { color: var(--text-secondary); font-size: 12px; }
@media (max-width: 900px) { .marketplace-hero { grid-template-columns: 1fr; gap: 28px; padding: 36px 28px; } .category-list { grid-template-columns: repeat(3, 1fr); } .category-item:nth-child(3) { border-right: 0; } .category-item:nth-child(-n+3) { border-bottom: 1px solid var(--border-color); } .products-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 600px) { .home-page { padding-top: 16px; } .marketplace-hero { padding: 28px 20px; } .hero-copy h1 { font-size: 34px; } .hero-actions { flex-direction: column; align-items: stretch; } .category-list, .trust-strip { grid-template-columns: repeat(2, 1fr); } .category-item:nth-child(3) { border-right: 1px solid var(--border-color); } .category-item:nth-child(even) { border-right: 0; } .category-item:nth-child(n+3) { border-bottom: 1px solid var(--border-color); } .category-item:nth-last-child(-n+2) { border-bottom: 0; } .products-grid, .featured-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } .section-heading { align-items: flex-start; } }
</style>
