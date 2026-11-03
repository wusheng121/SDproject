<template>
  <div class="agent-key-panel">
    <el-alert
      title="API Key 只用于 Agent 服务账号，不用于普通用户登录。完整 Key 只在创建时显示一次。"
      type="info"
      :closable="false"
      show-icon
      class="notice"
    />

    <div class="toolbar">
      <el-select v-model="selectedUserId" placeholder="选择 Agent 服务账号" style="width: 260px" @change="loadKeys">
        <el-option v-for="user in agentUsers" :key="user.id" :label="`${user.username} (${user.email})`" :value="user.id" />
      </el-select>
      <el-button type="primary" :disabled="!selectedUserId" @click="openCreate">创建 API Key</el-button>
    </div>

    <el-table :data="keys" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="prefix" label="Key 前缀" min-width="160" />
      <el-table-column label="Scopes" min-width="220">
        <template #default="{ row }">
          <el-tag v-for="scope in row.scopes" :key="scope" size="small" class="scope-tag">{{ scope }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="expires_at" label="过期时间" width="180" />
      <el-table-column prop="last_used_at" label="最后使用" width="180" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="danger" plain @click="revoke(row)">吊销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!agentUsers.length && !loading" description="没有 Agent 服务账号，请先将用户角色设置为 Agent" />

    <el-dialog v-model="createVisible" title="创建 Agent API Key" width="520px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如 MCP Inspector" />
        </el-form-item>
        <el-form-item label="Scopes">
          <el-checkbox-group v-model="form.scopes">
            <el-checkbox label="product:view">商品查询</el-checkbox>
            <el-checkbox label="recommendation:query">推荐查询</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="有效期">
          <el-input-number v-model="form.expires_in_days" :min="0" :max="3650" />
          <span class="hint">天，0 表示永不过期</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="keyVisible" title="API Key 已创建" width="620px">
      <el-alert title="请立即复制保存，关闭后无法再次查看完整 Key。" type="warning" :closable="false" show-icon />
      <pre class="key-value">{{ createdKey }}</pre>
      <template #footer>
        <el-button type="primary" @click="keyVisible = false">我已保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  apiCreateAgentKey,
  apiGetAgentKeys,
  apiGetAgentUsers,
  apiRevokeAgentKey
} from "../api/admin";

const agentUsers = ref([]);
const selectedUserId = ref(null);
const keys = ref([]);
const loading = ref(false);
const saving = ref(false);
const createVisible = ref(false);
const keyVisible = ref(false);
const createdKey = ref("");
const form = reactive({ name: "mcp-agent", scopes: ["product:view", "recommendation:query"], expires_in_days: 30 });

async function loadUsers() {
  loading.value = true;
  try {
    const res = await apiGetAgentUsers();
    agentUsers.value = res.data.data || [];
    if (agentUsers.value.length) {
      selectedUserId.value = agentUsers.value[0].id;
      await loadKeys();
    }
  } finally {
    loading.value = false;
  }
}

async function loadKeys() {
  if (!selectedUserId.value) return;
  loading.value = true;
  try {
    const res = await apiGetAgentKeys(selectedUserId.value);
    keys.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  form.name = "mcp-agent";
  form.scopes = ["product:view", "recommendation:query"];
  form.expires_in_days = 30;
  createVisible.value = true;
}

async function create() {
  if (!form.scopes.length) {
    ElMessage.error("至少选择一个 scope");
    return;
  }
  saving.value = true;
  try {
    const res = await apiCreateAgentKey(selectedUserId.value, { ...form });
    createdKey.value = res.data.data.api_key;
    createVisible.value = false;
    keyVisible.value = true;
    await loadKeys();
  } finally {
    saving.value = false;
  }
}

async function revoke(row) {
  await ElMessageBox.confirm(`确认吊销「${row.name}」？吊销后立即失效。`, "吊销 API Key", { type: "warning" });
  await apiRevokeAgentKey(selectedUserId.value, row.id);
  ElMessage.success("已吊销");
  await loadKeys();
}

onMounted(loadUsers);
</script>

<style scoped>
.notice {
  margin-bottom: 16px;
}
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.scope-tag {
  margin: 2px 4px 2px 0;
}
.hint {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.key-value {
  margin-top: 16px;
  padding: 14px;
  border-radius: 8px;
  background: var(--bg-hover);
  white-space: pre-wrap;
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
</style>
