// frontend/src/contexts/UploadContext.jsx
import { createContext, useContext, useState, useCallback } from 'react'
import axios from 'axios'
import apiClient from '../api/client'

const UploadContext = createContext(null)

export function UploadProvider({ children }) {
  const [queue, setQueue] = useState([])

  function updateItem(id, patch) {
    setQueue(q => q.map(item => item.id === id ? { ...item, ...patch } : item))
  }

  async function processFile(id, file) {
    updateItem(id, { status: 'uploading' })
    try {
      // 1. 获取 presigned URL
      const { data: { url, key } } = await apiClient.get('/upload/presigned-url', {
        params: { filename: file.name, contentType: file.type },
      })
      // 2. 直传 S3（不带 JWT header）
      await axios.put(url, file, { headers: { 'Content-Type': file.type } })
      updateItem(id, { status: 'recognizing' })
      // 3. 触发识别
      const { data: question } = await apiClient.post('/questions/recognize', { imageKey: key })
      updateItem(id, { status: question.status === 'failed' ? 'failed' : 'done', question })
    } catch {
      updateItem(id, { status: 'failed' })
    }
  }

  const addFiles = useCallback((files) => {
    const newItems = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      question: null,
    }))
    setQueue(q => [...q, ...newItems])
    newItems.forEach(item => processFile(item.id, item.file))
  }, [])

  const retryFile = useCallback((id) => {
    const item = queue.find(i => i.id === id)
    if (item) processFile(id, item.file)
  }, [queue])

  return (
    <UploadContext.Provider value={{ queue, addFiles, retryFile }}>
      {children}
    </UploadContext.Provider>
  )
}

export function useUpload() {
  return useContext(UploadContext)
}
