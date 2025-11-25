import { useState, useEffect } from 'react'
import AddCocktailForm from '../components/addCocktailForm'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'

const CocktailsPage = () => {
  const { user, isAuthenticated } = useAuth()
  const [cocktails, setCocktails] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingCocktail, setEditingCocktail] = useState(null)
  const [failedImages, setFailedImages] = useState(new Set())

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

  // Check if the current user owns this cocktail
  const isOwner = (cocktail) => {
    return isAuthenticated && user && cocktail.user_id === user.id
  }

  return (
    <div className="card">
      {isAuthenticated ? (
        editingCocktail ? (
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
        )
      ) : (
        <div className="info-message">
          <p>Please <a href="/login">log in</a> to create and manage your own cocktail recipes.</p>
        </div>
      )}
      <div className="cocktails-list">
        <h3>All Cocktails</h3>
        {loading && <div>Loading...</div>}
        {error && <div className="error-message">{error}</div>}
        {!loading && !error && (
          <>
            {cocktails.length === 0 ? (
              <p>No cocktails found. {!isAuthenticated && 'Log in to create the first one!'}</p>
            ) : (
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
                            onError={() => {
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
                      {c.user && (
                        <span className="created-by">
                          Created by: {c.user.email}
                        </span>
                      )}
                      {c.created_at && (
                        <span className="created-at">
                          Created: {new Date(c.created_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                      {isAuthenticated && isOwner(c) && (
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
                      )}
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
          </>
        )}
      </div>
    </div>
  )
}

export default CocktailsPage

