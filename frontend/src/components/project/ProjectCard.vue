<template>
  <div class="glass-panel project-card" @click="$router.push('/workspace/' + project.id)">
    <div class="card-header">
      <h3 class="project-name">{{ project.name }}</h3>
      <StatusBadge :status="overallStatus" />
    </div>
    <div class="card-body">
      <span class="modality-tag">{{ modalityLabel }}</span>
      <span class="file-count">{{ project.files_count || 0 }} 个文件</span>
    </div>
    <div class="card-footer" v-if="project.progress">
      <div class="progress-bar"><div class="progress-fill" :style="{ width: project.progress.pct + '%' }" :class="{ done: project.progress.pct === 100, failed: project.progress.failed > 0 }"></div></div>
      <span class="progress-text">{{ project.progress.done }}/{{ project.progress.total }}</span>
    </div>
    <div class="card-time">{{ formatDate(project.created_at) }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
const props = defineProps({ project: Object, required: true })
const modalityLabels = { scrna: '单细胞转录组', bulk_rna: 'Bulk RNA-seq', spatial: '空间转录组', tcr: 'TCR 免疫组库', amplicon: '扩增子 16S', metagenomics: '宏基因组', proteomics: '蛋白质组' }
const modalityLabel = computed(() => modalityLabels[props.project.modality] || props.project.modality)
const overallStatus = computed(() => {
  if (!props.project.progress) return 'pending'
  if (props.project.progress.failed > 0) return 'failed'
  if (props.project.progress.running > 0) return 'running'
  if (props.project.progress.done === props.project.progress.total && props.project.progress.total > 0) return 'done'
  return 'pending'
})
function formatDate(d) { return d ? d.replace('T', ' ').substring(0, 16) : '' }
</script>

<style scoped>
.project-card { padding: 16px; cursor: pointer; transition: transform .15s; }
.project-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.project-name { font-size: 15px; font-weight: 600; margin: 0; color: var(--text-primary); }
.card-body { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; }
.modality-tag { font-size: 11px; padding: 1px 8px; border-radius: var(--border-radius-sm); background: var(--accent-100); color: var(--accent-700); }
.file-count { font-size: 12px; color: var(--text-secondary); }
.card-footer { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.progress-bar { flex: 1; height: 4px; background: var(--bg-tertiary); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent-500); border-radius: 2px; transition: width .3s; }
.progress-fill.done { background: var(--color-success); }
.progress-fill.failed { background: var(--color-error); }
.progress-text { font-size: 11px; color: var(--text-muted); min-width: 32px; text-align: right; }
.card-time { font-size: 11px; color: var(--text-muted); }
</style>
