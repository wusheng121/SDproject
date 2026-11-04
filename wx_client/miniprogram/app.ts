import { isLoggedIn } from "./utils/auth";
import { applyThemeChrome, getTheme } from "./utils/theme";

App({
  onLaunch() {
    // 登录态从本地 Storage 恢复；API 401 由 utils/request.ts 统一刷新。
    isLoggedIn();
    applyThemeChrome(getTheme());
  }
});
