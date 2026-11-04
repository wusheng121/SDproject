import {
  deleteProduct,
  editProduct,
  getPriceReference,
  listCategories,
  productDetail,
  publishProduct,
  recognizeListing,
  uploadProductImage
} from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

const CONDITIONS = ["全新", "几乎全新", "轻微使用", "明显使用", "重度使用"];
const TRADE_METHODS = ["校内面交", "快递寄送", "线上协商"];

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
          reject(new Error("图片大小不能超过 4MB"));
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
    loggedIn: false,
    editingId: 0,
    loaded: false,
    categories: [] as string[],
    conditions: CONDITIONS,
    tradeMethods: TRADE_METHODS,
    form: {
      name: "",
      brand: "",
      category: "",
      description: "",
      condition: "",
      defect_description: "",
      price: "",
      trade_method: "",
      trade_location: ""
    },
    selectedImage: "",
    imagePreview: "",
    savedImageUrl: "",
    aiTags: { category: "", condition: "" },
    priceReference: null as any,
    recognizing: false,
    loadingPrice: false,
    submitting: false
  },

  onLoad(options: any) {
    this.setData({ editingId: Number(options.id || 0) });
  },

  onShow() {
    applyPageTheme(this);
    const editId = Number(wx.getStorageSync("cm_edit_publish_id") || 0);
    if (editId) {
      wx.removeStorageSync("cm_edit_publish_id");
      this.setData({
        editingId: editId,
        loaded: false,
        selectedImage: "",
        imagePreview: "",
        savedImageUrl: "",
        priceReference: null
      });
    }
    const loggedIn = isLoggedIn();
    this.setData({ loggedIn });
    if (!loggedIn) return;
    this.prepare();
  },

  async prepare() {
    if (!this.data.loaded) {
      await this.loadCategories();
      if (this.data.editingId) await this.loadProduct();
      this.setData({ loaded: true });
    }
  },

  async loadCategories() {
    try {
      const result = await listCategories();
      this.setData({ categories: result.items || [] });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  async loadProduct() {
    try {
      const product = await productDetail(this.data.editingId);
      this.setData({
        form: {
          name: product.name || "",
          brand: product.brand || "",
          category: (product.categories || [])[0] || "",
          description: product.description || "",
          condition: product.condition || "",
          defect_description: product.defect_description || "",
          price: product.price ? String(product.price) : "",
          trade_method: product.trade_method || "",
          trade_location: product.trade_location || ""
        },
        savedImageUrl: product.image_url || "",
        imagePreview: assetUrl(product.image_url || "")
      });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  goLogin() {
    wx.navigateTo({ url: "/pages/login/login?redirect=publish" });
  },

  onInput(event: any) {
    const field = event.currentTarget.dataset.field;
    this.setData({ ["form." + field]: event.detail.value });
  },

  chooseCategory(event: any) {
    const category = this.data.categories[Number(event.detail.value)] || "";
    this.setData({ "form.category": category });
    this.loadPriceReference();
  },

  chooseCondition(event: any) {
    this.setData({ "form.condition": CONDITIONS[Number(event.detail.value)] || "" });
  },

  chooseTradeMethod(event: any) {
    this.setData({ "form.trade_method": TRADE_METHODS[Number(event.detail.value)] || "" });
  },

  async pickImage() {
    try {
      const path = await chooseImage();
      this.setData({ selectedImage: path, imagePreview: path });
    } catch (error) {
      if ((error as Error).message !== "取消选择图片") {
        wx.showToast({ title: (error as Error).message, icon: "none" });
      }
    }
  },

  async recognizeImage() {
    if (this.data.recognizing) return;
    let path = this.data.selectedImage;
    if (!path) {
      try {
        path = await chooseImage();
        this.setData({ selectedImage: path, imagePreview: path });
      } catch (error) {
        if ((error as Error).message !== "取消选择图片") {
          wx.showToast({ title: (error as Error).message, icon: "none" });
        }
        return;
      }
    }
    this.setData({ recognizing: true });
    try {
      const data = await recognizeListing(path);
      const recognition = data.recognition || {};
      if (!recognition || !Object.keys(recognition).length) {
        wx.showToast({ title: data.message || "没有识别出商品信息", icon: "none" });
        return;
      }
      const category = this.data.categories.includes(recognition.category) ? recognition.category : "";
      const condition = CONDITIONS.includes(recognition.condition) ? recognition.condition : "";
      this.setData({
        "form.name": recognition.name || this.data.form.name,
        "form.brand": recognition.brand || this.data.form.brand,
        "form.description": recognition.description || this.data.form.description,
        "form.category": category || this.data.form.category,
        "form.condition": condition || this.data.form.condition,
        aiTags: { category, condition }
      });
      if (category || this.data.form.category) await this.loadPriceReference();
      wx.showToast({ title: "已根据图片填充信息", icon: "success" });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ recognizing: false });
    }
  },

  async loadPriceReference() {
    if (!this.data.form.category) return;
    this.setData({ loadingPrice: true });
    try {
      const data = await getPriceReference(this.data.form.category);
      this.setData({ priceReference: data });
    } catch {
      this.setData({ priceReference: null });
    } finally {
      this.setData({ loadingPrice: false });
    }
  },

  validate(): string {
    const form = this.data.form;
    if (!form.name.trim()) return "请填写商品名称";
    if (!form.category) return "请选择商品分类";
    if (!form.condition) return "请选择商品成色";
    if (!form.description.trim()) return "请填写商品描述";
    const price = Number(form.price);
    if (!Number.isFinite(price) || price <= 0 || price > 100000) return "价格需大于 0 且不超过 100000";
    if (form.name.length > 80) return "商品名称不能超过 80 字";
    if (form.description.length > 1000) return "商品描述不能超过 1000 字";
    return "";
  },

  async submit() {
    if (this.data.submitting) return;
    const error = this.validate();
    if (error) {
      wx.showToast({ title: error, icon: "none" });
      return;
    }
    this.setData({ submitting: true });
    try {
      let imageUrl = this.data.savedImageUrl;
      if (this.data.selectedImage) {
        const uploaded = await uploadProductImage(this.data.selectedImage);
        imageUrl = uploaded.image_url;
      }
      const form = this.data.form;
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        brand: form.brand.trim(),
        category: form.category,
        description: form.description.trim(),
        condition: form.condition,
        defect_description: form.defect_description.trim(),
        has_notes: Boolean(form.defect_description.trim()),
        price: Number(form.price),
        trade_method: form.trade_method,
        trade_location: form.trade_location.trim(),
        image_url: imageUrl || undefined,
        ai_category: this.data.aiTags.category || undefined,
        ai_condition: this.data.aiTags.condition || undefined
      };
      if (this.data.editingId) {
        await editProduct(this.data.editingId, payload);
        this.resetForm();
        wx.showToast({ title: "商品已更新", icon: "success" });
        setTimeout(() => wx.switchTab({ url: "/pages/profile/profile" }), 600);
      } else {
        await publishProduct(payload);
        this.resetForm();
        wx.showToast({ title: "已提交审核", icon: "success" });
        setTimeout(() => wx.switchTab({ url: "/pages/index/index" }), 700);
      }
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ submitting: false });
    }
  },

  resetForm() {
    this.setData({
      editingId: 0,
      selectedImage: "",
      imagePreview: "",
      savedImageUrl: "",
      aiTags: { category: "", condition: "" },
      priceReference: null,
      form: {
        name: "",
        brand: "",
        category: "",
        description: "",
        condition: "",
        defect_description: "",
        price: "",
        trade_method: "",
        trade_location: ""
      }
    });
  },

  cancel() {
    this.resetForm();
    wx.navigateBack({ fail: () => wx.switchTab({ url: "/pages/index/index" }) });
  },

  remove() {
    if (!this.data.editingId) return;
    wx.showModal({
      title: "确认删除",
      content: "删除后无法恢复，已上架商品将直接下架。",
      success: async (result) => {
        if (!result.confirm) return;
        try {
          await deleteProduct(this.data.editingId);
          this.resetForm();
          wx.showToast({ title: "已处理", icon: "none" });
          setTimeout(() => wx.switchTab({ url: "/pages/profile/profile" }), 500);
        } catch (error) {
          wx.showToast({ title: (error as Error).message, icon: "none" });
        }
      }
    });
  }
});
