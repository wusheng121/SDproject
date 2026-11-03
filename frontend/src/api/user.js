import http from "./http";

export function apiCaptcha() {
  return http.get("/v1/auth/captcha");
}

export function apiRegister({ username, email, password, phone, captcha_id, captcha_code }) {
  return http.post("/v1/auth/register", { username, email, password, phone, captcha_id, captcha_code });
}

export function apiLogin({ identifier, password, remember, captcha_id, captcha_code }) {
  return http.post(
    "/v1/auth/login",
    { identifier, password, remember, captcha_id, captcha_code },
    { skipAuthRedirect: true }
  );
}

export function apiRefresh() {
  return http.post("/v1/auth/refresh", {}, { skipAuthRedirect: true });
}

export function apiLogout() {
  return http.post("/v1/auth/logout", {}, { skipAuthRedirect: true });
}

export function apiProfile() {
  return http.get("/v1/users/me");
}

export function apiUpdateProfile(data) {
  return http.patch("/v1/users/me", data);
}

export function apiCloseAccount(password) {
  return http.post("/v1/users/me/close", { password });
}

export function apiUserFavorites() {
  return http.get("/v1/users/me/favorites");
}

export function apiUserStats() {
  return http.get("/v1/users/me/stats");
}

export function apiGetPreferences() {
  return http.get("/v1/users/me/preferences");
}

export function apiSavePreferences(categories) {
  return http.put("/v1/users/me/preferences", { categories });
}

export function apiVerifyEmail(token) {
  return http.post("/v1/auth/verify-email", { token });
}

export function apiForgotPassword(email) {
  return http.post("/v1/auth/forgot-password", { email });
}

export function apiResetPassword(token, newPassword) {
  return http.post("/v1/auth/reset-password", { token, new_password: newPassword });
}

export function apiChangePassword(currentPassword, newPassword) {
  return http.post("/v1/users/me/password", {
    current_password: currentPassword,
    new_password: newPassword
  });
}
