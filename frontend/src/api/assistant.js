import http from "./http";

export function apiAssistantChat({ message, sessionId, filename }) {
  return http.post("/v1/assistant/chat", {
    message,
    session_id: sessionId,
    filename
  });
}
