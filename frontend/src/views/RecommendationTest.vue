<template>
  <div class="test-page">
    <header class="page-heading"><div><p class="eyebrow">RECOMMENDATION LAB</p><h1>推荐效果测试</h1><p>调整偏好和行为样本，观察 A/B/C/D 阶段如何改变商品排序。</p></div><el-button @click="router.push('/user-center')">返回个人中心</el-button></header>

    <div class="test-layout">
      <aside class="control-panel">
        <h2>测试输入</h2>
        <label class="field-label">推荐阶段</label>
        <el-select v-model="form.stage" class="full-width"><el-option v-for="stage in stages" :key="stage.key" :label="`${stage.key} · ${stage.name}`" :value="stage.key" /></el-select>
        <div class="field-help">自动判断：无偏好为 A；有偏好且无行为为 B；1–9 次行为为 C；10 次及以上为 D。</div>

        <label class="field-label">兴趣品类</label>
        <el-select v-model="form.categories" class="full-width" multiple collapse-tags collapse-tags-tooltip placeholder="选择兴趣品类">
          <el-option v-for="category in categories" :key="category" :label="category" :value="category" />
        </el-select>

        <label class="field-label">模拟行为次数 <strong>{{ form.behavior_count }}</strong></label>
        <el-slider v-model="form.behavior_count" :min="0" :max="20" :marks="behaviorMarks" />
        <div class="field-help">仅改变本次预览使用的阶段，不会写入或伪造用户行为记录。</div>

        <el-button class="run-button" type="primary" :loading="loading" @click="runTest">运行推荐测试</el-button>
        <el-button class="reset-button" @click="loadSavedPreferences">载入我的真实偏好</el-button>
      </aside>

      <main class="results-panel">
        <div v-if="result" class="summary-grid">
          <div><span>当前阶段</span><strong>{{ result.strategy }} · {{ result.strategy_name }}</strong></div>
          <div><span>测试偏好</span><strong>{{ result.preferences?.length ? result.preferences.join("、") : "未设置" }}</strong></div>
          <div><span>历史行为</span><strong>{{ result.behavior_count }} 次</strong></div>
          <div><span>候选商品</span><strong>{{ result.candidate_count }} 件</strong></div>
        </div>

        <section class="stage-guide">
          <h2>阶段定义</h2>
          <div class="stage-list">
            <div v-for="stage in stages" :key="stage.key" :class="['stage-row', { selected: result?.strategy === stage.key }]"><b>{{ stage.key }}</b><div><strong>{{ stage.name }}</strong><p>{{ stage.description }}</p></div><span>{{ stage.rule }}</span></div>
          </div>
        </section>

        <section class="result-list">
          <div class="result-heading"><div><h2>本次推荐结果</h2><p>{{ result?.message || "配置测试输入后运行推荐。" }}</p></div><el-button v-if="result" @click="runTest">重新测试</el-button></div>
          <div v-if="loading" class="empty-hint">正在计算推荐结果...</div>
          <div v-else-if="result?.items?.length" class="products-grid"><article v-for="(item, index) in result.items" :key="item.id" class="result-item"><span class="rank">{{ index + 1 }}</span><ProductCard :product="item" @open="router.push(`/product/${item.id}`)" /><div class="score-line"><span>推荐分 {{ item.recommendation_score }}</span><span>{{ item.reason }}</span></div></article></div>
          <el-empty v-else-if="result" description="当前输入下没有可推荐商品" />
          <el-empty v-else description="推荐商品将显示在这里" />
        </section>

        <section v-if="result" class="validation-note"><strong>如何判断偏好是否生效</strong><p>对比 A 与 B：设置品类后，B 阶段应优先展示该品类商品；对比换不同品类，推荐理由和商品类别应随之变化。C/D 还会结合已记录行为；预览中的模拟次数只用于验证阶段切换，不会修改生产行为数据。</p></section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import ProductCard from "../components/ProductCard.vue";
import { apiListCategories } from "../api/products";
import { apiGetPreferences } from "../api/user";
import { apiPreviewRecommendations } from "../api/behavior";

const router = useRouter();
const categories = ref([]);
const loading = ref(false);
const result = ref(null);
const stages = [
  { key: "A", name: "全局热门", rule: "無偏好", description: "没有设置兴趣偏好时，按照全站互动热度排序。" },
  { key: "B", name: "兴趣内容推荐", rule: "有偏好，0 次行为", description: "优先推荐用户主动选择品类中的商品。" },
  { key: "C", name: "轻量混合", rule: "有偏好，1–9 次行为", description: "结合偏好品类与少量浏览、收藏等行为。" },
  { key: "D", name: "协同行为推荐", rule: "有偏好，≥10 次行为", description: "重点依据用户行为形成的品类兴趣排序。" }
];
const behaviorMarks = { 0: "0", 1: "B→C", 9: "9", 10: "C→D", 20: "20" };
const form = reactive({ stage: "B", categories: [], behavior_count: 0 });

async function loadCategories() {
  try {
    const response = await apiListCategories();
    categories.value = response.data?.data?.items || [];
  } catch (error) {
    ElMessage.error(error?.message || "品类加载失败");
  }
}
async function loadSavedPreferences() {
  try {
    const response = await apiGetPreferences();
    form.categories = response.data?.data?.preferred_categories || [];
    ElMessage.success("已载入账户真实偏好");
  } catch (error) {
    ElMessage.error(error?.message || "偏好加载失败");
  }
}
async function runTest() {
  loading.value = true;
  try {
    const response = await apiPreviewRecommendations({ stage: form.stage, categories: form.categories, behavior_count: form.behavior_count, limit: 8 });
    result.value = response.data?.data || null;
    if (!result.value) ElMessage.warning("没有收到推荐结果");
  } catch (error) {
    ElMessage.error(error?.message || "推荐测试失败");
  } finally {
    loading.value = false;
  }
}
onMounted(loadCategories);
</script>

<style scoped>
.test-page { padding: 34px 0; }
.page-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 24px; }
.eyebrow { margin: 0 0 7px; color: var(--primary-color); font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.page-heading h1 { margin: 0; color: var(--text-primary); font-size: 30px; }
.page-heading p:last-child { margin: 8px 0 0; color: var(--text-secondary); font-size: 13px; }
.test-layout { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 18px; align-items: start; }
.control-panel, .stage-guide, .result-list, .validation-note { border: 1px solid var(--border-color); background: var(--bg-card); }
.control-panel { padding: 20px; }
.control-panel h2, .stage-guide h2, .result-heading h2 { margin: 0; color: var(--text-primary); font-size: 17px; }
.field-label { display: flex; justify-content: space-between; margin: 20px 0 8px; color: var(--text-primary); font-size: 12px; font-weight: 650; }
.field-label strong { color: var(--primary-color); }
.full-width { width: 100%; }
.field-help { margin-top: 8px; color: var(--text-secondary); font-size: 11px; line-height: 1.65; }
.run-button, .reset-button { width: 100%; margin: 18px 0 0; }
.reset-button { margin-top: 8px; }
.results-panel { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid var(--border-color); background: var(--bg-card); }
.summary-grid div { display: flex; flex-direction: column; gap: 8px; min-width: 0; padding: 15px; border-right: 1px solid var(--border-color); }
.summary-grid div:last-child { border-right: 0; }
.summary-grid span { color: var(--text-secondary); font-size: 11px; }
.summary-grid strong { overflow: hidden; color: var(--text-primary); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.stage-guide { padding: 18px; }
.stage-list { margin-top: 13px; }
.stage-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 11px 9px; border-top: 1px solid var(--border-color); }
.stage-row.selected { background: var(--bg-hover); }
.stage-row > b { display: grid; width: 25px; height: 25px; place-items: center; color: white; background: var(--primary-color); border-radius: 50%; font-size: 12px; }
.stage-row strong { color: var(--text-primary); font-size: 12px; }
.stage-row p { margin: 4px 0 0; color: var(--text-secondary); font-size: 11px; }
.stage-row > span { color: var(--text-secondary); font-size: 10px; text-align: right; }
.result-list { padding: 18px; }
.result-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.result-heading p { margin: 6px 0 0; color: var(--text-secondary); font-size: 11px; }
.products-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 13px; }
.result-item { position: relative; min-width: 0; }
.rank { position: absolute; top: -7px; left: -7px; z-index: 2; display: grid; width: 23px; height: 23px; place-items: center; color: #fff; background: #c6533d; border-radius: 50%; font-size: 11px; font-weight: 700; }
.score-line { display: flex; justify-content: space-between; gap: 8px; padding-top: 6px; color: var(--text-secondary); font-size: 10px; }
.score-line span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-hint { padding: 32px 0; color: var(--text-secondary); text-align: center; }
.validation-note { padding: 17px 18px; }
.validation-note strong { color: var(--text-primary); font-size: 13px; }
.validation-note p { margin: 8px 0 0; color: var(--text-secondary); font-size: 11px; line-height: 1.75; }
@media (max-width: 900px) { .test-layout { grid-template-columns: 1fr; } .products-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 600px) { .test-page { padding-top: 24px; } .page-heading { align-items: flex-start; } .page-heading h1 { font-size: 25px; } .summary-grid { grid-template-columns: repeat(2, 1fr); } .summary-grid div:nth-child(2) { border-right: 0; } .summary-grid div:nth-child(-n+2) { border-bottom: 1px solid var(--border-color); } .products-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .stage-row { grid-template-columns: 28px minmax(0, 1fr); } .stage-row > span { grid-column: 2; text-align: left; } }
</style>
