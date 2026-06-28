import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'

const SUBJECT_COLORS = {
  数学: 'bg-blue-50 text-blue-700 border-blue-200',
  语文: 'bg-red-50 text-red-700 border-red-200',
  英语: 'bg-green-50 text-green-700 border-green-200',
  物理: 'bg-purple-50 text-purple-700 border-purple-200',
  化学: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  生物: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  历史: 'bg-orange-50 text-orange-700 border-orange-200',
  地理: 'bg-teal-50 text-teal-700 border-teal-200',
  政治: 'bg-pink-50 text-pink-700 border-pink-200',
  其他: 'bg-gray-50 text-gray-700 border-gray-200',
}

export default function DashboardPage() {
  const [total, setTotal] = useState(0)
  const [subjectStats, setSubjectStats] = useState([])
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function load() {
      const [qResp, tResp] = await Promise.all([
        apiClient.get('/questions'),
        apiClient.get('/tags'),
      ])
      const items = qResp.data.items ?? []
      const countBySubject = {}
      for (const q of items) {
        countBySubject[q.subject] = (countBySubject[q.subject] ?? 0) + 1
      }
      const sorted = Object.entries(countBySubject)
        .map(([subject, count]) => ({ subject, count }))
        .sort((a, b) => b.count - a.count)
      setTotal(items.length)
      setSubjectStats(sorted)
      setTags(tResp.data)
    }
    load().finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-center mt-20 text-gray-400">加载中...</p>

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">概览</h1>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Link to="/errors"
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center hover:border-indigo-300 hover:shadow-md transition-all">
          <p className="text-4xl font-bold text-indigo-600">{total}</p>
          <p className="text-gray-500 mt-1">总错题数</p>
          <p className="text-xs text-indigo-400 mt-2">点击查看全部 →</p>
        </Link>
        <Link to="/tags"
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center hover:border-indigo-300 hover:shadow-md transition-all">
          <p className="text-4xl font-bold text-indigo-600">{tags.length}</p>
          <p className="text-gray-500 mt-1">标签数</p>
          <p className="text-xs text-indigo-400 mt-2">点击管理标签 →</p>
        </Link>
      </div>

      {subjectStats.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">按科目分布</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {subjectStats.map(({ subject, count }) => (
              <button key={subject}
                onClick={() => navigate(`/errors?subject=${encodeURIComponent(subject)}`)}
                className={`flex items-center justify-between px-4 py-3 rounded-xl border text-sm font-medium hover:shadow-sm transition-all ${SUBJECT_COLORS[subject] ?? SUBJECT_COLORS['其他']}`}>
                <span>{subject}</span>
                <span className="text-lg font-bold">{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {tags.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">标签</h2>
          <div className="flex flex-wrap gap-2">
            {tags.map(tag => (
              <button key={tag.tagId}
                onClick={() => navigate(`/errors?tagId=${tag.tagId}`)}
                className="px-3 py-1.5 rounded-full text-sm font-medium text-white hover:opacity-80 transition-opacity"
                style={{ backgroundColor: tag.color }}>
                {tag.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <Link to="/upload"
        className="block w-full bg-indigo-600 text-white text-center py-3 rounded-xl font-semibold hover:bg-indigo-700">
        + 添加错题
      </Link>
    </div>
  )
}
