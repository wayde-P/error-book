// frontend/src/components/SearchBar.jsx
import { useState } from 'react'

export default function SearchBar({ onSearch, placeholder = '搜索题目内容...' }) {
  const [value, setValue] = useState('')

  function handleKeyDown(e) {
    if (e.key === 'Enter') onSearch(value.trim())
  }

  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full border border-gray-300 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <span className="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
    </div>
  )
}
