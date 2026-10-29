import axios from "axios";
import { ElMessage } from "element-plus";

import router from "../router";
import { clearAccessToken, getAccessToken, setAccessToken } from "./token";

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const normalizedBaseUrl = rawBaseUrl ? rawBaseUrl.replace(/\/$/, "") : "/api";

const http = axios.create({
  baseURL: normalizedBaseUrl,
  timeout: 10000,
  withCredentials: true
});

const authClient = axios.create({
  baseURL: normalizedBaseUrl,
  timeout: 10000,
  withCredentials: true
});

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function normalizeBody(body) {
  if (body && body.error) {
    const error = new Error(body.error.message || "请求失败");
    error.code = body.error.code;
    error.details = body.error.details;
    error.traceId = body.error.trace_id;
    throw error;
  }
  if (body && typeof body === "object" && "code" in body) {
    return body;
  }
  if (body && typeof body === "object" && "data" in body) {
    return { code: 0, message: "ok", data: body.data, pagination: body.pagination };
  }
  return body;
}

let refreshing = null;

export async function refreshAccessToken() {
  if (!refreshing) {
    refreshing = authClient
      .post("/v1/auth/refresh")
      .then((response) => {
        const body = normalizeBody(response.data);
        const token = body.data?.access_token || "";
        setAccessToken(token);
        return token;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;
    const isAuthCall = String(original.url || "").includes("/v1/auth/");
    const serverMessage =
      error?.response?.data?.error?.message || error?.response?.data?.message;
    if (serverMessage) {
      error.message = serverMessage;
    }

    if (status === 401 && !original._retried && !isAuthCall) {
      original._retried = true;
      try {
        const token = await refreshAccessToken();
        if (token) {
          original.headers = original.headers || {};
          original.headers.Authorization = `Bearer ${token}`;
          return http(original);
        }
      } catch {
        // fall through to logout
      }
    }

    if (status === 401) {
      clearAccessToken();
      if (!original.skipAuthRedirect && router.currentRoute.value.path !== "/login") {
        ElMessage.error("登录已过期，请重新登录");
        router.push("/login");
      }
    } else {
      const message = serverMessage || error?.message || "请求失败";
      if (!isAuthCall) ElMessage.error(message);
    }

    return Promise.reject(error);
  }
);

export default http;
