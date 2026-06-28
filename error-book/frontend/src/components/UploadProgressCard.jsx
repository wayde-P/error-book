// frontend/src/components/UploadProgressCard.jsx
const STATUS_LABEL = {
  pending: '等待中...',
  uploading: '上传中...',
  recognizing: '识别中...',
  done: '完成 ✓',
  failed: '识别失败',
}

const STATUS_COLOR = {
  pending: 'bg-gray-200',
  uploading: 'bg-blue-400',
  recognizing: 'bg-yellow-400',
  done: 'bg-green-400',
  failed: 'bg-red-400',
}

export default function UploadProgressCard({ item, onRetry }) {
  const { file, status } = item
  const isDone = status === 'done'
  const isFailed = status === 'failed'
  const progress = { pending: 0, uploading: 40, recognizing: 75, done: 100, failed: 100 }[status]

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{isFailed ? '❌' : isDone ? '✅' : '🖼️'}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
          <p className={`text-xs mt-0.5 ${isFailed ? 'text-red-500' : 'text-gray-400'}`}>
            {STATUS_LABEL[status]}
          </p>
        </div>
        {isFailed && (
          <button onClick={() => onRetry(item.id)}
            className="text-xs text-indigo-600 hover:underline flex-shrink-0">重试</button>
        )}
      </div>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full transition-all duration-500 ${STATUS_COLOR[status]}`}
          style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
