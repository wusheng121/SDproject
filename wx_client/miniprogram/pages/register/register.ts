import { getCaptcha, register } from "../../utils/api";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    username: "",
    email: "",
    password: "",
    phone: "",
    captchaId: "",
    captchaImage: "",
    captchaCode: "",
    loading: false
  },

  onLoad() {
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

  goLogin() {
    wx.navigateBack();
  },

  async submit() {
    const { username, email, password, phone, captchaCode } = this.data;
    if (!username || !email || !password || !captchaCode) {
      wx.showToast({ title: "请填写完整信息", icon: "none" });
      return;
    }
    this.setData({ loading: true });
    try {
      await register({
        username,
        email,
        password,
        phone,
        captcha_id: this.data.captchaId,
        captcha_code: captchaCode
      });
      wx.showToast({ title: "注册成功，请登录", icon: "success" });
      setTimeout(() => wx.navigateBack(), 800);
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
      await this.loadCaptcha();
      this.setData({ captchaCode: "" });
    } finally {
      this.setData({ loading: false });
    }
  }
});
