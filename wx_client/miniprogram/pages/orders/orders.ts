import { cancelOrder, getOrders, payOrder, reviewOrder } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { formatTime } from "../../utils/format";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    orders: [] as any[],
    loading: false,
    reviewVisible: false,
    reviewTarget: null as any,
    reviewScore: 5,
    reviewComment: "",
    reviewLoading: false
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=orders" });
      return;
    }
    this.load();
  },

  async load() {
    this.setData({ loading: true });
    try {
      const result = await getOrders();
      this.setData({
        orders: (result.items || []).map((order) => ({
          ...order,
          created_at: formatTime(order.created_at),
          status_text: this.statusText(order.status)
        }))
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  statusText(status: string) {
    return ({ pending: "待支付", paid: "已支付", cancelled: "已取消" } as Record<string, string>)[status] || status;
  },

  async pay(event: any) {
    const id = Number(event.currentTarget.dataset.id);
    try {
      await payOrder(id);
      wx.showToast({ title: "模拟支付成功", icon: "success" });
      await this.load();
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  async cancel(event: any) {
    const id = Number(event.currentTarget.dataset.id);
    try {
      await cancelOrder(id);
      wx.showToast({ title: "订单已取消", icon: "none" });
      await this.load();
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  openReview(event: any) {
    const dataset = event.currentTarget.dataset;
    this.setData({
      reviewVisible: true,
      reviewTarget: {
        orderId: Number(dataset.orderId),
        productId: Number(dataset.productId),
        name: dataset.name || "商品"
      },
      reviewScore: 5,
      reviewComment: ""
    });
  },

  closeReview() {
    this.setData({ reviewVisible: false, reviewTarget: null, reviewComment: "" });
  },

  chooseScore(event: any) {
    this.setData({ reviewScore: Number(event.currentTarget.dataset.score) });
  },

  onReviewInput(event: any) {
    this.setData({ reviewComment: event.detail.value });
  },

  stop() {},

  async submitReview() {
    const target = this.data.reviewTarget;
    if (!target || this.data.reviewLoading) return;
    if (this.data.reviewComment.length > 500 || this.data.reviewComment.includes("<")) {
      wx.showToast({ title: "评价不能超过 500 字且不能包含 HTML 标签", icon: "none" });
      return;
    }
    this.setData({ reviewLoading: true });
    try {
      await reviewOrder(target.orderId, target.productId, this.data.reviewScore, this.data.reviewComment.trim());
      wx.showToast({ title: "评价已提交", icon: "success" });
      this.setData({ reviewVisible: false, reviewTarget: null });
      await this.load();
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ reviewLoading: false });
    }
  }
});
