import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  useEffect(() => {
    setIsMenuOpen(false)
  }, [location.pathname])

  const toggleMenu = () => setIsMenuOpen((prev) => !prev)
  const handleNavClick = () => setIsMenuOpen(false)

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <Link to="/" className="navbar-title-link" onClick={handleNavClick}>
            <span className="navbar-title">Cocktail Recipe Manager</span>
          </Link>
        </div>
        <button
          type="button"
          className="navbar-toggle"
          onClick={toggleMenu}
          aria-label="Toggle navigation menu"
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
              Cocktails
            </Link>
            <Link
              to="/ingredients"
              className={`nav-link ${location.pathname === '/ingredients' ? 'active' : ''}`}
              onClick={handleNavClick}
            >
              Ingredients
            </Link>
            <Link
              to="/cocktail-scaler"
              className={`nav-link ${location.pathname === '/cocktail-scaler' ? 'active' : ''}`}
              onClick={handleNavClick}
            >
              Cocktail Scaler
            </Link>
          </div>

          <div className="navbar-auth">
            {isAuthenticated && user ? (
              <>
                <span className="navbar-user">Welcome, {user.email}</span>
                <button
                  onClick={() => {
                    handleNavClick()
                    logout()
                  }}
                  className="nav-link logout-button"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link" onClick={handleNavClick}>Login</Link>
                <Link to="/signup" className="nav-link" onClick={handleNavClick}>Sign Up</Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar

