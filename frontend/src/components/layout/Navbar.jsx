import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const location = useLocation()

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-title-link">
          <h1 className="navbar-title">🍹 Cocktail Recipe Manager</h1>
        </Link>
        <div className="navbar-links">
          <Link
            to="/"
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            Cocktails
          </Link>
          <Link
            to="/ingredients"
            className={`nav-link ${location.pathname === '/ingredients' ? 'active' : ''}`}
          >
            Ingredients
          </Link>
          <Link
            to="/cocktail-scaler"
            className={`nav-link ${location.pathname === '/cocktail-scaler' ? 'active' : ''}`}
          >
            Cocktail Scaler
          </Link>
          {isAuthenticated && user ? (
            <>
              <span className="navbar-user">Welcome, {user.email}</span>
              <button onClick={logout} className="nav-link logout-button">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link">Login</Link>
              <Link to="/signup" className="nav-link">Sign Up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar

