// frontend/src/components/NavBar.jsx
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function NavBar() {
  const { signOut } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await signOut()
    navigate('/login')
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold text-indigo-600">错题本</Link>
      <div className="flex items-center gap-6">
        <Link to="/" className="text-sm text-gray-600 hover:text-indigo-600">概览</Link>
        <Link to="/upload" className="text-sm text-gray-600 hover:text-indigo-600">上传题目</Link>
        <Link to="/errors" className="text-sm text-gray-600 hover:text-indigo-600">错题库</Link>
        <Link to="/tags" className="text-sm text-gray-600 hover:text-indigo-600">标签管理</Link>
        <button onClick={handleSignOut} className="text-sm text-gray-400 hover:text-red-500">退出</button>
      </div>
    </nav>
  )
}
