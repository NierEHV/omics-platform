<script setup>
import { useFilesStore } from "../stores/files.js";
import { useI18n } from "../i18n.js";
import { File, X, Upload, Database, Table } from "lucide-vue-next";
import FileUploader from "./FileUploader.vue";
import { ref } from "vue";

const filesStore = useFilesStore();
const { t } = useI18n();
const showUploader = ref(false);

function getFileIcon(ext) {
  if ([".h5ad", ".h5mu"].includes(ext)) return Database;
  if ([".csv", ".tsv"].includes(ext)) return Table;
  return File;
}

function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function onUploaded(file) {
  filesStore.upload(file);
  showUploader.value = false;
}
</script>

<template>
  <aside class="file-panel">
    <div class="file-panel-header">
      <h3>{{ t("data.title") }}</h3>
      <button class="icon-button" @click="showUploader = true">
        <Upload :size="16" />
      </button>
    </div>

    <div class="file-panel-list">
      <div v-if="filesStore.files.length === 0" style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">
        {{ t("data.empty") }}
      </div>
      <div
        v-for="file in filesStore.files" :key="file.name"
        class="file-panel-item"
        :class="{ active: filesStore.selectedFile?.name === file.name }"
        @click="filesStore.select(file)"
      >
        <component :is="getFileIcon(file.extension)" :size="16" style="color:var(--accent-600);flex-shrink:0" />
        <span class="file-panel-item-name">{{ file.name }}</span>
        <span class="file-panel-item-size">{{ formatSize(file.size) }}</span>
      </div>
    </div>

    <div
      class="file-panel-upload"
      @click="showUploader = true"
    >
      <Upload :size="18" style="margin-bottom:4px" />
      <div>{{ t("file.upload") }}</div>
    </div>

    <FileUploader
      v-if="showUploader"
      @close="showUploader = false"
      @uploaded="onUploaded"
    />
  </aside>
</template>
