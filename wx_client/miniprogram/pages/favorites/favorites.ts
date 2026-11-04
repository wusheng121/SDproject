import { listFavorites, toggleFavorite } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    items: [] as any[],
    loading: false
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=favorites" });
      return;
    }
    this.load();
  },

  async load() {
    this.setData({ loading: true });
    try {
      const items = await listFavorites();
      this.setData({
        items: (items || []).map((item) => ({
          ...item,
          image_url: assetUrl(item.image_url || "")
        }))
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  openProduct(event: any) {
    wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${event.detail.id}` });
  },

  async remove(event: any) {
    const id = Number(event.currentTarget.dataset.id);
    try {
      await toggleFavorite(id, false);
      await this.load();
      wx.showToast({ title: "已取消收藏", icon: "none" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  }
});
