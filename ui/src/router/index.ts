import { createRouter, createWebHistory } from "vue-router";
import DashboardPages from "../pages/DashboardPages.vue";

// 注意：方案 A 下页面入口挂在 /ui/
export const router = createRouter({
  history: createWebHistory("/ui/"),
  routes: [
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: DashboardPages },
  ],
});

