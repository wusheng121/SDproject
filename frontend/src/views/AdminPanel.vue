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
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.is_active" size="small" type="danger" plain @click="banUser(row)">封禁</el-button>
                <el-button v-else size="small" type="success" plain @click="unbanUser(row)">解封</el-button>
                <el-button size="small" @click="setAdmin(row, true)">设为管理员</el-button>
                <el-button size="small" @click="setAdmin(row, false)">设为普通用户</el-button>
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
                <el-button v-if="row.status === 'pending' || row.status === 'approved'" size="small" type="danger" plain @click="rejectProduct(row)">拒绝</el-button>
                <el-button v-if="row.status === 'approved'" size="small" @click="offlineProduct(row)">下架</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" background layout="total, prev, pager, next" :total="productTotal" :page-size="productPageSize" :current-page="productPage" @current-change="loadProducts" />
        </el-tab-pane>

        <el-tab-pane label="操作日志" name="logs">
          <div class="toolbar">
            <el-input v-model="logFilters.action" placeholder="动作，如 user.ban" clearable style="width: 220px" @keyup.enter="loadLogs(1)" />
            <el-input v-model="logFilters.resource_type" placeholder="资源类型" clearable style="width: 160px" @keyup.enter="loadLogs(1)" />
            <el-button type="primary" @click="loadLogs(1)">查询</el-button>
          </div>
          <el-table :data="logs" stripe v-loading="loading">
            <el-table-column prop="created_at" label="时间" width="180" />
            <el-table-column prop="actor" label="操作者" width="120" />
            <el-table-column prop="action" label="动作" min-width="150" />
            <el-table-column label="资源" min-width="140">
              <template #default="{ row }">{{ row.resource_type || '-' }} / {{ row.resource_id || '-' }}</template>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";

import {
  apiApproveProduct,
  apiBanUser,
  apiGetLogs,
  apiGetProducts,
  apiGetStatistics,
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

const logs = ref([]);
const logTotal = ref(0);
const logPage = ref(1);
const logPageSize = 20;
const logFilters = reactive({ action: "", resource_type: "" });

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

async function loadLogs(page = 1) {
  logPage.value = page;
  loading.value = true;
  try {
    const res = await apiGetLogs({ ...logFilters, page, page_size: logPageSize });
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
  const { value } = await ElMessageBox.prompt("请输入封禁原因", "封禁用户", { inputPlaceholder: "原因" });
  await apiBanUser(row.id, value || "管理员操作");
  ElMessage.success("已封禁");
  await loadUsers(userPage.value);
}

async function unbanUser(row) {
  await ElMessageBox.confirm(`确认解封 ${row.username}？`, "解封用户", { type: "warning" });
  await apiUnbanUser(row.id);
  ElMessage.success("已解封");
  await loadUsers(userPage.value);
}

async function setAdmin(row, isAdmin) {
  const roles = isAdmin ? ["admin"] : ["normal_user"];
  await ElMessageBox.confirm(`确认将 ${row.username} 的角色改为 ${roles[0]}？`, "修改角色");
  await apiSetUserRoles(row.id, roles);
  ElMessage.success("角色已更新");
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
.pager {
  margin-top: 16px;
  justify-content: flex-end;
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
