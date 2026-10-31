<template>
  <div class="orders-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">我的订单</h2>
        <p class="page-subtitle">待支付订单可以模拟支付或取消，支付完成后可以评价</p>
      </div>
      <el-button type="primary" @click="reload">刷新</el-button>
    </div>

    <el-card>
      <el-empty v-if="orders.length === 0" description="还没有订单" />
      <div v-for="order in orders" :key="order.id" :class="['order-card', { highlight: highlightId === order.id }]">
        <div class="order-head">
          <div>
            <strong>订单 #{{ order.id }}</strong>
            <span class="time">{{ formatTime(order.created_at) }}</span>
          </div>
          <el-tag :type="statusType(order.status)">{{ statusText(order.status) }}</el-tag>
        </div>
        <div v-for="item in order.items" :key="item.id" class="order-item">
          <div class="item-main" @click="openProduct(item.product_id)">
            <div class="name">{{ item.name }}</div>
            <div class="meta">¥{{ item.price }} × {{ item.quantity }}</div>
          </div>
          <div v-if="item.reviewed" class="reviewed">
            <el-rate :model-value="item.review.score" disabled />
            <span>{{ item.review.comment || "已评价" }}</span>
          </div>
          <el-button
            v-else-if="order.status === 'paid'"
            type="primary"
            plain
            @click="openReview(order, item)"
          >
            评价
          </el-button>
        </div>
        <div class="order-foot">
          <div>合计 <strong>¥{{ order.total_amount }}</strong></div>
          <div class="actions" v-if="order.status === 'pending'">
            <el-button @click="cancel(order.id)">取消订单</el-button>
            <el-button type="primary" @click="pay(order.id)">模拟支付</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="reviewVisible" title="评价商品" width="420px">
      <p class="dialog-name">{{ reviewTarget?.name }}</p>
      <el-rate v-model="reviewScore" />
      <el-input
        v-model="reviewComment"
        type="textarea"
        :rows="4"
        maxlength="500"
        show-word-limit
        placeholder="说说商品成色和使用感受"
      />
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitReview">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";

import { apiCancelOrder, apiGetOrders, apiPayOrder, apiReviewOrder } from "../api/trade";

const route = useRoute();
const router = useRouter();
const orders = ref([]);
const highlightId = ref(Number(route.query.highlight) || null);
const reviewVisible = ref(false);
const reviewTarget = ref(null);
const reviewScore = ref(5);
const reviewComment = ref("");
const submitting = ref(false);

const statusText = (status) => ({ pending: "待支付", paid: "已支付", cancelled: "已取消" }[status] || status);
const statusType = (status) => ({ pending: "warning", paid: "success", cancelled: "info" }[status] || "info");

function formatTime(value) {
  if (!value) return "";
  return value.replace("T", " ").slice(0, 16);
}

async function reload() {
  const res = await apiGetOrders();
  orders.value = res.data.data?.items || [];
}

async function pay(orderId) {
  try {
    await ElMessageBox.confirm("确认模拟支付？支付后商品会标记为已售出。", "模拟支付", {
      confirmButtonText: "确认支付",
      cancelButtonText: "再想想",
      type: "warning"
    });
  } catch {
    return;
  }
  await apiPayOrder(orderId);
  ElMessage.success("支付成功");
  await reload();
}

async function cancel(orderId) {
  try {
    await ElMessageBox.confirm("取消后商品会回到购物车。", "取消订单", {
      confirmButtonText: "取消订单",
      cancelButtonText: "留下",
      type: "warning"
    });
  } catch {
    return;
  }
  await apiCancelOrder(orderId);
  ElMessage.success("订单已取消");
  await reload();
}

function openReview(order, item) {
  reviewTarget.value = { orderId: order.id, productId: item.product_id, name: item.name };
  reviewScore.value = 5;
  reviewComment.value = "";
  reviewVisible.value = true;
}

async function submitReview() {
  if (!reviewScore.value) {
    ElMessage.warning("请先打分");
    return;
  }
  submitting.value = true;
  try {
    await apiReviewOrder(
      reviewTarget.value.orderId,
      reviewTarget.value.productId,
      reviewScore.value,
      reviewComment.value
    );
    ElMessage.success("评价已提交");
    reviewVisible.value = false;
    await reload();
  } finally {
    submitting.value = false;
  }
}

function openProduct(id) {
  router.push(`/product/${id}`);
}

onMounted(reload);
</script>

<style scoped>
.orders-page {
  padding: 24px;
  max-width: 980px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.order-card {
  padding: 16px 0 8px;
  border-bottom: 1px solid var(--border-color);
}

.order-card.highlight {
  background: rgba(168, 181, 255, 0.15);
  border-radius: 12px;
  padding: 16px;
}

.order-head,
.order-foot,
.order-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.time {
  margin-left: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.order-item {
  padding: 12px 0;
}

.item-main {
  cursor: pointer;
  flex: 1;
}

.name {
  color: var(--text-primary);
  font-weight: 650;
}

.meta,
.reviewed {
  color: var(--text-secondary);
  font-size: 13px;
}

.reviewed {
  display: flex;
  align-items: center;
  gap: 8px;
}

.order-foot {
  margin: 8px 0 16px;
  color: var(--text-primary);
}

.actions {
  display: flex;
  gap: 8px;
}

.dialog-name {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-weight: 650;
}

@media (max-width: 768px) {
  .page-header,
  .order-item,
  .order-foot {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
