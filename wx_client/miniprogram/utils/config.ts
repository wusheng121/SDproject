// 开发：微信开发者工具中可访问本机 8080。
// 真机调试请改成电脑局域网 IP，例如 http://192.168.1.10:8080。
export const BASE_URL = "http://127.0.0.1:8080";
export const API_BASE = `${BASE_URL}/api`;

export function assetUrl(path: string): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
