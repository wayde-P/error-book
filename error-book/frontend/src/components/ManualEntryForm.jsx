import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import apiClient from '../api/client'

const SUBJECTS = ['数学', '语文', '英语', '物理', '化学', '生物', '历史', '地理', '政治', '其他']

export default function ManualEntryForm() {
  const navigate = useNavigate()
  const [subject, setSubject] = useState('数学')
  const [content, setContent] = useState('')
  const [analysis, setAnalysis] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!content.trim()) return
    setLoading(true)
    setError(null)
    try {
      await apiClient.post('/questions/manual', { subject, content: content.trim(), analysis: analysis.trim() })
      setDone(true)
    } catch (err) {
      setError('提交失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div className="text-center py-12">
        <div className="text-5xl mb-4">✅</div>
        <p className="text-gray-700 font-semibold mb-6">题目已保存到错题库</p>
        <div className="flex gap-3 justify-center">
          <button onClick={() => { setDone(false); setContent(''); setAnalysis('') }}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
            继续录入
          </button>
          <button onClick={() => navigate('/errors')}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
            查看错题库 →
          </button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">科目</label>
        <div className="flex flex-wrap gap-2">
          {SUBJECTS.map(s => (
            <button key={s} type="button" onClick={() => setSubject(s)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                subject === s
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
              }`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          题目内容 <span className="text-red-500">*</span>
        </label>
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="请输入题目内容..."
          rows={5}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          错误分析 <span className="text-gray-400 font-normal">（可选）</span>
        </label>
        <textarea
          value={analysis}
          onChange={e => setAnalysis(e.target.value)}
          placeholder="记录错误原因、解题思路..."
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
        />
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <button type="submit" disabled={loading || !content.trim()}
        className="w-full bg-blue-500 text-white py-3 rounded-xl font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {loading ? '保存中...' : '保存到错题库'}
      </button>
    </form>
  )
}
