import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from './contexts/AuthContext'
import './styles/App.css'
import Navbar from './components/layout/Navbar'
import LoginPage from './pages/auth/LoginPage'
import SignupPage from './pages/auth/SignupPage'
import CocktailsPage from './pages/CocktailsPage'
import CocktailDetailPage from './pages/CocktailDetailPage'
import CreateCocktailPage from './pages/CreateCocktailPage'
import IngredientsPage from './pages/IngredientsPage'
import CocktailScaler from './pages/cocktailScaler'
import InventoryPage from './pages/InventoryPage'
import OrdersPage from './pages/OrdersPage'
import EventsPage from './pages/EventsPage'
import EventDetailPage from './pages/EventDetailPage'
import EventFormPage from './pages/EventFormPage'
import ProtectedRoute from './components/layout/ProtectedRoute'

function App() {
  const { isAuthenticated } = useAuth()
  const { i18n, t } = useTranslation()

  useEffect(() => {
    const lang = (i18n.language || 'en').split('-')[0]
    const isHebrew = lang === 'he'
    document.documentElement.lang = isHebrew ? 'he' : 'en'
    document.documentElement.dir = isHebrew ? 'rtl' : 'ltr'

    // Inventory mobile "card" labels are rendered via CSS ::before.
    // CSS variables must contain quoted strings, so we JSON.stringify the value.
    const setVar = (name, value) => {
      document.documentElement.style.setProperty(name, JSON.stringify(String(value ?? '')))
    }
    setVar('--inv_lbl_name', t('inventory.columns.name'))
    setVar('--inv_lbl_subcategory', t('inventory.columns.subcategory'))
    setVar('--inv_lbl_ingredient', t('inventory.columns.ingredient'))
    setVar('--inv_lbl_qty', t('inventory.columns.qty'))
    setVar('--inv_lbl_reserved', t('inventory.columns.reserved'))
    setVar('--inv_lbl_unit', t('inventory.columns.unit'))
    setVar('--inv_lbl_price', t('inventory.columns.price'))
    setVar('--inv_lbl_bar_qty', t('inventory.columns.barQty'))
    setVar('--inv_lbl_wh_qty', t('inventory.columns.whQty'))
    setVar('--inv_lbl_status', t('inventory.columns.status'))
    setVar('--inv_lbl_actions', t('inventory.columns.actions'))
    setVar('--inv_lbl_when', t('inventory.columns.when'))
    setVar('--inv_lbl_location', t('inventory.columns.location'))
    setVar('--inv_lbl_item', t('inventory.columns.item'))
    setVar('--inv_lbl_change', t('inventory.columns.change'))
    setVar('--inv_lbl_reason', t('inventory.columns.reason'))

    // Orders mobile "card" labels (also rendered via CSS ::before)
    setVar('--orders_lbl_ingredient', t('orders.columns.ingredient'))
    setVar('--orders_lbl_needed', t('orders.columns.needed'))
    setVar('--orders_lbl_bottles', t('orders.columns.bottles'))
    setVar('--orders_lbl_actions', t('orders.columns.actions'))
  }, [i18n.language])

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
          <Route path="/cocktail-scaler" element={<CocktailScaler />} />
          <Route path="/cocktails/:id" element={<CocktailDetailPage />} />
          <Route path="/create-cocktail" element={<CreateCocktailPage />} />
          <Route path="/ingredients" element={<IngredientsPage />} />
          <Route
            path="/inventory"
            element={(
              <ProtectedRoute>
                <InventoryPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/orders"
            element={(
              <ProtectedRoute requireAdmin>
                <OrdersPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/events"
            element={(
              <ProtectedRoute requireAdmin>
                <EventsPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/events/new"
            element={(
              <ProtectedRoute requireAdmin>
                <EventFormPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/events/:id"
            element={(
              <ProtectedRoute requireAdmin>
                <EventDetailPage />
              </ProtectedRoute>
            )}
          />
          <Route
            path="/events/:id/edit"
            element={(
              <ProtectedRoute requireAdmin>
                <EventFormPage />
              </ProtectedRoute>
            )}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  )
}

export default App
