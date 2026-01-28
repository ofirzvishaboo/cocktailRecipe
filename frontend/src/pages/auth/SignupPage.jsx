import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../contexts/AuthContext'
import '../../styles/auth.css'

const SignupPage = () => {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signup } = useAuth()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Validate passwords match
    if (password !== confirmPassword) {
      setError(t('auth.signup.passwordsNoMatch'))
      return
    }

    // Validate password length
    if (password.length < 8) {
      setError(t('auth.signup.passwordTooShort'))
      return
    }

    setLoading(true)

    const result = await signup(email, password, firstName, lastName)

    if (result.success) {
      navigate('/')
    } else {
      setError(result.error)
    }

    setLoading(false)
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>{t('auth.signup.title')}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="firstName">{t('auth.signup.firstName')}</label>
            <input
              type="text"
              id="firstName"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              required
              placeholder={t('auth.signup.firstNamePlaceholder')}
            />
          </div>

          <div className="form-group">
            <label htmlFor="lastName">{t('auth.signup.lastName')}</label>
            <input
              type="text"
              id="lastName"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              required
              placeholder={t('auth.signup.lastNamePlaceholder')}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">{t('auth.signup.email')}</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder={t('auth.signup.emailPlaceholder')}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">{t('auth.signup.password')}</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder={t('auth.signup.passwordPlaceholder')}
              minLength={8}
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">{t('auth.signup.confirmPassword')}</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              placeholder={t('auth.signup.confirmPasswordPlaceholder')}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? t('auth.signup.submitting') : t('auth.signup.submit')}
          </button>
        </form>

        <p className="auth-link">
          {t('auth.signup.haveAccount')} <Link to="/login">{t('auth.signup.loginLink')}</Link>
        </p>
      </div>
    </div>
  )
}

export default SignupPage

