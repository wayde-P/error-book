// frontend/src/components/UploadDropzone.jsx
import { useRef, useState } from 'react'
import { useUpload } from '../contexts/UploadContext'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp']
const MAX_SIZE = 10 * 1024 * 1024

export default function UploadDropzone() {
  const { addFiles } = useUpload()
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  function validate(files) {
    return Array.from(files).filter(f => ACCEPTED.includes(f.type) && f.size <= MAX_SIZE)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const valid = validate(e.dataTransfer.files)
    if (valid.length) addFiles(valid)
  }

  function handleChange(e) {
    const valid = validate(e.target.files)
    if (valid.length) addFiles(valid)
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors
        ${dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 hover:border-indigo-300'}`}>
      <p className="text-4xl mb-3">📷</p>
      <p className="text-gray-600 font-medium">点击或拖拽图片到此处上传</p>
      <p className="text-gray-400 text-sm mt-1">支持 JPG、PNG、WebP，单张最大 10MB</p>
      <input ref={inputRef} type="file" accept={ACCEPTED.join(',')} multiple onChange={handleChange} className="hidden" />
    </div>
  )
}
