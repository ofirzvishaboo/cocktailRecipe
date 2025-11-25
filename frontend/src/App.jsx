import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import './App.css'
import Login from './components/Login'
import Signup from './components/Signup'
import CocktailsPage from './pages/CocktailsPage'
import Ingredients from './components/Ingredients'

function App() {
  const { isAuthenticated, user, logout } = useAuth()
  const location = useLocation()

  return (
    <>
      {/* Professional Navbar */}
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

      {/* Main Content */}
      <main className="main-content">
        <Routes>
          <Route path="/login" element={
            isAuthenticated ? <Navigate to="/" replace /> : <Login />
          } />
          <Route path="/signup" element={
            isAuthenticated ? <Navigate to="/" replace /> : <Signup />
          } />
          <Route path="/" element={<CocktailsPage />} />
          <Route path="/ingredients" element={<Ingredients />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}

export default App
