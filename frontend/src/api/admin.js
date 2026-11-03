import http from "./http";

export function apiGetUsers(params) {
  return http.get("/v1/admin/users", { params });
}

export function apiGetUser(userId) {
  return http.get(`/v1/admin/users/${userId}`);
}

export function apiBanUser(userId) {
  return http.post(`/v1/admin/users/${userId}/ban`);
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

export function apiGetAgentDialogue(sessionId) {
  return http.get(`/v1/admin/agent-dialogues/${sessionId}`);
}

export function apiGetStatistics() {
  return http.get("/v1/admin/stats");
}

export function apiGetAgentSessions(params) {
  return http.get("/v1/admin/agent-sessions", { params });
}

export function apiGetAgentSession(sessionId) {
  return http.get(`/v1/admin/agent-sessions/${sessionId}`);
}

export function apiDeleteAgentSession(sessionId) {
  return http.delete(`/v1/admin/agent-sessions/${sessionId}`);
}

export function apiGetSkills(params) {
  return http.get("/v1/admin/skills", { params });
}

export function apiGetSkill(skillId) {
  return http.get(`/v1/admin/skills/${skillId}`);
}

export function apiCreateSkill(payload) {
  return http.post("/v1/admin/skills", payload);
}

export function apiUpdateSkill(skillId, payload) {
  return http.put(`/v1/admin/skills/${skillId}`, payload);
}

export function apiPublishSkill(skillId) {
  return http.post(`/v1/admin/skills/${skillId}/publish`);
}

export function apiDisableSkill(skillId) {
  return http.post(`/v1/admin/skills/${skillId}/disable`);
}

export function apiTestSkill(skillId, params) {
  return http.post(`/v1/admin/skills/${skillId}/test`, { params });
}

export function apiGetAgentUsers() {
  return http.get("/v1/admin/agent-users");
}

export function apiGetAgentKeys(userId) {
  return http.get(`/v1/admin/agent-users/${userId}/api-keys`);
}

export function apiCreateAgentKey(userId, payload) {
  return http.post(`/v1/admin/agent-users/${userId}/api-keys`, payload);
}

export function apiRevokeAgentKey(userId, keyId) {
  return http.delete(`/v1/admin/agent-users/${userId}/api-keys/${keyId}`);
}
