<script setup>
import { useRoute, useRouter } from "vue-router";
import { useUiStore } from "../stores/ui.js";
import { LayoutDashboard, Dna, FolderKanban, Settings, Sun, Moon } from "lucide-vue-next";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();

const navItems = [
  { path: "/overview", label: "概览", icon: LayoutDashboard },
  { path: "/workspace", label: "分析工作台", icon: Dna },
  { path: "/projects", label: "项目管理", icon: FolderKanban },
  { path: "/settings", label: "设置", icon: Settings },
];

function isActive(path) {
  return route.path.startsWith(path);
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand" @click="router.push('/')">
      <Dna :size="24" />
      <span class="brand-text">Omics Copilot</span>
    </div>

    <nav class="sidebar-nav">
      <button
        v-for="item in navItems" :key="item.path"
        class="nav-item" :class="{ active: isActive(item.path) }"
        @click="router.push(item.path)"
      >
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-footer">
      <button class="theme-toggle" @click="ui.toggleTheme()">
        <Sun :size="16" v-if="ui.theme === 'dark'" />
        <Moon :size="16" v-else />
        <span>{{ ui.theme === 'light' ? '暗色模式' : '亮色模式' }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px; min-width: 220px; height: 100vh;
  display: flex; flex-direction: column;
  background: var(--sidebar-bg, var(--gray-50));
  border-right: 1px solid var(--gray-100);
  padding: 16px 10px;
}
.sidebar-brand {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; margin-bottom: 20px; cursor: pointer;
  color: var(--accent-600);
}
.brand-text { font-size: 15px; font-weight: 700; }
.sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border: none; border-radius: 8px;
  background: transparent; cursor: pointer;
  font-size: 13px; color: var(--gray-600);
  transition: background .15s, color .15s;
}
.nav-item:hover { background: var(--gray-100); color: var(--gray-800); }
.nav-item.active { background: var(--accent-100); color: var(--accent-700); font-weight: 600; }
.sidebar-footer { padding-top: 12px; border-top: 1px solid var(--gray-100); }
.theme-toggle {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 8px 12px; border: none; border-radius: 8px;
  background: transparent; cursor: pointer;
  font-size: 12px; color: var(--gray-500);
}
.theme-toggle:hover { background: var(--gray-100); }
</style>
