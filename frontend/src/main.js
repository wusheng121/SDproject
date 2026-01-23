import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import router from "./router";
import "./styles/global.css";
import { initTheme } from "./composables/useTheme";

// 初始化主题
initTheme();

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount("#app");






















