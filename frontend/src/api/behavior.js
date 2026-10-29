import http from "./http";

export function apiAddBehavior(data) {
  return http.post("/v1/behaviors", data);
}

export function apiGetUserBehaviors(params) {
  return http.get("/v1/users/me/behaviors", { params });
}

export function apiToggleFavorite(productId, favorite = true) {
  return http.post("/v1/behaviors", {
    product_id: productId,
    behavior_type: "favorite",
    value: favorite ? 1 : 0
  });
}

export function apiGetFavorites() {
  return http.get("/v1/users/me/favorites");
}

export function apiGetRecommendations(limit = 10) {
  return http.get("/recommendations", { params: { limit } });
}

export function apiAddReview(productId, score, comment) {
  return http.post("/behavior/review", {
    product_id: productId,
    score,
    comment
  });
}

export function apiGetMyReviews() {
  return http.get("/my-reviews");
}
