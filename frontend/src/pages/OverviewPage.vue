<template>
  <div class="page-overview" style="max-width:900px;margin:0 auto;padding:32px 24px">
    <div class="hero-card glass-panel" style="text-align:center;padding:40px;margin-bottom:20px">
      <h1 style="font-size:28px;font-weight:800;margin:0 0 8px;color:var(--accent-600)">Omics Copilot</h1>
      <p class="subtitle" style="font-size:15px;color:var(--text-secondary);margin:0 0 20px">AI 驱动的可视化多组学分析平台</p>
      <div style="display:flex;gap:10px;justify-content:center">
        <button class="primary-button" @click="$router.push('/workspace')">进入分析工作台</button>
        <button class="secondary-button" @click="$router.push('/projects')">管理项目</button>
      </div>
    </div>

    <div class="step-grid" style="margin-bottom:20px">
      <div class="stat-tile glass-panel" style="text-align:center;padding:20px;flex-direction:column">
        <span style="font-size:28px;font-weight:800;color:var(--accent-600);display:block">{{ projectCount }}</span>
        <span style="font-size:12px;color:var(--text-secondary);margin-top:4px">分析项目</span>
      </div>
      <div class="stat-tile glass-panel" style="text-align:center;padding:20px;flex-direction:column">
        <span style="font-size:28px;font-weight:800;color:var(--accent-600);display:block">{{ capacity.cpu_cores || '?' }}</span>
        <span style="font-size:12px;color:var(--text-secondary);margin-top:4px">CPU 核心</span>
      </div>
      <div class="stat-tile glass-panel" style="text-align:center;padding:20px;flex-direction:column">
        <span style="font-size:28px;font-weight:800;color:var(--accent-600);display:block">{{ capacity.ram_gb || '?' }} GB</span>
        <span style="font-size:12px;color:var(--text-secondary);margin-top:4px">可用内存</span>
      </div>
    </div>

    <div class="agent-grid">
      <div class="glass-panel" v-for="m in modalities" :key="m.modality" @click="createAndGo(m.modality)" style="padding:20px;cursor:pointer;transition:transform .15s">
        <h3 style="margin:0 0 4px;font-size:16px;color:var(--text-primary)">{{ m.name }}</h3>
        <p style="font-size:13px;color:var(--text-secondary);margin:0 0 8px">{{ m.nodeCount || 0 }} 个分析步骤</p>
        <span style="font-size:11px;color:var(--accent-600);background:var(--accent-50);padding:2px 8px;border-radius:var(--border-radius-sm)">{{ m.nodeCount || 0 }} 分析步骤</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import { getSystemCapacity, getDAGTemplates } from '@/api'
const router = useRouter()
const projects = useProjectsStore()
const projectCount = ref(0); const capacity = ref({}); const modalities = ref([])
onMounted(async () => { await projects.loadList(); projectCount.value = projects.list.length; try { capacity.value = await getSystemCapacity() } catch {}; try { modalities.value = await getDAGTemplates() } catch {} })
async function createAndGo(modality) { const p = await projects.create('新分析项目', modality); router.push('/workspace/' + p.id) }
</script>
