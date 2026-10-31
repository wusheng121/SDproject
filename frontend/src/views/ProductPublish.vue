<template>
  <div class="publish-page">
    <div class="page-heading">
      <div><p class="eyebrow">SELLER STUDIO</p><h1>让闲置，找到下一位需要它的人</h1><p>完善商品信息，让买家更快了解你的物品。</p></div>
      <div class="hero-progress"><span class="progress-dot active">1</span><span>填写信息</span><i></i><span class="progress-dot">2</span><span>提交审核</span></div>
    </div>

    <div class="publish-layout">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="publish-form" @submit.prevent="submitForm">
        <section class="form-section ai-section">
          <div class="section-heading"><div><span class="section-kicker">OPTIONAL AI ASSIST</span><h2>拍张照片，AI 帮你填写</h2><p>识别商品品类、品牌与成色，结果都可以手动修改。</p></div><span class="ai-badge">智能辅助</span></div>
          <div class="recognition-tools">
            <input ref="imageInput" type="file" accept="image/*" hidden @change="recognizeImage" />
            <el-button type="primary" :loading="recognizing" @click="imageInput?.click()">{{ recognizing ? "正在识别…" : "选择商品照片" }}</el-button>
            <span>可选步骤 · 不使用也可以直接填写</span>
          </div>
          <img v-if="imagePreview" :src="imagePreview" class="image-preview" alt="商品图片预览" />
        </section>

        <section class="form-section">
          <div class="section-heading"><div><span class="section-kicker">01 · 商品信息</span><h2>商品信息</h2><p>把名称、品类、成色和使用情况一次写清楚。</p></div></div>
          <el-form-item label="商品名称" prop="name"><el-input v-model="form.name" maxlength="200" placeholder="如：小米 13 256G" /></el-form-item>
          <div class="two-columns">
            <el-form-item label="商品品类" prop="category"><el-select v-model="form.category" filterable placeholder="请选择品类"><el-option v-for="category in categories" :key="category" :label="category" :value="category" /></el-select></el-form-item>
            <el-form-item label="品牌"><el-input v-model="form.brand" maxlength="100" placeholder="如：小米、无品牌" /></el-form-item>
          </div>
          <div class="two-columns">
            <el-form-item label="商品成色" prop="condition"><el-select v-model="form.condition" placeholder="请选择"><el-option v-for="condition in conditionOptions" :key="condition" :label="condition" :value="condition" /></el-select></el-form-item>
            <el-form-item label="是否有笔记"><el-select v-model="form.has_notes"><el-option label="没有笔记" :value="false" /><el-option label="有少量笔记" :value="true" /></el-select></el-form-item>
          </div>
          <el-form-item label="商品描述" prop="description"><el-input v-model="form.description" type="textarea" :rows="4" maxlength="4000" show-word-limit placeholder="介绍购买时间、使用情况和配件，例如：使用一年，功能正常，附原装充电器。" /></el-form-item>
          <el-form-item label="瑕疵说明"><el-input v-model="form.defect_description" maxlength="500" placeholder="如：边角有轻微磨损；没有瑕疵可留空" /></el-form-item>
          <p class="form-tip">如实描述成色和瑕疵，能减少交易沟通成本。</p>
        </section>

        <section class="form-section">
          <div class="section-heading"><div><span class="section-kicker">02 · 价格板块</span><h2>价格与交易</h2><p>查看同类商品行情，再填写期望价格和交接方式。</p></div></div>
          <el-form-item label="期望价格（元）" prop="price"><el-input v-model="form.price" type="number" min="0.01" step="0.01" placeholder="输入你期望的售价" /></el-form-item>
          <div class="price-reference">
            <div><strong>同类商品价格参考</strong><span v-if="priceReference">{{ priceReference.sample_count }} 件已审核商品</span></div>
            <p v-if="priceReference?.sample_count">近期价格 {{ priceReference.min_price }} - {{ priceReference.max_price }} 元，中位数 {{ priceReference.median_price }} 元</p>
            <p v-else>{{ priceReference ? "暂无足够的同类历史商品，可自行定价。" : "选择品类和成色后查询历史参考价。" }}</p>
            <el-button size="small" :loading="loadingPrice" :disabled="!form.category || !form.condition" @click="loadPriceReference">查询价格参考</el-button>
          </div>
          <div class="two-columns">
            <el-form-item label="交易方式"><el-select v-model="form.trade_method" clearable placeholder="请选择"><el-option label="校内当面交易" value="线下当面" /><el-option label="快递邮寄" value="快递邮寄" /><el-option label="均可协商" value="均可协商" /></el-select></el-form-item>
            <el-form-item label="期望交易地点"><el-input v-model="form.trade_location" maxlength="200" placeholder="如：校门口、图书馆附近" /></el-form-item>
          </div>
        </section>
        <div class="form-actions"><el-button @click="router.back()">取消</el-button><el-button type="primary" :loading="submitting" @click="submitForm">提交审核</el-button></div>
      </el-form>
      <aside class="guide-panel">
        <div class="guide-heading"><span class="guide-mark">✓</span><div><h2>发布小贴士</h2><p>把这几项写好，更容易成交</p></div></div>
        <ul><li><strong>标题写清品牌和型号</strong><span>方便买家搜索和判断</span></li><li><strong>成色选择贴近实际</strong><span>笔记、磨损情况可以单独说明</span></li><li><strong>先参考行情再定价</strong><span>价格建议基于同类已审核商品</span></li></ul>
        <div class="review-note"><strong>提交后会发生什么？</strong><p>商品将进入管理员审核，通过后展示在商品列表。</p></div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { apiGetPriceReference, apiListCategories, apiPublishProduct, apiRecognizeProduct } from "../api/products";

const router = useRouter();
const formRef = ref(null);
const imageInput = ref(null);
const categories = ref([]);
const conditionOptions = ["全新", "九五新", "九成新", "八成新", "七成新"];
const recognizing = ref(false);
const loadingPrice = ref(false);
const submitting = ref(false);
const priceReference = ref(null);
const imagePreview = ref("");
const form = reactive({ name: "", brand: "", category: "", description: "", condition: "", has_notes: false, defect_description: "", price: "", trade_method: "", trade_location: "" });
const rules = {
  name: [{ required: true, message: "请填写商品名称", trigger: "blur" }],
  category: [{ required: true, message: "请选择商品品类", trigger: "change" }],
  condition: [{ required: true, message: "请选择商品成色", trigger: "change" }],
  description: [{ required: true, message: "请描述商品使用情况", trigger: "blur" }],
  price: [{ required: true, message: "请填写期望价格", trigger: "blur" }, { validator: (_rule, value, callback) => Number(value) > 0 ? callback() : callback(new Error("价格必须大于 0")), trigger: "blur" }]
};

onMounted(async () => {
  try {
    const response = await apiListCategories();
    categories.value = response.data.data.items || [];
  } catch {
    ElMessage.error("商品品类加载失败");
  }
});

onBeforeUnmount(() => {
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value);
});

async function recognizeImage(event) {
  const image = event.target.files?.[0];
  event.target.value = "";
  if (!image) return;
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value);
  imagePreview.value = URL.createObjectURL(image);
  recognizing.value = true;
  try {
    const response = await apiRecognizeProduct(image);
    const result = response.data.data.recognition;
    form.name = result.name || form.name;
    form.brand = result.brand || form.brand;
    form.condition = result.condition || form.condition;
    form.category = categories.value.includes(result.category) ? result.category : form.category;
    ElMessage.success("已填入识别建议，请核对并修改");
  } catch (error) {
    ElMessage.error(error.message || "图片识别失败");
  } finally {
    recognizing.value = false;
  }
}

async function loadPriceReference() {
  if (!form.category || !form.condition) return;
  loadingPrice.value = true;
  try {
    const response = await apiGetPriceReference({ category: form.category, condition: form.condition });
    priceReference.value = response.data.data;
  } catch (error) {
    ElMessage.error(error.message || "价格参考获取失败");
  } finally {
    loadingPrice.value = false;
  }
}

async function submitForm() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }
  submitting.value = true;
  try {
    await apiPublishProduct({ ...form, price: Number(form.price) });
    ElMessage.success("商品已提交审核");
    router.push("/user-center");
  } catch (error) {
    ElMessage.error(error.message || "商品提交失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.publish-page { padding: 42px 0 32px; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 34px; }
.eyebrow, .section-kicker { margin: 0 0 9px; color: var(--primary-color); font-size: 12px; font-weight: 800; letter-spacing: 1.2px; }
.page-heading h1 { max-width: 700px; margin: 0; color: var(--text-primary); font-size: clamp(30px, 4vw, 42px); line-height: 1.18; letter-spacing: 0; }
.page-heading p:last-child { margin: 12px 0 0; color: var(--text-secondary); font-size: 16px; line-height: 1.6; }
.hero-progress { display: flex; align-items: center; gap: 8px; padding-bottom: 5px; color: var(--text-secondary); font-size: 13px; white-space: nowrap; }
.progress-dot { display: grid; width: 26px; height: 26px; place-items: center; border: 1px solid var(--border-color); border-radius: 50%; }
.progress-dot.active { color: #fff; border-color: var(--primary-color); background: var(--primary-color); }
.hero-progress i { width: 34px; height: 1px; margin: 0 4px; background: var(--border-color); }
.publish-layout { display: grid; grid-template-columns: minmax(0, 1fr) 285px; gap: 26px; align-items: start; }
.publish-form, .guide-panel { border: 1px solid var(--border-color); background: var(--bg-card); box-shadow: 0 10px 30px rgba(31, 41, 55, .05); }
.form-section { padding: 30px 32px; border-bottom: 1px solid var(--border-color); }
.section-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px; }
.section-heading h2 { margin: 3px 0 7px; color: var(--text-primary); font-size: 22px; letter-spacing: 0; }
.section-heading p { margin: 0; color: var(--text-secondary); font-size: 14px; line-height: 1.6; }
.section-heading > span { color: var(--text-secondary); font-size: 13px; white-space: nowrap; }
.ai-section { background: linear-gradient(135deg, color-mix(in srgb, var(--primary-color) 8%, var(--bg-card)), var(--bg-card) 70%); }
.ai-section .section-heading { align-items: flex-start; }
.ai-badge { padding: 6px 11px; color: var(--primary-color); border: 1px solid color-mix(in srgb, var(--primary-color) 28%, transparent); background: color-mix(in srgb, var(--primary-color) 8%, transparent); border-radius: 20px; font-size: 12px; font-weight: 700; }
.recognition-tools { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
.recognition-tools :deep(.el-button) { min-height: 42px; padding: 0 20px; font-size: 14px; }
.recognition-tools span { color: var(--text-secondary); font-size: 13px; }
.image-preview { display: block; max-width: 240px; max-height: 190px; object-fit: contain; margin: 0 0 18px; border-radius: 8px; }
.two-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.two-columns :deep(.el-select) { width: 100%; }
.form-section :deep(.el-form-item__label) { color: var(--text-primary); font-size: 14px; font-weight: 600; }
.form-section :deep(.el-input__inner), .form-section :deep(.el-textarea__inner) { font-size: 15px; }
.form-section :deep(.el-input__wrapper), .form-section :deep(.el-textarea__inner) { border-radius: 7px; }
.form-tip { margin: -4px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.6; }
.price-reference { margin: 0 0 24px; padding: 18px; border: 1px solid var(--border-color); background: var(--bg-secondary); border-radius: 9px; }
.price-reference > div { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.price-reference strong { color: var(--text-primary); font-size: 15px; }
.price-reference span, .price-reference p { color: var(--text-secondary); font-size: 13px; line-height: 1.6; }
.price-reference p { margin: 9px 0 14px; }
.price-reference :deep(.el-button) { min-height: 34px; font-size: 13px; }
.form-actions { display: flex; justify-content: flex-end; gap: 12px; padding: 22px 32px; }
.form-actions :deep(.el-button) { min-width: 100px; min-height: 40px; font-size: 14px; }
.guide-panel { position: sticky; top: 94px; padding: 24px; }
.guide-heading { display: flex; align-items: center; gap: 12px; padding-bottom: 19px; border-bottom: 1px solid var(--border-color); }
.guide-mark { display: grid; width: 35px; height: 35px; place-items: center; color: white; background: #39a878; border-radius: 50%; font-size: 18px; }
.guide-heading h2 { margin: 0 0 4px; font-size: 18px; }
.guide-heading p { margin: 0; color: var(--text-secondary); font-size: 13px; }
.guide-panel ul { display: grid; gap: 19px; margin: 22px 0; padding: 0; list-style: none; }
.guide-panel li { display: flex; flex-direction: column; gap: 4px; }
.guide-panel li strong, .review-note strong { color: var(--text-primary); font-size: 14px; }
.guide-panel li span { color: var(--text-secondary); font-size: 13px; line-height: 1.5; }
.review-note { padding: 16px; border-radius: 8px; background: var(--bg-secondary); }
.review-note p { margin: 8px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.7; }
@media (max-width: 850px) { .page-heading { align-items: flex-start; flex-direction: column; } .publish-layout { grid-template-columns: 1fr; } .guide-panel { position: static; } }
@media (max-width: 560px) { .publish-page { padding-top: 26px; } .page-heading h1 { font-size: 30px; } .form-section { padding: 24px 18px; } .section-heading h2 { font-size: 20px; } .two-columns { grid-template-columns: 1fr; gap: 0; } .recognition-tools { align-items: flex-start; flex-direction: column; } .form-actions { padding: 18px; } .form-actions :deep(.el-button) { flex: 1; } }
</style>
