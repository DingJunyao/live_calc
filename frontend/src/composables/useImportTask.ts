import { ref, onUnmounted } from 'vue'
import api from '@/api/client'

export interface ImportTask {
  id: number
  task_type: string
  status: 'pending' | 'running' | 'success' | 'failed'
  progress: {
    stage: string
    current: number
    total: number
    message: string
  }
  stats: Record<string, number>
  error: string | null
  created_at: string
  updated_at: string
}

function inferTaskType(endpoint: string): string {
  if (endpoint.includes('import-from-repo')) return 'git_import'
  if (endpoint.includes('import-from-local')) return 'local_import'
  if (endpoint.includes('upload')) return 'upload_import'
  if (endpoint.includes('quantities')) return 'ai_quantities'
  if (endpoint.includes('densities')) return 'ai_densities'
  return 'import'
}

export function useImportTask() {
  const tasks = ref<ImportTask[]>([])
  const pollingMap = new Map<number, ReturnType<typeof setInterval>>()

  async function fetchTasks(limit = 10) {
    try {
      const data: ImportTask[] = await api.get('/import/tasks', {
        params: { limit },
      })
      tasks.value = data || []
      // Resume polling for running/pending tasks
      tasks.value.forEach((t) => {
        if (t.status === 'running' || t.status === 'pending') {
          startPolling(t.id)
        }
      })
    } catch {
      // ignore network/parse errors
    }
  }

  async function startTask(
    endpoint: string,
    axiosConfig: Record<string, any> = {},
  ): Promise<number | null> {
    try {
      const data: any = await api.post(endpoint, {}, axiosConfig)
      const taskId = data?.task_id
      if (taskId) {
        startPolling(taskId)
        // Immediately add to local list so user sees it right away
        tasks.value.unshift({
          id: taskId,
          task_type: inferTaskType(endpoint),
          status: 'pending',
          progress: { stage: '等待中', current: 0, total: 0, message: '' },
          stats: {},
          error: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        return taskId
      }
    } catch (e: any) {
      console.error('Task start failed', e)
    }
    return null
  }

  async function startUploadTask(file: File): Promise<number | null> {
    try {
      const form = new FormData()
      form.append('file', file)
      const data: any = await api.post('/import/data/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const taskId = data?.task_id
      if (taskId) {
        startPolling(taskId)
        tasks.value.unshift({
          id: taskId,
          task_type: 'upload_import',
          status: 'pending',
          progress: { stage: '等待中', current: 0, total: 0, message: '' },
          stats: {},
          error: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        return taskId
      }
    } catch (e: any) {
      console.error('Upload task start failed', e)
    }
    return null
  }

  function startPolling(taskId: number) {
    if (pollingMap.has(taskId)) return
    const interval = setInterval(async () => {
      try {
        const task: ImportTask = await api.get(`/import/task/${taskId}`)
        const idx = tasks.value.findIndex((t) => t.id === taskId)
        if (idx >= 0) {
          tasks.value[idx] = task
        } else {
          tasks.value.unshift(task)
        }
        // Stop polling when task reaches a terminal state
        if (task.status === 'success' || task.status === 'failed') {
          stopPolling(taskId)
        }
      } catch {
        stopPolling(taskId)
      }
    }, 2000)
    pollingMap.set(taskId, interval)
  }

  function stopPolling(taskId: number) {
    const interval = pollingMap.get(taskId)
    if (interval) {
      clearInterval(interval)
      pollingMap.delete(taskId)
    }
  }

  onUnmounted(() => {
    pollingMap.forEach((interval) => clearInterval(interval))
    pollingMap.clear()
  })

  return { tasks, fetchTasks, startTask, startUploadTask }
}
