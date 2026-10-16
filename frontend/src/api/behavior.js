import http from "./http";

// 添加用户行为（通用接口）
export function apiAddBehavior(data) {
  return http.post("/behavior", data);
}

// 获取用户行为列表
export function apiGetUserBehaviors(params) {
  return http.get("/behavior", { params });
}

// 收藏/取消收藏（兼容旧接口）
export function apiToggleFavorite(productId, favorite = true) {
  return http.post("/behavior/favorite", { product_id: productId, favorite });
}

// 获取我的收藏列表
export function apiGetFavorites() {
  return http.get("/favorites");
}

// 获取推荐商品
export function apiGetRecommendations(limit = 10) {
  return http.get("/recommendations", { params: { limit } });
}

// TODO: 评价接口，待实现
export function apiAddReview(productId, score, comment) {
  return http.post("/behavior/review", {
    product_id: productId,
    score,
    comment,
  });
}

// TODO: 获取我的评价列表，待实现
export function apiGetMyReviews() {
  return http.get("/my-reviews");
}
