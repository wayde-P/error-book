// frontend/src/contexts/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react'
import { Amplify } from 'aws-amplify'
import { signIn, signUp, signOut, confirmSignUp, fetchAuthSession, getCurrentUser } from 'aws-amplify/auth'

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
      loginWith: { email: true },
    },
  },
})

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function getToken() {
    const session = await fetchAuthSession()
    return session.tokens?.idToken?.toString()
  }

  const value = {
    user,
    loading,
    getToken,
    signIn: async (email, password) => {
      const result = await signIn({ username: email, password })
      const u = await getCurrentUser()
      setUser(u)
      return result
    },
    signUp: (email, password) => signUp({ username: email, password, options: { userAttributes: { email } } }),
    confirmSignUp: (email, code) => confirmSignUp({ username: email, confirmationCode: code }),
    signOut: async () => { await signOut(); setUser(null) },
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center"><span className="text-gray-500">加载中...</span></div>

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
