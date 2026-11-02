<template>
  <div class="admin-page">
    <div class="admin-header">
      <div>
        <h1 class="page-title">管理后台</h1>
        <p class="page-subtitle">用户、商品审核、操作日志与平台统计</p>
      </div>
      <el-button :loading="loading" @click="reloadAll">刷新</el-button>
    </div>

    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :md="6">
        <el-card shadow="never"><div class="stat-label">用户总数</div><div class="stat-value">{{ stats.users.total }}</div></el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="never"><div class="stat-label">商品总数</div><div class="stat-value">{{ stats.products.total }}</div></el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="never"><div class="stat-label">待审核</div><div class="stat-value warning">{{ stats.products.pending }}</div></el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="never"><div class="stat-label">行为记录</div><div class="stat-value">{{ stats.behaviors }}</div></el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="用户管理" name="users">
          <div class="toolbar">
            <el-input v-model="userFilters.keyword" placeholder="用户名或邮箱" clearable style="width: 240px" @keyup.enter="loadUsers(1)" />
            <el-select v-model="userFilters.role" placeholder="角色" clearable style="width: 150px" @change="loadUsers(1)">
              <el-option label="普通用户" value="normal_user" />
              <el-option label="管理员" value="admin" />
              <el-option label="Agent" value="agent_service" />
            </el-select>
            <el-select v-model="userFilters.status" placeholder="状态" clearable style="width: 130px" @change="loadUsers(1)">
              <el-option label="正常" value="active" />
              <el-option label="已封禁" value="banned" />
            </el-select>
            <el-button type="primary" @click="loadUsers(1)">查询</el-button>
          </div>
          <el-table :data="users" stripe v-loading="loading">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="phone" label="手机号" width="140" />
            <el-table-column label="角色" min-width="150">
              <template #default="{ row }">
                <el-tag v-for="role in row.roles" :key="role" size="small" class="role-tag">{{ role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                  {{ row.is_active ? '正常' : '已封禁' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <div class="user-actions">
                  <el-button size="small" type="primary" @click="viewUserDetail(row)">详情</el-button>
                  <el-button v-if="row.is_active" size="small" type="danger" plain @click="banUser(row)">封禁</el-button>
                  <el-button v-else size="small" type="success" plain @click="unbanUser(row)">解封</el-button>
                  <el-dropdown trigger="click">
                    <el-button size="small">
                      更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item @click="setAdmin(row, true)">设为管理员</el-dropdown-item>
                        <el-dropdown-item @click="setAdmin(row, false)">设为普通用户</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" background layout="total, prev, pager, next" :total="userTotal" :page-size="userPageSize" :current-page="userPage" @current-change="loadUsers" />
        </el-tab-pane>

        <el-tab-pane label="商品审核" name="products">
          <div class="toolbar">
            <el-select v-model="productFilters.status" placeholder="全部状态" clearable style="width: 160px" @change="loadProducts(1)">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="已下架" value="offline" />
            </el-select>
            <el-button type="primary" @click="loadProducts(1)">查询</el-button>
          </div>
          <el-table :data="products" stripe v-loading="loading">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="name" label="商品" min-width="180" />
            <el-table-column prop="price" label="价格" width="100" />
            <el-table-column prop="condition" label="成色" width="100" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="卖家" width="130">
              <template #default="{ row }">{{ row.seller?.username || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'pending' || row.status === 'rejected'" size="small" type="success" @click="approveProduct(row)">通过</el-button>
                <el-button v-if="row.status === 'pending'" size="small" type="danger" plain @click="rejectProduct(row)">拒绝</el-button>
                <el-button v-if="row.status === 'approved'" size="small" @click="offlineProduct(row)">下架</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" background layout="total, prev, pager, next" :total="productTotal" :page-size="productPageSize" :current-page="productPage" @current-change="loadProducts" />
        </el-tab-pane>

        <el-tab-pane label="操作日志" name="logs">
          <div class="toolbar">
            <el-select v-model="logFilters.action" placeholder="全部动作" clearable style="width: 220px" @change="loadLogs(1)">
              <el-option v-for="item in logActions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-select v-model="logFilters.resource_type" placeholder="全部资源" clearable style="width: 180px" @change="loadLogs(1)">
              <el-option v-for="item in logResourceTypes" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-button type="primary" @click="loadLogs(1)">查询</el-button>
          </div>
          <el-table :data="logs" stripe v-loading="loading">
            <el-table-column prop="created_at" label="时间" width="180" />
            <el-table-column prop="actor" label="操作者" width="120" />
            <el-table-column prop="action" label="动作" min-width="150" />
            <el-table-column label="内容" min-width="220">
              <template #default="{ row }">
                <span v-if="logPreview(row)">{{ logPreview(row) }}</span>
                <el-button v-if="row.resource_type === 'agent_dialogue' && row.resource_id" link type="primary" @click="openDialogue(row)">查看对话</el-button>
                <span v-else-if="!logPreview(row)">-</span>
              </template>
            </el-table-column>
            <el-table-column label="资源" min-width="140">
              <template #default="{ row }">{{ resourceLabel(row.resource_type) }} / {{ row.resource_id || '-' }}</template>
            </el-table-column>
            <el-table-column prop="ip" label="IP" width="140" />
            <el-table-column prop="trace_id" label="Trace ID" min-width="180" />
          </el-table>
          <el-pagination class="pager" background layout="total, prev, pager, next" :total="logTotal" :page-size="logPageSize" :current-page="logPage" @current-change="loadLogs" />
        </el-tab-pane>

        <el-tab-pane label="平台统计" name="stats">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户总数">{{ stats.users.total }}</el-descriptions-item>
            <el-descriptions-item label="活跃用户">{{ stats.users.active }}</el-descriptions-item>
            <el-descriptions-item label="商品总数">{{ stats.products.total }}</el-descriptions-item>
            <el-descriptions-item label="待审核商品">{{ stats.products.pending }}</el-descriptions-item>
            <el-descriptions-item label="已上架商品">{{ stats.products.approved }}</el-descriptions-item>
            <el-descriptions-item label="行为记录">{{ stats.behaviors }}</el-descriptions-item>
            <el-descriptions-item label="订单总数">{{ stats.orders }}</el-descriptions-item>
            <el-descriptions-item label="统计时间">{{ stats.generated_at }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="dialogueVisible" title="购物助手对话" width="640px">
      <p v-if="dialogue" class="dialogue-meta">{{ dialogue.username || '用户' }} · {{ dialogue.updated_at || '' }}</p>
      <div v-if="dialogue" class="dialogue-thread">
        <div v-for="(item, index) in dialogue.messages || []" :key="index" :class="['dialogue-line', item.role]">
          <strong>{{ item.role === 'user' ? '用户' : '助手' }}</strong>
          <p>{{ item.content || (item.filename ? `上传了 ${item.filename}` : '') }}</p>
        </div>
        <p v-if="!(dialogue.messages || []).length" class="dialogue-meta">这段对话没有内容</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowDown } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";

import {
  apiApproveProduct,
  apiBanUser,
  apiGetAgentDialogue,
  apiGetLogs,
  apiGetProducts,
  apiGetStatistics,
  apiGetUser,
  apiGetUsers,
  apiOfflineProduct,
  apiRejectProduct,
  apiSetUserRoles,
  apiUnbanUser
} from "../api/admin";
import { useUserStore } from "../stores/user";

const router = useRouter();
const userStore = useUserStore();
const activeTab = ref("users");
const loading = ref(false);

const users = ref([]);
const userTotal = ref(0);
const userPage = ref(1);
const userPageSize = 20;
const userFilters = reactive({ keyword: "", role: "", status: "" });

const products = ref([]);
const productTotal = ref(0);
const productPage = ref(1);
const productPageSize = 20;
const productFilters = reactive({ status: "" });

const dialogueVisible = ref(false);
const dialogue = ref(null);
const logs = ref([]);
const logTotal = ref(0);
const logPage = ref(1);
const logPageSize = 20;
const logFilters = reactive({ action: "", resource_type: "" });
const logActions = [
  { value: "user.roles.update", label: "修改用户身份" },
  { value: "user.ban", label: "封禁用户" },
  { value: "user.unban", label: "解除封禁" },
  { value: "product.approve", label: "通过商品" },
  { value: "product.reject", label: "拒绝商品" },
  { value: "product.offline", label: "下架商品" },
  { value: "agent.dialogue.query", label: "购物助手查询" },
  { value: "agent.dialogue.refuse", label: "购物助手拒绝" },
  { value: "agent.products.query", label: "外部查询商品" },
  { value: "agent.recommendations.query", label: "外部查询推荐" }
];
const logResourceTypes = [
  { value: "user", label: "用户" },
  { value: "product", label: "商品" },
  { value: "agent_dialogue", label: "购物助手对话" },
  { value: "recommendation", label: "推荐" },
  { value: "skill", label: "外部技能" }
];

const stats = ref({
  users: { total: 0, active: 0 },
  products: { total: 0, pending: 0, approved: 0 },
  behaviors: 0,
  orders: 0,
  generated_at: "-"
});

function statusType(status) {
  return { pending: "warning", approved: "success", rejected: "danger", offline: "info", sold: "info" }[status] || "info";
}
function statusText(status) {
  return { pending: "待审核", approved: "已通过", rejected: "已拒绝", offline: "已下架", sold: "已售出" }[status] || status;
}

async function loadUsers(page = 1) {
  userPage.value = page;
  loading.value = true;
  try {
    const res = await apiGetUsers({ ...userFilters, page, page_size: userPageSize });
    users.value = res.data.data || [];
    userTotal.value = res.data.pagination?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function viewUserDetail(row) {
  try {
    const res = await apiGetUser(row.id);
    const user = res.data.data.user;
    const behaviors = res.data.data.recent_behaviors || [];
    const windowDays = res.data.data.behavior_window_days || 7;
    
    const content = `
      <div style="text-align: left;">
        <p><strong>用户名：</strong>${user.username}</p>
        <p><strong>邮箱：</strong>${user.email || '-'}</p>
        <p><strong>近${windowDays}天行为记录（${behaviors.length}条）：</strong></p>
        ${behaviors.length ? `
          <ul style="max-height: 300px; overflow-y: auto; padding-left: 20px;">
            ${behaviors.map(b => `
              <li style="margin: 8px 0;">
                <strong>${b.behavior_label}</strong> - ${b.product_name || '商品已删除'}
                <br><small style="color: #999;">${b.created_at} · 权重: ${b.weight}</small>
              </li>
            `).join('')}
          </ul>
        ` : '<p style="color: #999;">暂无行为记录</p>'}
      </div>
    `;
    
    await ElMessageBox.alert(content, '用户详情', { dangerouslyUseHTMLString: true, confirmButtonText: '关闭' });
  } catch (error) {
    ElMessage.error('加载用户详情失败');
  }
}

async function loadProducts(page = 1) {
  productPage.value = page;
  loading.value = true;
  try {
    const res = await apiGetProducts({ ...productFilters, page, page_size: productPageSize });
    products.value = res.data.data || [];
    productTotal.value = res.data.pagination?.total || 0;
  } finally {
    loading.value = false;
  }
}

function resourceLabel(type) {
  return logResourceTypes.find((item) => item.value === type)?.label || type || "-";
}

function logPreview(row) {
  if (!row.after_json) return "";
  try {
    const data = typeof row.after_json === "string" ? JSON.parse(row.after_json) : row.after_json;
    return [data.message, data.reply].filter(Boolean).join(" → ");
  } catch {
    return "";
  }
}

async function openDialogue(row) {
  const res = await apiGetAgentDialogue(row.resource_id);
  dialogue.value = res.data.data;
  dialogueVisible.value = true;
}

async function loadLogs(page = 1) {
  logPage.value = page;
  loading.value = true;
  try {
    const res = await apiGetLogs({
      action: logFilters.action || undefined,
      resource_type: logFilters.resource_type || undefined,
      page,
      page_size: logPageSize
    });
    logs.value = res.data.data || [];
    logTotal.value = res.data.pagination?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  const res = await apiGetStatistics();
  stats.value = res.data.data;
}

async function reloadAll() {
  await Promise.all([loadUsers(userPage.value), loadProducts(productPage.value), loadLogs(logPage.value), loadStats()]);
}

function onTabChange(name) {
  if (name === "users") loadUsers(1);
  if (name === "products") loadProducts(1);
  if (name === "logs") loadLogs(1);
  if (name === "stats") loadStats();
}

async function banUser(row) {
  await ElMessageBox.confirm(`确认封禁 ${row.username}？封禁后该账号不能登录。`, "封禁用户");
  await apiBanUser(row.id);
  ElMessage.success("已封禁");
  await loadUsers(userPage.value);
}

async function unbanUser(row) {
  await ElMessageBox.confirm(`确认解封 ${row.username}？`, "解封用户", { type: "warning" });
  await apiUnbanUser(row.id);
  ElMessage.success("已解封");
  await loadUsers(userPage.value);
}

async function setAdmin(row, makeAdmin) {
  const roles = makeAdmin ? ["admin", "normal_user"] : ["normal_user"];
  const label = makeAdmin ? "管理员" : "普通用户";
  const extra = makeAdmin ? "登录时仍可以选择普通用户。" : "之后只能以普通用户登录。";
  await ElMessageBox.confirm(`确认将 ${row.username} 改为${label}？${extra}`, "修改身份");
  await apiSetUserRoles(row.id, roles);
  if (row.id === userStore.profile?.id) {
    ElMessage.success("身份已更新，请重新登录并选择身份");
    await userStore.logout();
    router.push("/login");
    return;
  }
  ElMessage.success("身份已更新");
  await loadUsers(userPage.value);
}

async function approveProduct(row) {
  await apiApproveProduct(row.id);
  ElMessage.success("审核通过");
  await loadProducts(productPage.value);
}

async function rejectProduct(row) {
  const { value } = await ElMessageBox.prompt("请输入拒绝原因", "拒绝商品", { inputPlaceholder: "原因" });
  await apiRejectProduct(row.id, value || "信息不完整");
  ElMessage.success("已拒绝");
  await loadProducts(productPage.value);
}

async function offlineProduct(row) {
  const { value } = await ElMessageBox.prompt("请输入下架原因", "下架商品", { inputPlaceholder: "原因" });
  await apiOfflineProduct(row.id, value || "管理员操作");
  ElMessage.success("已下架");
  await loadProducts(productPage.value);
}

onMounted(async () => {
  if (!userStore.initialized) await userStore.bootstrap();
  if (!userStore.isAdmin) {
    ElMessage.error("无权访问管理后台");
    router.push("/");
    return;
  }
  await reloadAll();
});
</script>

<style scoped>
.admin-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}
.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title {
  margin: 0 0 6px;
  font-size: 30px;
  font-weight: 800;
  color: var(--text-primary);
}
.page-subtitle {
  margin: 0;
  color: var(--text-secondary);
}
.stats-row {
  margin-bottom: 16px;
}
.stat-label {
  color: var(--text-secondary);
  font-size: 14px;
}
.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--primary-color);
}
.stat-value.warning {
  color: #e6a23c;
}
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.role-tag {
  margin: 2px 4px 2px 0;
}
.user-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.dialogue-meta {
  margin: 0 0 12px;
  color: var(--text-secondary);
}
.dialogue-thread {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
}
.dialogue-line {
  padding: 10px 12px;
  border-radius: 10px;
}
.dialogue-line p {
  margin: 6px 0 0;
  white-space: pre-wrap;
  line-height: 1.6;
}
.dialogue-line.user {
  background: rgba(88, 101, 242, 0.12);
}
.dialogue-line.assistant {
  background: var(--bg-hover);
}
@media (max-width: 768px) {
  .admin-page {
    padding: 12px;
  }
  .admin-header {
    align-items: flex-start;
    gap: 12px;
    flex-direction: column;
  }
}
</style>
