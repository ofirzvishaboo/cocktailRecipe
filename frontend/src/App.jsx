import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import './styles/App.css'
import Navbar from './components/layout/Navbar'
import LoginPage from './pages/auth/LoginPage'
import SignupPage from './pages/auth/SignupPage'
import CocktailsPage from './pages/CocktailsPage'
import CocktailDetailPage from './pages/CocktailDetailPage'
import CreateCocktailPage from './pages/CreateCocktailPage'
import IngredientsPage from './pages/IngredientsPage'

function App() {
  const { isAuthenticated } = useAuth()

  return (
    <>
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/login" element={
            isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
          } />
          <Route path="/signup" element={
            isAuthenticated ? <Navigate to="/" replace /> : <SignupPage />
          } />
          <Route path="/" element={<CocktailsPage />} />
          <Route path="/cocktails/:id" element={<CocktailDetailPage />} />
          <Route path="/create-cocktail" element={<CreateCocktailPage />} />
          <Route path="/ingredients" element={<IngredientsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}

export default App
