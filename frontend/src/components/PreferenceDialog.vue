<template>
  <el-dialog
    v-model="visible"
    title="选择您的电影兴趣标签"
    width="600px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="true"
  >
    <div style="margin-bottom: 12px; color: #606266">
      选择您感兴趣的电影类型，系统将为您推荐相关内容（可多选）
      <span v-if="selectedGenres.length > 0" style="color: #409eff; font-weight: bold">
        - 已选择 {{ selectedGenres.length }} 个
      </span>
      <span v-else style="color: #f56c6c; font-weight: bold">
        - 请至少选择 1 个类型
      </span>
    </div>
    <div style="margin-bottom: 12px">
      <el-button size="small" @click="handleSelectAll" :disabled="selectedGenres.length === allGenres.length">
        全选
      </el-button>
      <el-button size="small" @click="handleClearAll" :disabled="selectedGenres.length === 0">
        清空
      </el-button>
    </div>
    <el-checkbox-group v-model="selectedGenres">
      <el-row :gutter="12">
        <el-col v-for="g in allGenres" :key="g" :span="6" style="margin-bottom: 12px">
          <el-checkbox :label="g">{{ g }}</el-checkbox>
        </el-col>
      </el-row>
    </el-checkbox-group>

    <template #footer>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <el-button text @click="handleSkip">跳过（推荐热门）</el-button>
        <div>
          <el-button @click="visible = false">取消</el-button>
          <el-button 
            type="primary" 
            @click="handleSave" 
            :disabled="selectedGenres.length === 0"
          >
            确定（{{ selectedGenres.length || '未选择' }}）
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { apiListGenres } from "../api/movies";
import { apiSavePreferences } from "../api/user";

const props = defineProps({
  modelValue: Boolean,
});

const emit = defineEmits(["update:modelValue", "saved"]);

const visible = ref(false);
const allGenres = ref([]);
const selectedGenres = ref([]);

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val) {
      loadGenres();
    }
  }
);

watch(visible, (val) => {
  if (!val) {
    emit("update:modelValue", false);
  }
});

async function loadGenres() {
  const resp = await apiListGenres();
  // 后端返回的是 { items: [...] }
  allGenres.value = resp?.data?.items || [];
  console.log('加载的电影类型:', allGenres.value);
}

async function handleSave() {
  if (selectedGenres.value.length === 0) {
    ElMessage.warning("请至少选择一个类型");
    return;
  }
  await apiSavePreferences(selectedGenres.value);
  ElMessage.success("兴趣标签已保存");
  visible.value = false;
  emit("saved", selectedGenres.value);
}

function handleSkip() {
  // 跳过 = 保存空列表（用户明确不选）
  apiSavePreferences([]);
  ElMessage.info("已跳过兴趣选择，将为您推荐全局热门内容");
  visible.value = false;
  emit("saved", []);
}

function handleSelectAll() {
  selectedGenres.value = [...allGenres.value];
}

function handleClearAll() {
  selectedGenres.value = [];
}
</script>









