import { defineStore } from "pinia";

import {
  apiLogin,
  apiLogout,
  apiProfile,
  apiRefresh,
  apiSavePreferences
} from "../api/user";
import { clearAccessToken, getAccessToken, setAccessToken } from "../api/token";

export const useUserStore = defineStore("user", {
  state: () => ({
    token: getAccessToken(),
    profile: null,
    initialized: false,
    bootstrapping: false
  }),
  getters: {
    username: (state) => state.profile?.username || "",
    isAdmin: (state) =>
      state.profile?.user_type === "admin" || (state.profile?.roles || []).includes("admin"),
    permissions: (state) => state.profile?.permissions || []
  },
  actions: {
    setSession(token, profile) {
      setAccessToken(token);
      this.token = token;
      this.profile = profile || this.profile;
    },
    async login({ identifier, password, remember }) {
      const resp = await apiLogin({ identifier, password, remember });
      const payload = resp?.data?.data || {};
      this.setSession(payload.access_token || "", payload.user || null);
      return resp;
    },
    async bootstrap() {
      if (this.initialized) return;
      if (this.bootstrapping) return;
      this.bootstrapping = true;
      try {
        const resp = await apiRefresh();
        const payload = resp?.data?.data || {};
        this.setSession(payload.access_token || "", payload.user || null);
      } catch {
        this.token = "";
        this.profile = null;
        clearAccessToken();
      } finally {
        this.initialized = true;
        this.bootstrapping = false;
      }
    },
    async logout() {
      try {
        await apiLogout();
      } catch {
        // best effort: the cookie may already be invalid
      }
      this.token = "";
      this.profile = null;
      this.initialized = true;
      clearAccessToken();
    },
    async fetchProfile() {
      const resp = await apiProfile();
      this.profile = resp?.data?.data?.user || null;
      return resp;
    },
    async savePreferences(categories) {
      return apiSavePreferences(categories);
    },
    hasPermission(permission) {
      return this.permissions.includes(permission);
    }
  }
});
