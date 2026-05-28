import { defineStore } from 'pinia'
import {
  fetchProjects, createProject, getProject, updateProject, deleteProject,
  uploadFileToProject, deleteProjectFile,
} from '@/api'

export const useProjectsStore = defineStore('projects', {
  state: () => ({
    list: [],
    current: null,
    loading: false,
  }),

  actions: {
    async loadList(params = {}) {
      this.loading = true
      try {
        this.list = await fetchProjects(params)
      } finally {
        this.loading = false
      }
    },

    async create(name, modality, meta = {}) {
      const p = await createProject({ name, modality, meta })
      await this.loadList()
      return p
    },

    async open(projectId) {
      const p = await getProject(projectId)
      this.current = p
      return p
    },

    async remove(projectId) {
      await deleteProject(projectId)
      this.list = this.list.filter(p => p.id !== projectId)
      if (this.current?.id === projectId) {
        this.current = null
      }
    },

    async update(projectId, data) {
      await updateProject(projectId, data)
      if (this.current?.id === projectId) {
        Object.assign(this.current, data)
      }
    },

    async uploadFile(projectId, file) {
      const result = await uploadFileToProject(projectId, file)
      if (this.current?.id === projectId) {
        this.current = await getProject(projectId)
      }
      return result
    },

    async deleteFile(projectId, fileId) {
      await deleteProjectFile(projectId, fileId)
      if (this.current?.id === projectId) {
        this.current = await getProject(projectId)
      }
    },
  },
})
