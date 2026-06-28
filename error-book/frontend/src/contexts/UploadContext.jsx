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
      const { data: { url, key } } = await apiClient.get('/upload/presigned-url', {
        params: { filename: file.name, contentType: file.type },
      })
      await axios.put(url, file, { headers: { 'Content-Type': file.type } })
      updateItem(id, { status: 'recognizing' })
      const { data: questions } = await apiClient.post('/questions/recognize', { imageKey: key })
      const allFailed = questions.every(q => q.status === 'failed')
      updateItem(id, { status: allFailed ? 'failed' : 'done', questions })
    } catch {
      updateItem(id, { status: 'failed', questions: [] })
    }
  }

  const addFiles = useCallback((files) => {
    const newItems = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      questions: [],
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
