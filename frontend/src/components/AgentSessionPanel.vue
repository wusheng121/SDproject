<template>
  <div class="agent-session-panel">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="会话标题 / 用户 / Agent" clearable style="width: 260px" @keyup.enter="load(1)" />
      <el-button type="primary" @click="load(1)">查询</el-button>
    </div>

    <el-table :data="rows" stripe v-loading="loading" @row-click="open">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="agent_code" label="Agent" width="120" />
      <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="message_count" label="消息数" width="80" />
      <el-table-column prop="last_message" label="最后消息" min-width="220" show-overflow-tooltip />
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button size="small" @click.stop="open(row)">查看</el-button>
          <el-button size="small" type="danger" plain @click.stop="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="pager" background layout="total, prev, pager, next" :total="total" :page-size="pageSize" :current-page="page" @current-change="load" />

    <el-dialog v-model="visible" title="Agent 会话详情" width="900px">
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="会话 ID">{{ detail.session.id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ detail.session.username }}</el-descriptions-item>
          <el-descriptions-item label="Agent">{{ detail.session.agent_code }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ detail.session.title }}</el-descriptions-item>
          <el-descriptions-item label="上下文" :span="2">{{ detail.session.context_json || '-' }}</el-descriptions-item>
        </el-descriptions>

        <h4>消息</h4>
        <div class="message-thread">
          <div v-for="message in detail.messages || []" :key="message.id" :class="['message-row', message.role]">
            <strong>{{ message.role === 'user' ? '用户' : 'Agent' }}</strong>
            <p>{{ message.content || '-' }}</p>
            <small>{{ message.created_at }}</small>
          </div>
        </div>

        <template v-if="detail.actions?.length">
          <h4>动作</h4>
          <el-table :data="detail.actions" size="small" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="action_type" label="类型" width="130" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="payload_json" label="参数" min-width="260" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { apiDeleteAgentSession, apiGetAgentSession, apiGetAgentSessions } from "../api/admin";

const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const keyword = ref("");
const loading = ref(false);
const visible = ref(false);
const detail = ref(null);

async function load(nextPage = 1) {
  page.value = nextPage;
  loading.value = true;
  try {
    const response = await apiGetAgentSessions({ keyword: keyword.value || undefined, page: page.value, page_size: pageSize });
    rows.value = response.data.data || [];
    total.value = response.data.pagination?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function open(row) {
  try {
    const response = await apiGetAgentSession(row.id);
    detail.value = response.data.data;
    visible.value = true;
  } catch (error) {
    ElMessage.error(error.message || "加载会话失败");
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除会话「${row.title || row.id}」？删除后不再显示。`, "删除 Agent 会话", { type: "warning" });
  await apiDeleteAgentSession(row.id);
  ElMessage.success("会话已删除");
  await load(page.value);
}

onMounted(() => load(1));
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.message-thread {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.message-row {
  padding: 10px;
  border-radius: 8px;
  background: var(--bg-hover);
}
.message-row.user {
  background: rgba(88, 101, 242, 0.10);
}
.message-row p {
  margin: 6px 0;
  white-space: pre-wrap;
  line-height: 1.6;
}
.message-row small {
  color: var(--text-secondary);
}
h4 {
  margin: 16px 0 8px;
}
</style>
