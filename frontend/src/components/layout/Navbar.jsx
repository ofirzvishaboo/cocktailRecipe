import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../contexts/AuthContext'

const Navbar = () => {
  const { isAuthenticated, isAdmin, isBartender, hasStaffProfile, user, logout } = useAuth()
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false)
  const [isAdminMenuOpen, setIsAdminMenuOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const langMenuRef = useRef(null)
  const adminMenuRef = useRef(null)
  const userMenuRef = useRef(null)
  const { t, i18n } = useTranslation()

  const isAdminPage = ['/dashboard', '/orders', '/schedule', '/checklists/history'].includes(location.pathname)
    || location.pathname.startsWith('/events')

  const hasStaffSection = isAuthenticated && ((isBartender || isAdmin) || hasStaffProfile)

  useEffect(() => {
    setIsMenuOpen(false)
    setIsLangMenuOpen(false)
    setIsAdminMenuOpen(false)
    setIsUserMenuOpen(false)
  }, [location.pathname])

  const handleNavClick = () => setIsMenuOpen(false)

  const currentLang = (i18n.language || 'en').split('-')[0]
  const displayName = (() => {
    const first = (user?.first_name || '').trim()
    return first || user?.email || ''
  })()

  useEffect(() => {
    const menus = [
      { open: isLangMenuOpen, ref: langMenuRef, close: () => setIsLangMenuOpen(false) },
      { open: isAdminMenuOpen, ref: adminMenuRef, close: () => setIsAdminMenuOpen(false) },
      { open: isUserMenuOpen, ref: userMenuRef, close: () => setIsUserMenuOpen(false) },
    ]
    const anyOpen = menus.some(m => m.open)
    if (!anyOpen) return

    const onDown = (e) => {
      menus.forEach(({ open, ref, close }) => {
        if (!open) return
        const el = ref.current
        if (el && e.target instanceof Node && !el.contains(e.target)) close()
      })
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('touchstart', onDown, { passive: true })
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('touchstart', onDown)
    }
  }, [isLangMenuOpen, isAdminMenuOpen, isUserMenuOpen])

  return (
    <nav className="app-navbar">
      <div className="navbar-container">

        <div className="navbar-left">
          <Link
            to={{ pathname: '/', search: location.pathname === '/' ? location.search : '' }}
            className="navbar-title-link"
            onClick={handleNavClick}
          >
            <span className="navbar-title">{t('nav.title')}</span>
          </Link>
        </div>

        <button
          type="button"
          className="navbar-toggle"
          onClick={() => setIsMenuOpen((prev) => !prev)}
          aria-label={t('nav.toggleMenu')}
          aria-expanded={isMenuOpen}
        >
          <span />
          <span />
          <span />
        </button>

        <div className={`navbar-links ${isMenuOpen ? 'open' : ''}`}>
          <div className="navbar-nav">

            {/* ── כלים יומיומיים ── */}
            <span className="navbar-section-label">{t('nav.sections.tools')}</span>
            <Link
              to={{ pathname: '/', search: location.pathname === '/' ? location.search : '' }}
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

            {/* ── צוות ── */}
            {hasStaffSection && (
              <span className="navbar-section-label">{t('nav.sections.staff')}</span>
            )}
            {isAuthenticated && (isBartender || isAdmin) && (
              <Link
                to="/checklists"
                className={`nav-link ${location.pathname === '/checklists' ? 'active' : ''}`}
                onClick={handleNavClick}
              >
                {t('nav.checklists')}
              </Link>
            )}
            {isAuthenticated && hasStaffProfile && (
              <Link
                to="/my-schedule"
                className={`nav-link nav-link--emphasis ${location.pathname === '/my-schedule' ? 'active' : ''}`}
                onClick={handleNavClick}
              >
                {t('nav.mySchedule')}
              </Link>
            )}

            {/* ── תפעול ── */}
            {isAuthenticated && (
              <>
                <span className="navbar-section-label">{t('nav.sections.operations')}</span>
                <Link
                  to="/inventory"
                  className={`nav-link ${location.pathname === '/inventory' ? 'active' : ''}`}
                  onClick={handleNavClick}
                >
                  {t('nav.inventory')}
                </Link>
              </>
            )}

            {/* ── ניהול ── */}
            {isAuthenticated && isAdmin && (
              <>
                {/* Desktop: dropdown */}
                <div className="nav-dropdown nav-desktop-only" ref={adminMenuRef}>
                  <button
                    type="button"
                    className={`nav-link nav-dropdown-trigger ${isAdminPage ? 'active' : ''}`}
                    onClick={() => setIsAdminMenuOpen((p) => !p)}
                    aria-haspopup="menu"
                    aria-expanded={isAdminMenuOpen}
                  >
                    {t('nav.sections.management')}
                  </button>
                  {isAdminMenuOpen && (
                    <div className="nav-dropdown-menu" role="menu">
                      <Link
                        to="/dashboard"
                        className={`nav-dropdown-item ${location.pathname === '/dashboard' ? 'active' : ''}`}
                        onClick={() => { handleNavClick(); setIsAdminMenuOpen(false) }}
                      >
                        {t('nav.dashboard')}
                      </Link>
                      <Link
                        to="/orders"
                        className={`nav-dropdown-item ${location.pathname === '/orders' ? 'active' : ''}`}
                        onClick={() => { handleNavClick(); setIsAdminMenuOpen(false) }}
                      >
                        {t('nav.orders')}
                      </Link>
                      <Link
                        to="/events"
                        className={`nav-dropdown-item ${location.pathname.startsWith('/events') ? 'active' : ''}`}
                        onClick={() => { handleNavClick(); setIsAdminMenuOpen(false) }}
                      >
                        {t('nav.events')}
                      </Link>
                      <Link
                        to="/schedule"
                        className={`nav-dropdown-item ${location.pathname === '/schedule' ? 'active' : ''}`}
                        onClick={() => { handleNavClick(); setIsAdminMenuOpen(false) }}
                      >
                        {t('nav.schedule')}
                      </Link>
                      <Link
                        to="/checklists/history"
                        className={`nav-dropdown-item ${location.pathname === '/checklists/history' ? 'active' : ''}`}
                        onClick={() => { handleNavClick(); setIsAdminMenuOpen(false) }}
                      >
                        {t('nav.checklistHistory')}
                      </Link>
                    </div>
                  )}
                </div>

                {/* Mobile: section + individual links */}
                <span className="navbar-section-label nav-mobile-only">{t('nav.sections.management')}</span>
                <Link
                  to="/dashboard"
                  className={`nav-link nav-mobile-only ${location.pathname === '/dashboard' ? 'active' : ''}`}
                  onClick={handleNavClick}
                >
                  {t('nav.dashboard')}
                </Link>
                <Link
                  to="/orders"
                  className={`nav-link nav-mobile-only ${location.pathname === '/orders' ? 'active' : ''}`}
                  onClick={handleNavClick}
                >
                  {t('nav.orders')}
                </Link>
                <Link
                  to="/events"
                  className={`nav-link nav-mobile-only ${location.pathname.startsWith('/events') ? 'active' : ''}`}
                  onClick={handleNavClick}
                >
                  {t('nav.events')}
                </Link>
                <Link
                  to="/schedule"
                  className={`nav-link nav-mobile-only ${location.pathname === '/schedule' ? 'active' : ''}`}
                  onClick={handleNavClick}
                >
                  {t('nav.schedule')}
                </Link>
                <Link
                  to="/checklists/history"
                  className={`nav-link nav-mobile-only ${location.pathname === '/checklists/history' ? 'active' : ''}`}
                  onClick={handleNavClick}
                >
                  {t('nav.checklistHistory')}
                </Link>
              </>
            )}
          </div>

          {/* ── אזור משתמש ── */}
          <div className="navbar-auth">
            <span className="navbar-section-label">{t('nav.sections.account')}</span>

            {/* Language toggle */}
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
                    onClick={() => { i18n.changeLanguage('en'); setIsLangMenuOpen(false) }}
                  >
                    EN
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    className={`lang-menu-item ${currentLang === 'he' ? 'active' : ''}`}
                    onClick={() => { i18n.changeLanguage('he'); setIsLangMenuOpen(false) }}
                  >
                    עברית
                  </button>
                </div>
              )}
            </div>

            {isAuthenticated && user ? (
              <>
                {/* Desktop: user dropdown */}
                <div className="nav-user-dropdown nav-desktop-only" ref={userMenuRef}>
                  <button
                    type="button"
                    className="nav-link nav-user-trigger"
                    onClick={() => setIsUserMenuOpen((p) => !p)}
                    aria-haspopup="menu"
                    aria-expanded={isUserMenuOpen}
                  >
                    {displayName}
                  </button>
                  {isUserMenuOpen && (
                    <div className="nav-dropdown-menu nav-user-menu" role="menu">
                      <button
                        type="button"
                        role="menuitem"
                        className="nav-dropdown-item nav-dropdown-item--danger"
                        onClick={() => { logout(); setIsUserMenuOpen(false) }}
                      >
                        {t('nav.logout')}
                      </button>
                    </div>
                  )}
                </div>

                {/* Mobile: welcome text + logout button */}
                <span className="navbar-user nav-mobile-only">
                  {t('nav.welcome', { name: displayName })}
                </span>
                <button
                  type="button"
                  className="nav-link logout-button nav-mobile-only"
                  onClick={() => { handleNavClick(); logout() }}
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
