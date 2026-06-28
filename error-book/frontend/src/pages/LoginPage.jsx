// frontend/src/pages/LoginPage.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { signIn, signUp, confirmSignUp } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')  // login | register | confirm
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await signIn(email, password)
        navigate('/')
      } else if (mode === 'register') {
        await signUp(email, password)
        setMode('confirm')
      } else {
        await confirmSignUp(email, code)
        setMode('login')
      }
    } catch (err) {
      setError(err.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-md p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-indigo-600 mb-6 text-center">错题本</h1>
        <h2 className="text-lg font-semibold text-gray-700 mb-4 text-center">
          {mode === 'login' ? '登录' : mode === 'register' ? '注册' : '验证邮箱'}
        </h2>
        {error && <p className="text-red-500 text-sm mb-4 text-center">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode !== 'confirm' && (
            <>
              <input type="email" placeholder="邮箱" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" required />
              <input type="password" placeholder="密码（8位以上，含大小写和数字）" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" required />
            </>
          )}
          {mode === 'confirm' && (
            <input type="text" placeholder="请输入邮箱验证码" value={code} onChange={e => setCode(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400" required />
          )}
          <button type="submit" disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50">
            {loading ? '处理中...' : mode === 'login' ? '登录' : mode === 'register' ? '注册' : '验证'}
          </button>
        </form>
        {mode !== 'confirm' && (
          <p className="text-center text-sm text-gray-500 mt-4">
            {mode === 'login' ? '没有账号？' : '已有账号？'}
            <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              className="text-indigo-600 font-medium ml-1 hover:underline">
              {mode === 'login' ? '注册' : '登录'}
            </button>
          </p>
        )}
      </div>
    </div>
  )
}
