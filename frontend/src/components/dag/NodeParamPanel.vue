<template>
  <Transition name="slide"><div class="param-panel glass-panel" v-if="node">
    <div class="panel-header"><h4>{{ node.label || nodeId }}</h4><StatusBadge :status="nodeState?.status || 'pending'" /><button class="icon-button" @click="$emit('close')" style="width:24px;height:24px">&times;</button></div>
    <div class="panel-body">
      <div class="form-group" v-for="p in nodeParams" :key="p.key"><label>{{ p.label }}</label>
        <input v-if="p.type === 'integer' || p.type === 'number'" :type="p.type === 'integer' ? 'number' : 'number'" :step="p.type === 'integer' ? 1 : (p.step || 0.1)" v-model.number="params[p.key]" />
        <input v-else-if="p.type === 'string'" type="text" v-model="params[p.key]" />
        <select v-else-if="p.type === 'select'" v-model="params[p.key]"><option v-for="o in p.options" :key="o" :value="o">{{ o }}</option></select>
      </div>
      <div v-if="nodeState?.status === 'done' || nodeState?.status === 'failed'" style="margin-top:12px">
        <p v-if="nodeState?.status === 'done'" style="font-size:12px;font-weight:500;color:var(--color-success);margin:0 0 4px">执行结果</p>
        <p v-if="nodeState?.status === 'failed'" style="font-size:12px;font-weight:500;color:var(--color-error);margin:0 0 4px">错误信息</p>
        <pre style="font-size:11px;background:var(--bg-code);padding:8px;border-radius:var(--border-radius-sm);max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-all">{{ formatResult(nodeState?.result || nodeState?.error_msg) }}</pre>
      </div>
    </div>
    <div class="panel-footer">
      <button class="text-button" v-if="nodeState?.status === 'done'" @click="onModify" style="padding:6px 12px;font-size:13px">修改参数</button>
      <button class="primary-button" @click="onRun" :disabled="running || nodeState?.status === 'running'" style="padding:6px 14px;font-size:13px">{{ running ? '运行中...' : nodeState?.status === 'done' ? '重新运行' : '运行此节点' }}</button>
    </div>
  </div></Transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
const props = defineProps({ node: Object, nodeId: String, nodeState: Object, running: Boolean })
const emit = defineEmits(['run', 'modify', 'close'])
const params = ref({})
const nodeParams = computed(() => props.node?.params || [])
watch(() => props.node, (n) => { if (n) { const p = {}; n.params?.forEach(param => { p[param.key] = props.nodeState?.params?.[param.key] ?? param.default }); params.value = p } }, { immediate: true })
function onRun() { emit('run', { nodeId: props.nodeId || props.node?.id, params: params.value, isRerun: props.nodeState?.status === 'done' }) }
function onModify() { if (confirm('修改参数将重置该节点及所有下游节点。确定继续？')) emit('modify', { nodeId: props.nodeId || props.node?.id }) }
function formatResult(r) { if (!r) return ''; try { return JSON.stringify(typeof r === 'string' ? JSON.parse(r) : r, null, 2) } catch { return String(r) } }
</script>

<style scoped>
.param-panel { width: 100%; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; }
.panel-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.panel-header h4 { margin: 0; font-size: 15px; flex: 1; color: var(--text-primary); }
.panel-body { flex: 1; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: var(--text-secondary); }
.form-group input, .form-group select { width: 100%; padding: 6px 8px; border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); font-size: 13px; background: var(--bg-input); color: var(--text-primary); }
.panel-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-color); }
</style>
