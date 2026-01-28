import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../contexts/AuthContext'

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false)
  const langMenuRef = useRef(null)
  const { t, i18n } = useTranslation()

  useEffect(() => {
    setIsMenuOpen(false)
    setIsLangMenuOpen(false)
  }, [location.pathname])

  const toggleMenu = () => setIsMenuOpen((prev) => !prev)
  const handleNavClick = () => setIsMenuOpen(false)
  const currentLang = (i18n.language || 'en').split('-')[0]
  const displayName = (() => {
    const first = (user?.first_name || '').trim()
    return first || user?.email || ''
  })()

  useEffect(() => {
    if (!isLangMenuOpen) return
    const onDown = (e) => {
      const el = langMenuRef.current
      if (!el) return
      if (e.target instanceof Node && !el.contains(e.target)) setIsLangMenuOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('touchstart', onDown, { passive: true })
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('touchstart', onDown)
    }
  }, [isLangMenuOpen])

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <Link to="/" className="navbar-title-link" onClick={handleNavClick}>
            <span className="navbar-title">{t('nav.title')}</span>
          </Link>
        </div>
        <button
          type="button"
          className="navbar-toggle"
          onClick={toggleMenu}
          aria-label={t('nav.toggleMenu')}
          aria-expanded={isMenuOpen}
        >
          <span />
          <span />
          <span />
        </button>
        <div className={`navbar-links ${isMenuOpen ? 'open' : ''}`}>
          <div className="navbar-nav">
            <Link
              to="/"
              className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
              onClick={handleNavClick}
            >
              {t('nav.cocktails')}
            </Link>
            <Link
              to="/ingredients"
              className={`nav-link ${location.pathname === '/ingredients' ? 'active' : ''}`}
              onClick={handleNavClick}
            >
              {t('nav.ingredients')}
            </Link>
            <Link
              to="/cocktail-scaler"
              className={`nav-link ${location.pathname === '/cocktail-scaler' ? 'active' : ''}`}
              onClick={handleNavClick}
            >
              {t('nav.scaler')}
            </Link>
            {isAuthenticated && (
              <Link
                to="/inventory"
                className={`nav-link ${location.pathname === '/inventory' ? 'active' : ''}`}
                onClick={handleNavClick}
              >
                {t('nav.inventory')}
              </Link>
            )}
          </div>

          <div className="navbar-auth">
            <div className="lang-toggle lang-toggle--dropdown" ref={langMenuRef}>
              <button
                type="button"
                className="lang-btn lang-btn--trigger"
                aria-haspopup="menu"
                aria-expanded={isLangMenuOpen}
                onClick={() => setIsLangMenuOpen((p) => !p)}
              >
                {currentLang === 'he' ? 'עברית' : 'EN'}
              </button>
              {isLangMenuOpen && (
                <div className="lang-menu" role="menu" aria-label={t('nav.language')}>
                  <button
                    type="button"
                    role="menuitem"
                    className={`lang-menu-item ${currentLang === 'en' ? 'active' : ''}`}
                    onClick={() => {
                      i18n.changeLanguage('en')
                      setIsLangMenuOpen(false)
                    }}
                  >
                    EN
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    className={`lang-menu-item ${currentLang === 'he' ? 'active' : ''}`}
                    onClick={() => {
                      i18n.changeLanguage('he')
                      setIsLangMenuOpen(false)
                    }}
                  >
                    עברית
                  </button>
                </div>
              )}
            </div>
            {isAuthenticated && user ? (
              <>
                <span className="navbar-user">{t('nav.welcome', { name: displayName })}</span>
                <button
                  onClick={() => {
                    handleNavClick()
                    logout()
                  }}
                  className="nav-link logout-button"
                >
                  {t('nav.logout')}
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link" onClick={handleNavClick}>{t('nav.login')}</Link>
                <Link to="/signup" className="nav-link" onClick={handleNavClick}>{t('nav.signup')}</Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar

