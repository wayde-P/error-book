import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../api/client'
import TagBadge from './TagBadge'

const SUBJECTS = ['数学', '语文', '英语', '物理', '化学', '生物', '历史', '地理', '政治', '其他']

export default function ErrorCard({ question, tags = [], onSubjectChange }) {
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState(question.subject || '未分类')
  const ref = useRef(null)
  const tagMap = Object.fromEntries(tags.map(t => [t.tagId, t]))

  useEffect(() => {
    setSubject(question.subject || '未分类')
  }, [question.subject])

  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (!ref.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  async function handleSelect(e, newSubject) {
    e.preventDefault()
    e.stopPropagation()
    setOpen(false)
    if (newSubject === subject) return
    setSubject(newSubject)
    await apiClient.put(`/questions/${question.questionId}`, { subject: newSubject })
    onSubjectChange?.(question.questionId, newSubject)
  }

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
            <div ref={ref} className="relative">
              <button
                onClick={e => { e.preventDefault(); e.stopPropagation(); setOpen(v => !v) }}
                className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded hover:bg-indigo-100 transition-colors">
                {subject} ▾
              </button>
              {open && (
                <div className="absolute left-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1 min-w-24">
                  {SUBJECTS.map(s => (
                    <button key={s} onClick={e => handleSelect(e, s)}
                      className={`block w-full text-left px-3 py-1.5 text-sm hover:bg-indigo-50 ${s === subject ? 'text-indigo-600 font-medium' : 'text-gray-700'}`}>
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <span className="text-xs text-gray-400">
              {question.createdAt
                ? new Date(question.createdAt).toLocaleString('zh-CN', {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', second: '2-digit',
                    hour12: false,
                  })
                : ''}
            </span>
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
