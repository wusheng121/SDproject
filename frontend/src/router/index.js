import { createRouter, createWebHistory } from "vue-router";

import Home from "../views/Home.vue";
import Search from "../views/Search.vue";
import MovieInfo from "../views/MovieInfo.vue";
import Register from "../views/Register.vue";
import Login from "../views/Login.vue";
import Favorites from "../views/Favorites.vue";
import Rate from "../views/Rate.vue";

const routes = [
  { path: "/", name: "Home", component: Home },
  { path: "/search", name: "Search", component: Search },
  { path: "/movies/:id", name: "MovieInfo", component: MovieInfo, props: true },
  { path: "/register", name: "Register", component: Register },
  { path: "/login", name: "Login", component: Login },
  { path: "/favorites", name: "Favorites", component: Favorites },
  { path: "/rate", name: "Rate", component: Rate }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;



