import { filterNl, listCategories, recognizeProduct, searchProducts } from "../../utils/api";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

const PAGE_SIZE = 12;

function chooseImage(): Promise<string> {
  return new Promise((resolve, reject) => {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album", "camera"],
      success: (result) => {
        const file = result.tempFiles[0];
        if (!file) {
          reject(new Error("未选择图片"));
          return;
        }
        if (file.size > 4 * 1024 * 1024) {
          reject(new Error("图片不能超过 4MB"));
          return;
        }
        resolve(file.tempFilePath);
      },
      fail: () => reject(new Error("取消选择图片"))
    });
  });
}

Page({
  data: {
    theme: "light",
    keyword: "",
    category: "",
    minPrice: "",
    maxPrice: "",
    condition: "",
    categories: [] as string[],
    products: [] as any[],
    total: 0,
    page: 1,
    hasMore: false,
    searched: false,
    loading: false,
    loadingMore: false,
    recognizing: false,
    parsing: false
  },

  onShow() {
    applyPageTheme(this);
  },

  async onLoad() {
    try {
      const categories = await listCategories();
      this.setData({ categories: categories.items || [] });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  onReachBottom() {
    this.loadMore();
  },

  onInput(event: any) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: event.detail.value });
  },

  chooseCategory(event: any) {
    const index = Number(event.detail.value);
    this.setData({ category: this.data.categories[index] || "" });
  },

  buildParams() {
    const params: Record<string, unknown> = {};
    if (this.data.keyword) params.q = this.data.keyword;
    if (this.data.category) params.category = this.data.category;
    if (this.data.minPrice) params.min_price = Number(this.data.minPrice);
    if (this.data.maxPrice) params.max_price = Number(this.data.maxPrice);
    if (this.data.condition) params.min_condition = this.data.condition;
    return params;
  },

  async aiParse() {
    const text = this.data.keyword.trim();
    if (!text) {
      wx.showToast({ title: "先输入一句筛选需求", icon: "none" });
      return;
    }
    this.setData({ parsing: true });
    try {
      const result = await filterNl(text);
      const filters = result.filters || {};
      this.setData({
        category: filters.category || this.data.category,
        condition: filters.min_condition || this.data.condition,
        minPrice: filters.min_price == null ? this.data.minPrice : String(filters.min_price),
        maxPrice: filters.max_price == null ? this.data.maxPrice : String(filters.max_price)
      });
      await this.search();
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ parsing: false });
    }
  },

  async aiImageSearch() {
    if (this.data.recognizing) return;
    let path = "";
    try {
      path = await chooseImage();
    } catch (error) {
      if ((error as Error).message !== "取消选择图片") {
        wx.showToast({ title: (error as Error).message, icon: "none" });
      }
      return;
    }
    this.setData({ recognizing: true });
    try {
      const result = await recognizeProduct(path);
      const recognition = result.recognition || {};
      if (recognition.category) {
        this.setData({ category: recognition.category, keyword: recognition.name || this.data.keyword });
      }
      await this.search();
      wx.showToast({ title: "已按图片识别结果搜索", icon: "success" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ recognizing: false });
    }
  },

  async search() {
    this.setData({ loading: true, searched: true, page: 1 });
    try {
      const result = await searchProducts({
        ...this.buildParams(),
        page: 1,
        page_size: PAGE_SIZE
      });
      const items = (result.items || []).map((item) => ({
        ...item,
        image_url: assetUrl(item.image_url || "")
      }));
      this.setData({
        products: items,
        total: result.total || items.length,
        page: 1,
        hasMore: items.length < (result.total || items.length)
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  async loadMore() {
    if (this.data.loading || this.data.loadingMore || !this.data.hasMore || !this.data.searched) return;
    const nextPage = this.data.page + 1;
    this.setData({ loadingMore: true });
    try {
      const result = await searchProducts({
        ...this.buildParams(),
        page: nextPage,
        page_size: PAGE_SIZE
      });
      const items = (result.items || []).map((item) => ({
        ...item,
        image_url: assetUrl(item.image_url || "")
      }));
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

  openAssistant() {
    wx.navigateTo({ url: "/pages/assistant/assistant" });
  },

  openProduct(event: any) {
    wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${event.detail.id}` });
  }
});
