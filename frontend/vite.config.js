import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  build: {
    minify: false
  },
  server: {
    allowedHosts: [".ngrok-free.dev"],
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true
      },
      "/uploads": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true
      }
    }
  },
  preview: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true
      },
      "/uploads": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true
      }
    }
  }
});






















