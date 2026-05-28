<script setup>
import { ref, onMounted } from "vue";
import { useI18n } from "../i18n.js";
import { useSettingsStore } from "../stores/settings.js";
import { useUiStore } from "../stores/ui.js";
import {
  Settings, Plus, Trash2, Check, Key, Globe, Cpu,
  Eye, EyeOff, Zap, Shield, ChevronDown, ChevronUp,
  Wifi, X,
} from "lucide-vue-next";

const { t } = useI18n();
const settingsStore = useSettingsStore();
const ui = useUiStore();

const showKey = ref({});
const expanded = ref({});
const testing = ref({});
const testResult = ref({});
const saveMsg = ref("");

onMounted(() => {
  settingsStore.load();
});

function addProfile(preset) {
  const id = preset.provider + "_" + Date.now();
  settingsStore.addProfile(preset);
  expanded.value[id] = true;
}

async function handleSave() {
  try {
    await settingsStore.save();
    saveMsg.value = "success";
    setTimeout(() => { saveMsg.value = ""; }, 2500);
  } catch (e) {
    saveMsg.value = "error";
    setTimeout(() => { saveMsg.value = ""; }, 3000);
  }
}

function handleSetActive(id) {
  settingsStore.setActive(id);
  settingsStore.save();
}

function handleRemove(id) {
  settingsStore.removeProfile(id);
  settingsStore.save();
  delete expanded.value[id];
  delete testResult.value[id];
}

function toggleKey(id) {
  showKey.value[id] = !showKey.value[id];
}

function toggleExpand(id) {
  expanded.value[id] = !expanded.value[id];
}

async function handleTest(profile) {
  const id = profile.id;
  testing.value[id] = true;
  testResult.value[id] = null;
  try {
    const result = await settingsStore.test(profile);
    testResult.value[id] = result;
  } catch (e) {
    testResult.value[id] = { ok: false, error: e.message };
  } finally {
    testing.value[id] = false;
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-header">
      <div>
        <h2>{{ t("settings.title") }}</h2>
        <p>{{ t("settings.subtitle") }}</p>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <span
          v-if="settingsStore.ready"
          class="chip chip-green"
        ><Zap :size="12" /> {{ t("settings.connected") }}</span>
        <span
          v-else
          class="chip chip-orange"
        >{{ t("settings.notConnected") }}</span>
      </div>
    </div>

    <!-- Save toast -->
    <div v-if="saveMsg" class="toast" :class="saveMsg === 'success' ? 'toast-success' : 'toast-error'">
      <Check v-if="saveMsg === 'success'" :size="16" />
      <X v-else :size="16" />
      <span>{{ saveMsg === 'success' ? t("settings.saveSuccess") : t("settings.saveFailed") }}</span>
    </div>

    <!-- Status -->
    <div v-if="settingsStore.activeProfile" class="section-card glass-panel" style="display:flex;align-items:center;gap:12px">
      <div class="stat-icon stat-icon-green" style="width:36px;height:36px">
        <Check :size="18" />
      </div>
      <div style="flex:1">
        <div style="font-weight:700;font-size:14px">{{ settingsStore.activeProfile.name }}</div>
        <div style="font-size:12px;color:var(--text-muted)">{{ settingsStore.activeProfile.model }}</div>
      </div>
    </div>

    <!-- Preset buttons -->
    <div class="section-card glass-panel">
      <h3 style="font-size:15px;font-weight:700;margin:0 0 14px">{{ t("settings.addProvider") }}</h3>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button
          v-for="preset in settingsStore.presets" :key="preset.provider"
          class="secondary-button"
          @click="addProfile(preset)"
        >
          <Plus :size="14" />
          {{ preset.name }}
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="settingsStore.profiles.length === 0" class="empty-state">
      <div class="empty-state-icon"><Settings :size="40" /></div>
      <h4>{{ t("settings.noProviders") }}</h4>
      <p>{{ t("settings.noProvidersHint") }}</p>
    </div>

    <!-- Profile list -->
    <div v-for="profile in settingsStore.profiles" :key="profile.id" class="section-card glass-panel">
      <!-- Header: always visible -->
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="display:flex;align-items:center;gap:10px">
          <div class="stat-icon stat-icon-blue" style="width:34px;height:34px">
            <Cpu :size="16" />
          </div>
          <div>
            <div style="font-weight:700;font-size:14px">{{ profile.name }}</div>
            <div style="font-size:11px;color:var(--text-muted)">{{ profile.provider }} — {{ profile.model }}</div>
          </div>
        </div>
        <div style="display:flex;gap:6px;align-items:center">
          <button
            v-if="settingsStore.activeProfileId !== profile.id"
            class="secondary-button"
            style="padding:6px 12px;font-size:12px"
            @click="handleSetActive(profile.id)"
          >
            {{ t("settings.setActive") }}
          </button>
          <button
            v-else
            class="chip chip-green"
            style="padding:6px 12px"
          >
            <Check :size="12" /> {{ t("settings.active") }}
          </button>
          <button class="icon-button" @click="toggleExpand(profile.id)">
            <ChevronDown v-if="!expanded[profile.id]" :size="16" />
            <ChevronUp v-else :size="16" />
          </button>
          <button class="icon-button" @click="handleRemove(profile.id)">
            <Trash2 :size="14" style="color:var(--color-error)" />
          </button>
        </div>
      </div>

      <!-- Test result -->
      <div
        v-if="testResult[profile.id]"
        class="test-result"
        :class="testResult[profile.id].ok ? 'test-success' : 'test-error'"
        style="margin-top:10px;padding:8px 12px;border-radius:8px;font-size:12px;display:flex;align-items:center;gap:8px"
      >
        <Check v-if="testResult[profile.id].ok" :size="14" style="color:var(--color-success)" />
        <X v-else :size="14" style="color:var(--color-error)" />
        <span>{{ testResult[profile.id].ok ? t("settings.testSuccess") : testResult[profile.id].error }}</span>
      </div>

      <!-- Expandable fields -->
      <div v-if="expanded[profile.id]" style="display:flex;flex-direction:column;gap:10px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border-color)">
        <div>
          <label class="field-label">
            <Key :size="12" /> {{ t("settings.apiKey") }}
          </label>
          <div style="display:flex;gap:6px">
            <input
              :type="showKey[profile.id] ? 'text' : 'password'"
              class="app-input"
              v-model="profile.api_key"
              :placeholder="'sk-...'"
              style="flex:1"
            />
            <button class="icon-button" @click="toggleKey(profile.id)">
              <component :is="showKey[profile.id] ? EyeOff : Eye" :size="14" />
            </button>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div>
            <label class="field-label">
              <Globe :size="12" /> {{ t("settings.baseUrl") }}
            </label>
            <input
              type="text"
              class="app-input"
              v-model="profile.base_url"
              placeholder="https://api.openai.com/v1"
            />
          </div>
          <div>
            <label class="field-label">
              <Cpu :size="12" /> {{ t("settings.model") }}
            </label>
            <input
              type="text"
              class="app-input"
              v-model="profile.model"
              placeholder="gpt-4o"
            />
          </div>
        </div>

        <div>
          <label class="field-label">{{ t("settings.name") }}</label>
          <input
            type="text"
            class="app-input"
            v-model="profile.name"
            :placeholder="t('settings.namePlaceholder')"
          />
        </div>

        <div style="display:flex;gap:8px">
          <button
            class="secondary-button"
            style="padding:8px 16px;font-size:13px"
            :disabled="testing[profile.id]"
            @click="handleTest(profile)"
          >
            <Wifi v-if="!testing[profile.id]" :size="14" />
            <span
              v-else
              class="spinner"
              style="width:14px;height:14px;border-width:2px"
            ></span>
            {{ testing[profile.id] ? t("settings.testing") : t("settings.testConnection") }}
          </button>
        </div>
      </div>
    </div>

    <!-- Save -->
    <div v-if="settingsStore.profiles.length > 0" style="display:flex;justify-content:flex-end">
      <button class="primary-button" @click="handleSave">
        <Shield :size="16" />
        {{ t("settings.save") }}
      </button>
    </div>
  </div>
</template>
