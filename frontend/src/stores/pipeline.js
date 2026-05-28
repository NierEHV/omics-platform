import { defineStore } from 'pinia'
import {
  getNodeStates, updateNodeParams, runNode, runPipeline, getLogs,
} from '@/api'

export const usePipelineStore = defineStore('pipeline', {
  state: () => ({
    nodes: {},
    selectedNodeId: null,
    logs: [],
    runningNodeIds: new Set(),
  }),

  getters: {
    selectedNode(state) {
      return state.nodes[state.selectedNodeId] || null
    },
    nodeStatuses(state) {
      const result = {}
      Object.entries(state.nodes).forEach(([id, n]) => {
        result[id] = n.status || 'pending'
      })
      return result
    },
  },

  actions: {
    async loadNodes(projectId) {
      const nodeList = await getNodeStates(projectId)
      const nodes = {}
      nodeList.forEach(n => {
        nodes[n.node_id] = n
        if (n.params) {
          try { nodes[n.node_id].params = JSON.parse(n.params) } catch {}
        }
        if (n.result) {
          try { nodes[n.node_id].result = JSON.parse(n.result) } catch {}
        }
      })
      this.nodes = nodes
    },

    selectNode(nodeId) {
      this.selectedNodeId = nodeId === this.selectedNodeId ? null : nodeId
    },

    async updateParams(projectId, nodeId, params, resetDownstream = false) {
      const payload = {
        params: JSON.stringify(params),
        reset_downstream: resetDownstream,
      }
      await updateNodeParams(projectId, nodeId, payload)
      await this.loadNodes(projectId)
    },

    async executeNode(projectId, nodeId, params, onStatusChange) {
      this.runningNodeIds.add(nodeId)
      this.nodes[nodeId] = { ...this.nodes[nodeId], status: 'running' }

      await runNode(projectId, nodeId, params, onStatusChange)

      this.runningNodeIds.delete(nodeId)
      await this.loadNodes(projectId)
    },

    async executeAll(projectId, onStatusChange) {
      await runPipeline(projectId, onStatusChange)
      await this.loadNodes(projectId)
    },

    async loadLogs(projectId, nodeId = null) {
      this.logs = await getLogs(projectId, nodeId)
    },
  },
})
