import { defineStore } from "pinia";
import { ref } from "vue";
import { getSettings, updateSettings, getPresets, getSettingsStatus, testConnection } from "../api.js";
import { useUiStore } from "./ui.js";

export const useSettingsStore = defineStore("settings", () => {
  const ui = useUiStore();
  const profiles = ref([]);
  const activeProfileId = ref(null);
  const presets = ref([]);
  const ready = ref(false);
  const activeProfile = ref(null);

  async function load() {
    try {
      const data = await getSettings();
      profiles.value = data.profiles || [];
      activeProfileId.value = data.active_profile_id || null;
      const p = await getPresets();
      presets.value = p;
      const s = await getSettingsStatus();
      ready.value = s.ready;
      activeProfile.value = s.active_profile || null;
    } catch (e) {
      ui.setError(e.message);
    }
  }

  async function save() {
    try {
      const result = await updateSettings({
        profiles: profiles.value,
        active_profile_id: activeProfileId.value,
      });
      ready.value = result.ready;
    } catch (e) {
      ui.setError(e.message);
    }
  }

  function addProfile(preset) {
    const id = preset.provider + "_" + Date.now();
    profiles.value.push({
      id,
      provider: preset.provider,
      name: preset.name,
      base_url: preset.base_url,
      model: preset.model,
      api_key: "",
    });
  }

  function removeProfile(id) {
    profiles.value = profiles.value.filter((p) => p.id !== id);
    if (activeProfileId.value === id) {
      activeProfileId.value = null;
      activeProfile.value = null;
      ready.value = false;
    }
  }

  function setActive(id) {
    activeProfileId.value = id;
  }

  async function test(profile) {
    const result = await testConnection({
      api_key: profile.api_key,
      base_url: profile.base_url,
      model: profile.model,
    });
    return result;
  }

  return { profiles, activeProfileId, presets, ready, activeProfile, load, save, addProfile, removeProfile, setActive, test };
});
