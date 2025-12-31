import http from "./http";

export function apiListMovies(params) {
  return http.get("/movies", { params });
}

export function apiMovieDetail(id) {
  return http.get(`/movies/${id}`);
}

export function apiSearchMovies(q) {
  return http.get("/movies/search", { params: { q } });
}





