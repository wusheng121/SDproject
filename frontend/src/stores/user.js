import { defineStore } from "pinia";

import { apiLogin, apiProfile } from "../api/user";

export const useUserStore = defineStore("user", {
  state: () => ({
    token: localStorage.getItem("token") || "",
    profile: null
  }),
  actions: {
    async login({ identifier, password, remember }) {
      const resp = await apiLogin({ identifier, password, remember });
      const token = resp?.data?.token || "";
      this.token = token;
      if (token) localStorage.setItem("token", token);
      return resp;
    },
    logout() {
      this.token = "";
      this.profile = null;
      localStorage.removeItem("token");
    },
    async fetchProfile() {
      const resp = await apiProfile();
      this.profile = resp?.data || null;
      return resp;
    }
  }
});





