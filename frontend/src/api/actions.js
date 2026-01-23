import http from "./http";

export function apiToggleFavorite({ movie_id, favorite }) {
  return http.post("/action/favorite", { movie_id, favorite });
}

export function apiRateMovie({ movie_id, score, comment }) {
  return http.post("/action/rate", { movie_id, score, comment });
}

export function apiRecommendations(limit = 10) {
  return http.get("/recommendations", { params: { limit } });
}

export function apiGetMyRatings() {
  return http.get("/user/ratings");
}






















