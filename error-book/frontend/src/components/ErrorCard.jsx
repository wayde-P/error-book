// frontend/src/components/ErrorCard.jsx
import { Link } from 'react-router-dom'
import TagBadge from './TagBadge'

export default function ErrorCard({ question, tags = [] }) {
  const tagMap = Object.fromEntries(tags.map(t => [t.tagId, t]))

  return (
    <Link to={`/errors/${question.questionId}`}
      className="block bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
      <div className="flex gap-3">
        {question.imageUrl && (
          <img src={question.imageUrl} alt="题目图片"
            className="w-20 h-20 object-cover rounded-lg flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
              {question.subject || '未分类'}
            </span>
            <span className="text-xs text-gray-400">{question.createdAt?.slice(0, 10)}</span>
          </div>
          <p className="text-sm text-gray-700 line-clamp-2">{question.content || '识别失败'}</p>
          {question.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {question.tags.map(tagId => tagMap[tagId] && (
                <TagBadge key={tagId} name={tagMap[tagId].name} color={tagMap[tagId].color} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}
