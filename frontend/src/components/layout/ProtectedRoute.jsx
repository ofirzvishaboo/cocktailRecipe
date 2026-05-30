import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../contexts/AuthContext'

const ProtectedRoute = ({ children, requireAdmin = false, requireBartender = false }) => {
  const { isAuthenticated, isAdmin, isBartender, loading } = useAuth()
  const { t } = useTranslation()

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh'
      }}>
        <div>{t('common.loading')}</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/" replace />
  }

  if (requireBartender && !isBartender) {
    return <Navigate to="/" replace />
  }

  return children
}

export default ProtectedRoute

