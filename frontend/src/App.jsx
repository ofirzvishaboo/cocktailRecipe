import { useState, useEffect } from 'react'
import './App.css'
import AddCocktailForm from './components/addCocktailForm'
import Ingredients from './components/Ingredients'
import api from './api'

function App() {
  // Get active tab from URL hash, default to 'cocktails'
  const getActiveTabFromHash = () => {
    const hash = window.location.hash.slice(1) // Remove the '#'
    return hash === 'ingredients' ? 'ingredients' : 'cocktails'
  }

  const [activeTab, setActiveTab] = useState(getActiveTabFromHash)
  const [cocktails, setCocktails] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingCocktail, setEditingCocktail] = useState(null)
  const [failedImages, setFailedImages] = useState(new Set())

  // Listen for hash changes (browser back/forward buttons)
  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getActiveTabFromHash())
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Update URL hash when tab changes
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    window.location.hash = tab
  }

  const AddCocktail = (cocktail) => {
    setCocktails([...cocktails, cocktail])
  }

  const removeCocktail = async (cocktailId) => {
    try {
      await api.delete(`/cocktail-recipes/${cocktailId}`)
      setCocktails(cocktails.filter(c => c.id !== cocktailId))
    } catch (e) {
      setError('Failed to delete cocktail')
      console.error('Failed to delete cocktail', e)
    }
  }

  const editCocktail = (cocktail) => {
    if (!cocktail.id) {
      setError('Cannot edit cocktail without ID')
      return
    }
    setEditingCocktail(cocktail)
  }

  const updateCocktail = async (updatedCocktail) => {
    try {
      const response = await api.put(`/cocktail-recipes/${updatedCocktail.id}`, updatedCocktail)
      // Use the API response which includes all fields (created_at, image_url, etc.)
      const updatedCocktailFromApi = response.data
      setCocktails(cocktails.map(c => c.id === updatedCocktailFromApi.id ? updatedCocktailFromApi : c))
      setEditingCocktail(null)
    } catch (e) {
      setError('Failed to update cocktail')
      console.error('Failed to update cocktail', e)
    }
  }

  const cancelEdit = () => {
    setEditingCocktail(null)
  }

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const res = await api.get('/cocktail-recipes/')
        console.log('Loaded cocktails:', res.data)
        setCocktails(res.data || [])
      } catch (e) {
        setError('Failed to load cocktails')
        console.error('Failed to load cocktails', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <>
      {/* Professional Navbar */}
      <nav className="navbar">
        <div className="navbar-container">
          <h1 className="navbar-title">🍹 Cocktail Recipe Manager</h1>
          <div className="navbar-links">
            <button
              onClick={() => handleTabChange('cocktails')}
              className={`nav-link ${activeTab === 'cocktails' ? 'active' : ''}`}
            >
              Cocktails
            </button>
            <button
              onClick={() => handleTabChange('ingredients')}
              className={`nav-link ${activeTab === 'ingredients' ? 'active' : ''}`}
            >
              Ingredients
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">

      {/* Cocktails Tab */}
      {activeTab === 'cocktails' && (
        <div className="card">
          {editingCocktail ? (
            <div>
              <h3>Edit Cocktail</h3>
              <AddCocktailForm
                AddCocktail={updateCocktail}
                initialCocktail={editingCocktail}
                onCancel={cancelEdit}
                isEdit={true}
              />
            </div>
          ) : (
            <AddCocktailForm AddCocktail={AddCocktail} />
          )}
          <div className="cocktails-list">
            <h3>Cocktails</h3>
            {loading && <div>Loading...</div>}
            {error && <div className="error-message">{error}</div>}
            {!loading && !error && (
              <ul>
                {cocktails.map((c, idx) => (
                  <li key={`${c.name}-${idx}`}>
                    <div className="cocktail-item">
                      <div className="cocktail-info">
                        {c.image_url && !failedImages.has(c.id) ? (
                          <img
                            src={c.image_url}
                            alt={c.name}
                            className="cocktail-image"
                            onError={(e) => {
                              console.error('Failed to load image:', c.image_url, 'for cocktail:', c.name)
                              setFailedImages(prev => new Set(prev).add(c.id))
                            }}
                            onLoad={() => console.log('Image loaded successfully:', c.image_url)}
                          />
                        ) : (
                          <div className="cocktail-image-placeholder">
                            {c.image_url ? 'Invalid Image' : 'No Image'}
                          </div>
                        )}
                        <div className="cocktail-details">
                      <strong>{c.name}</strong>
                          {c.created_at && (
                            <span className="created-at">
                              Created: {new Date(c.created_at).toLocaleString()}
                            </span>
                          )}
                        </div>
                      </div>
                      <div>
                        <button
                          onClick={() => editCocktail(c)}
                          className="button-edit"
                          disabled={!c.id}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => removeCocktail(c.id)}
                          className="button-remove"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                    <ul>
                      {(c.ingredients || []).map((ing, i) => (
                        <li key={`${ing.name}-${i}`}>{ing.name} - {ing.ml} ml</li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Ingredients Tab */}
      {activeTab === 'ingredients' && (
        <Ingredients />
      )}
      </main>
    </>
  )
}

export default App
