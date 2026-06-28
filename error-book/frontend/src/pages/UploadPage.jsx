import { useNavigate } from 'react-router-dom'
import { useUpload } from '../contexts/UploadContext'
import UploadDropzone from '../components/UploadDropzone'
import UploadProgressCard from '../components/UploadProgressCard'
import ManualEntryForm from '../components/ManualEntryForm'

export default function UploadPage() {
  const { queue, retryFile } = useUpload()
  const navigate = useNavigate()
  const allDone = queue.length > 0 && queue.every(i => i.status === 'done' || i.status === 'failed')

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">添加错题</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-700 mb-4">📷 拍照识别</h2>
          <UploadDropzone />
          {queue.length > 0 && (
            <div className="mt-5 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">识别进度</p>
              {queue.map(item => (
                <UploadProgressCard key={item.id} item={item} onRetry={retryFile} />
              ))}
            </div>
          )}
          {allDone && (
            <button onClick={() => navigate('/errors')}
              className="mt-5 w-full bg-green-500 text-white py-2.5 rounded-xl font-semibold hover:bg-green-600">
              查看错题库 →
            </button>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-700 mb-4">✏️ 手动录入</h2>
          <ManualEntryForm />
        </div>
      </div>
    </div>
  )
}
