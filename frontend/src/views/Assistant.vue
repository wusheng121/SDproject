<template>
  <div class="assistant-page">
    <div class="page-header">
      <h2 class="page-title">购物助手</h2>
      <p class="page-subtitle">配了 DeepSeek 密钥后，由模型组织回答；商品仍从数据库查出。它不能删除、改价或支付。</p>
    </div>

    <el-card class="chat-card">
      <div class="prompts">
        <span>可以依次点这几句：</span>
        <el-button v-for="prompt in prompts" :key="prompt" size="small" @click="sendText(prompt)">
          {{ prompt }}
        </el-button>
      </div>

      <div class="messages">
        <div v-if="messages.length === 0" class="hint">先说「平板」，再说「只要九成新」，然后说「便宜一点」。</div>
        <div v-for="(item, index) in messages" :key="index" :class="['bubble', item.role]">
          <p v-if="item.engine" class="engine">{{ item.engine === "deepseek" ? "DeepSeek" : "规则查询" }}</p>
          <p class="reply-text">{{ item.content }}</p>
          <button
            v-for="product in item.items || []"
            :key="product.id"
            class="product-line"
            type="button"
            @click="openProduct(product)"
          >
            {{ product.name }} · {{ product.condition }} · ¥{{ product.price }}
          </button>
        </div>
      </div>

      <div class="composer">
        <el-input
          v-model="draft"
          placeholder="例如：1000元以内的平板"
          @keyup.enter="sendText(draft)"
        />
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
        <el-button @click="fileInput.click()">上传图片</el-button>
        <el-button type="primary" :loading="sending" @click="sendText(draft)">发送</el-button>
      </div>
      <p v-if="filename" class="file-name">将按文件名识物：{{ filename }}</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import { apiAssistantChat } from "../api/assistant";

const router = useRouter();
const prompts = ["平板", "只要九成新", "便宜一点", "有什么推荐", "帮我删掉这个商品"];
const messages = ref([]);
const draft = ref("");
const sessionId = ref("");
const filename = ref("");
const sending = ref(false);
const fileInput = ref(null);

function openProduct(product) {
  router.push(`/product/${product.id}`);
}

function onFile(event) {
  const file = event.target.files?.[0];
  filename.value = file ? file.name : "";
}

async function sendText(text) {
  const message = (text || "").trim();
  if (!message && !filename.value) return;
  sending.value = true;
  messages.value.push({ role: "user", content: message || `上传图片 ${filename.value}` });
  try {
    const response = await apiAssistantChat({
      message,
      sessionId: sessionId.value,
      filename: filename.value
    });
    const data = response.data.data;
    sessionId.value = data.session_id;
    messages.value.push({
      role: "assistant",
      content: data.reply,
      engine: data.engine,
      items: data.items || []
    });
    draft.value = "";
    filename.value = "";
    if (fileInput.value) fileInput.value.value = "";
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.assistant-page {
  padding: 24px;
  max-width: 980px;
  margin: 0 auto;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.page-subtitle,
.hint,
.file-name {
  color: var(--text-secondary);
  font-size: 14px;
}

.chat-card {
  margin-top: 16px;
}

.prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 240px;
  margin-bottom: 16px;
}

.bubble {
  max-width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
}

.engine {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.reply-text {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.7;
}

.product-line {
  display: block;
  width: 100%;
  margin-top: 8px;
  padding: 8px 10px;
  text-align: left;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
}

.bubble.user {
  align-self: flex-end;
  background: rgba(88, 101, 242, 0.16);
  color: var(--text-primary);
}

.bubble.assistant {
  align-self: flex-start;
  background: var(--bg-hover);
  color: var(--text-primary);
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.composer {
  display: flex;
  gap: 8px;
}
</style>
