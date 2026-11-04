import {
  assistantMessage,
  cancelAssistantAction,
  confirmAssistantAction
} from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { assetUrl } from "../../utils/config";
import { applyPageTheme } from "../../utils/theme";

const WELCOME = "你好，我是校园集市 AI 助手。可以帮你找商品、比较价格、推荐校园好物。";
const MAX_MESSAGE = 500;

function normalizeActions(actions: any[]): any[] {
  return (actions || []).map((action) => ({
    ...action,
    status: action.status || "pending",
    draft: action.type === "seller_message" ? (action.payload?.content || "") : "",
    loading: false
  }));
}

Page({
  data: {
    theme: "light",
    messages: [{ role: "assistant", content: WELCOME, items: [], actions: [] }] as any[],
    draft: "",
    sessionId: 0,
    sending: false,
    scrollTarget: "msg-0",
    prompts: ["1000 元以内的平板", "推荐适合新生的教材", "帮我比较手机和耳机"]
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=assistant" });
    }
  },

  onInput(event: any) {
    this.setData({ draft: event.detail.value });
  },

  usePrompt(event: any) {
    this.setData({ draft: event.currentTarget.dataset.text || "" });
    this.send();
  },

  reset() {
    this.setData({
      messages: [{ role: "assistant", content: WELCOME, items: [], actions: [] }],
      sessionId: 0,
      draft: "",
      scrollTarget: "msg-0"
    });
  },

  async send() {
    const content = this.data.draft.trim();
    if (!content || this.data.sending) return;
    const messages = this.data.messages.concat([{ role: "user", content, items: [], actions: [] }]);
    this.setData({
      messages,
      draft: "",
      sending: true,
      scrollTarget: `msg-${messages.length - 1}`
    });
    try {
      const result = await assistantMessage(content, this.data.sessionId);
      const reply = result.reply || "暂时没有找到合适的回复。";
      const items = (result.items || []).map((item) => ({
        ...item,
        image_url: assetUrl(item.image_url || "")
      }));
      const next = this.data.messages.concat([{
        role: "assistant",
        content: reply,
        items,
        actions: normalizeActions(result.action_proposals || [])
      }]);
      this.setData({
        messages: next,
        sessionId: result.session_id || this.data.sessionId,
        scrollTarget: `msg-${next.length - 1}`
      });
    } catch (error) {
      const next = this.data.messages.concat([{
        role: "assistant",
        content: (error as Error).message || "AI 暂时不可用，请稍后再试。",
        items: [],
        actions: []
      }]);
      this.setData({ messages: next, scrollTarget: `msg-${next.length - 1}` });
    } finally {
      this.setData({ sending: false });
    }
  },

  onActionInput(event: any) {
    const messageIndex = Number(event.currentTarget.dataset.messageIndex);
    const actionIndex = Number(event.currentTarget.dataset.actionIndex);
    this.setData({
      [`messages[${messageIndex}].actions[${actionIndex}].draft`]: event.detail.value
    });
  },

  async confirmAction(event: any) {
    const messageIndex = Number(event.currentTarget.dataset.messageIndex);
    const actionIndex = Number(event.currentTarget.dataset.actionIndex);
    const action = this.data.messages[messageIndex]?.actions?.[actionIndex];
    if (!action || action.loading || action.status !== "pending") return;

    const content = action.type === "seller_message" ? String(action.draft || "").trim() : "";
    if (action.type === "seller_message") {
      if (!content) {
        wx.showToast({ title: "请输入要发送的消息", icon: "none" });
        return;
      }
      if (content.length > MAX_MESSAGE) {
        wx.showToast({ title: "消息不能超过 500 字", icon: "none" });
        return;
      }
    }

    this.setData({ [`messages[${messageIndex}].actions[${actionIndex}].loading`]: true });
    try {
      await confirmAssistantAction(action.action_id, content);
      this.updateAction(messageIndex, actionIndex, {
        status: action.type === "cart_add" ? "已加入购物车" : "已发送",
        loading: false
      });
      wx.showToast({
        title: action.type === "cart_add" ? "已加入购物车" : "消息已发送",
        icon: "success"
      });
    } catch (error) {
      this.setData({ [`messages[${messageIndex}].actions[${actionIndex}].loading`]: false });
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  async cancelAction(event: any) {
    const messageIndex = Number(event.currentTarget.dataset.messageIndex);
    const actionIndex = Number(event.currentTarget.dataset.actionIndex);
    const action = this.data.messages[messageIndex]?.actions?.[actionIndex];
    if (!action || action.loading || action.status !== "pending") return;

    this.setData({ [`messages[${messageIndex}].actions[${actionIndex}].loading`]: true });
    try {
      await cancelAssistantAction(action.action_id);
      this.updateAction(messageIndex, actionIndex, { status: "已取消", loading: false });
      wx.showToast({ title: "操作已取消", icon: "none" });
    } catch (error) {
      this.setData({ [`messages[${messageIndex}].actions[${actionIndex}].loading`]: false });
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  updateAction(messageIndex: number, actionIndex: number, patch: Record<string, unknown>) {
    const updates: Record<string, unknown> = {};
    Object.keys(patch).forEach((key) => {
      updates[`messages[${messageIndex}].actions[${actionIndex}].${key}`] = patch[key];
    });
    this.setData(updates);
  },

  openProduct(event: any) {
    wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${event.currentTarget.dataset.id}` });
  }
});
