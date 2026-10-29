<template>
  <el-dialog
    v-model="visible"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    width="700px"
    class="preference-dialog"
  >
    <template #header>
      <div class="dialog-header">
        <div class="header-icon">🎯</div>
        <div class="header-content">
          <h2 class="header-title">选择你感兴趣的品类</h2>
          <p class="header-subtitle">告诉我们你想买什么，我们为你推荐好物</p>
        </div>
      </div>
    </template>

    <div class="dialog-body">
      <!-- 选择状态提示 -->
      <div class="selection-status">
        <div class="status-info">
          <span class="status-icon">✨</span>
          <span v-if="selectedCategories.length > 0" class="status-text selected">
            已选择 <strong>{{ selectedCategories.length }}</strong> 个品类
      </span>
          <span v-else class="status-text unselected">
            请至少选择 <strong>1</strong> 个你感兴趣的品类
      </span>
    </div>
        <div class="quick-actions">
          <button 
            class="quick-btn" 
            @click="handleSelectAll" 
            :disabled="selectedCategories.length === allCategories.length"
          >
        全选
          </button>
          <button 
            class="quick-btn" 
            @click="handleClearAll" 
            :disabled="selectedCategories.length === 0"
          >
        清空
          </button>
        </div>
      </div>

      <!-- 品类选择网格 -->
      <div class="categories-grid">
        <label 
          v-for="category in allCategories" 
          :key="category"
          :class="['category-item', { selected: selectedCategories.includes(category) }]"
        >
          <input 
            type="checkbox" 
            :value="category" 
            v-model="selectedCategories"
            class="category-checkbox"
          />
          <span class="category-icon">{{ getCategoryIcon(category) }}</span>
          <span class="category-name">{{ category }}</span>
          <span class="check-mark">✓</span>
        </label>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <button class="footer-btn skip-btn" @click="handleSkip">
          <span class="btn-icon">⏭️</span>
          <span>跳过（推荐热门）</span>
        </button>
        <div class="footer-actions">
          <button class="footer-btn cancel-btn" @click="visible = false">
            取消
          </button>
          <button 
            class="footer-btn save-btn" 
            @click="handleSave" 
            :disabled="selectedCategories.length === 0"
          >
            <span class="btn-icon">🎉</span>
            <span>确定{{ selectedCategories.length > 0 ? `（${selectedCategories.length}）` : '' }}</span>
          </button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { apiListCategories } from "../api/products";
import { apiSavePreferences } from "../api/user";

const props = defineProps({
  modelValue: Boolean,
});

const emit = defineEmits(["update:modelValue", "saved"]);

const visible = ref(false);
const allCategories = ref([]);
const selectedCategories = ref([]);

// 品类图标映射
const categoryIcons = {
  '保温杯': '☕',
  '运动鞋': '👟',
  '手机': '📱',
  '耳机': '🎧',
  'T恤': '👕',
  '鼠标': '🖱️',
  '键盘': '⌨️',
  '台灯': '💡',
  '书籍': '📚',
  '自行车': '🚲',
};

function getCategoryIcon(category) {
  return categoryIcons[category] || '📦';
}

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val) {
      loadCategories();
    }
  }
);

watch(visible, (val) => {
  if (!val) {
    emit("update:modelValue", false);
  }
});

async function loadCategories() {
  try {
    const res = await apiListCategories();
    if (res.data.code === 0) {
      allCategories.value = res.data.data.items || [];
    }
  } catch (error) {
    console.error("加载品类失败:", error);
  }
}

async function handleSave() {
  if (selectedCategories.value.length === 0) {
    ElMessage.warning("请至少选择一个品类");
    return;
  }
  await apiSavePreferences(selectedCategories.value);
  ElMessage.success("🎉 兴趣标签已保存");
  visible.value = false;
  emit("saved", selectedCategories.value);
}

function handleSkip() {
  apiSavePreferences([]);
  ElMessage.info("已跳过兴趣选择，将为您推荐全局热门商品");
  visible.value = false;
  emit("saved", []);
}

function handleSelectAll() {
  selectedCategories.value = [...allCategories.value];
}

function handleClearAll() {
  selectedCategories.value = [];
}
</script>

<style scoped>
/* 对话框样式覆盖 */
:deep(.el-dialog) {
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

:deep(.el-dialog__header) {
  padding: 0;
  margin: 0;
  background: transparent;
}

:deep(.el-dialog__body) {
  padding: 0 32px 24px;
}

:deep(.el-dialog__footer) {
  padding: 0 32px 32px;
}

:deep(.el-dialog__headerbtn) {
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  transition: all 0.3s ease;
}

:deep(.el-dialog__headerbtn:hover) {
  background: white;
  transform: rotate(90deg);
}

:deep(.el-dialog__close) {
  color: var(--primary-color);
  font-size: 20px;
  font-weight: bold;
}

/* 对话框头部 */
.dialog-header {
  background: var(--primary-gradient);
  padding: 40px 32px;
  display: flex;
  align-items: center;
  gap: 20px;
  position: relative;
  overflow: hidden;
}

.dialog-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
}

.header-icon {
  font-size: 60px;
  line-height: 1;
  animation: bounce 2s ease-in-out infinite;
  position: relative;
  z-index: 2;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.header-content {
  flex: 1;
  position: relative;
  z-index: 2;
}

.header-title {
  font-size: 28px;
  font-weight: 800;
  color: white;
  margin: 0 0 8px 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.header-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
  font-weight: 500;
}

/* 对话框主体 */
.dialog-body {
  padding-top: 32px;
}

/* 选择状态 */
.selection-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-hover);
  border-radius: 16px;
  margin-bottom: 24px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-icon {
  font-size: 24px;
}

.status-text {
  font-size: 15px;
  font-weight: 500;
}

.status-text.selected {
  color: var(--primary-color);
}

.status-text.unselected {
  color: var(--text-secondary);
}

.status-text strong {
  font-weight: 800;
  font-size: 18px;
}

.quick-actions {
  display: flex;
  gap: 8px;
}

.quick-btn {
  padding: 8px 16px;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-color);
  cursor: pointer;
  transition: all 0.3s ease;
}

.quick-btn:hover:not(:disabled) {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.quick-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 品类网格 */
.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.category-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 12px;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.category-item:hover {
  border-color: var(--primary-color);
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(88, 101, 242, 0.2);
}

.category-item.selected {
  background: var(--primary-gradient);
  border-color: var(--primary-color);
  box-shadow: 0 8px 20px rgba(88, 101, 242, 0.3);
}

.category-checkbox {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.category-icon {
  font-size: 36px;
  margin-bottom: 8px;
  transition: transform 0.3s ease;
}

.category-item:hover .category-icon {
  transform: scale(1.2);
}

.category-item.selected .category-icon {
  transform: scale(1.1);
}

.category-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: center;
  transition: color 0.3s ease;
}

.category-item.selected .category-name {
  color: white;
}

.check-mark {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: var(--primary-color);
  opacity: 0;
  transform: scale(0);
  transition: all 0.3s ease;
}

.category-item.selected .check-mark {
  opacity: 1;
  transform: scale(1);
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.footer-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-icon {
  font-size: 18px;
}

.skip-btn {
  background: transparent;
  color: var(--text-secondary);
  border: 2px solid var(--border-color);
}

.skip-btn:hover {
  background: var(--bg-hover);
  border-color: var(--text-secondary);
}

.cancel-btn {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 2px solid var(--border-color);
}

.cancel-btn:hover {
  background: var(--bg-hover);
  border-color: var(--text-secondary);
}

.save-btn {
  background: var(--primary-gradient);
  color: white;
  box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4);
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(88, 101, 242, 0.5);
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .categories-grid {
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
    gap: 10px;
  }

  .category-item {
    padding: 16px 8px;
  }

  .category-icon {
    font-size: 30px;
  }

  .category-name {
    font-size: 12px;
  }

  .dialog-footer {
    flex-direction: column;
  }

  .footer-actions {
    width: 100%;
  }

  .footer-btn {
    flex: 1;
  }

  .skip-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>









