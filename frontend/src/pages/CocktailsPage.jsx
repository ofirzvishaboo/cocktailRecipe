import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AddCocktailForm from '../components/cocktail/AddCocktailForm'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import ConfirmDialog from '../components/common/ConfirmDialog'

const CocktailsPage = () => {
  const { user, isAuthenticated, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [cocktails, setCocktails] = useState([])
  const [filteredCocktails, setFilteredCocktails] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingCocktail, setEditingCocktail] = useState(null)
  const [failedImages, setFailedImages] = useState(new Set())
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [pendingDeleteCocktailId, setPendingDeleteCocktailId] = useState(null)

  const getIngredientNames = (cocktail) => {
    const ris = cocktail?.recipe_ingredients
    if (Array.isArray(ris) && ris.length > 0) {
      return ris.map((ri) => (ri.ingredient_name || '').trim()).filter(Boolean)
    }
    return []
  }

  const getIngredientChips = (cocktail, max = 7) => {
    const names = getIngredientNames(cocktail)
    const shown = names.slice(0, max)
    const remaining = Math.max(0, names.length - shown.length)
    return { shown, remaining }
  }

  const requestRemoveCocktail = (cocktailId) => {
    setPendingDeleteCocktailId(cocktailId)
    setDeleteConfirmOpen(true)
  }

  const removeCocktail = async () => {
    const cocktailId = pendingDeleteCocktailId
    if (!cocktailId) return

    try {
      await api.delete(`/cocktail-recipes/${cocktailId}`)
      const updatedCocktails = cocktails.filter(c => c.id !== cocktailId)
      setCocktails(updatedCocktails)
      // Re-apply search filter
      if (!searchQuery.trim()) {
        setFilteredCocktails(updatedCocktails)
      } else {
        const query = searchQuery.toLowerCase().trim()

        // Check if query contains commas (multiple ingredient search)
        if (query.includes(',')) {
          const ingredientQueries = query.split(',').map(q => q.trim()).filter(q => q.length > 0)

          const filtered = updatedCocktails.filter(cocktail => {
            const names = getIngredientNames(cocktail).map((n) => n.toLowerCase())
            if (names.length === 0) return false

            return ingredientQueries.every((ingQuery) => {
              const q = (ingQuery || '').trim()
              if (!q) return true
              return names.some((n) => n.includes(q))
            })
          })
          setFilteredCocktails(filtered)
        } else {
          // Search by cocktail name OR single ingredient
          const filtered = updatedCocktails.filter(cocktail => {
            const nameMatch = cocktail.name && cocktail.name.toLowerCase().startsWith(query)
            const ingredientMatch = getIngredientNames(cocktail).some((n) => n.toLowerCase().includes(query))
            return nameMatch || ingredientMatch
          })
          setFilteredCocktails(filtered)
        }
      }
    } catch (e) {
      setError('Failed to delete cocktail')
      console.error('Failed to delete cocktail', e)
    } finally {
      setDeleteConfirmOpen(false)
      setPendingDeleteCocktailId(null)
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
      // AddCocktailForm already performs the API request and passes back the updated cocktail
      const updatedCocktailFromApi = updatedCocktail
      const updatedCocktails = cocktails.map(c => c.id === updatedCocktailFromApi.id ? updatedCocktailFromApi : c)
      setCocktails(updatedCocktails)
      setEditingCocktail(null)
      // Re-apply search filter
      if (!searchQuery.trim()) {
        setFilteredCocktails(updatedCocktails)
      } else {
        const query = searchQuery.toLowerCase().trim()

        // Check if query contains commas (multiple ingredient search)
        if (query.includes(',')) {
          const ingredientQueries = query.split(',').map(q => q.trim()).filter(q => q.length > 0)

          const filtered = updatedCocktails.filter(cocktail => {
            const names = getIngredientNames(cocktail).map((n) => n.toLowerCase())
            if (names.length === 0) return false

            return ingredientQueries.every((ingQuery) => {
              const q = (ingQuery || '').trim()
              if (!q) return true
              return names.some((n) => n.includes(q))
            })
          })
          setFilteredCocktails(filtered)
        } else {
          // Search by cocktail name OR single ingredient
          const filtered = updatedCocktails.filter(cocktail => {
            const nameMatch = cocktail.name && cocktail.name.toLowerCase().startsWith(query)
            const ingredientMatch = getIngredientNames(cocktail).some((n) => n.toLowerCase().includes(query))
            return nameMatch || ingredientMatch
          })
          setFilteredCocktails(filtered)
        }
      }
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
        setCocktails(res.data || [])
        setFilteredCocktails(res.data || [])
      } catch (e) {
        setError('Failed to load cocktails')
        console.error('Failed to load cocktails', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Filter cocktails based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredCocktails(cocktails)
    } else {
      const query = searchQuery.toLowerCase().trim()

      // Check if query contains commas (multiple ingredient search)
      if (query.includes(',')) {
        // Split by comma and filter out empty strings
        const ingredientQueries = query.split(',').map(q => q.trim()).filter(q => q.length > 0)

        const filtered = cocktails.filter(cocktail => {
          const names = getIngredientNames(cocktail).map((n) => n.toLowerCase())
          if (names.length === 0) return false

          // Each query must match at least one ingredient (substring match)
          return ingredientQueries.every((ingQuery) => {
            const q = (ingQuery || '').trim()
            if (!q) return true
            return names.some((n) => n.includes(q))
          })
        })
        setFilteredCocktails(filtered)
      } else {
        // Search by cocktail name OR single ingredient
        const filtered = cocktails.filter(cocktail => {
          // Check if name matches
          const nameMatch = cocktail.name && cocktail.name.toLowerCase().startsWith(query)

          // Check if any ingredient matches
          const ingredientMatch = getIngredientNames(cocktail).some((n) => n.toLowerCase().includes(query))

          return nameMatch || ingredientMatch
        })
        setFilteredCocktails(filtered)
      }
    }
  }, [searchQuery, cocktails])

  const classicCocktails = useMemo(() => {
    return (filteredCocktails || []).filter((c) => !!c?.is_base)
  }, [filteredCocktails])

  const signatureCocktails = useMemo(() => {
    return (filteredCocktails || []).filter((c) => !c?.is_base)
  }, [filteredCocktails])

  // Check if the current user owns this cocktail
  const isOwner = (cocktail) => {
    return isAuthenticated && user && (isAdmin || cocktail.created_by_user_id === user.id)
  }

  return (
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
        <>
          <div className="cocktails-header">
            <div className={`search-container ${!isAuthenticated ? 'search-container-full' : ''}`}>
              <input
                type="text"
                placeholder="Search by name or ingredients (e.g., vodka, lime)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>
            {isAuthenticated && (
              <button
                onClick={() => navigate('/create-cocktail')}
                className="button-primary"
              >
                Create Cocktail
              </button>
            )}
          </div>

          <div className="cocktails-list">

            {loading && <div className="loading">Loading...</div>}
            {error && <div className="error-message">{error}</div>}
            {!loading && !error && (
              <>
                {(classicCocktails.length === 0 && signatureCocktails.length === 0) ? (
                  <p>
                    {searchQuery.trim()
                      ? `No cocktails found matching "${searchQuery}"`
                      : cocktails.length === 0
                        ? `No cocktails found. ${!isAuthenticated ? 'Log in to create the first one!' : ''}`
                        : 'No cocktails match your search.'}
                  </p>
                ) : (
                  <>
                    <h3>Classic Cocktails</h3>
                    {classicCocktails.length === 0 ? (
                      <div className="empty-state">
                        {searchQuery.trim()
                          ? `No classic cocktails match "${searchQuery}"`
                          : 'No classic cocktails yet.'}
                      </div>
                    ) : (
                      <ul className="cocktails-grid">
                        {classicCocktails.map((c) => {
                          const chips = getIngredientChips(c)
                          return (
                            <li key={c.id || c.name}>
                              <div className="cocktail-card">
                                <Link to={`/cocktails/${c.id}`} className="cocktail-card-link">
                                  <div className="cocktail-card-media">
                                    {c.picture_url && !failedImages.has(c.id) ? (
                                      <img
                                        src={c.picture_url}
                                        alt={c.name}
                                        className="cocktail-card-image"
                                        onError={() => {
                                          setFailedImages((prev) => new Set(prev).add(c.id))
                                        }}
                                      />
                                    ) : (
                                      <div className="cocktail-card-image-placeholder">
                                        {c.picture_url ? 'Invalid Image' : 'No Image'}
                                      </div>
                                    )}
                                  </div>
                                  <div className="cocktail-card-body">
                                    <div className="cocktail-card-title">{c.name}</div>
                                    {(chips.shown.length > 0) && (
                                      <div className="ingredient-chips">
                                        {chips.shown.map((name) => (
                                          <span key={name} className="ingredient-chip">{name}</span>
                                        ))}
                                        {chips.remaining > 0 && (
                                          <span className="ingredient-chip ingredient-chip-more">+{chips.remaining} more</span>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </Link>

                                {isAuthenticated && isOwner(c) && (
                                  <div className="cocktail-card-actions">
                                    <button
                                      onClick={() => editCocktail(c)}
                                      className="button-edit"
                                      disabled={!c.id}
                                    >
                                      Edit
                                    </button>
                                    <button
                                      onClick={() => requestRemoveCocktail(c.id)}
                                      className="button-remove"
                                    >
                                      Remove
                                    </button>
                                  </div>
                                )}
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    )}

                    <h3 style={{ marginTop: '1.5rem' }}>Signature Cocktails</h3>
                    {signatureCocktails.length === 0 ? (
                      <div className="empty-state">
                        {searchQuery.trim()
                          ? `No signature cocktails match "${searchQuery}"`
                          : 'No signature cocktails yet.'}
                      </div>
                    ) : (
                      <ul className="cocktails-grid">
                        {signatureCocktails.map((c) => {
                          const chips = getIngredientChips(c)
                          return (
                            <li key={c.id || c.name}>
                              <div className="cocktail-card">
                                <Link to={`/cocktails/${c.id}`} className="cocktail-card-link">
                                  <div className="cocktail-card-media">
                                    {c.picture_url && !failedImages.has(c.id) ? (
                                      <img
                                        src={c.picture_url}
                                        alt={c.name}
                                        className="cocktail-card-image"
                                        onError={() => {
                                          setFailedImages((prev) => new Set(prev).add(c.id))
                                        }}
                                      />
                                    ) : (
                                      <div className="cocktail-card-image-placeholder">
                                        {c.picture_url ? 'Invalid Image' : 'No Image'}
                                      </div>
                                    )}
                                  </div>
                                  <div className="cocktail-card-body">
                                    <div className="cocktail-card-title">{c.name}</div>
                                    {(chips.shown.length > 0) && (
                                      <div className="ingredient-chips">
                                        {chips.shown.map((name) => (
                                          <span key={name} className="ingredient-chip">{name}</span>
                                        ))}
                                        {chips.remaining > 0 && (
                                          <span className="ingredient-chip ingredient-chip-more">+{chips.remaining} more</span>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </Link>

                                {isAuthenticated && isOwner(c) && (
                                  <div className="cocktail-card-actions">
                                    <button
                                      onClick={() => editCocktail(c)}
                                      className="button-edit"
                                      disabled={!c.id}
                                    >
                                      Edit
                                    </button>
                                    <button
                                      onClick={() => requestRemoveCocktail(c.id)}
                                      className="button-remove"
                                    >
                                      Remove
                                    </button>
                                  </div>
                                )}
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </>
      )}

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Delete cocktail?"
        message={`Are you sure you want to delete "${cocktails.find(c => c.id === pendingDeleteCocktailId)?.name || ''}"? This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onCancel={() => {
          setDeleteConfirmOpen(false)
          setPendingDeleteCocktailId(null)
        }}
        onConfirm={removeCocktail}
      />
    </div>
  )
}

export default CocktailsPage

