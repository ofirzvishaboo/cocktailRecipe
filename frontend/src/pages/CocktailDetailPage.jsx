import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import AddCocktailForm from '../components/cocktail/AddCocktailForm'
import ConfirmDialog from '../components/common/ConfirmDialog'

const CocktailDetailPage = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, isAuthenticated, isAdmin } = useAuth()
  const [cocktail, setCocktail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  useEffect(() => {
    const loadCocktail = async () => {
      try {
        setLoading(true)
        setError('')
        const response = await api.get(`/cocktail-recipes/${id}`)
        setCocktail(response.data)
      } catch (e) {
        if (e.response?.status === 404) {
          setError('Cocktail not found')
        } else {
          setError('Failed to load cocktail')
          console.error('Failed to load cocktail', e)
        }
      } finally {
        setLoading(false)
      }
    }
    loadCocktail()
  }, [id])

  const handleDelete = async () => {
    try {
      await api.delete(`/cocktail-recipes/${id}`)
      navigate('/')
    } catch (e) {
      setError('Failed to delete cocktail')
      console.error('Failed to delete cocktail', e)
    } finally {
      setDeleteConfirmOpen(false)
    }
  }

  const handleUpdate = async (updatedCocktail) => {
    try {
      // AddCocktailForm already performs the API request and passes back the updated cocktail
      setCocktail(updatedCocktail)
      setEditing(false)
    } catch (e) {
      setError('Failed to update cocktail')
      console.error('Failed to update cocktail', e)
    }
  }

  const isOwner = () => {
    return isAuthenticated && user && cocktail && (isAdmin || cocktail.created_by_user_id === user.id)
  }

  if (loading) {
    return (
      <div className="card">
        <div className="loading">Loading cocktail...</div>
      </div>
    )
  }

  if (error && !cocktail) {
    return (
      <div className="card">
        <div className="error-message">{error}</div>
        <Link to="/" className="button-primary">Back to Cocktails</Link>
      </div>
    )
  }

  if (!cocktail) {
    return null
  }

  if (editing) {
    return (
      <div className="card">
        <h2>Edit Cocktail</h2>
        <AddCocktailForm
          AddCocktail={handleUpdate}
          initialCocktail={cocktail}
          onCancel={() => setEditing(false)}
          isEdit={true}
        />
      </div>
    )
  }

  return (
    <div className="card">
      <div className="cocktail-detail-header">
        <Link to="/" className="back-link">← Back to Cocktails</Link>
      </div>

      <div className="cocktail-detail-content">
        <div className="cocktail-detail-image">
          {(cocktail.picture_url || cocktail.image_url) && !imageError ? (
            <img
              src={cocktail.picture_url || cocktail.image_url}
              alt={cocktail.name}
              className="cocktail-detail-image-large"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="cocktail-image-placeholder-large">
              {(cocktail.picture_url || cocktail.image_url) ? 'Invalid Image' : 'No Image'}
            </div>
          )}
        </div>

        <div className="cocktail-detail-info">
          <div className="cocktail-title-row">
            <h1 className="cocktail-detail-title">{cocktail.name}</h1>
            {isOwner() && (
              <div className="cocktail-actions-inline">
                <button
                  onClick={() => setEditing(true)}
                  className="button-edit"
                >
                  Edit
                </button>
                <button
                  onClick={() => setDeleteConfirmOpen(true)}
                  className="button-remove"
                >
                  Delete
                </button>
              </div>
            )}
          </div>

          {cocktail.description && (
            <div className="cocktail-description">
              <p>{cocktail.description}</p>
            </div>
          )}

          <div className="cocktail-meta">
            {cocktail.user && (
              <div className="meta-item">
                <strong>Created by:</strong> {cocktail.user.email}
              </div>
            )}
            {cocktail.created_at && (
              <div className="meta-item">
                <strong>Created:</strong> {new Date(cocktail.created_at).toLocaleString()}
              </div>
            )}
          </div>

          <div className="cocktail-ingredients-section">
            <h2>Ingredients</h2>
            {(cocktail.recipe_ingredients && cocktail.recipe_ingredients.length > 0) ? (
              <ul className="ingredients-list-detailed">
                {cocktail.recipe_ingredients.map((ri, i) => (
                  <li key={`${ri.ingredient_id}-${i}`} className="ingredient-item-detailed">
                    <span className="ingredient-name">{ri.ingredient_name || 'Unknown'}</span>
                    <span className="ingredient-brand">{ri.bottle_name || '-'}</span>
                    <span className="ingredient-amount">
                      {ri.quantity} {ri.unit}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (cocktail.ingredients && cocktail.ingredients.length > 0 ? (
              <ul className="ingredients-list-detailed">
                {cocktail.ingredients.map((ing, i) => (
                  <li key={`${ing.name}-${i}`} className="ingredient-item-detailed">
                    <span className="ingredient-name">{ing.name}</span>
                    <span className="ingredient-brand">-</span>
                    <span className="ingredient-amount">{ing.ml} ml</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No ingredients listed.</p>
            ))}
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Delete cocktail?"
        message={`Are you sure you want to delete "${cocktail.name}"? This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onCancel={() => setDeleteConfirmOpen(false)}
        onConfirm={handleDelete}
      />
    </div>
  )
}

export default CocktailDetailPage

