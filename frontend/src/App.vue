<script setup>
import { provide } from "vue";
import { useUiStore } from "./stores/ui.js";
import { createI18n, I18N_KEY } from "./i18n.js";
import AppSidebar from "./components/AppSidebar.vue";
import { X } from "lucide-vue-next";

const ui = useUiStore();
const i18n = createI18n();
provide(I18N_KEY, i18n);
</script>

<template>
  <div class="app-frame">
    <AppSidebar />
    <main class="main-content">
      <router-view />
    </main>

    <!-- Error toasts -->
    <div
      v-if="ui.errors.length"
      style="position:fixed;bottom:20px;right:20px;z-index:200;display:flex;flex-direction:column;gap:8px"
    >
      <div
        v-for="e in ui.errors" :key="e.id"
        class="error-banner"
        style="margin:0;display:flex;align-items:center;gap:10px;max-width:400px;box-shadow:var(--shadow-lg)"
      >
        <span style="flex:1">{{ e.msg }}</span>
        <button class="icon-button" style="width:24px;height:24px" @click="ui.clearError(e.id)">
          <X :size="14" />
        </button>
      </div>
    </div>
  </div>
</template>
