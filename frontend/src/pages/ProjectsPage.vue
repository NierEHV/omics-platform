<template>
  <div class="page-shell page-stack" style="padding-top:28px">
    <div class="page-header">
      <h1 style="font-size:24px;font-weight:800;margin:0;color:var(--text-primary)">分析项目</h1>
      <button class="primary-button" @click="showCreate = true">+ 新建项目</button>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:20px">
      <select v-model="filterModality" @change="loadProjects" style="padding:6px 10px;border:1px solid var(--border-color);border-radius:var(--border-radius-sm);font-size:13px;background:var(--bg-input);color:var(--text-primary)">
        <option value="">全部组学</option><option value="scrna">单细胞转录组</option><option value="bulk_rna">Bulk RNA-seq</option><option value="spatial">空间转录组</option><option value="tcr">TCR 免疫组库</option><option value="amplicon">扩增子 16S</option><option value="metagenomics">宏基因组</option><option value="proteomics">蛋白质组</option>
      </select>
      <select v-model="filterStatus" @change="loadProjects" style="padding:6px 10px;border:1px solid var(--border-color);border-radius:var(--border-radius-sm);font-size:13px;background:var(--bg-input);color:var(--text-primary)">
        <option value="">全部状态</option><option value="running">运行中</option><option value="completed">已完成</option><option value="failed">失败</option>
      </select>
      <input v-model="searchQuery" placeholder="搜索项目..." @input="onSearchInput" style="width:200px;padding:6px 10px;border:1px solid var(--border-color);border-radius:var(--border-radius-sm);font-size:13px;background:var(--bg-input);color:var(--text-primary)" />
      <span style="font-size:11px;color:var(--text-muted);margin-left:auto" v-if="capacity">{{ capacity.cpu_cores }}核 / {{ capacity.ram_gb }}GB · 建议 {{ capacity.recommended_max_parallel }} 并行</span>
    </div>
    <div class="agent-grid" v-if="!loading">
      <ProjectCard v-for="p in store.list" :key="p.id" :project="p" />
      <div v-if="store.list.length === 0" style="grid-column:1/-1;text-align:center;padding:60px 0;color:var(--text-muted)">
        <p>暂无项目</p><button class="primary-button" @click="showCreate = true">创建第一个项目</button>
      </div>
    </div>
    <div v-else style="text-align:center;padding:60px 0;color:var(--text-muted)">加载中...</div>
    <ProjectCreate :show="showCreate" @close="showCreate = false" @create="onCreate" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import { getSystemCapacity } from '@/api'
import ProjectCard from '@/components/project/ProjectCard.vue'
import ProjectCreate from '@/components/project/ProjectCreate.vue'

const store = useProjectsStore()
const loading = ref(false); const showCreate = ref(false)
const filterModality = ref(''); const filterStatus = ref(''); const searchQuery = ref('')
const capacity = ref(null); let searchTimer = null

async function loadProjects() {
  loading.value = true
  const params = {}
  if (filterModality.value) params.modality = filterModality.value
  if (filterStatus.value) params.status = filterStatus.value
  if (searchQuery.value) params.search = searchQuery.value
  await store.loadList(params)
  loading.value = false
}
function onSearchInput() { clearTimeout(searchTimer); searchTimer = setTimeout(loadProjects, 300) }
async function onCreate({ name, modality, description }) { await store.create(name, modality, description ? { description } : {}); showCreate.value = false }
onMounted(async () => { await loadProjects(); try { capacity.value = await getSystemCapacity() } catch {} })
</script>
