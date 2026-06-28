import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import apiClient from '../api/client'
import SearchBar from '../components/SearchBar'
import ErrorCard from '../components/ErrorCard'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 10

export default function ErrorBankPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [questions, setQuestions] = useState([])
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [showAll, setShowAll] = useState(false)
  const [sortBySubject, setSortBySubject] = useState(false)

  const selectedTag = searchParams.get('tagId')
  const keyword = searchParams.get('keyword') ?? ''
  const selectedSubject = searchParams.get('subject')

  useEffect(() => {
    apiClient.get('/tags').then(r => setTags(r.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    setPage(1)
    setShowAll(false)
    const params = {}
    if (selectedTag) params.tagId = selectedTag
    if (keyword) params.keyword = keyword
    apiClient.get('/questions', { params })
      .then(r => {
        let items = r.data.items ?? []
        if (selectedSubject) items = items.filter(q => q.subject === selectedSubject)
        setQuestions(items)
      })
      .finally(() => setLoading(false))
  }, [selectedTag, keyword, selectedSubject])

  function setTag(tagId) {
    const p = new URLSearchParams(searchParams)
    if (tagId) p.set('tagId', tagId); else p.delete('tagId')
    p.delete('subject')
    setSearchParams(p)
  }

  function setKeyword(kw) {
    const p = new URLSearchParams(searchParams)
    if (kw) p.set('keyword', kw); else p.delete('keyword')
    setSearchParams(p)
  }

  const displayed = [...questions]
    .sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''))
    .sort(sortBySubject
      ? (a, b) => (a.subject || '').localeCompare(b.subject || '', 'zh')
      : () => 0
    )

  const totalPages = Math.max(1, Math.ceil(displayed.length / PAGE_SIZE))
  const pageItems = showAll ? displayed : displayed.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-800">
          错题库
          <span className="ml-2 text-xs text-gray-400">v3</span>
          {selectedSubject && (
            <span className="ml-2 text-base font-normal text-indigo-600">· {selectedSubject}</span>
          )}
        </h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setSortBySubject(v => !v); setPage(1) }}
            className={`text-sm px-3 py-1 rounded-full border transition-colors ${
              sortBySubject
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'text-gray-600 border-gray-300 hover:border-indigo-400'
            }`}>
            按科目排序
          </button>
          {(selectedTag || selectedSubject || keyword) && (
            <button onClick={() => setSearchParams({})}
              className="text-sm text-gray-400 hover:text-red-500">
              清除筛选 ×
            </button>
          )}
        </div>
      </div>
      <SearchBar onSearch={setKeyword} />
      <div className="flex flex-wrap gap-2 my-4">
        <button onClick={() => setTag(null)}
          className={`px-3 py-1 rounded-full text-sm font-medium ${!selectedTag ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          全部
        </button>
        {tags.map(tag => (
          <button key={tag.tagId} onClick={() => setTag(tag.tagId === selectedTag ? null : tag.tagId)}
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
        <>
          <div className="space-y-3">
            {pageItems.map(q => (
              <ErrorCard key={q.questionId} question={q} tags={tags}
                onSubjectChange={(qId, newSubject) =>
                  setQuestions(qs => qs.map(x => x.questionId === qId ? { ...x, subject: newSubject } : x))
                }
              />
            ))}
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            showAll={showAll}
            onToggleShowAll={() => { setShowAll(v => !v); setPage(1) }}
          />
        </>
      )}
    </div>
  )
}
