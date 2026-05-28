<template>
  <div class="file-manager glass-panel">
    <div class="fm-header">
      <h5>数据文件</h5>
      <span class="file-count">{{ files.length }} 个文件</span>
    </div>
    <div class="fm-toolbar">
      <label class="primary-button" style="padding:4px 12px;font-size:12px;cursor:pointer">
        上传文件<input type="file" hidden @change="$emit('upload', $event)" accept=".h5ad,.h5mu,.csv,.tsv,.txt,.fastq,.fq,.fasta,.fa" />
      </label>
    </div>
    <div class="fm-table-wrapper" v-if="files.length > 0">
      <table class="fm-table">
        <thead>
          <tr>
            <th class="col-name">名称</th>
            <th class="col-type">类型</th>
            <th class="col-size">大小</th>
            <th class="col-meta">数据信息</th>
            <th class="col-date">上传时间</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.id">
            <td class="col-name">
              <span class="file-icon">{{ fileIcon(f.extension) }}</span>
              <span class="file-name">{{ f.filename }}</span>
            </td>
            <td class="col-type"><span class="type-tag">{{ f.extension?.replace('.','') || '--' }}</span></td>
            <td class="col-size">{{ formatSize(f.size_bytes) }}</td>
            <td class="col-meta"><span class="meta-text">{{ fileMeta(f.metadata) }}</span></td>
            <td class="col-date">{{ formatDate(f.uploaded_at) }}</td>
            <td class="col-actions">
              <button class="icon-button" @click="$emit('delete', f.id)" title="删除" style="width:22px;height:22px">&times;</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="fm-empty" v-else>
      <p>暂无数据文件</p>
      <p class="fm-empty-hint">上传 .h5ad / .csv / .fastq 等格式的组学数据文件</p>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ files: { type: Array, default: () => [] } })
defineEmits(['upload', 'delete'])

const typeIcons = { '.h5ad': '🧬', '.h5mu': '🧬', '.csv': '📊', '.tsv': '📊', '.txt': '📄', '.fastq': '🧬', '.fq': '🧬', '.fasta': '🧬', '.fa': '🧬' }
function fileIcon(ext) { return typeIcons[ext?.toLowerCase()] || '📁' }
function formatSize(bytes) { if (!bytes) return '--'; if (bytes < 1024) return bytes + ' B'; if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'; return (bytes / 1048576).toFixed(1) + ' MB' }
function formatDate(d) { return d ? d.replace('T', ' ').substring(0, 16) : '--' }
function fileMeta(m) { if (!m) return '--'; if (typeof m === 'string') { try { m = JSON.parse(m) } catch { return '--' } } if (m.n_obs && m.n_vars) return m.n_obs + ' cells × ' + m.n_vars + ' genes'; if (m.shape) return m.shape.join(' × '); return '--' }
</script>

<style scoped>
.file-manager { padding: 12px; font-size: 13px; display: flex; flex-direction: column; max-height: 100%; }
.fm-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.fm-header h5 { margin: 0; font-size: 13px; color: var(--text-primary); }
.file-count { font-size: 11px; color: var(--text-muted); }
.fm-toolbar { margin-bottom: 8px; }
.fm-table-wrapper { flex: 1; overflow-y: auto; }
.fm-table { width: 100%; border-collapse: collapse; }
.fm-table th { position: sticky; top: 0; background: var(--bg-card); padding: 6px 8px; text-align: left; font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border-color); }
.fm-table td { padding: 6px 8px; border-bottom: 1px solid var(--border-color); font-size: 12px; color: var(--text-primary); }
.fm-table tr:hover td { background: var(--bg-card-hover); }
.col-name { min-width: 120px; }
.col-type { width: 60px; }
.col-size { width: 70px; white-space: nowrap; color: var(--text-secondary) !important; }
.col-meta { min-width: 140px; }
.col-date { width: 110px; white-space: nowrap; font-size: 11px !important; color: var(--text-muted) !important; }
.col-actions { width: 30px; text-align: center; }
.file-icon { margin-right: 6px; }
.file-name { font-weight: 500; word-break: break-all; }
.type-tag { font-size: 10px; padding: 1px 6px; border-radius: var(--border-radius-sm); background: var(--accent-100); color: var(--accent-700); text-transform: uppercase; }
.meta-text { font-size: 11px; color: var(--text-secondary); }
.fm-empty { text-align: center; padding: 24px 0; color: var(--text-muted); }
.fm-empty p { margin: 0; }
.fm-empty-hint { font-size: 11px; margin-top: 4px !important; }
</style>
