<template>
  <span class="status-badge" :class="'status-' + status">
    <span class="status-dot"></span>
    <span class="status-label">{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: { type: String, default: 'pending' } })
const labels = { pending: '待执行', ready: '就绪', running: '运行中', done: '完成', failed: '失败' }
const label = computed(() => labels[props.status] || props.status)
</script>

<style scoped>
.status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-pending { background: var(--bg-tertiary); color: var(--text-muted); }
.status-pending .status-dot { background: var(--text-muted); }
.status-ready { background: #eff6ff; color: var(--color-info); }
.status-ready .status-dot { background: var(--color-info); }
.status-running { background: #fef9c3; color: var(--color-warning); }
.status-running .status-dot { background: var(--color-warning); animation: pulse-dot 1s infinite; }
.status-done { background: #f0fdf4; color: var(--color-success); }
.status-done .status-dot { background: var(--color-success); }
.status-failed { background: #fef2f2; color: var(--color-error); }
.status-failed .status-dot { background: var(--color-error); }
@keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
</style>
