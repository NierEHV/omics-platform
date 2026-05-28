<template>
  <div>
    <div class="step-grid" v-if="resultData">
      <div class="stat-tile glass-panel" style="flex-direction:column;text-align:center;padding:12px"><span style="font-size:22px;font-weight:700;color:var(--accent-600)">{{ resultData.n_obs || '?' }}</span><span style="font-size:11px;color:var(--text-secondary);margin-top:2px">过滤后细胞数</span></div>
      <div class="stat-tile glass-panel" style="flex-direction:column;text-align:center;padding:12px"><span style="font-size:22px;font-weight:700;color:var(--accent-600)">{{ resultData.n_vars || '?' }}</span><span style="font-size:11px;color:var(--text-secondary);margin-top:2px">过滤后基因数</span></div>
      <div class="stat-tile glass-panel" style="flex-direction:column;text-align:center;padding:12px"><span style="font-size:22px;font-weight:700;color:var(--accent-600)">{{ elapsed || '-' }}</span><span style="font-size:11px;color:var(--text-secondary);margin-top:2px">耗时</span></div>
    </div>
    <div style="padding:40px;text-align:center;background:var(--bg-tertiary);border-radius:var(--border-radius-md);border:2px dashed var(--border-color);color:var(--text-muted)">
      <p>Violin Plot — n_genes_by_counts | total_counts | pct_counts_mt</p>
      <p style="font-size:11px;margin-top:6px">图表接入后此处将展示 QC 过滤前后的分布对比</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ node: Object, nodeState: Object })
const resultData = computed(() => { const r = props.nodeState?.result; return r ? (typeof r === 'string' ? tryParse(r) : r) : null })
const elapsed = computed(() => { const s = props.nodeState?.started_at; const f = props.nodeState?.finished_at; if (!s || !f) return null; const ms = new Date(f) - new Date(s); return ms > 0 ? (ms / 1000).toFixed(1) + 's' : null })
function tryParse(v) { try { return JSON.parse(v) } catch { return v } }
</script>
