import http from "./http";

export function apiRegister({ username, email, password }) {
  return http.post("/register", { username, email, password });
}

export function apiLogin({ identifier, password, remember }) {
  return http.post("/login", { identifier, password, remember });
}

export function apiProfile() {
  return http.get("/user/profile");
}

export function apiUserFavorites() {
  return http.get("/user/favorites");
}

export function apiUserRatings() {
  return http.get("/user/ratings");
}




