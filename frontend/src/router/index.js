import { createRouter, createWebHistory } from "vue-router";

import Home from "../views/Home.vue";
import Search from "../views/Search.vue";
import MovieInfo from "../views/MovieInfo.vue";
import Register from "../views/Register.vue";
import Login from "../views/Login.vue";
import Favorites from "../views/Favorites.vue";
import Rate from "../views/Rate.vue";
import MyRatings from "../views/MyRatings.vue";
import UserCenter from "../views/UserCenter.vue";
import MapExplore from "../views/MapExplore.vue";

const routes = [
  { path: "/", name: "Home", component: Home },
  { path: "/search", name: "Search", component: Search },
  { path: "/movies/:id", name: "MovieInfo", component: MovieInfo, props: true },
  { path: "/register", name: "Register", component: Register },
  { path: "/login", name: "Login", component: Login },
  { path: "/favorites", name: "Favorites", component: Favorites, meta: { requiresAuth: true } },
  { path: "/rate", name: "Rate", component: Rate, meta: { requiresAuth: true } },
  { path: "/my-ratings", name: "MyRatings", component: MyRatings, meta: { requiresAuth: true } },
  { path: "/user-center", name: "UserCenter", component: UserCenter, meta: { requiresAuth: true } },
  { path: "/map", name: "MapExplore", component: MapExplore }
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




