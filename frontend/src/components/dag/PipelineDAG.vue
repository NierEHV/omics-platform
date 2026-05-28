<template>
  <div class="dag-wrapper" :style="{ height: height + 'px' }">
    <div class="dag-resize-handle" @mousedown="onResizeStart"></div>
    <div class="dag-container" ref="containerRef"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Graph } from '@antv/g6'

const STATUS_STYLE = {
  pending: { bg: '#e8e4e0', border: '#c5c0b8', text: '#8a8178', labelBg: 'transparent' },
  ready:   { bg: '#eff6ff', border: '#60a5fa', text: '#1e40af', labelBg: 'transparent' },
  running: { bg: '#fef3c7', border: '#f59e0b', text: '#78350f', labelBg: 'transparent' },
  done:    { bg: '#dcfce7', border: '#4ade80', text: '#166534', labelBg: 'transparent' },
  failed:  { bg: '#fee2e2', border: '#f87171', text: '#991b1b', labelBg: 'transparent' },
}

const props = defineProps({ template: Object, nodeStates: { type: Object, default: () => ({}) } })
const emit = defineEmits(['select-node'])
const containerRef = ref(null)
let graph = null

const height = ref(350)
let resizeStartY = 0
let resizeStartH = 0

function onResizeStart(e) {
  e.preventDefault()
  resizeStartY = e.clientY
  resizeStartH = height.value
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
}
function onResizeMove(e) {
  const delta = resizeStartY - e.clientY
  height.value = Math.max(200, Math.min(800, resizeStartH + delta))
  nextTick(() => { if (graph) { graph.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight); graph.render() } })
}
function onResizeEnd() {
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
}

function buildGraphData() {
  const nodes = (props.template.nodes || []).map(n => {
    const status = props.nodeStates[n.id]?.status || 'pending'
    const s = STATUS_STYLE[status] || STATUS_STYLE.pending
    return {
      id: n.id, data: { nodeId: n.id, label: n.label, status, type: n.type || 'analysis' },
      style: {
        fill: s.bg, stroke: s.border, lineWidth: status === 'running' ? 2.5 : 1.5,
        labelText: n.label, labelFill: s.text, labelFontSize: 13, labelFontWeight: 600,
        labelPlacement: 'center', labelBackgroundFill: s.labelBg, labelBackgroundRadius: 0,
        size: [170, 44], radius: 10,
        opacity: status === 'pending' ? 0.5 : 1,
        ports: [{ key: 'left', placement: [0, 0.5] }, { key: 'right', placement: [1, 0.5] }],
      },
    }
  })
  const edges = (props.template.edges || []).map(e => {
    const sStat = props.nodeStates[e.source]?.status || 'pending'
    const active = sStat === 'done' || sStat === 'running'
    return { source: e.source, target: e.target, style: { stroke: active ? '#f59e0b' : '#d6d3d1', lineWidth: active ? 2 : 1, endArrow: true, opacity: active ? 1 : 0.3 } }
  })
  return { nodes, edges }
}

function initGraph() {
  if (!containerRef.value) return
  graph = new Graph({
    container: containerRef.value, data: buildGraphData(), width: containerRef.value.clientWidth, height: containerRef.value.clientHeight,
    layout: { type: 'dagre', rankdir: 'LR', nodesep: 60, ranksep: 100 },
    node: { type: 'rect', style: { size: [170, 44], radius: 10 }, state: { selected: { stroke: '#f59e0b', lineWidth: 2, shadowBlur: 10, shadowColor: 'rgba(245,158,11,0.4)' } } },
    edge: { type: 'cubic-vertical', style: { stroke: '#d6d3d1', lineWidth: 1.5, endArrow: true } },
    behaviors: ['zoom-canvas', 'drag-canvas'],
    autoFit: 'view', animation: true,
  })
  graph.on('node:click', (evt) => { const nid = evt.target?.id; if (nid) emit('select-node', nid) })
  graph.render()
}

function updateGraph() { if (!graph) return; graph.setData(buildGraphData()); graph.draw() }
onMounted(() => nextTick(initGraph))
watch(() => [props.nodeStates, props.template], () => updateGraph(), { deep: true })
onUnmounted(() => { if (graph) graph.destroy() })
defineExpose({ updateGraph })
</script>

<style scoped>
.dag-wrapper { position: relative; border-top: 1px solid var(--border-color); background: var(--bg-primary); }
.dag-resize-handle { position: absolute; top: -3px; left: 0; right: 0; height: 8px; cursor: ns-resize; z-index: 20; background: var(--border-color); opacity: 0.3; transition: opacity .15s; }
.dag-resize-handle:hover { opacity: 0.8; background: var(--accent-300); }
.dag-container { width: 100%; height: 100%; }
</style>
