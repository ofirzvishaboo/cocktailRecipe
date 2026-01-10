import { useState, useEffect } from 'react'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import ConfirmDialog from '../components/common/ConfirmDialog'

function IngredientsPage() {
  const { isAdmin, isAuthenticated } = useAuth()
  const [ingredients, setIngredients] = useState([])
  const [filteredIngredients, setFilteredIngredients] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [pendingDeleteIngredientId, setPendingDeleteIngredientId] = useState(null)
  const [editingIngredient, setEditingIngredient] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [expandedIngredientIds, setExpandedIngredientIds] = useState(() => new Set())
  const [brandsByIngredientId, setBrandsByIngredientId] = useState({})
  const [brandFormByIngredientId, setBrandFormByIngredientId] = useState({})
  const [editingBrandById, setEditingBrandById] = useState({})
  const [form, setForm] = useState({
    name: '',
    brand_name: '',
    bottle_size_ml: '',
    bottle_price: '',
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

        // Optional: create initial bottle + price (normalized schema)
        const bottleName = (form.brand_name || '').trim()
        const bottleSizeMl = parseInt(form.bottle_size_ml, 10)
        const bottlePrice = parseFloat(form.bottle_price)
        const hasBottleFields = bottleName || form.bottle_size_ml || form.bottle_price
        if (hasBottleFields) {
          if (!bottleName || Number.isNaN(bottleSizeMl) || Number.isNaN(bottlePrice)) {
            throw new Error('Invalid bottle fields (name, size, and price are required)')
          }
          const bottleRes = await api.post(`/ingredients/${res.data.id}/bottles`, {
            name: bottleName,
            volume_ml: bottleSizeMl,
            is_default_cost: true,
          })
          await api.post(`/ingredients/bottles/${bottleRes.data.id}/prices`, {
            price: bottlePrice,
            currency: 'ILS',
          })
          // Refresh cache for this ingredient if user expands later
          setBrandsByIngredientId((prev) => ({
            ...prev,
            [res.data.id]: { loading: false, error: '', brands: [] },
          }))
        }
      }

      setForm({ name: '', brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
      setShowAddForm(false)
    } catch (e) {
      setError(editingIngredient ? 'Failed to update ingredient' : 'Failed to create ingredient')
      console.error('Failed to save ingredient', e)
    } finally {
      setForm(prev => ({ ...prev, submitting: false }))
    }
  }

  const requestRemoveIngredient = (ingredientId) => {
    setPendingDeleteIngredientId(ingredientId)
    setDeleteConfirmOpen(true)
  }

  const removeIngredient = async () => {
    const ingredientId = pendingDeleteIngredientId
    if (!ingredientId) return

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
    } finally {
      setDeleteConfirmOpen(false)
      setPendingDeleteIngredientId(null)
    }
  }

  const editIngredient = (ingredient) => {
    setEditingIngredient(ingredient)
    setForm({ name: ingredient.name, brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
  }

  const cancelEdit = () => {
    setEditingIngredient(null)
    setForm({ name: '', brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
    setShowAddForm(false)
  }

  const loadBrands = async (ingredientId) => {
    try {
      setBrandsByIngredientId((prev) => ({
        ...prev,
        [ingredientId]: { loading: true, error: '', brands: prev?.[ingredientId]?.brands || [] },
      }))
      const res = await api.get(`/ingredients/${ingredientId}/bottles`)
      const bottles = res.data || []
      // Adapt normalized bottles to the legacy "brand" row shape used by this screen
      const brands = bottles.map((b) => ({
        id: b.id,
        ingredient_id: b.ingredient_id,
        brand_name: b.name,
        bottle_size_ml: b.volume_ml,
        bottle_price: b.current_price?.price ?? '',
      }))
      setBrandsByIngredientId((prev) => ({
        ...prev,
        [ingredientId]: { loading: false, error: '', brands },
      }))
    } catch (e) {
      setBrandsByIngredientId((prev) => ({
        ...prev,
        [ingredientId]: { loading: false, error: 'Failed to load brands', brands: prev?.[ingredientId]?.brands || [] },
      }))
      console.error('Failed to load brands', e)
    }
  }

  const toggleBrands = async (ingredientId) => {
    setExpandedIngredientIds((prev) => {
      const next = new Set(prev)
      if (next.has(ingredientId)) next.delete(ingredientId)
      else next.add(ingredientId)
      return next
    })

    if (!brandsByIngredientId[ingredientId]) {
      await loadBrands(ingredientId)
    }
  }

  const updateBrandForm = (ingredientId, patch) => {
    setBrandFormByIngredientId((prev) => ({
      ...prev,
      [ingredientId]: {
        brand_name: prev?.[ingredientId]?.brand_name ?? '',
        bottle_size_ml: prev?.[ingredientId]?.bottle_size_ml ?? '',
        bottle_price: prev?.[ingredientId]?.bottle_price ?? '',
        submitting: prev?.[ingredientId]?.submitting ?? false,
        ...patch,
      },
    }))
  }

  const createBrand = async (ingredientId) => {
    const bf = brandFormByIngredientId[ingredientId] || {}
    const brandName = (bf.brand_name || '').trim()
    const bottleSizeMl = parseInt(bf.bottle_size_ml, 10)
    const bottlePrice = parseFloat(bf.bottle_price)
    if (!brandName || Number.isNaN(bottleSizeMl) || Number.isNaN(bottlePrice)) return

    try {
      updateBrandForm(ingredientId, { submitting: true })
      const bottleRes = await api.post(`/ingredients/${ingredientId}/bottles`, {
        name: brandName,
        volume_ml: bottleSizeMl,
        is_default_cost: false,
      })
      await api.post(`/ingredients/bottles/${bottleRes.data.id}/prices`, {
        price: bottlePrice,
        currency: 'ILS',
      })
      updateBrandForm(ingredientId, { brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
      await loadBrands(ingredientId)
    } catch (e) {
      updateBrandForm(ingredientId, { submitting: false })
      setError('Failed to create brand')
      console.error('Failed to create brand', e)
    }
  }

  const startEditBrand = (brand) => {
    setEditingBrandById((prev) => ({
      ...prev,
      [brand.id]: {
        brand_name: brand.brand_name ?? '',
        bottle_size_ml: brand.bottle_size_ml ?? '',
        bottle_price: brand.bottle_price ?? '',
        submitting: false,
      },
    }))
  }

  const cancelEditBrand = (brandId) => {
    setEditingBrandById((prev) => {
      const next = { ...prev }
      delete next[brandId]
      return next
    })
  }

  const updateEditingBrand = (brandId, patch) => {
    setEditingBrandById((prev) => ({
      ...prev,
      [brandId]: { ...(prev[brandId] || {}), ...patch },
    }))
  }

  const saveBrand = async (brandId, ingredientId) => {
    const eb = editingBrandById[brandId]
    if (!eb) return
    const brandName = (eb.brand_name || '').trim()
    const bottleSizeMl = parseInt(eb.bottle_size_ml, 10)
    const bottlePrice = parseFloat(eb.bottle_price)
    if (!brandName || Number.isNaN(bottleSizeMl) || Number.isNaN(bottlePrice)) return

    try {
      updateEditingBrand(brandId, { submitting: true })
      await api.put(`/ingredients/bottles/${brandId}`, {
        name: brandName,
        volume_ml: bottleSizeMl,
      })
      // Add a new price record (simple approach)
      await api.post(`/ingredients/bottles/${brandId}/prices`, {
        price: bottlePrice,
        currency: 'ILS',
      })
      cancelEditBrand(brandId)
      await loadBrands(ingredientId)
    } catch (e) {
      updateEditingBrand(brandId, { submitting: false })
      setError('Failed to update brand')
      console.error('Failed to update brand', e)
    }
  }

  const deleteBrand = async (brandId, ingredientId) => {
    try {
      await api.delete(`/ingredients/bottles/${brandId}`)
      await loadBrands(ingredientId)
    } catch (e) {
      setError('Failed to delete brand')
      console.error('Failed to delete brand', e)
    }
  }

  return (
    <div className="card">
      <div className="ingredients-header">
        <div className={`search-container ${!isAdmin ? 'search-container-full' : ''}`}>
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
                <input
                  type="text"
                  placeholder="Brand (optional)"
                  value={form.brand_name}
                  onChange={(e) => setForm(prev => ({ ...prev, brand_name: e.target.value }))}
                  className="form-input form-input-small"
                />
                <input
                  type="number"
                  placeholder="Bottle size (ml)"
                  value={form.bottle_size_ml}
                  onChange={(e) => setForm(prev => ({ ...prev, bottle_size_ml: e.target.value }))}
                  className="form-input form-input-small"
                  min="1"
                  step="1"
                />
                <input
                  type="number"
                  placeholder="Bottle price"
                  value={form.bottle_price}
                  onChange={(e) => setForm(prev => ({ ...prev, bottle_price: e.target.value }))}
                  className="form-input form-input-small"
                  min="0"
                  step="0.01"
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
                    <div className="ingredient-actions">
                      {isAuthenticated && (
                        <button
                          onClick={() => toggleBrands(ing.id)}
                          className="button-secondary button-brands"
                          type="button"
                        >
                          {expandedIngredientIds.has(ing.id) ? 'Hide Brands' : 'Brands'}
                        </button>
                      )}
                    {isAdmin && (
                        <>
                        <button
                          onClick={() => editIngredient(ing)}
                          className="button-edit"
                            type="button"
                        >
                          Edit
                        </button>
                        <button
                            onClick={() => requestRemoveIngredient(ing.id)}
                          className="button-remove"
                            type="button"
                        >
                          Remove
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {expandedIngredientIds.has(ing.id) && (
                    <div className="brands-panel">
                      <div className="brands-header">
                        <h4>Brands / Bottles</h4>
                        <button type="button" className="button-secondary" onClick={() => loadBrands(ing.id)}>
                          Refresh
                        </button>
                      </div>

                      {brandsByIngredientId?.[ing.id]?.loading && <div className="loading">Loading brands...</div>}
                      {brandsByIngredientId?.[ing.id]?.error && (
                        <div className="error-message">{brandsByIngredientId[ing.id].error}</div>
                      )}

                      {!brandsByIngredientId?.[ing.id]?.loading && (
                        <div className="brands-list">
                          {(brandsByIngredientId?.[ing.id]?.brands || []).length === 0 ? (
                            <div className="empty-state">No brands yet.</div>
                          ) : (
                            (brandsByIngredientId?.[ing.id]?.brands || []).map((b) => {
                              const eb = editingBrandById[b.id]
                              const isEditing = !!eb
                              return (
                                <div key={b.id} className="brand-row">
                                  {isEditing ? (
                                    <>
                                      <input
                                        className="form-input"
                                        value={eb.brand_name}
                                        onChange={(e) => updateEditingBrand(b.id, { brand_name: e.target.value })}
                                        placeholder="Brand name"
                                      />
                                      <input
                                        className="form-input form-input-small"
                                        value={eb.bottle_size_ml}
                                        onChange={(e) => updateEditingBrand(b.id, { bottle_size_ml: e.target.value })}
                                        placeholder="Size (ml)"
                                        type="number"
                                        min="1"
                                        step="1"
                                      />
                                      <input
                                        className="form-input form-input-small"
                                        value={eb.bottle_price}
                                        onChange={(e) => updateEditingBrand(b.id, { bottle_price: e.target.value })}
                                        placeholder="Price"
                                        type="number"
                                        min="0"
                                        step="0.01"
                                      />
                                      {isAdmin && (
                                        <div className="brand-actions">
                                          <button
                                            type="button"
                                            className="button-primary"
                                            disabled={eb.submitting}
                                            onClick={() => saveBrand(b.id, ing.id)}
                                          >
                                            Save
                                          </button>
                                          <button
                                            type="button"
                                            className="button-secondary"
                                            disabled={eb.submitting}
                                            onClick={() => cancelEditBrand(b.id)}
                                          >
                                            Cancel
                                          </button>
                                        </div>
                                      )}
                                    </>
                                  ) : (
                                    <>
                                      <div className="brand-display">
                                        <strong>{b.brand_name}</strong>
                                        <span>{b.bottle_size_ml} ml</span>
                                        <span>{b.bottle_price}</span>
                                      </div>
                                      {isAdmin && (
                                        <div className="brand-actions">
                                          <button type="button" className="button-edit" onClick={() => startEditBrand(b)}>
                                            Edit
                                          </button>
                                          <button
                                            type="button"
                                            className="button-remove"
                                            onClick={() => deleteBrand(b.id, ing.id)}
                                          >
                                            Delete
                                          </button>
                                        </div>
                                      )}
                                    </>
                                  )}
                                </div>
                              )
                            })
                          )}
                        </div>
                      )}

                      {isAdmin && (
                        <div className="brand-create">
                          <h4>Add Brand</h4>
                          <div className="brand-row">
                            <input
                              className="form-input"
                              value={brandFormByIngredientId?.[ing.id]?.brand_name ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { brand_name: e.target.value })}
                              placeholder="Brand name"
                            />
                            <input
                              className="form-input form-input-small"
                              value={brandFormByIngredientId?.[ing.id]?.bottle_size_ml ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { bottle_size_ml: e.target.value })}
                              placeholder="Bottle size (ml)"
                              type="number"
                              min="1"
                              step="1"
                            />
                            <input
                              className="form-input form-input-small"
                              value={brandFormByIngredientId?.[ing.id]?.bottle_price ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { bottle_price: e.target.value })}
                              placeholder="Bottle price"
                              type="number"
                              min="0"
                              step="0.01"
                            />
                            <button
                              type="button"
                              className="button-primary"
                              disabled={brandFormByIngredientId?.[ing.id]?.submitting}
                              onClick={() => createBrand(ing.id)}
                            >
                              Add
                            </button>
                          </div>
                      </div>
                    )}
                  </div>
                  )}
                </li>
              ))
            )}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Delete ingredient?"
        message={`Are you sure you want to delete "${ingredients.find(i => i.id === pendingDeleteIngredientId)?.name || ''}"? This cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onCancel={() => {
          setDeleteConfirmOpen(false)
          setPendingDeleteIngredientId(null)
        }}
        onConfirm={removeIngredient}
      />
    </div>
  )
}

export default IngredientsPage

