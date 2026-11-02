<template>
  <div class="messages-page">
    <aside class="conversation-list">
      <h1>消息</h1>
      <p>和卖家或买家的对话会留在这里。</p>
      <button
        v-for="item in conversations"
        :key="item.id"
        type="button"
        :class="{ active: current && current.id === item.id }"
        @click="selectConversation(item)"
      >
        <strong>{{ item.peer_name }}</strong>
        <small>{{ item.product_name }}</small>
        <span>{{ item.last_message || "还没有消息" }}</span>
      </button>
      <p v-if="!conversations.length" class="empty">还没有对话。在商品页点「联系卖家」即可开始。</p>
    </aside>
    <section v-if="current" class="thread">
      <header>
        <div>
          <strong>{{ current.peer_name }}</strong>
          <button type="button" @click="router.push(`/product/${current.product_id}`)">{{ current.product_name }}</button>
        </div>
      </header>
      <div ref="scroller" class="bubbles">
        <div v-if="!thread.length" class="empty">发一句话，对方登录后就能看到。</div>
        <div v-for="item in thread" :key="item.id" :class="['bubble', item.sender_id === myId ? 'mine' : 'theirs']">
          <p>{{ item.content }}</p>
          <small>{{ item.created_at }}</small>
        </div>
      </div>
      <form @submit.prevent="send">
        <el-input v-model="draft" maxlength="500" placeholder="输入消息，回车发送" @keyup.enter="send" />
        <el-button type="primary" :loading="sending" native-type="submit">发送</el-button>
      </form>
    </section>
    <section v-else class="thread empty-thread">
      <p>选择左边的对话，或从商品详情进入。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useUserStore } from "../stores/user";
import { apiConversationMessages, apiListConversations, apiOpenConversation, apiSendMessage } from "../api/messages";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const conversations = ref([]);
const current = ref(null);
const thread = ref([]);
const draft = ref("");
const sending = ref(false);
const scroller = ref(null);
const myId = computed(() => userStore.profile?.id);
let timer = 0;

onMounted(async () => {
  await loadConversations();
  const productId = Number(route.query.product);
  if (productId) {
    try {
      const response = await apiOpenConversation(productId);
      current.value = response.data.data;
      await loadConversations();
      await loadThread();
    } catch (error) {
      ElMessage.warning(error.message || "暂时不能联系卖家");
    }
  }
  timer = window.setInterval(refresh, 4000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});

async function loadConversations() {
  const response = await apiListConversations();
  conversations.value = response.data.data || [];
}

async function selectConversation(item) {
  current.value = item;
  await loadThread();
}

async function loadThread() {
  if (!current.value) return;
  const response = await apiConversationMessages(current.value.id);
  thread.value = response.data.data || [];
  await nextTick();
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight;
}

async function refresh() {
  try {
    await loadConversations();
    if (current.value) {
      const latest = conversations.value.find((item) => item.id === current.value.id);
      if (latest) current.value = latest;
      await loadThread();
    }
  } catch {
    // 下一轮再拉，避免轮询把页面打断。
  }
}

async function send() {
  const content = draft.value.trim();
  if (!current.value || !content || sending.value) return;
  sending.value = true;
  try {
    await apiSendMessage(current.value.id, content);
    draft.value = "";
    await loadThread();
    await loadConversations();
  } catch (error) {
    ElMessage.error(error.message || "发送失败");
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.messages-page { display: grid; grid-template-columns: 280px minmax(0, 1fr); min-height: 640px; margin: 28px 0; border: 1px solid var(--border-color); background: var(--bg-card); }
.conversation-list { padding: 22px 16px; border-right: 1px solid var(--border-color); background: var(--bg-secondary); }
.conversation-list h1 { margin: 0 0 6px; font-size: 24px; }
.conversation-list > p { margin: 0 0 16px; color: var(--text-secondary); font-size: 13px; }
.conversation-list button { display: grid; width: 100%; gap: 3px; margin-bottom: 8px; padding: 12px; text-align: left; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-card); cursor: pointer; }
.conversation-list button.active { border-color: var(--primary-color); }
.conversation-list strong { color: var(--text-primary); }
.conversation-list small, .conversation-list span, .empty { color: var(--text-secondary); font-size: 13px; }
.conversation-list span { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.thread { display: flex; min-width: 0; flex-direction: column; }
.thread header { padding: 16px 20px; border-bottom: 1px solid var(--border-color); }
.thread header strong { display: block; }
.thread header button { padding: 0; border: 0; color: var(--primary-color); background: transparent; cursor: pointer; }
.bubbles { flex: 1; overflow-y: auto; padding: 18px 20px; }
.bubble { max-width: 70%; margin-bottom: 12px; padding: 10px 12px; border-radius: 10px; }
.bubble p { margin: 0; white-space: pre-wrap; }
.bubble small { display: block; margin-top: 4px; color: var(--text-secondary); font-size: 12px; }
.bubble.mine { margin-left: auto; background: color-mix(in srgb, var(--primary-color) 16%, var(--bg-card)); }
.bubble.theirs { background: var(--bg-secondary); }
.thread form { display: flex; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--border-color); }
.empty-thread { display: grid; place-items: center; color: var(--text-secondary); }
@media (max-width: 760px) { .messages-page { grid-template-columns: 1fr; } .conversation-list { border-right: 0; border-bottom: 1px solid var(--border-color); } }
</style>
