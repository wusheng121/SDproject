import { getRecommendations, listCategories, listProducts, searchProducts } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

const PAGE_SIZE = 12;

Page({
  data: {
    theme: "light",
    loggedIn: false,
    products: [] as any[],
    recommendations: [] as any[],
    recommendationMeta: {} as any,
    recommendationOffset: 0,
    recommendationLoading: false,
    categories: [] as string[],
    quickCategories: [] as any[],
    activeCategory: "",
    totalProducts: 0,
    page: 1,
    hasMore: false,
    loading: false,
    loadingMore: false
  },

  onShow() {
    applyPageTheme(this);
    this.setData({ loggedIn: isLoggedIn() });
    this.load();
    this.loadRecommendations(0);
  },

  onReachBottom() {
    this.loadMore();
  },

  async load() {
    this.setData({ loading: true, page: 1 });
    try {
      const [products, categories] = await Promise.all([
        listProducts(1, PAGE_SIZE),
        listCategories()
      ]);
      const names = categories.items || [];
      this.setData({
        products: this.withImages(products.items || []),
        totalProducts: products.total || (products.items || []).length,
        page: 1,
        hasMore: (products.items || []).length < (products.total || 0),
        activeCategory: "",
        categories: names,
        quickCategories: names.slice(0, 6).map((name) => ({
          name,
          short: name.slice(0, 1),
          note: "校园好物"
        }))
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadMore() {
    if (this.data.loading || this.data.loadingMore || !this.data.hasMore) return;
    const nextPage = this.data.page + 1;
    this.setData({ loadingMore: true });
    try {
      const result = this.data.activeCategory
        ? await searchProducts({ category: this.data.activeCategory, page: nextPage, page_size: PAGE_SIZE })
        : await listProducts(nextPage, PAGE_SIZE);
      const items = this.withImages(result.items || []);
      const products = this.data.products.concat(items);
      this.setData({
        products,
        page: nextPage,
        hasMore: products.length < (result.total || products.length)
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loadingMore: false });
    }
  },

  async chooseCategory(event: any) {
    const category = event.currentTarget.dataset.category || "";
    this.setData({ activeCategory: category, page: 1, loading: true });
    try {
      const products = category
        ? await searchProducts({ category, page: 1, page_size: PAGE_SIZE })
        : await listProducts(1, PAGE_SIZE);
      const items = this.withImages(products.items || []);
      this.setData({
        products: items,
        page: 1,
        hasMore: items.length < (products.total || items.length)
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadRecommendations(offset = 0) {
    if (!isLoggedIn()) {
      this.setData({ recommendations: [], recommendationMeta: {}, loggedIn: false });
      return;
    }
    this.setData({ recommendationLoading: true, loggedIn: true });
    try {
      const result = await getRecommendations(6, offset);
      this.setData({
        recommendations: this.withImages(result.items || []),
        recommendationMeta: result,
        recommendationOffset: offset
      });
    } catch (error) {
      this.setData({ recommendations: [], recommendationMeta: {} });
    } finally {
      this.setData({ recommendationLoading: false });
    }
  },

  refreshRecommendations() {
    const nextOffset = this.data.recommendationOffset + 6;
    const total = Number(this.data.recommendationMeta.candidate_count || 0);
    this.loadRecommendations(nextOffset >= total ? 0 : nextOffset);
  },

  withImages(items: any[]) {
    return items.map((item) => ({
      ...item,
      image_url: assetUrl(item.image_url || "")
    }));
  },

  openSearch() {
    wx.navigateTo({ url: "/pages/search/search" });
  },

  openAssistant() {
    wx.navigateTo({ url: "/pages/assistant/assistant" });
  },

  openPublish() {
    wx.switchTab({ url: "/pages/publish/publish" });
  },

  openProduct(event: any) {
    wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${event.detail.id}` });
  }
});
