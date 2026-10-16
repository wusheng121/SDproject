import http from "./http";

// TODO: 管理员接口，待实现

// 获取用户列表
export function apiGetUsers(params) {
  return http.get("/admin/users", { params });
}

// 封禁用户
export function apiBanUser(userId) {
  return http.post(`/admin/users/${userId}/ban`);
}

// 获取待审核商品列表
export function apiGetPendingProducts(params) {
  return http.get("/admin/products/pending", { params });
}

// 审核通过商品
export function apiApproveProduct(productId) {
  return http.post(`/admin/products/${productId}/approve`);
}

// 审核拒绝商品
export function apiRejectProduct(productId) {
  return http.post(`/admin/products/${productId}/reject`);
}

// 获取操作日志
export function apiGetLogs(params) {
  return http.get("/admin/logs", { params });
}

// 获取统计数据
export function apiGetStatistics() {
  return http.get("/admin/stats");
}
