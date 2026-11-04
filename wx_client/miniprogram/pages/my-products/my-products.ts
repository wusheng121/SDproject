import { myProducts } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

const STATUS: Record<string, string> = {
  pending: "待审核",
  approved: "已上架",
  rejected: "已拒绝",
  offline: "已下架",
  sold: "已售出"
};

Page({
  data: {
    theme: "light",
    items: [] as any[],
    loading: false
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=my-products" });
      return;
    }
    this.load();
  },

  async load() {
    this.setData({ loading: true });
    try {
      const result = await myProducts();
      this.setData({
        items: (result.items || []).map((item) => ({
          ...item,
          image_url: assetUrl(item.image_url || ""),
          status_text: STATUS[item.status || ""] || item.status || "未知"
        }))
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  edit(event: any) {
    wx.setStorageSync("cm_edit_publish_id", Number(event.currentTarget.dataset.id));
    wx.switchTab({ url: "/pages/publish/publish" });
  },

  open(event: any) {
    if (event.currentTarget.dataset.status !== "approved") return;
    wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${event.currentTarget.dataset.id}` });
  },

  goPublish() {
    wx.switchTab({ url: "/pages/publish/publish" });
  }
});
