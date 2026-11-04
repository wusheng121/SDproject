import { getPreferences, profile, userStats } from "../../utils/api";
import { clearSession, getUser, isLoggedIn } from "../../utils/auth";
import { applyPageTheme, setTheme, Theme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    dark: false,
    user: {} as any,
    loggedIn: false,
    stats: { favorites: 0, behaviors: 0, products: 0, categories: 0 },
    preferences: [] as string[]
  },

  onShow() {
    const theme = applyPageTheme(this);
    const loggedIn = isLoggedIn();
    this.setData({ dark: theme === "dark", loggedIn, user: getUser() || {} });
    if (loggedIn) this.load();
  },

  async load() {
    try {
      const [userData, statsData, preferenceData] = await Promise.all([
        profile(),
        userStats(),
        getPreferences()
      ]);
      this.setData({
        user: userData.user || {},
        loggedIn: true,
        stats: statsData || this.data.stats,
        preferences: preferenceData.preferred_categories || []
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  goLogin() {
    wx.navigateTo({ url: "/pages/login/login" });
  },

  goFavorites() {
    wx.navigateTo({ url: "/pages/favorites/favorites" });
  },

  goMyProducts() {
    wx.navigateTo({ url: "/pages/my-products/my-products" });
  },

  goOrders() {
    wx.switchTab({ url: "/pages/orders/orders" });
  },

  goMessages() {
    wx.navigateTo({ url: "/pages/messages/messages" });
  },

  goSettings() {
    wx.navigateTo({ url: "/pages/settings/settings" });
  },

  toggleTheme(event: any) {
    const theme: Theme = event.detail.value ? "dark" : "light";
    setTheme(theme);
    this.setData({ theme, dark: theme === "dark" });
  },

  logout() {
    clearSession();
    this.setData({
      loggedIn: false,
      user: {},
      stats: { favorites: 0, behaviors: 0, products: 0, categories: 0 },
      preferences: []
    });
    wx.showToast({ title: "已退出登录", icon: "none" });
  }
});
