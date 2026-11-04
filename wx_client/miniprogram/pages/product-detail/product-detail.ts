import { addCart, openConversation, productDetail, productReviews, toggleFavorite } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    id: 0,
    product: null as any,
    reviews: [] as any[],
    loading: false,
    favorite: false
  },

  onShow() {
    applyPageTheme(this);
  },

  onLoad(options: any) {
    const id = Number(options.id);
    this.setData({ id });
    this.load(id);
  },

  async load(id: number) {
    this.setData({ loading: true });
    try {
      const [product, reviews] = await Promise.all([
        productDetail(id),
        productReviews(id).catch(() => ({ items: [] }))
      ]);
      this.setData({
        product: { ...product, image_url: assetUrl(product.image_url || "") },
        reviews: reviews.items || [],
        favorite: Boolean(product.is_favorited)
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  requireLogin(): boolean {
    if (isLoggedIn()) return true;
    wx.navigateTo({ url: "/pages/login/login?redirect=back" });
    return false;
  },

  async favorite() {
    if (!this.requireLogin()) return;
    try {
      await toggleFavorite(this.data.id, !this.data.favorite);
      this.setData({ favorite: !this.data.favorite });
      wx.showToast({ title: this.data.favorite ? "已收藏" : "已取消收藏", icon: "none" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  async addToCart() {
    if (!this.requireLogin()) return;
    try {
      await addCart(this.data.id);
      wx.showToast({ title: "已加入购物车", icon: "success" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  async contactSeller() {
    if (!this.requireLogin()) return;
    try {
      const conversation = await openConversation(this.data.id);
      wx.navigateTo({ url: `/pages/messages/messages?id=${conversation.id}` });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  }
});
