import { API_BASE } from "./config";
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  updateAccessToken
} from "./auth";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  data?: Record<string, unknown>;
  auth?: boolean;
  timeout?: number;
}

interface RawResponse {
  statusCode: number;
  data: any;
}

let refreshing: Promise<string> | null = null;

function rawRequest(path: string, options: RequestOptions): Promise<RawResponse> {
  return new Promise((resolve, reject) => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    const token = getAccessToken();
    if (options.auth !== false && token) {
      headers.Authorization = `Bearer ${token}`;
    }
    wx.request({
      url: `${API_BASE}${path}`,
      method: options.method || "GET",
      data: options.data,
      header: headers,
      timeout: options.timeout || 20000,
      success: (res) => resolve({ statusCode: res.statusCode, data: res.data }),
      fail: (error) => reject(new Error(error.errMsg || "网络请求失败"))
    });
  });
}

function messageOf(body: any): string {
  return body?.error?.message || body?.message || "请求失败";
}

function refreshAccessToken(): Promise<string> {
  if (refreshing) return refreshing;
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearSession();
    return Promise.reject(new Error("登录已过期，请重新登录"));
  }
  refreshing = rawRequest("/v1/auth/miniprogram/refresh", {
    method: "POST",
    auth: false,
    data: { refresh_token: refreshToken }
  })
    .then((response) => {
      const body = response.data;
      if (response.statusCode < 200 || response.statusCode >= 300 || body?.error) {
        throw new Error(messageOf(body));
      }
      const data = body?.data || {};
      if (!data.access_token) throw new Error("刷新登录失败");
      updateAccessToken(data.access_token);
      if (data.refresh_token) {
        wx.setStorageSync("cm_refresh_token", data.refresh_token);
      }
      if (data.user) wx.setStorageSync("cm_user", data.user);
      return data.access_token as string;
    })
    .catch((error) => {
      clearSession();
      throw error;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await rawRequest(path, options);
  if (response.statusCode === 401 && options.auth !== false) {
    await refreshAccessToken();
    response = await rawRequest(path, options);
  }
  if (response.statusCode === 401) {
    clearSession();
    throw new Error("登录已过期，请重新登录");
  }
  const body = response.data;
  if (response.statusCode < 200 || response.statusCode >= 300 || body?.error) {
    throw new Error(messageOf(body));
  }
  return (body && Object.prototype.hasOwnProperty.call(body, "data") ? body.data : body) as T;
}

export { refreshAccessToken };
