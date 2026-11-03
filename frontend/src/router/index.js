import { createRouter, createWebHistory } from "vue-router";

import Home from "../views/Home.vue";
import Search from "../views/Search.vue";
import ProductDetail from "../views/ProductDetail.vue";
import Register from "../views/Register.vue";
import Login from "../views/Login.vue";
import ForgotPassword from "../views/ForgotPassword.vue";
import ResetPassword from "../views/ResetPassword.vue";
import VerifyEmail from "../views/VerifyEmail.vue";
import ChangePassword from "../views/ChangePassword.vue";
import Favorites from "../views/Favorites.vue";
import UserCenter from "../views/UserCenter.vue";
import ProductPublish from "../views/ProductPublish.vue";
import AdminPanel from "../views/AdminPanel.vue";
import UnifiedAssistant from "../views/UnifiedAssistant.vue";
import RecommendationTest from "../views/RecommendationTest.vue";
import Cart from "../views/Cart.vue";
import Orders from "../views/Orders.vue";
import Messages from "../views/Messages.vue";
import { useUserStore } from "../stores/user";

const routes = [
  { path: "/", name: "Home", component: Home },
  { path: "/search", name: "Search", component: Search },
  { path: "/product/:id", name: "ProductDetail", component: ProductDetail, props: true },
  {
    path: "/publish",
    name: "ProductPublish",
    component: ProductPublish,
    meta: { requiresAuth: true }
  },
  {
    path: "/admin",
    name: "AdminPanel",
    component: AdminPanel,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  { path: "/register", name: "Register", component: Register },
  { path: "/login", name: "Login", component: Login },
  { path: "/forgot-password", name: "ForgotPassword", component: ForgotPassword },
  { path: "/reset-password", name: "ResetPassword", component: ResetPassword },
  { path: "/verify-email", name: "VerifyEmail", component: VerifyEmail },
  {
    path: "/change-password",
    name: "ChangePassword",
    component: ChangePassword,
    meta: { requiresAuth: true }
  },
  {
    path: "/assistant",
    name: "Assistant",
    component: UnifiedAssistant,
    meta: { requiresAuth: true }
  },
  {
    path: "/agent-workbench",
    redirect: { path: "/assistant", query: { mode: "complex" } }
  },
  {
    path: "/favorites",
    name: "Favorites",
    component: Favorites,
    meta: { requiresAuth: true }
  },
  {
    path: "/recommendation-test",
    name: "RecommendationTest",
    component: RecommendationTest,
    meta: { requiresAuth: true }
  },
  {
    path: "/cart",
    name: "Cart",
    component: Cart,
    meta: { requiresAuth: true }
  },
  {
    path: "/orders",
    name: "Orders",
    component: Orders,
    meta: { requiresAuth: true }
  },
  {
    path: "/messages",
    name: "Messages",
    component: Messages,
    meta: { requiresAuth: true }
  },
  {
    path: "/user-center",
    name: "UserCenter",
    component: UserCenter,
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to) => {
  const userStore = useUserStore();
  if (!userStore.initialized) {
    await userStore.bootstrap();
  }
  if (to.meta?.requiresAuth && !userStore.token) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  if (to.meta?.requiresAdmin && !userStore.isAdmin) {
    return { path: "/" };
  }
  return true;
});

export default router;
