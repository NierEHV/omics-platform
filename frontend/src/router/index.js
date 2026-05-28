import { createRouter, createWebHashHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/overview" },
  { path: "/overview", name: "overview", component: () => import("../pages/OverviewPage.vue") },
  { path: "/workspace", name: "workspace", component: () => import("../pages/WorkspacePage.vue") },
  { path: "/workspace/:id", name: "workspace-project", component: () => import("../pages/WorkspacePage.vue") },
  { path: "/projects", name: "projects", component: () => import("../pages/ProjectsPage.vue") },
  { path: "/settings", name: "settings", component: () => import("../pages/SettingsPage.vue") },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
