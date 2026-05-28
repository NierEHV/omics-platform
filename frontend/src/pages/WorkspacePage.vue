<template>
  <div style="height:100%;display:flex;flex-direction:column;overflow:hidden">
    <div v-if="!projectId" style="max-width:600px;margin:60px auto;text-align:center;padding:24px">
      <h2 style="margin:0 0 8px;color:var(--text-primary)">选择分析项目</h2>
      <p style="color:var(--text-secondary);margin-bottom:20px">从项目列表中选择一个项目开始分析，或创建新项目</p>
      <div v-if="projects.list.length" style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">
        <div class="glass-panel" v-for="p in projects.list" :key="p.id" @click="$router.push('/workspace/' + p.id)" style="display:flex;align-items:center;gap:12px;padding:12px 16px;cursor:pointer">
          <span style="flex:1;font-weight:600;font-size:14px;color:var(--text-primary)">{{ p.name }}</span>
          <span style="font-size:11px;color:var(--text-muted)">{{ p.modality }}</span>
          <StatusBadge :status="p.status === 'completed' ? 'done' : p.status === 'running' ? 'running' : 'pending'" />
        </div>
      </div>
      <button class="primary-button" @click="$router.push('/projects')">浏览项目列表</button>
    </div>

    <template v-else>
      <header style="display:flex;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-color);gap:16px">
        <router-link to="/projects" style="font-size:13px;color:var(--text-secondary);text-decoration:none">&larr; 项目列表</router-link>
        <div style="display:flex;align-items:center;gap:10px;flex:1"><h2 style="margin:0;font-size:17px;color:var(--text-primary)">{{ project?.name || '加载中...' }}</h2><StatusBadge :status="projectStatus" /></div>
        <button class="primary-button" @click="runAll" :disabled="isRunning" style="padding:6px 14px;font-size:13px">{{ isRunning ? '运行中...' : '运行全部' }}</button>
      </header>

      <div style="flex:1;display:flex;flex-direction:row;overflow:hidden">
        <!-- Main area: Results + DAG -->
        <div style="flex:1;display:flex;flex-direction:column;overflow:hidden">
          <div style="flex:1;overflow-y:auto;padding:12px 0;min-height:120px">
            <ResultPanel :selected-node="selectedTemplateNode" :node-id="selectedNodeId" :node-state="pipeline.nodes[selectedNodeId]" />
          </div>
          <PipelineDAG ref="dagRef" :template="template" :node-states="pipeline.nodeStatuses" @select-node="onSelectNode" />
        </div>

        <!-- Right panel: Files + Node params, resizable -->
        <div class="resize-col" :style="{ width: rightWidth + 'px' }">
          <div class="resize-col-handle" @mousedown="onColResizeStart"></div>
          <div style="flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:8px;padding:8px">
            <FileManager :files="files" @upload="onUpload" @delete="onDeleteFile" />
            <NodeParamPanel v-if="selectedNodeId" :node="selectedTemplateNode" :node-id="selectedNodeId" :node-state="pipeline.nodes[selectedNodeId]" :running="isNodeRunning(selectedNodeId)" @run="onRunNode" @modify="onModifyParams" @close="selectedNodeId = null" />
          </div>
        </div>
      </div>
      <AIChatPanel :project-id="projectId" @run-all="runAll" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { usePipelineStore } from '@/stores/pipeline'
import { getTemplate } from '@/templates/DAGTemplates'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PipelineDAG from '@/components/dag/PipelineDAG.vue'
import NodeParamPanel from '@/components/dag/NodeParamPanel.vue'
import ResultPanel from '@/components/results/ResultPanel.vue'
import FileManager from '@/components/project/FileManager.vue'
import AIChatPanel from '@/components/ai/AIChatPanel.vue'

const route = useRoute()
const projectId = computed(() => route.params.id || '')
const projects = useProjectsStore()
const pipeline = usePipelineStore()

const project = computed(() => projects.current)
const files = computed(() => project.value?.files || [])
const template = computed(() => getTemplate(project.value?.modality || 'scrna'))
const selectedNodeId = ref(null)
const isRunning = ref(false)
const runningNodeIds = ref(new Set())

const rightWidth = ref(320)
let colStartX = 0, colStartW = 0
function onColResizeStart(e) { e.preventDefault(); colStartX = e.clientX; colStartW = rightWidth.value; document.addEventListener('mousemove', onColResizeMove); document.addEventListener('mouseup', onColResizeEnd) }
function onColResizeMove(e) { rightWidth.value = Math.max(200, Math.min(500, colStartW - (e.clientX - colStartX))) }
function onColResizeEnd() { document.removeEventListener('mousemove', onColResizeMove); document.removeEventListener('mouseup', onColResizeEnd) }

const selectedTemplateNode = computed(() => { if (!selectedNodeId.value || !template.value) return null; return template.value.nodes.find(n => n.id === selectedNodeId.value) || null })
const projectStatus = computed(() => { if (!project.value) return 'pending'; const ns = Object.values(pipeline.nodes); if (ns.some(n => n.status === 'running')) return 'running'; if (ns.some(n => n.status === 'failed')) return 'failed'; if (ns.length > 0 && ns.every(n => n.status === 'done')) return 'done'; return 'pending' })
const isNodeRunning = (nodeId) => runningNodeIds.value.has(nodeId)

function onSelectNode(nodeId) { selectedNodeId.value = nodeId }
async function onRunNode({ nodeId, params, isRerun }) { if (isRerun) { await pipeline.updateParams(projectId.value, nodeId, params, true) } else { await pipeline.updateParams(projectId.value, nodeId, params, false) }; runningNodeIds.value.add(nodeId); pipeline.nodes[nodeId] = { ...pipeline.nodes[nodeId], status: 'running' }; await pipeline.executeNode(projectId.value, nodeId, params, () => {}); runningNodeIds.value.delete(nodeId); await loadAll() }
async function onModifyParams({ nodeId }) { await pipeline.updateParams(projectId.value, nodeId, {}, true); await loadAll() }
async function runAll() { isRunning.value = true; try { await pipeline.executeAll(projectId.value, (type, data) => { if (type === 'node_status') { pipeline.nodes[data.node_id] = { ...pipeline.nodes[data.node_id], status: data.status, result: data.result } } }) } finally { isRunning.value = false; await loadAll() } }
async function onUpload(e) { const file = e.target.files?.[0]; if (file) { await projects.uploadFile(projectId.value, file); await loadAll() } }
async function onDeleteFile(fileId) { await projects.deleteFile(projectId.value, fileId); await loadAll() }
async function loadAll() { await projects.open(projectId.value); await pipeline.loadNodes(projectId.value) }
onMounted(() => { if (projectId.value) loadAll(); projects.loadList() })
</script>

<style scoped>
.resize-col { position: relative; display: flex; flex-direction: column; border-left: 1px solid var(--border-color); background: var(--bg-primary); }
.resize-col-handle { position: absolute; left: -3px; top: 0; bottom: 0; width: 6px; cursor: col-resize; z-index: 20; }
.resize-col-handle:hover { background: var(--accent-300); opacity: 0.4; }
</style>
