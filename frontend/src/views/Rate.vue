<template>
  <div>
    <h2 style="margin: 0 0 12px">评分 / 反馈页</h2>

    <el-card style="max-width: 680px">
      <el-form :model="form" label-width="110px" @submit.prevent>
        <el-form-item label="电影ID">
          <el-input v-model="form.movie_id" placeholder="例如：1" />
        </el-form-item>
        <el-form-item label="评分(1-5)">
          <el-rate v-model="form.score" />
        </el-form-item>
        <el-form-item label="评论(可选)">
          <el-input v-model="form.comment" type="textarea" :rows="4" placeholder="写点观后感..." />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submit">提交评分</el-button>
        </el-form-item>
      </el-form>

      <el-divider />
      <div style="color: #666; font-size: 13px">最近一次提交结果：</div>
      <pre style="background: #fafafa; padding: 12px; border-radius: 6px">{{ lastResult }}</pre>
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
    if (resp?.code === 0) ElMessage.success("评分已提交（mock）");
    else ElMessage.error(resp?.message || "提交失败");
  } finally {
    loading.value = false;
  }
}
</script>


















