import { refreshAccessToken, request } from "./request";
import { API_BASE } from "./config";
import { getAccessToken } from "./auth";

export interface Captcha {
  captcha_id: string;
  image: string;
}

export interface UserProfile {
  id: number;
  username: string;
  email?: string;
  roles?: string[];
  user_type?: string;
  must_change_password?: boolean;
}

export interface Product {
  id: number;
  name: string;
  price: number;
  condition: string;
  image_url?: string;
  description?: string;
  categories?: string[];
  status?: string;
  brand?: string;
  defect_description?: string;
  trade_method?: string;
  trade_location?: string;
  behavior_count?: number;
  is_favorited?: boolean;
  seller?: { id: number; username: string };
}

export interface ProductPage {
  items: Product[];
  total: number;
}

export function getCaptcha() {
  return request<Captcha>("/v1/auth/captcha", { auth: false });
}

export function miniLogin(payload: {
  identifier: string;
  password: string;
  captcha_id: string;
  captcha_code: string;
}) {
  return request<{ access_token: string; refresh_token: string; user: UserProfile }>(
    "/v1/auth/miniprogram/login",
    { method: "POST", data: payload, auth: false }
  );
}

export function register(payload: {
  username: string;
  email: string;
  password: string;
  phone?: string;
  captcha_id: string;
  captcha_code: string;
}) {
  return request("/v1/auth/register", { method: "POST", data: payload, auth: false });
}

export function listProducts(page = 1, pageSize = 12) {
  return request<ProductPage>("/products", {
    data: { page, page_size: pageSize }
  });
}

export function searchProducts(params: Record<string, unknown>) {
  return request<ProductPage>("/products/search", { data: params });
}

export function listCategories() {
  return request<{ items: string[] }>("/categories");
}

export function uploadProductImage(filePath: string): Promise<{ image_url: string }> {
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().readFile({
      filePath,
      encoding: "base64",
      success: (result) => {
        const mime = /\.png$/i.test(filePath) ? "image/png" : "image/jpeg";
        request<{ image_url: string }>("/products/images", {
          method: "POST",
          data: { image_base64: result.data as string, mime }
        }).then(resolve, reject);
      },
      fail: () => reject(new Error("图片读取失败"))
    });
  });
}

export function publishProduct(data: Record<string, unknown>) {
  return request<{ id: number; status: string }>("/products", {
    method: "POST",
    data
  });
}

export function editProduct(id: number, data: Record<string, unknown>) {
  return request("/products/" + id, { method: "PUT", data });
}

export function deleteProduct(id: number) {
  return request("/products/" + id, { method: "DELETE" });
}

export function myProducts() {
  return request<{ items: Product[] }>("/v1/users/me/products");
}

export function getPriceReference(category: string) {
  return request<Record<string, any>>("/products/price-reference", {
    data: { category }
  });
}

export function recognizeListing(filePath: string): Promise<Record<string, any>> {
  return new Promise((resolve, reject) => {
    const send = (accessToken: string) => {
      wx.uploadFile({
        url: `${API_BASE}/ai/listing-recognize`,
        filePath,
        name: "image",
        header: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        success: (response) => {
          let body: any = {};
          try {
            body = JSON.parse(response.data || "{}");
          } catch {
            reject(new Error("识图结果解析失败"));
            return;
          }
          if (response.statusCode === 401) {
            refreshAccessToken()
              .then((token) => send(token))
              .catch(reject);
            return;
          }
          if (response.statusCode < 200 || response.statusCode >= 300 || body.error) {
            reject(new Error(body?.error?.message || body?.message || "识图失败"));
            return;
          }
          resolve(body.data || {});
        },
        fail: (error) => reject(new Error(error.errMsg || "识图请求失败"))
      });
    };
    send(getAccessToken());
  });
}

export function recognizeProduct(filePath: string): Promise<Record<string, any>> {
  return new Promise((resolve, reject) => {
    const send = (accessToken: string) => {
      wx.uploadFile({
        url: `${API_BASE}/ai/recognize`,
        filePath,
        name: "image",
        header: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        success: (response) => {
          let body: any = {};
          try {
            body = JSON.parse(response.data || "{}");
          } catch {
            reject(new Error("识图结果解析失败"));
            return;
          }
          if (response.statusCode === 401) {
            refreshAccessToken()
              .then((token) => send(token))
              .catch(reject);
            return;
          }
          if (response.statusCode < 200 || response.statusCode >= 300 || body.error) {
            reject(new Error(body?.error?.message || body?.message || "识图失败"));
            return;
          }
          resolve(body.data || {});
        },
        fail: (error) => reject(new Error(error.errMsg || "识图请求失败"))
      });
    };
    send(getAccessToken());
  });
}

export function filterNl(text: string) {
  return request<{ filters: Record<string, any> }>("/ai/filter/nl", {
    method: "POST",
    data: { text }
  });
}

export function productDetail(id: number) {
  return request<Product>(`/products/${id}`);
}

export function productReviews(id: number) {
  return request<{ items: any[] }>(`/v1/products/${id}/reviews`, { auth: false });
}

export function toggleFavorite(productId: number, favorite = true) {
  return request("/v1/behaviors", {
    method: "POST",
    data: { product_id: productId, behavior_type: "favorite", value: favorite ? 1 : 0 }
  });
}

export function listFavorites() {
  return request<Product[]>("/v1/users/me/favorites");
}

export function getCart() {
  return request<{ items: any[]; total_amount: number }>("/v1/cart");
}

export function addCart(productId: number) {
  return request("/v1/cart", { method: "POST", data: { product_id: productId } });
}

export function removeCart(productId: number) {
  return request(`/v1/cart/${productId}`, { method: "DELETE" });
}

export function getOrders() {
  return request<{ items: any[] }>("/v1/orders");
}

export function createOrder(productIds: number[]) {
  return request("/v1/orders", { method: "POST", data: { product_ids: productIds } });
}

export function payOrder(orderId: number) {
  return request(`/v1/orders/${orderId}/pay`, { method: "POST" });
}

export function cancelOrder(orderId: number) {
  return request(`/v1/orders/${orderId}/cancel`, { method: "POST" });
}

export function listConversations() {
  return request<any[]>("/v1/messages/conversations");
}

export function openConversation(productId: number) {
  return request<{ id: number }>("/v1/messages/conversations", {
    method: "POST",
    data: { product_id: productId }
  });
}

export function conversationMessages(id: number) {
  return request<any[]>(`/v1/messages/conversations/${id}`);
}

export function sendMessage(id: number, content: string) {
  return request(`/v1/messages/conversations/${id}`, {
    method: "POST",
    data: { content }
  });
}

export function profile() {
  return request<{ user: UserProfile }>("/v1/users/me");
}

export function userStats() {
  return request<{ favorites: number; behaviors: number; products: number; categories: number }>("/v1/users/me/stats");
}

export function getPreferences() {
  return request<{ preferred_categories: string[]; has_preference: boolean }>("/v1/users/me/preferences");
}

export function savePreferences(categories: string[]) {
  return request("/v1/users/me/preferences", { method: "PUT", data: { categories } });
}

export function updateProfile(data: { username?: string; email?: string; phone?: string }) {
  return request<{ user: UserProfile }>("/v1/users/me", { method: "PUT", data });
}

export function changePassword(currentPassword: string, newPassword: string) {
  return request("/v1/users/me/password", {
    method: "POST",
    data: { current_password: currentPassword, new_password: newPassword }
  });
}

export function closeAccount(password: string) {
  return request("/v1/users/me/close", { method: "POST", data: { password } });
}

export function reviewOrder(orderId: number, productId: number, score: number, comment: string) {
  return request(`/v1/orders/${orderId}/reviews`, {
    method: "POST",
    data: { product_id: productId, score, comment }
  });
}

export function getRecommendations(limit = 6, offset = 0) {
  return request<{ items: Product[]; candidate_count?: number; strategy_name?: string; behavior_count?: number }>(
    "/recommendations",
    { data: { limit, offset } }
  );
}

export function getRecommendationQuality() {
  return request<Record<string, any>>("/recommendations/quality");
}

export function assistantMessage(message: string, sessionId = 0) {
  return request<{ session_id: number; reply: string; items?: Product[]; action_proposals?: any[] }>(
    "/v1/assistant/message",
    {
      method: "POST",
      data: {
        message,
        session_id: sessionId || null
      },
      timeout: 90000
    }
  );
}

export function confirmAssistantAction(actionId: number, content = "") {
  return request<{ executed: boolean; action_type: string; result: any }>(
    `/v1/assistant/actions/${actionId}/confirm`,
    {
      method: "POST",
      data: content ? { content } : {}
    }
  );
}

export function cancelAssistantAction(actionId: number) {
  return request<{ cancelled: boolean }>(`/v1/assistant/actions/${actionId}/cancel`, {
    method: "POST"
  });
}
