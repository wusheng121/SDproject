<template>
  <div>
    <h2 style="margin: 0 0 12px">个人收藏夹 / 列表页</h2>

    <el-alert
      title="说明：当前页面先做演示用的本地列表（你后续可对接后端 Favorite 表，做真实的收藏列表接口）"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />

    <el-card>
      <el-empty v-if="items.length === 0" description="暂无收藏（先去电影详情页点收藏试试）" />
      <el-table v-else :data="items" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="release_year" label="年份" width="120" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="remove(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";

// 演示：本地假数据（你后续改成从后端拉取）
const items = ref([
  { id: 1, title: "Interstellar", release_year: 2014 },
  { id: 2, title: "Inception", release_year: 2010 }
]);

function remove(id) {
  items.value = items.value.filter((x) => x.id !== id);
}
</script>



