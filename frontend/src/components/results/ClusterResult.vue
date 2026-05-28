<template>
  <div>
    <div class="step-grid" v-if="resultData">
      <div class="stat-tile glass-panel" style="flex-direction:column;text-align:center;padding:12px"><span style="font-size:22px;font-weight:700;color:var(--accent-600)">{{ resultData.n_clusters || '?' }}</span><span style="font-size:11px;color:var(--text-secondary);margin-top:2px">聚类数量</span></div>
      <div class="stat-tile glass-panel" style="flex-direction:column;text-align:center;padding:12px"><span style="font-size:22px;font-weight:700;color:var(--accent-600)">{{ params?.resolution || 1.0 }}</span><span style="font-size:11px;color:var(--text-secondary);margin-top:2px">分辨率</span></div>
    </div>
    <div style="padding:40px;text-align:center;background:var(--bg-tertiary);border-radius:var(--border-radius-md);border:2px dashed var(--border-color);color:var(--text-muted)"><p>UMAP 按簇着色 + 簇大小柱状图</p><p style="font-size:11px;margin-top:6px">接入真实图表后将展示聚类结果的空间分布</p></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ node: Object, nodeState: Object })
const resultData = computed(() => { const r = props.nodeState?.result; return r ? (typeof r === 'string' ? tryParse(r) : r) : null })
const params = computed(() => { const p = props.nodeState?.params; return p ? (typeof p === 'string' ? tryParse(p) : p) : null })
function tryParse(v) { try { return JSON.parse(v) } catch { return v } }
</script>
