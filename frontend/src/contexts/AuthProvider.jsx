import { useState, useEffect } from 'react'
import api from '../api'
import { AuthContext } from './AuthContext'

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('/users/me')
      setUser(response.data)
    } catch (error) {
      console.error('Failed to fetch user:', error)
      // If token is invalid, clear it
      if (error.response?.status === 401) {
        setToken(null)
        setUser(null)
        localStorage.removeItem('token')
        delete api.defaults.headers.common['Authorization']
      }
    } finally {
      setLoading(false)
    }
  }

  // Set up axios interceptor to include token in requests
  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      // Fetch current user
      fetchCurrentUser()
    } else {
      delete api.defaults.headers.common['Authorization']
      setUser(null)
      setLoading(false)
    }
  }, [token])

  const login = async (email, password) => {
    try {
      const formData = new FormData()
      formData.append('username', email)
      formData.append('password', password)

      const response = await api.post('/auth/jwt/login', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const accessToken = response.data.access_token
      setToken(accessToken)
      localStorage.setItem('token', accessToken)
      api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`

      // Fetch user data
      await fetchCurrentUser()
      return { success: true }
    } catch (error) {
      console.error('Login failed:', error)
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed. Please check your credentials.',
      }
    }
  }

  const signup = async (email, password, firstName, lastName) => {
    try {
      await api.post('/auth/register', {
        email,
        password,
        first_name: (firstName || '').trim() || undefined,
        last_name: (lastName || '').trim() || undefined,
      })
      // After successful signup, automatically log in
      const loginResult = await login(email, password)
      return loginResult
    } catch (error) {
      console.error('Signup failed:', error)
      return {
        success: false,
        error: error.response?.data?.detail || 'Signup failed. Please try again.',
      }
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    setLoading(false)
  }

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    isAdmin: user?.is_superuser || false,
    login,
    signup,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthProvider

