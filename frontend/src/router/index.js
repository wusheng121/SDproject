import { createRouter, createWebHistory } from "vue-router";

import Home from "../views/Home.vue";
import Search from "../views/Search.vue";
import ProductDetail from "../views/ProductDetail.vue";
import Register from "../views/Register.vue";
import Login from "../views/Login.vue";
import Favorites from "../views/Favorites.vue";
import UserCenter from "../views/UserCenter.vue";
import ProductPublish from "../views/ProductPublish.vue";
import AdminPanel from "../views/AdminPanel.vue";

const routes = [
  { path: "/", name: "Home", component: Home },
  { path: "/search", name: "Search", component: Search },
  { path: "/product/:id", name: "ProductDetail", component: ProductDetail, props: true },
  { path: "/publish", name: "ProductPublish", component: ProductPublish, meta: { requiresAuth: true } },
  { path: "/admin", name: "AdminPanel", component: AdminPanel, meta: { requiresAuth: true } },
  { path: "/register", name: "Register", component: Register },
  { path: "/login", name: "Login", component: Login },
  { path: "/favorites", name: "Favorites", component: Favorites, meta: { requiresAuth: true } },
  { path: "/user-center", name: "UserCenter", component: UserCenter, meta: { requiresAuth: true } }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;

router.beforeEach((to) => {
  if (to.meta?.requiresAuth) {
    const token = localStorage.getItem("token");
    if (!token) return { path: "/login" };
  }
  return true;
});




