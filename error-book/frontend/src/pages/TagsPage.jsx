// frontend/src/pages/TagsPage.jsx
import { useState, useEffect } from 'react'
import apiClient from '../api/client'
import TagBadge from '../components/TagBadge'

const PRESET_COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#8B5CF6', '#EC4899']

export default function TagsPage() {
  const [tags, setTags] = useState([])
  const [name, setName] = useState('')
  const [color, setColor] = useState(PRESET_COLORS[0])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiClient.get('/tags').then(r => setTags(r.data))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    const { data } = await apiClient.post('/tags', { name: name.trim(), color })
    setTags(t => [...t, data])
    setName('')
    setLoading(false)
  }

  async function handleDelete(tagId) {
    await apiClient.delete(`/tags/${tagId}`)
    setTags(t => t.filter(tag => tag.tagId !== tagId))
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">标签管理</h1>
      <form onSubmit={handleCreate} className="bg-white rounded-xl border border-gray-100 p-4 mb-6 space-y-3">
        <input type="text" placeholder="标签名称（如：数学、易错）" value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">颜色：</span>
          {PRESET_COLORS.map(c => (
            <button key={c} type="button" onClick={() => setColor(c)}
              className={`w-6 h-6 rounded-full border-2 transition-transform ${color === c ? 'border-gray-800 scale-110' : 'border-transparent'}`}
              style={{ backgroundColor: c }} />
          ))}
        </div>
        <button type="submit" disabled={loading || !name.trim()}
          className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
          创建标签
        </button>
      </form>
      <div className="space-y-2">
        {tags.map(tag => (
          <div key={tag.tagId} className="flex items-center justify-between bg-white rounded-xl border border-gray-100 px-4 py-3">
            <TagBadge name={tag.name} color={tag.color} />
            <button onClick={() => handleDelete(tag.tagId)} className="text-xs text-red-400 hover:text-red-600">删除</button>
          </div>
        ))}
        {tags.length === 0 && <p className="text-center text-gray-400 text-sm">暂无标签，先创建一个吧</p>}
      </div>
    </div>
  )
}
