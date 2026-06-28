// frontend/src/pages/ErrorBankPage.jsx
import { useState, useEffect } from 'react'
import apiClient from '../api/client'
import SearchBar from '../components/SearchBar'
import TagBadge from '../components/TagBadge'
import ErrorCard from '../components/ErrorCard'

export default function ErrorBankPage() {
  const [questions, setQuestions] = useState([])
  const [tags, setTags] = useState([])
  const [selectedTag, setSelectedTag] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get('/tags').then(r => setTags(r.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = {}
    if (selectedTag) params.tagId = selectedTag
    if (keyword) params.keyword = keyword
    apiClient.get('/questions', { params })
      .then(r => setQuestions(r.data.items ?? []))
      .finally(() => setLoading(false))
  }, [selectedTag, keyword])

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">错题库</h1>
      <SearchBar onSearch={setKeyword} />
      <div className="flex flex-wrap gap-2 my-4">
        <button onClick={() => setSelectedTag(null)}
          className={`px-3 py-1 rounded-full text-sm font-medium ${!selectedTag ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          全部
        </button>
        {tags.map(tag => (
          <button key={tag.tagId} onClick={() => setSelectedTag(tag.tagId === selectedTag ? null : tag.tagId)}
            className={`px-3 py-1 rounded-full text-sm font-medium ${selectedTag === tag.tagId ? 'text-white' : 'bg-gray-100 text-gray-600'}`}
            style={selectedTag === tag.tagId ? { backgroundColor: tag.color } : {}}>
            {tag.name}
          </button>
        ))}
      </div>
      {loading ? (
        <p className="text-center mt-10 text-gray-400">加载中...</p>
      ) : questions.length === 0 ? (
        <p className="text-center mt-10 text-gray-400">暂无错题</p>
      ) : (
        <div className="space-y-3">
          {questions.map(q => <ErrorCard key={q.questionId} question={q} tags={tags} />)}
        </div>
      )}
    </div>
  )
}
