// frontend/src/pages/UploadPage.jsx
import { useNavigate } from 'react-router-dom'
import { useUpload } from '../contexts/UploadContext'
import UploadDropzone from '../components/UploadDropzone'
import UploadProgressCard from '../components/UploadProgressCard'

export default function UploadPage() {
  const { queue, retryFile } = useUpload()
  const navigate = useNavigate()
  const allDone = queue.length > 0 && queue.every(i => i.status === 'done' || i.status === 'failed')

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">上传题目</h1>
      <UploadDropzone />
      {queue.length > 0 && (
        <div className="mt-6 space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">识别进度</h2>
          {queue.map(item => (
            <UploadProgressCard key={item.id} item={item} onRetry={retryFile} />
          ))}
        </div>
      )}
      {allDone && (
        <button onClick={() => navigate('/errors')}
          className="mt-6 w-full bg-green-500 text-white py-3 rounded-xl font-semibold hover:bg-green-600">
          查看错题库 →
        </button>
      )}
    </div>
  )
}
