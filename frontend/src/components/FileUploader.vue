<script setup>
import { ref } from "vue";
import { useI18n } from "../i18n.js";
import { Upload, X, FileWarning } from "lucide-vue-next";

const emit = defineEmits(["close", "uploaded"]);
const { t } = useI18n();

const dragging = ref(false);
const uploading = ref(false);
const error = ref("");
const allowedExtensions = [".h5ad", ".h5mu", ".csv", ".tsv", ".txt", ".fastq", ".fq", ".fasta", ".fa"];

function validate(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!allowedExtensions.includes(ext)) {
    error.value = `${t("file.invalidType")}: ${ext}`;
    return false;
  }
  return true;
}

function onDragOver(e) {
  e.preventDefault();
  dragging.value = true;
}

function onDragLeave() {
  dragging.value = false;
}

async function onDrop(e) {
  e.preventDefault();
  dragging.value = false;
  const file = e.dataTransfer.files[0];
  if (file && validate(file)) {
    await doUpload(file);
  }
}

async function onFileChange(e) {
  const file = e.target.files[0];
  if (file && validate(file)) {
    await doUpload(file);
  }
}

async function doUpload(file) {
  uploading.value = true;
  error.value = "";
  try {
    emit("uploaded", file);
  } catch (e) {
    error.value = e.message;
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal-panel" style="width:min(440px,100%)">
      <div class="modal-header">
        <h3>{{ t("data.upload") }}</h3>
        <button class="icon-button" @click="emit('close')"><X :size="18" /></button>
      </div>
      <div class="modal-body">
        <div
          class="file-panel-upload"
          :style="{
            borderColor: dragging ? 'var(--accent-400)' : 'var(--border-color)',
            padding: '32px',
            margin: 0,
          }"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
        >
          <Upload v-if="!uploading" :size="28" style="margin-bottom:8px;color:var(--accent-500)" />
          <div v-if="uploading" class="loading-spinner" style="margin-bottom:8px"></div>
          <div style="font-weight:600;font-size:14px">
            {{ uploading ? t("file.uploading") : dragging ? t("file.dropHere") : t("file.upload") }}
          </div>
          <input
            type="file"
            style="position:absolute;inset:0;opacity:0;cursor:pointer"
            :accept="allowedExtensions.join(',')"
            @change="onFileChange"
            :disabled="uploading"
          />
          <div style="font-size:11px;color:var(--text-muted);margin-top:6px">
            .h5ad .h5mu .csv .tsv .fastq .fasta
          </div>
        </div>

        <div v-if="error" class="error-banner" style="margin:0;display:flex;align-items:center;gap:8px">
          <FileWarning :size="14" />
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>
