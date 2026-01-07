<template>
  <el-card shadow="hover" style="width: 220px">
    <div style="display: flex; flex-direction: column; gap: 8px">
      <div
        style="
          height: 280px;
          background: #f2f2f2;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 6px;
          overflow: hidden;
        "
      >
        <img v-if="movie?.poster_url" :src="movie.poster_url" alt="poster" style="width: 100%; height: 100%; object-fit: cover" />
        <div v-else style="color: #999">无海报</div>
      </div>

      <div style="font-weight: 600; line-height: 1.2">{{ movie?.title || "-" }}</div>
      <div style="font-size: 12px; color: #666">年份：{{ movie?.release_year || "-" }}</div>
      <div v-if="movie?.rating_avg != null" style="font-size: 12px; color: #666">评分：{{ movie.rating_avg }}</div>

      <el-button type="primary" @click="$emit('open', movie)">查看详情</el-button>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  movie: {
    type: Object,
    default: null
  }
});

defineEmits(["open"]);
</script>


















