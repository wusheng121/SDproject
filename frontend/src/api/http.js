import axios from "axios";
import { ElMessage } from "element-plus";

import router from "../router";

const http = axios.create({
  baseURL: "/api",
  timeout: 10000
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const status = err?.response?.status;

    // 统一处理 token 过期/未登录
    if (status === 401) {
      localStorage.removeItem("token");
      ElMessage.error("登录已过期，请重新登录");
      if (router.currentRoute.value.path !== "/login") router.push("/login");
    } else {
      const msg = err?.response?.data?.message || err?.message || "请求失败";
      ElMessage.error(msg);
    }

    return Promise.reject(err);
  }
);

export default http;




