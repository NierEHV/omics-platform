import { defineStore } from "pinia";
import { ref, watch } from "vue";

export const useUiStore = defineStore("ui", () => {
  const theme = ref(localStorage.getItem("omics-copilot:theme") || "light");
  const sidebarCollapsed = ref(false);
  const errors = ref([]);
  const loading = ref(false);

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", theme.value);
  }

  watch(theme, (val) => {
    localStorage.setItem("omics-copilot:theme", val);
    applyTheme();
  }, { immediate: true });

  function toggleTheme() {
    theme.value = theme.value === "light" ? "dark" : "light";
  }

  function setError(msg, timeout = 6000) {
    const id = Date.now();
    errors.value.push({ id, msg });
    if (timeout > 0) {
      setTimeout(() => {
        errors.value = errors.value.filter((e) => e.id !== id);
      }, timeout);
    }
  }

  function clearError(id) {
    errors.value = errors.value.filter((e) => e.id !== id);
  }

  function setLoading(v) {
    loading.value = v;
  }

  return { theme, sidebarCollapsed, errors, loading, toggleTheme, setError, clearError, setLoading, applyTheme };
});
