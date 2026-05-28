<template>
  <div class="result-panel">
    <div v-if="!selectedNode" class="result-empty"><p>点击流程图中的节点查看分析结果</p></div>
    <template v-else>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
        <h4 style="margin:0;font-size:16px;color:var(--text-primary)">{{ selectedNode.label || nodeId }}</h4>
        <StatusBadge :status="nodeState?.status || 'pending'" />
      </div>
      <component :is="resultComponent" v-if="resultComponent" :node="selectedNode" :node-state="nodeState" :node-id="nodeId" />
      <div v-else-if="nodeState?.status === 'done' && nodeState?.result">
        <div class="result-kv"><span>状态</span><span class="kv-val success">成功</span></div>
        <div class="result-kv" v-for="(v,k) in displayFields" :key="k"><span>{{ k }}</span><span class="kv-val">{{ v }}</span></div>
        <div class="result-kv" v-if="displayMsg"><span>详情</span><span class="kv-val msg">{{ displayMsg }}</span></div>
      </div>
      <div v-else-if="nodeState?.status === 'failed'" class="error-banner" style="margin:0"><p>{{ nodeState?.error_msg || '未知错误' }}</p></div>
      <div v-else class="result-placeholder"><p>此节点尚未执行。点击右侧面板的"运行此节点"开始分析。</p></div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import QcResult from './QcResult.vue'
import ClusterResult from './ClusterResult.vue'
import MarkersResult from './MarkersResult.vue'

const props = defineProps({ selectedNode: Object, nodeId: String, nodeState: Object })

const componentMap = { qc: QcResult, cluster: ClusterResult, markers: MarkersResult }

const resultComponent = computed(() => componentMap[props.nodeId] || null)

const resultObj = computed(() => {
  const r = props.nodeState?.result
  if (!r) return null
  return typeof r === 'string' ? tryParse(r) : r
})

const displayFields = computed(() => {
  if (!resultObj.value) return {}
  const skip = ['status', 'msg', 'output', 'top_markers']
  const out = {}
  for (const [k, v] of Object.entries(resultObj.value)) {
    if (!skip.includes(k)) out[k] = typeof v === 'object' ? JSON.stringify(v).slice(0, 100) : v
  }
  return out
})

const displayMsg = computed(() => resultObj.value?.msg || '')

function tryParse(v) { try { return JSON.parse(v) } catch { return v } }
</script>

<style scoped>
.result-panel { padding: 16px; min-height: 150px; }
.result-empty { text-align: center; padding: 40px 0; color: var(--text-muted); }
.result-kv { display: flex; align-items: flex-start; gap: 12px; padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size: 13px; }
.result-kv span:first-child { color: var(--text-muted); min-width: 80px; font-weight: 500; }
.kv-val { color: var(--text-primary); word-break: break-all; }
.kv-val.success { color: var(--color-success); font-weight: 600; }
.kv-val.msg { font-size: 12px; color: var(--text-secondary); }
.result-placeholder { text-align: center; padding: 40px 0; color: var(--text-muted); }
</style>
