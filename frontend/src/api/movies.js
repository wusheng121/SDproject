import http from "./http";

export function apiListMovies(params) {
  return http.get("/movies", { params });
}

export function apiMovieDetail(id) {
  return http.get(`/movies/${id}`);
}

export function apiSearchMovies(params) {
  // 兼容旧用法：传字符串时当作 q
  if (typeof params === "string") {
    return http.get("/movies/search", { params: { q: params } });
  }
  return http.get("/movies/search", { params });
}

export function apiListGenres() {
  return http.get("/genres");
}







