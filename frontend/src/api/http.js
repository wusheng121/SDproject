import axios from "axios";

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
    // 这里可以做统一错误处理（课程项目先简单抛出）
    return Promise.reject(err);
  }
);

export default http;



