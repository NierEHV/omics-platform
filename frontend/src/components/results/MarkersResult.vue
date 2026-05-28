<template>
  <div>
    <div style="max-height:400px;overflow-y:auto;margin-bottom:12px" v-if="markers.length > 0">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr><th style="position:sticky;top:0;background:var(--bg-tertiary);padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:var(--text-secondary)">Cluster</th><th style="position:sticky;top:0;background:var(--bg-tertiary);padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:var(--text-secondary)">Rank</th><th style="position:sticky;top:0;background:var(--bg-tertiary);padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:var(--text-secondary)">Gene</th><th style="position:sticky;top:0;background:var(--bg-tertiary);padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:var(--text-secondary)">logFC</th><th style="position:sticky;top:0;background:var(--bg-tertiary);padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:var(--text-secondary)">pval_adj</th></tr></thead>
        <tbody><tr v-for="(m, i) in markers" :key="i"><td style="padding:6px 10px;border-bottom:1px solid var(--border-color)">{{ m.group }}</td><td style="padding:6px 10px;border-bottom:1px solid var(--border-color)">{{ m.rank }}</td><td style="padding:6px 10px;border-bottom:1px solid var(--border-color);font-weight:600;font-style:italic;color:var(--accent-600)">{{ m.gene }}</td><td style="padding:6px 10px;border-bottom:1px solid var(--border-color)">{{ fmt(m.logfoldchange) }}</td><td style="padding:6px 10px;border-bottom:1px solid var(--border-color)">{{ fp(m.pval_adj) }}</td></tr></tbody>
      </table>
    </div>
    <div v-if="markers.length > 0" style="padding:24px;text-align:center;background:var(--bg-tertiary);border-radius:var(--border-radius-md);border:2px dashed var(--border-color);color:var(--text-muted)"><p>热图占位 — Top 5 标记基因 per Cluster</p></div>
    <div v-else style="text-align:center;padding:40px;color:var(--text-muted)"><p>暂无标记基因数据</p></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ node: Object, nodeState: Object })
const markers = computed(() => { const r = props.nodeState?.result; if (!r) return []; const d = typeof r === 'string' ? tryParse(r) : r; return d?.top_markers || [] })
function tryParse(v) { try { return JSON.parse(v) } catch { return v } }
function fmt(v) { return v != null ? Number(v).toFixed(3) : '-' }
function fp(v) { return v != null ? Number(v).toExponential(2) : '-' }
</script>
