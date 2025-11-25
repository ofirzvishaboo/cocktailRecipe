import { useState, useEffect } from 'react'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'

function Ingredients() {
  const { isAdmin } = useAuth()
  const [ingredients, setIngredients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingIngredient, setEditingIngredient] = useState(null)
  const [form, setForm] = useState({
    name: '',
    submitting: false,
  })

  useEffect(() => {
    loadIngredients()
  }, [])

  const loadIngredients = async () => {
    try {
      setLoading(true)
      const res = await api.get('/ingredients/')
      setIngredients(res.data || [])
      setError('')
    } catch (e) {
      setError('Failed to load ingredients')
      console.error('Failed to load ingredients', e)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return

    try {
      setForm(prev => ({ ...prev, submitting: true }))

      if (editingIngredient) {
        // Update existing ingredient
        await api.put(`/ingredients/${editingIngredient.id}`, { name: form.name })
        setIngredients(ingredients.map(ing =>
          ing.id === editingIngredient.id
            ? { ...ing, name: form.name }
            : ing
        ))
        setEditingIngredient(null)
      } else {
        // Create new ingredient
        const res = await api.post('/ingredients/', { name: form.name })
        setIngredients([...ingredients, res.data])
      }

      setForm({ name: '', submitting: false })
    } catch (e) {
      setError(editingIngredient ? 'Failed to update ingredient' : 'Failed to create ingredient')
      console.error('Failed to save ingredient', e)
    } finally {
      setForm(prev => ({ ...prev, submitting: false }))
    }
  }

  const removeIngredient = async (ingredientId) => {
    try {
      await api.delete(`/ingredients/${ingredientId}`)
      setIngredients(ingredients.filter(ing => ing.id !== ingredientId))
    } catch (e) {
      setError('Failed to delete ingredient')
      console.error('Failed to delete ingredient', e)
    }
  }

  const editIngredient = (ingredient) => {
    setEditingIngredient(ingredient)
    setForm({ name: ingredient.name, submitting: false })
  }

  const cancelEdit = () => {
    setEditingIngredient(null)
    setForm({ name: '', submitting: false })
  }

  return (
    <div className="card">
      <h2 className="section-title">Ingredients Management</h2>

      {isAdmin ? (
        <form onSubmit={handleSubmit} className="ingredient-form">
          <div className="form-row">
            <input
              type="text"
              placeholder="Ingredient name"
              value={form.name}
              onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
              className="form-input"
            />
            <button
              type="submit"
              disabled={form.submitting || !form.name.trim()}
              className="button-primary"
            >
              {editingIngredient ? 'Update' : 'Add'} Ingredient
            </button>
            {editingIngredient && (
              <button
                type="button"
                onClick={cancelEdit}
                className="button-secondary"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      ) : (
        <div className="info-message">
          <p>Only administrators can add, edit, or remove ingredients.</p>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="ingredients-list">
        <h3>All Ingredients</h3>
        {loading && <div className="loading">Loading...</div>}
        {!loading && (
          <ul>
            {ingredients.length === 0 ? (
              <li className="empty-state">
                No ingredients yet. {!isAdmin && 'Only administrators can add ingredients.'}
              </li>
            ) : (
              ingredients.map((ing) => (
                <li key={ing.id} className="ingredient-item">
                  <div className="ingredient-item-content">
                    <strong>{ing.name}</strong>
                    {isAdmin && (
                      <div>
                        <button
                          onClick={() => editIngredient(ing)}
                          className="button-edit"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => removeIngredient(ing.id)}
                          className="button-remove"
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  )
}

export default Ingredients

