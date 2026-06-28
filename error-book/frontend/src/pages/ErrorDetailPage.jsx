// frontend/src/pages/ErrorDetailPage.jsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import TagBadge from '../components/TagBadge'

export default function ErrorDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [question, setQuestion] = useState(null)
  const [tags, setTags] = useState([])
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})

  useEffect(() => {
    Promise.all([apiClient.get(`/questions/${id}`), apiClient.get('/tags')])
      .then(([qr, tr]) => {
        setQuestion(qr.data)
        setForm({ subject: qr.data.subject, content: qr.data.content, analysis: qr.data.analysis, tags: qr.data.tags })
        setTags(tr.data)
      })
  }, [id])

  async function handleSave() {
    const { data } = await apiClient.put(`/questions/${id}`, form)
    setQuestion(data)
    setEditing(false)
  }

  async function handleDelete() {
    if (!confirm('确认删除这道错题？')) return
    await apiClient.delete(`/questions/${id}`)
    navigate('/errors')
  }

  const tagMap = Object.fromEntries(tags.map(t => [t.tagId, t]))

  if (!question) return <p className="text-center mt-20 text-gray-400">加载中...</p>

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <button onClick={() => navigate(-1)} className="text-sm text-indigo-600 mb-4 hover:underline">← 返回</button>
      {question.imageUrl && (
        <img src={question.imageUrl} alt="题目原图" className="w-full rounded-xl mb-6 shadow" />
      )}
      {editing ? (
        <div className="space-y-4">
          <input className="w-full border rounded-lg px-3 py-2" placeholder="科目" value={form.subject}
            onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} />
          <textarea className="w-full border rounded-lg px-3 py-2 h-24" placeholder="题目内容" value={form.content}
            onChange={e => setForm(f => ({ ...f, content: e.target.value }))} />
          <textarea className="w-full border rounded-lg px-3 py-2 h-24" placeholder="错误分析" value={form.analysis}
            onChange={e => setForm(f => ({ ...f, analysis: e.target.value }))} />
          <div className="flex gap-3">
            <button onClick={handleSave} className="bg-indigo-600 text-white px-4 py-2 rounded-lg">保存</button>
            <button onClick={() => setEditing(false)} className="text-gray-500 px-4 py-2 rounded-lg border">取消</button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full">
              {question.subject || '未分类'}
            </span>
            <div className="flex gap-2">
              <button onClick={() => setEditing(true)} className="text-sm text-gray-500 hover:text-indigo-600">编辑</button>
              <button onClick={handleDelete} className="text-sm text-red-400 hover:text-red-600">删除</button>
            </div>
          </div>
          <div>
            <h2 className="text-xs text-gray-400 uppercase tracking-wide mb-1">题目内容</h2>
            <p className="text-gray-700 whitespace-pre-wrap">{question.content}</p>
          </div>
          <div>
            <h2 className="text-xs text-gray-400 uppercase tracking-wide mb-1">错误分析</h2>
            <p className="text-gray-600 whitespace-pre-wrap">{question.analysis}</p>
          </div>
          {question.tags?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {question.tags.map(tagId => tagMap[tagId] && (
                <TagBadge key={tagId} name={tagMap[tagId].name} color={tagMap[tagId].color} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
