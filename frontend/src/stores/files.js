import { defineStore } from "pinia";
import { ref } from "vue";
import { listFiles, uploadFile, deleteFile, getFileInfo } from "../api.js";
import { useUiStore } from "./ui.js";

export const useFilesStore = defineStore("files", () => {
  const ui = useUiStore();
  const files = ref([]);
  const selectedFile = ref(null);
  const selectedFileInfo = ref(null);

  async function load() {
    try {
      files.value = await listFiles();
    } catch (e) {
      ui.setError(e.message);
    }
  }

  async function upload(file) {
    try {
      const info = await uploadFile(file);
      files.value.unshift(info);
      return info;
    } catch (e) {
      ui.setError(e.message);
      throw e;
    }
  }

  async function remove(filename) {
    try {
      await deleteFile(filename);
      files.value = files.value.filter((f) => f.name !== filename);
      if (selectedFile.value?.name === filename) {
        selectedFile.value = null;
        selectedFileInfo.value = null;
      }
    } catch (e) {
      ui.setError(e.message);
    }
  }

  async function inspect(filename) {
    try {
      selectedFileInfo.value = await getFileInfo(filename);
      selectedFile.value = files.value.find((f) => f.name === filename) || null;
    } catch (e) {
      ui.setError(e.message);
    }
  }

  function select(file) {
    selectedFile.value = file;
    if (file) inspect(file.name);
  }

  return { files, selectedFile, selectedFileInfo, load, upload, remove, inspect, select };
});
