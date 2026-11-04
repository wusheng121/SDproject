import { getCaptcha, miniLogin } from "../../utils/api";
import { setSession } from "../../utils/auth";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    redirect: "",
    identifier: "",
    password: "",
    captchaId: "",
    captchaImage: "",
    captchaCode: "",
    loading: false
  },

  onLoad(options: any) {
    this.setData({ redirect: options.redirect || "" });
    this.loadCaptcha();
  },

  onShow() {
    applyPageTheme(this);
  },

  async loadCaptcha() {
    try {
      const captcha = await getCaptcha();
      this.setData({ captchaId: captcha.captcha_id, captchaImage: captcha.image });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  onInput(event: any) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: event.detail.value });
  },

  async submit() {
    if (!this.data.identifier || !this.data.password || !this.data.captchaCode) {
      wx.showToast({ title: "请填写账号、密码和验证码", icon: "none" });
      return;
    }
    this.setData({ loading: true });
    try {
      const data = await miniLogin({
        identifier: this.data.identifier,
        password: this.data.password,
        captcha_id: this.data.captchaId,
        captcha_code: this.data.captchaCode
      });
      setSession(data);
      if (data.user?.must_change_password) {
        wx.showModal({
          title: "需要修改密码",
          content: "当前账号需要修改初始密码，请在 PC 端完成操作。",
          showCancel: false
        });
      }
      if (this.data.redirect === "publish") {
        wx.switchTab({ url: "/pages/publish/publish" });
      } else if (this.data.redirect === "cart") {
        wx.switchTab({ url: "/pages/cart/cart" });
      } else if (this.data.redirect === "orders") {
        wx.switchTab({ url: "/pages/orders/orders" });
      } else if (this.data.redirect === "favorites") {
        wx.navigateTo({ url: "/pages/favorites/favorites" });
      } else if (this.data.redirect === "my-products") {
        wx.navigateTo({ url: "/pages/my-products/my-products" });
      } else if (this.data.redirect === "settings") {
        wx.navigateTo({ url: "/pages/settings/settings" });
      } else if (this.data.redirect === "assistant") {
        wx.navigateTo({ url: "/pages/assistant/assistant" });
      } else if (this.data.redirect === "messages") {
        wx.navigateTo({ url: "/pages/messages/messages" });
      } else if (this.data.redirect === "back") {
        wx.navigateBack({ fail: () => wx.switchTab({ url: "/pages/index/index" }) });
      } else {
        wx.switchTab({ url: "/pages/index/index" });
      }
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
      await this.loadCaptcha();
      this.setData({ captchaCode: "" });
    } finally {
      this.setData({ loading: false });
    }
  },

  goRegister() {
    wx.navigateTo({ url: "/pages/register/register" });
  }
});
