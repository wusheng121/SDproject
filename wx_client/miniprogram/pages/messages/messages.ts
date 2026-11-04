import { conversationMessages, listConversations, sendMessage } from "../../utils/api";
import { isLoggedIn } from "../../utils/auth";
import { applyPageTheme } from "../../utils/theme";

Page({
  data: {
    theme: "light",
    conversations: [] as any[],
    current: null as any,
    messages: [] as any[],
    draft: "",
    targetId: 0,
    loading: false
  },

  onLoad(options: any) {
    this.setData({ targetId: Number(options.id || 0) });
  },

  onShow() {
    applyPageTheme(this);
    if (!isLoggedIn()) {
      wx.redirectTo({ url: "/pages/login/login?redirect=messages" });
      return;
    }
    this.loadConversations();
  },

  async loadConversations() {
    try {
      const conversations = await listConversations();
      this.setData({ conversations: conversations || [] });
      if (this.data.targetId) {
        const current = (conversations || []).find((item) => item.id === this.data.targetId)
          || { id: this.data.targetId, peer_name: "卖家", product_name: "商品会话" };
        this.setData({ current, targetId: 0 });
        await this.loadMessages(current.id);
      }
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  },

  selectConversation(event: any) {
    const current = this.data.conversations[Number(event.currentTarget.dataset.index)];
    if (!current) return;
    this.setData({ current });
    this.loadMessages(current.id);
  },

  async loadMessages(id: number) {
    this.setData({ loading: true });
    try {
      const messages = await conversationMessages(id);
      this.setData({ messages: messages || [] });
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  onInput(event: any) {
    this.setData({ draft: event.detail.value });
  },

  async send() {
    const content = this.data.draft.trim();
    if (!this.data.current || !content) return;
    try {
      await sendMessage(this.data.current.id, content);
      this.setData({ draft: "" });
      await this.loadMessages(this.data.current.id);
    } catch (error) {
      wx.showToast({ title: (error as Error).message, icon: "none" });
    }
  }
});
