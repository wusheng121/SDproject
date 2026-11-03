<template>
  <div class="assistant-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">SHOPPING ASSISTANT</p>
        <h1>购物助手</h1>
        <p class="sub">聊天、识图、商品链接分析、对比、加购和卖家沟通，都在同一个对话里。</p>
      </div>
      <el-button @click="reset">新对话</el-button>
    </div>

    <div class="assistant-layout">
      <aside class="history">
        <div v-for="item in sessions" :key="item.id" :class="['history-item', { active: item.id === sessionId }]" @click="openSession(item.id)">
          <span>{{ item.preview || item.title || "未命名对话" }}</span>
          <small>{{ item.updated_at }}</small>
          <el-button link type="danger" size="small" @click.stop="removeSession(item)">删除</el-button>
        </div>
        <p v-if="!sessions.length" class="hint">还没有历史对话</p>
      </aside>

      <el-card class="chat-card" shadow="never">
        <div class="prompts">
          <span>可以这样问：</span>
          <el-button v-for="prompt in prompts" :key="prompt" size="small" @click="sendText(prompt)">{{ prompt }}</el-button>
        </div>

        <div class="messages">
          <div v-if="!messages.length" class="hint empty">
            说“1000元以内的手机”，或粘贴商品链接：http://127.0.0.1:5173/product/3
          </div>
          <div v-for="(item, index) in messages" :key="index" :class="['bubble-wrap', item.role]">
            <img v-if="item.image" :src="item.image" class="preview" alt="上传的图片" />
            <p class="bubble">{{ item.content }}</p>

            <div v-if="item.metadata" class="result">
              <div v-if="item.metadata.plan_steps?.length" class="box plan-box">
              <h4>执行计划</h4>
              <ol>
                <li v-for="(step, index) in item.metadata.plan_steps" :key="index">{{ step }}</li>
              </ol>
            </div>

            <div v-if="item.metadata.items?.length" class="product-lines">
                <button v-for="product in item.metadata.items" :key="product.id" class="product-line" type="button" @click="openProduct(product.id)">
                  {{ product.name }} · {{ product.condition }} · ¥{{ product.price }}
                </button>
              </div>

              <div v-if="item.metadata.products?.length" class="product-grid">
                <button v-for="product in item.metadata.products" :key="product.id" class="product-card" type="button" @click="openProduct(product.id)">
                  <strong>{{ product.name }}</strong>
                  <span>¥{{ product.price }} · {{ product.condition }}</span>
                </button>
              </div>

              <div v-if="item.metadata.advice" class="box">
                <h4>购买建议</h4>
                <p>{{ item.metadata.advice.summary }}</p>
                <div v-if="item.metadata.advice.pros?.length"><strong>优点</strong><ul><li v-for="text in item.metadata.advice.pros" :key="text">{{ text }}</li></ul></div>
                <div v-if="item.metadata.advice.risks?.length"><strong>风险</strong><ul><li v-for="text in item.metadata.advice.risks" :key="text">{{ text }}</li></ul></div>
                <div v-if="item.metadata.advice.missing?.length"><strong>还缺少的信息</strong><ul><li v-for="text in item.metadata.advice.missing" :key="text">{{ text }}</li></ul></div>
              </div>

              <div v-if="item.metadata.questions?.length" class="box">
                <h4>建议问卖家</h4>
                <ul><li v-for="text in item.metadata.questions" :key="text">{{ text }}</li></ul>
              </div>

              <div v-if="item.metadata.comparison" class="box">
                <h4>商品对比</h4>
                <el-table :data="item.metadata.comparison.items" size="small" stripe @row-click="openComparisonProduct">
                  <el-table-column prop="name" label="商品" min-width="170" />
                  <el-table-column prop="price" label="价格" width="90" />
                  <el-table-column prop="condition" label="成色" width="90" />
                  <el-table-column prop="condition_score" label="成色分" width="80" />
                  <el-table-column prop="value_score" label="性价比" width="90" />
                  <el-table-column prop="defect_description" label="瑕疵" min-width="150" />
                </el-table>
                <p class="recommendation">{{ item.metadata.comparison.recommendation }}</p>
              </div>

              <div v-if="item.metadata.action_proposals?.length" class="box">
                <h4>待确认操作</h4>
                <el-card v-for="action in item.metadata.action_proposals" :key="action.action_id" shadow="never" class="action-card">
                  <div v-if="action.type === 'cart_add'">
                    <strong>加入购物车</strong>
                    <p>商品 ID：{{ action.payload.product_id }}</p>
                    <el-button size="small" type="primary" @click="confirmAction(action)">确认加入</el-button>
                    <el-button size="small" @click="cancelAction(action)">取消</el-button>
                  </div>
                  <div v-else-if="action.type === 'seller_message'">
                    <strong>给卖家发消息</strong>
                    <el-input v-model="action.draft" type="textarea" :rows="4" maxlength="500" show-word-limit />
                    <el-button size="small" type="primary" @click="confirmAction(action)">确认发送</el-button>
                    <el-button size="small" @click="cancelAction(action)">取消</el-button>
                  </div>
                  <el-tag v-if="action.status" size="small" class="action-status">{{ action.status }}</el-tag>
                </el-card>
              </div>
            </div>
          </div>
        </div>

        <div class="composer">
          <el-input v-model="draft" placeholder="说需求，或粘贴商品链接" @keyup.enter="sendText(draft)" />
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
          <el-button @click="fileInput?.click()">识图</el-button>
          <el-button type="primary" :loading="sending" @click="sendText(draft)">发送</el-button>
        </div>
        <p v-if="filename" class="file-name">已选择图片：{{ filename }}</p>
        <img v-if="imageDataUrl" :src="imageDataUrl" class="preview" alt="待发送图片" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  apiAssistantSessionMessages,
  apiAssistantSessions,
  apiCancelAgentAction,
  apiConfirmAgentAction,
  apiDeleteAssistantSession,
  apiUnifiedAssistantMessage
} from "../api/assistant";

const router = useRouter();
const route = useRoute();
const prompts = ["1000元以内的平板", "看看这个链接值不值得买：http://127.0.0.1:5173/product/3", "找手机，对比前三款性价比", "帮我问卖家电池健康"];
const messages = ref([]);
const sessions = ref([]);
const draft = ref("");
const sessionId = ref("");
const filename = ref("");
const imageDataUrl = ref("");
const sending = ref(false);
const fileInput = ref(null);

function normalizeActions(data, actions) {
  const list = Array.isArray(actions) ? actions : (data?.action_proposals || []);
  list.forEach((action) => {
    if (action.type === "seller_message" && !action.draft) action.draft = action.payload?.content || "";
    if (!action.status) action.status = "";
  });
  data.action_proposals = list;
  return data;
}

function showMessages(items) {
  messages.value = (items || []).map((item) => {
    const metadata = item.metadata || {};
    normalizeActions(metadata, item.actions);
    return { role: item.role, content: item.content, metadata };
  });
}

async function loadSessions() {
  const response = await apiAssistantSessions();
  sessions.value = response.data.data || [];
}

async function loadSession(id) {
  const response = await apiAssistantSessionMessages(id);
  sessionId.value = id;
  showMessages(response.data.data);
}

async function openSession(id) {
  await loadSession(id);
}

async function removeSession(item) {
  await ElMessageBox.confirm(`确认删除「${item.preview || item.title || "这段对话"}」？删除后不再显示。`, "删除会话", { type: "warning" });
  await apiDeleteAssistantSession(item.id);
  if (sessionId.value === item.id) reset();
  await loadSessions();
  if (!sessionId.value && sessions.value.length) await openSession(sessions.value[0].id);
  ElMessage.success("会话已删除");
}

function reset() {
  messages.value = [];
  sessionId.value = "";
  draft.value = "";
  filename.value = "";
  imageDataUrl.value = "";
  if (fileInput.value) fileInput.value.value = "";
}

function onFile(event) {
  const file = event.target.files?.[0];
  filename.value = "";
  imageDataUrl.value = "";
  if (!file) return;
  if (file.size > 4 * 1024 * 1024) {
    ElMessage.error("图片不能超过 4MB");
    event.target.value = "";
    return;
  }
  filename.value = file.name;
  const reader = new FileReader();
  reader.onload = () => {
    imageDataUrl.value = String(reader.result || "");
  };
  reader.readAsDataURL(file);
}

async function sendText(text) {
  const message = (text || "").trim();
  if ((!message && !imageDataUrl.value) || sending.value) return;
  messages.value.push({
    role: "user",
    content: message || `上传图片 ${filename.value}`,
    image: imageDataUrl.value
  });
  draft.value = "";
  sending.value = true;
  try {
    const response = await apiUnifiedAssistantMessage({
      message,
      sessionId: sessionId.value,
      filename: filename.value,
      imageDataUrl: imageDataUrl.value
    });
    const data = normalizeActions(response.data.data);
    sessionId.value = data.session_id;
    messages.value.push({ role: "assistant", content: data.reply, metadata: data });
    filename.value = "";
    imageDataUrl.value = "";
    if (fileInput.value) fileInput.value.value = "";
    await loadSessions();
  } catch (error) {
    messages.value.push({ role: "assistant", content: error.message || "助手处理失败" });
  } finally {
    sending.value = false;
  }
}

async function confirmAction(action) {
  try {
    const content = action.type === "seller_message" ? action.draft : "";
    await apiConfirmAgentAction(action.action_id, content);
    action.status = "已执行";
    ElMessage.success("操作已执行");
  } catch (error) {
    ElMessage.error(error.message || "执行失败");
  }
}

async function cancelAction(action) {
  await apiCancelAgentAction(action.action_id);
  action.status = "已取消";
}

function openProduct(id) {
  router.push(`/product/${id}`);
}

function openComparisonProduct(row) {
  if (row?.product_id) openProduct(row.product_id);
}

onMounted(async () => {
  await loadSessions();
  const link = String(route.query.link || "");
  if (link) {
    draft.value = `看看这个链接值不值得买：${link}`;
  }
  if (!link && sessions.value.length) {
    await openSession(sessions.value[0].id);
  }
});
</script>

<style scoped>
.assistant-page { max-width: 1100px; margin: 0 auto; padding: 28px 20px 40px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.eyebrow { margin: 0 0 6px; color: var(--primary-color); font-size: 12px; font-weight: 800; letter-spacing: 1px; }
h1 { margin: 0; font-size: 30px; }
.sub, .hint, .file-name { color: var(--text-secondary); font-size: 14px; }
.sub { margin: 8px 0 0; line-height: 1.6; }
.assistant-layout { display: grid; grid-template-columns: 220px 1fr; gap: 16px; align-items: start; }
.history { display: flex; flex-direction: column; gap: 8px; max-height: 680px; overflow-y: auto; }
.history-item { display: flex; flex-direction: column; gap: 4px; padding: 10px; text-align: left; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-card); cursor: pointer; }
.history-item.active { border-color: var(--primary-color); }
.history-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-item small { color: var(--text-secondary); font-size: 11px; }
.chat-card { min-height: 560px; }
.prompts { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 12px; color: var(--text-secondary); font-size: 13px; }
.messages { display: flex; flex-direction: column; gap: 14px; min-height: 360px; max-height: 62vh; overflow-y: auto; padding: 6px 2px; }
.empty { text-align: center; padding: 90px 20px; }
.bubble-wrap { display: flex; flex-direction: column; gap: 8px; }
.bubble-wrap.user { align-items: flex-end; }
.bubble { max-width: 86%; margin: 0; padding: 10px 14px; border-radius: 12px; line-height: 1.65; white-space: pre-wrap; }
.bubble-wrap.user .bubble { color: #fff; background: var(--primary-color); }
.bubble-wrap.assistant .bubble { background: var(--bg-hover); }
.result { display: flex; flex-direction: column; gap: 10px; width: 100%; }
.product-lines { display: flex; flex-direction: column; gap: 6px; }
.product-line { text-align: left; border: 0; padding: 8px 10px; border-radius: 8px; background: var(--bg-hover); cursor: pointer; }
.product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
.product-card { display: flex; flex-direction: column; gap: 6px; padding: 12px; text-align: left; border: 1px solid var(--border-color); border-radius: 10px; background: var(--bg-card); cursor: pointer; }
.product-card span { color: var(--text-secondary); font-size: 13px; }
.box { padding: 14px; border: 1px solid var(--border-color); border-radius: 10px; background: var(--bg-card); }
.box h4 { margin: 0 0 8px; }
.box p { margin: 6px 0; line-height: 1.6; }
.box ul { margin: 6px 0 10px; padding-left: 20px; line-height: 1.6; }
.recommendation { color: var(--text-secondary); }
.action-card { margin-top: 8px; }
.action-card p { color: var(--text-secondary); font-size: 13px; }
.action-status { margin-top: 8px; }
.composer { display: flex; gap: 10px; margin-top: 16px; }
.preview { max-width: 220px; max-height: 160px; margin-top: 10px; border-radius: 8px; object-fit: cover; }
@media (max-width: 760px) {
  .assistant-layout { grid-template-columns: 1fr; }
  .history { max-height: 150px; }
}
</style>
