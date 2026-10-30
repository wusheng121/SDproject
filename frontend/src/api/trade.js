import http from "./http";

export function apiGetCart() {
  return http.get("/v1/cart");
}

export function apiAddToCart(productId) {
  return http.post("/v1/cart", { product_id: productId });
}

export function apiRemoveFromCart(productId) {
  return http.delete(`/v1/cart/${productId}`);
}

export function apiCreateOrder(productIds) {
  const body = productIds?.length ? { product_ids: productIds } : {};
  return http.post("/v1/orders", body);
}

export function apiGetOrders() {
  return http.get("/v1/orders");
}

export function apiPayOrder(orderId) {
  return http.post(`/v1/orders/${orderId}/pay`);
}

export function apiCancelOrder(orderId) {
  return http.post(`/v1/orders/${orderId}/cancel`);
}

export function apiReviewOrder(orderId, productId, score, comment) {
  return http.post(`/v1/orders/${orderId}/reviews`, {
    product_id: productId,
    score,
    comment
  });
}

export function apiProductReviews(productId) {
  return http.get(`/v1/products/${productId}/reviews`);
}
