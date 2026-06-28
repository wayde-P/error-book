// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { UploadProvider } from './contexts/UploadContext'
import { setTokenGetter } from './api/client'
import NavBar from './components/NavBar'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ErrorBankPage from './pages/ErrorBankPage'
import ErrorDetailPage from './pages/ErrorDetailPage'
import TagsPage from './pages/TagsPage'

function ProtectedLayout() {
  const { user, getToken } = useAuth()
  setTokenGetter(getToken)
  if (!user) return <Navigate to="/login" replace />
  return (
    <UploadProvider>
      <NavBar />
      <main className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/errors" element={<ErrorBankPage />} />
          <Route path="/errors/:id" element={<ErrorDetailPage />} />
          <Route path="/tags" element={<TagsPage />} />
        </Routes>
      </main>
    </UploadProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
