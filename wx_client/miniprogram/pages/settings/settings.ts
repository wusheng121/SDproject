import {
  changePassword,
  closeAccount,
  getPreferences,
  listCategories,
  profile,
  savePreferences,
  updateProfile
} from "../../utils/api";
import { clearSession, getUser, isLoggedIn } from "../../utils/auth";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    username: "",
    email: "",
    preferenceItems: [] as any[],
    selectedCount: 0,
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
    savingProfile: false,
    savingPreferences: false,
    changingPassword: false
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=settings" });
      return;
    }
    this.load();
  },

  async load() {
    try {
      const [userData, preferenceData, categoryData] = await Promise.all([
        profile(),
        getPreferences(),
        listCategories()
      ]);
      const selected = preferenceData.preferred_categories || [];
      const items = (categoryData.items || []).map((name) => ({
        name,
        selected: selected.includes(name)
      }));
      this.setData({
        username: userData.user.username || "",
        email: userData.user.email || "",
        preferenceItems: items,
        selectedCount: selected.length
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  onUsernameInput(event: any) {
    this.setData({ username: event.detail.value });
  },

  onPasswordInput(event: any) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: event.detail.value });
  },

  async saveProfile() {
    const username = this.data.username.trim();
    if (username.length < 3 || username.length > 50 || username.includes("<")) {
      wx.showToast({ title: "用户名需为 3-50 位且不能包含 HTML 标签", icon: "none" });
      return;
    }
    this.setData({ savingProfile: true });
    try {
      const result = await updateProfile({ username });
      const user = result.user || {};
      wx.setStorageSync("cm_user", { ...(getUser() || {}), ...user });
      this.setData({ username: user.username || username });
      wx.showToast({ title: "资料已更新", icon: "success" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ savingProfile: false });
    }
  },

  togglePreference(event: any) {
    const index = Number(event.currentTarget.dataset.index);
    const items = this.data.preferenceItems.map((item: any, current: number) =>
      current === index ? { ...item, selected: !item.selected } : item
    );
    this.setData({
      preferenceItems: items,
      selectedCount: items.filter((item: any) => item.selected).length
    });
  },

  async savePreferences() {
    const categories = this.data.preferenceItems
      .filter((item: any) => item.selected)
      .map((item: any) => item.name);
    this.setData({ savingPreferences: true });
    try {
      await savePreferences(categories);
      wx.showToast({ title: "兴趣偏好已保存", icon: "success" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ savingPreferences: false });
    }
  },

  async changePassword() {
    const currentPassword = this.data.currentPassword;
    const newPassword = this.data.newPassword;
    if (!currentPassword) {
      wx.showToast({ title: "请输入当前密码", icon: "none" });
      return;
    }
    if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      wx.showToast({ title: "新密码至少 8 位且包含字母和数字", icon: "none" });
      return;
    }
    if (newPassword !== this.data.confirmPassword) {
      wx.showToast({ title: "两次输入的新密码不一致", icon: "none" });
      return;
    }
    this.setData({ changingPassword: true });
    try {
      await changePassword(currentPassword, newPassword);
      this.setData({ currentPassword: "", newPassword: "", confirmPassword: "" });
      wx.showToast({ title: "密码已更新", icon: "success" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ changingPassword: false });
    }
  },

  closeAccount() {
    wx.showModal({
      title: "注销账号",
      content: "注销后账号将无法登录，未成交商品会下架。请输入当前密码确认。",
      editable: true,
      placeholderText: "当前密码",
      confirmText: "确认注销",
      success: async (result) => {
        if (!result.confirm) return;
        const password = (result.content || "").trim();
        if (!password) {
          wx.showToast({ title: "请输入当前密码", icon: "none" });
          return;
        }
        try {
          await closeAccount(password);
          clearSession();
          wx.reLaunch({ url: "/pages/login/login" });
        } catch (error) {
          wx.showToast({ title: (error as Error).message, icon: "none" });
        }
      }
    });
  }
});
