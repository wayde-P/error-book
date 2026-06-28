// frontend/src/pages/DashboardPage.jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../api/client'

export default function DashboardPage() {
  const [stats, setStats] = useState({ total: 0, tags: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.get('/questions?lastKey='),
      apiClient.get('/tags'),
    ]).then(([qResp, tResp]) => {
      setStats({ total: qResp.data.items?.length ?? 0, tags: tResp.data })
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-center mt-20 text-gray-400">加载中...</p>

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">概览</h1>
      <div className="grid grid-cols-2 gap-4 mb-8">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
          <p className="text-4xl font-bold text-indigo-600">{stats.total}</p>
          <p className="text-gray-500 mt-1">总错题数</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
          <p className="text-4xl font-bold text-indigo-600">{stats.tags.length}</p>
          <p className="text-gray-500 mt-1">标签数</p>
        </div>
      </div>
      <Link to="/upload"
        className="block w-full bg-indigo-600 text-white text-center py-3 rounded-xl font-semibold hover:bg-indigo-700">
        + 上传新题目
      </Link>
    </div>
  )
}
