import http from "./http";

export function apiAssistantSessions() {
  return http.get("/v1/assistant/sessions");
}

export function apiAssistantSessionMessages(sessionId) {
  return http.get(`/v1/assistant/sessions/${sessionId}/messages`);
}

export function apiDeleteAssistantSession(sessionId) {
  return http.delete(`/v1/assistant/sessions/${sessionId}`);
}

export function apiUnifiedAssistantMessage({ message, sessionId, filename, imageDataUrl }) {
  return http.post(
    "/v1/assistant/message",
    {
      message,
      session_id: sessionId || null,
      filename: filename || "",
      image_data_url: imageDataUrl || ""
    },
    { timeout: 90000, timeoutErrorMessage: "助手处理超时，请稍后重试" }
  );
}

export function apiConfirmAgentAction(actionId, content) {
  return http.post(`/v1/assistant/actions/${actionId}/confirm`, content ? { content } : {});
}

export function apiCancelAgentAction(actionId) {
  return http.post(`/v1/assistant/actions/${actionId}/cancel`);
}
