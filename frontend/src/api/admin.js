import http from "./http";

export function apiGetUsers(params) {
  return http.get("/v1/admin/users", { params });
}

export function apiGetUser(userId) {
  return http.get(`/v1/admin/users/${userId}`);
}

export function apiBanUser(userId, reason) {
  return http.post(`/v1/admin/users/${userId}/ban`, { reason });
}

export function apiUnbanUser(userId) {
  return http.post(`/v1/admin/users/${userId}/unban`);
}

export function apiSetUserRoles(userId, roles) {
  return http.put(`/v1/admin/users/${userId}/roles`, { roles });
}

export function apiGetProducts(params) {
  return http.get("/v1/admin/products", { params });
}

export function apiApproveProduct(productId) {
  return http.post(`/v1/admin/products/${productId}/approve`);
}

export function apiRejectProduct(productId, reason) {
  return http.post(`/v1/admin/products/${productId}/reject`, { reason });
}

export function apiOfflineProduct(productId, reason) {
  return http.post(`/v1/admin/products/${productId}/offline`, { reason });
}

export function apiGetLogs(params) {
  return http.get("/v1/admin/operation-logs", { params });
}

export function apiGetStatistics() {
  return http.get("/v1/admin/stats");
}
