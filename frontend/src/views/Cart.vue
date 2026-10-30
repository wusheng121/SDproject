<template>
  <div class="cart-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">购物车</h2>
        <p class="page-subtitle">二手商品每件限购 1 件，结算后需要模拟支付</p>
      </div>
      <el-button type="primary" @click="reload">刷新</el-button>
    </div>

    <el-card class="cart-card">
      <el-empty v-if="items.length === 0" description="购物车是空的，去商品详情页看看吧" />
      <div v-else>
        <div v-for="item in items" :key="item.product_id" class="cart-row">
          <img v-if="item.image_url" :src="item.image_url" :alt="item.name" class="thumb" />
          <div v-else class="thumb placeholder">📦</div>
          <div class="info" @click="openProduct(item.product_id)">
            <div class="name">{{ item.name }}</div>
            <div class="meta">
              <span>{{ item.condition }}</span>
              <span>卖家 {{ item.seller?.username || "未知" }}</span>
              <el-tag v-if="item.status !== 'approved'" size="small" type="info">暂时不可结算</el-tag>
            </div>
          </div>
          <div class="price">¥{{ item.price }}</div>
          <el-button type="danger" plain @click="remove(item.product_id)">移除</el-button>
        </div>
        <div class="checkout-bar">
          <div>合计 <strong>¥{{ totalAmount }}</strong></div>
          <el-button type="primary" size="large" :loading="checkingOut" @click="checkout">
            结算
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";

import { apiCreateOrder, apiGetCart, apiRemoveFromCart } from "../api/trade";

const router = useRouter();
const items = ref([]);
const totalAmount = ref(0);
const checkingOut = ref(false);

async function reload() {
  const res = await apiGetCart();
  items.value = res.data.data?.items || [];
  totalAmount.value = res.data.data?.total_amount || 0;
}

async function remove(productId) {
  try {
    await ElMessageBox.confirm("确定从购物车移除这件商品吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    });
  } catch {
    return;
  }
  await apiRemoveFromCart(productId);
  ElMessage.success("已移除");
  await reload();
}

async function checkout() {
  checkingOut.value = true;
  try {
    const res = await apiCreateOrder();
    ElMessage.success("订单已创建，请完成模拟支付");
    router.push({ path: "/orders", query: { highlight: res.data.data?.id } });
  } finally {
    checkingOut.value = false;
  }
}

function openProduct(id) {
  router.push(`/product/${id}`);
}

onMounted(reload);
</script>

<style scoped>
.cart-page {
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

.cart-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.thumb {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  object-fit: cover;
  background: var(--bg-hover);
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.info {
  flex: 1;
  cursor: pointer;
}

.name {
  font-size: 16px;
  font-weight: 650;
  color: var(--text-primary);
}

.meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 13px;
}

.price {
  font-size: 20px;
  font-weight: 700;
  color: #ff4d4f;
}

.checkout-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 24px;
  margin-top: 20px;
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .cart-row {
    flex-wrap: wrap;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
