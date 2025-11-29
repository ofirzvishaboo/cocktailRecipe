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
        <Link to="/" className="navbar-title-link">
          <h1 className="navbar-title">🍹 Cocktail Recipe Manager</h1>
        </Link>
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
    </nav>
  )
}

export default Navbar

