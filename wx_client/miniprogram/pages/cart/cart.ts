import { createOrder, getCart, removeCart } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    items: [] as any[],
    total: 0,
    loading: false
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=cart" });
      return;
    }
    this.load();
  },

  async load() {
    this.setData({ loading: true });
    try {
      const cart = await getCart();
      this.setData({
        items: (cart.items || []).map((item) => ({
          ...item,
          image_url: assetUrl(item.image_url || "")
        })),
        total: cart.total_amount || 0
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async remove(event: any) {
    const id = Number(event.currentTarget.dataset.id);
    try {
      await removeCart(id);
      await this.load();
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  async checkout() {
    if (!this.data.items.length) return;
    try {
      await createOrder(this.data.items.map((item) => item.product_id));
      wx.showToast({ title: "订单已创建", icon: "success" });
      wx.switchTab({ url: "/pages/orders/orders" });
      this.load();
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  openProduct(event: any) {
    wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${event.currentTarget.dataset.id}` });
  }
});
