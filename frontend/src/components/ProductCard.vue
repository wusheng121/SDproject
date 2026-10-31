<template>
  <article class="product-card" role="button" tabindex="0" @click="$emit('open', product)" @keydown.enter="$emit('open', product)">
    <div class="product-image">
      <img v-if="product?.image_url" :src="product.image_url" :alt="product.name" class="image" loading="lazy" />
      <div v-else class="image-placeholder"><span>{{ product?.categories?.[0]?.slice(0, 1) || "闲" }}</span></div>
      <span v-if="product?.condition" class="condition-badge">{{ product.condition }}</span>
      <span v-if="product?.reason" class="recommendation-badge">{{ product.reason }}</span>
    </div>
    <div class="product-info">
      <div v-if="product?.categories?.length" class="product-category">{{ product.categories[0] }}</div>
      <h3 class="product-name" :title="product?.name">{{ product?.name || "未命名商品" }}</h3>
      <div class="product-bottom">
        <div class="product-price"><span>¥</span>{{ formatPrice(product?.price) }}</div>
        <div v-if="product?.behavior_count" class="product-interest">{{ product.behavior_count }} 人关注</div>
      </div>
    </div>
  </article>
</template>

<script setup>
defineProps({ product: { type: Object, default: null } });
defineEmits(["open"]);

function formatPrice(price) {
  const value = Number(price);
  return Number.isFinite(value) ? value.toLocaleString("zh-CN", { maximumFractionDigits: 2 }) : "面议";
}
</script>

<style scoped>
.product-card { min-width: 0; overflow: hidden; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-card); cursor: pointer; transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease; }
.product-card:hover, .product-card:focus-visible { border-color: var(--primary-color); box-shadow: 0 8px 22px rgba(31, 54, 45, .1); transform: translateY(-3px); outline: none; }
.product-image { position: relative; aspect-ratio: 4 / 3; overflow: hidden; background: #eef1ed; }
.image { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .25s ease; }
.product-card:hover .image { transform: scale(1.035); }
.image-placeholder { display: grid; width: 100%; height: 100%; place-items: center; color: #71907f; background: #e9eee9; }
.image-placeholder span { display: grid; width: 54px; height: 54px; place-items: center; border: 1px solid #b8c8bc; border-radius: 50%; font-size: 25px; }
.condition-badge, .recommendation-badge { position: absolute; top: 10px; padding: 5px 8px; border-radius: 3px; color: white; background: rgba(27, 42, 35, .76); font-size: 11px; }
.condition-badge { right: 10px; }
.recommendation-badge { left: 10px; background: rgba(54, 105, 78, .9); }
.product-info { padding: 12px 13px 13px; }
.product-category { overflow: hidden; margin-bottom: 5px; color: var(--text-secondary); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.product-name { display: -webkit-box; min-height: 40px; margin: 0; overflow: hidden; color: var(--text-primary); font-size: 14px; font-weight: 600; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.product-bottom { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-top: 10px; }
.product-price { color: #c6533d; font-size: 20px; font-weight: 750; white-space: nowrap; }
.product-price span { margin-right: 2px; font-size: 12px; }
.product-interest { overflow: hidden; color: var(--text-secondary); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 600px) { .product-info { padding: 10px; } .product-name { min-height: 38px; font-size: 13px; } .product-price { font-size: 18px; } }
</style>
