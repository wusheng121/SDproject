<template>
  <div class="rate-page">
    <h2 class="page-title">评分反馈</h2>

    <el-card class="rate-card">
      <el-form :model="form" label-width="110px" @submit.prevent>
        <el-form-item label="电影ID" class="form-item">
          <el-input v-model="form.movie_id" placeholder="例如：1" />
        </el-form-item>
        <el-form-item label="评分(1-5)" class="form-item">
          <el-rate v-model="form.score" />
        </el-form-item>
        <el-form-item label="评论(可选)" class="form-item">
          <el-input v-model="form.comment" type="textarea" :rows="4" placeholder="写点观后感..." />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submit">提交评分</el-button>
        </el-form-item>
      </el-form>

      <el-divider />
      <div class="result-label">最近一次提交结果：</div>
      <pre class="result-content">{{ lastResult }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { apiRateMovie } from "../api/actions";

const loading = ref(false);
const lastResult = ref(null);

const form = reactive({
  movie_id: "",
  score: 0,
  comment: ""
});

async function submit() {
  loading.value = true;
  try {
    const resp = await apiRateMovie({
      movie_id: form.movie_id,
      score: form.score,
      comment: form.comment
    });
    lastResult.value = resp;
    if (resp?.code === 0) ElMessage.success("评分已提交");
    else ElMessage.error(resp?.message || "提交失败");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.rate-page {
  animation: fadeIn 0.6s ease;
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

.page-title {
  margin: 0 0 24px 0;
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
}

.rate-card {
  max-width: 680px;
  background: var(--bg-card);
  border: none;
  box-shadow: var(--shadow-soft);
}

.form-item {
  color: var(--text-primary);
}

:deep(.el-form-item__label) {
  color: var(--text-primary);
  font-weight: 600;
}

:deep(.el-input__inner) {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border-color);
}

:deep(.el-textarea__inner) {
  background: var(--bg-card);
  color: var(--text-primary);
  border-color: var(--border-color);
}

.result-label {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.result-content {
  background: var(--bg-hover);
  color: var(--text-primary);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

@media (max-width: 768px) {
  .page-title {
    font-size: 24px;
  }
}
</style>
