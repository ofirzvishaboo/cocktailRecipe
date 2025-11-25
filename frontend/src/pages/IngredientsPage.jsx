import { useState, useEffect } from 'react'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'

function IngredientsPage() {
  const { isAdmin } = useAuth()
  const [ingredients, setIngredients] = useState([])
  const [filteredIngredients, setFilteredIngredients] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingIngredient, setEditingIngredient] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
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
      setFilteredIngredients(res.data || [])
      setError('')
    } catch (e) {
      setError('Failed to load ingredients')
      console.error('Failed to load ingredients', e)
    } finally {
      setLoading(false)
    }
  }

  // Filter ingredients based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredIngredients(ingredients)
    } else {
      const filtered = ingredients.filter(ing =>
        ing.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
      setFilteredIngredients(filtered)
    }
  }, [searchQuery, ingredients])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return

    try {
      setForm(prev => ({ ...prev, submitting: true }))

      if (editingIngredient) {
        // Update existing ingredient
        await api.put(`/ingredients/${editingIngredient.id}`, { name: form.name })
        const updatedIngredients = ingredients.map(ing =>
          ing.id === editingIngredient.id
            ? { ...ing, name: form.name }
            : ing
        )
        setIngredients(updatedIngredients)
        setEditingIngredient(null)
        // Re-apply search filter
        if (!searchQuery.trim()) {
          setFilteredIngredients(updatedIngredients)
        } else {
          const filtered = updatedIngredients.filter(ing =>
            ing.name.toLowerCase().includes(searchQuery.toLowerCase())
          )
          setFilteredIngredients(filtered)
        }
      } else {
        // Create new ingredient
        const res = await api.post('/ingredients/', { name: form.name })
        const updatedIngredients = [...ingredients, res.data]
        setIngredients(updatedIngredients)
        // Update filtered list if search matches
        if (!searchQuery.trim() || res.data.name.toLowerCase().includes(searchQuery.toLowerCase())) {
          setFilteredIngredients(updatedIngredients)
        }
      }

      setForm({ name: '', submitting: false })
      setShowAddForm(false)
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
      const updatedIngredients = ingredients.filter(ing => ing.id !== ingredientId)
      setIngredients(updatedIngredients)
      // Re-apply search filter
      if (!searchQuery.trim()) {
        setFilteredIngredients(updatedIngredients)
      } else {
        const filtered = updatedIngredients.filter(ing =>
          ing.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
        setFilteredIngredients(filtered)
      }
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
    setShowAddForm(false)
  }

  return (
    <div className="card">
      <div className="ingredients-header">
        <div className="search-container">
          <input
            type="text"
            placeholder="Search ingredients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>
        {isAdmin && !editingIngredient && (
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="button-primary"
          >
            {showAddForm ? 'Cancel' : 'Add Ingredient'}
          </button>
        )}
      </div>

      {isAdmin && (
        <>
          {showAddForm && !editingIngredient && (
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
                  Add Ingredient
                </button>
              </div>
            </form>
          )}
          {editingIngredient && (
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
                  Update Ingredient
                </button>
                <button
                  type="button"
                  onClick={cancelEdit}
                  className="button-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="ingredients-list">
        <h3>All Ingredients</h3>
        {loading && <div className="loading">Loading...</div>}
        {!loading && (
          <ul>
            {filteredIngredients.length === 0 ? (
              <li className="empty-state">
                {searchQuery.trim()
                  ? `No ingredients found matching "${searchQuery}"`
                  : ingredients.length === 0
                    ? `No ingredients yet. ${!isAdmin ? 'Only administrators can add ingredients.' : ''}`
                    : 'No ingredients match your search.'}
              </li>
            ) : (
              filteredIngredients.map((ing) => (
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

export default IngredientsPage

