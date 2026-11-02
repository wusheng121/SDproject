import http from "./http";

export function apiListConversations() {
  return http.get("/v1/messages/conversations");
}

export function apiOpenConversation(productId) {
  return http.post("/v1/messages/conversations", { product_id: productId });
}

export function apiConversationMessages(id) {
  return http.get(`/v1/messages/conversations/${id}`);
}

export function apiSendMessage(id, content) {
  return http.post(`/v1/messages/conversations/${id}`, { content });
}
