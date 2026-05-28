<template>
  <div class="modal-overlay" v-if="show" @click.self="$emit('close')">
    <div class="modal glass-panel">
      <h3>新建分析项目</h3>
      <div class="form-group"><label>项目名称</label><input v-model="name" placeholder="例如：PBMC3k 免疫分析" @keyup.enter="submit" /></div>
      <div class="form-group"><label>组学类型</label><select v-model="modality"><option value="scrna">单细胞转录组 (scRNA-seq)</option><option value="bulk_rna">Bulk RNA-seq</option><option value="spatial">空间转录组 (Spatial)</option><option value="tcr">TCR 免疫组库</option><option value="amplicon">扩增子 (16S rRNA)</option><option value="metagenomics">宏基因组</option><option value="proteomics">蛋白质组</option></select></div>
      <div class="form-group"><label>描述（可选）</label><textarea v-model="description" rows="2" placeholder="项目描述..."></textarea></div>
      <div class="modal-actions">
        <button class="secondary-button" @click="$emit('close')">取消</button>
        <button class="primary-button" @click="submit" :disabled="!name.trim()">创建项目</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ show: Boolean })
const emit = defineEmits(['close', 'create'])
const name = ref(''); const modality = ref('scrna'); const description = ref('')
function submit() { if (!name.value.trim()) return; emit('create', { name: name.value.trim(), modality: modality.value, description: description.value.trim() }); name.value = ''; description.value = '' }
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: var(--bg-modal-overlay); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal { width: 440px; padding: 24px; }
h3 { margin: 0 0 16px; font-size: 17px; color: var(--text-primary); }
.form-group { margin-bottom: 14px; }
label { display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary); }
input, select, textarea { width: 100%; padding: 8px 10px; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); font-size: 13px; background: var(--bg-input); color: var(--text-primary); }
textarea { resize: vertical; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>
