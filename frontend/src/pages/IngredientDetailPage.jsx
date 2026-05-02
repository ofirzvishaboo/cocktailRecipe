import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import ConfirmDialog from '../components/common/ConfirmDialog'

export default function IngredientDetailPage() {
  const { id } = useParams()
  const { isAdmin } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [ingredient, setIngredient] = useState(null)
  const [bottles, setBottles] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [brandSuggestions, setBrandSuggestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  // Ingredient name editing
  const [editingName, setEditingName] = useState(false)
  const [nameForm, setNameForm] = useState({ name: '', name_he: '' })

  // Add bottle form
  const [showAddBottle, setShowAddBottle] = useState(false)
  const [addBottleForm, setAddBottleForm] = useState({
    name: '',
    name_he: '',
    volume_ml: '',
    supplier_id: '',
    price: '',
    submitting: false,
  })

  // Edit bottle state: bottleId -> { name, name_he, volume_ml, supplier_id, price, submitting }
  const [editingBottle, setEditingBottle] = useState(null)
  const [editBottleForm, setEditBottleForm] = useState({})

  // Delete confirm
  const [deleteBottleId, setDeleteBottleId] = useState(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  const loadIngredient = useCallback(async (signal) => {
    if (!id) return
    try {
      setError('')
      const res = await api.get(`/ingredients/${id}`, { signal })
      setIngredient(res.data)
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return
      console.error('Failed to load ingredient', err)
      setError(t('ingredients.errors.loadFailed'))
      setIngredient(null)
    }
  }, [id, t])

  const loadBottles = useCallback(async (signal) => {
    if (!id) return
    try {
      const res = await api.get(`/ingredients/${id}/bottles`, { signal })
      setBottles(res.data || [])
    } catch (e) {
      if (e.name === 'CanceledError' || e.code === 'ERR_CANCELED') return
      console.error('Failed to load bottles', e)
      setBottles([])
    }
  }, [id])

  const loadSuppliers = useCallback(async (signal) => {
    if (!isAdmin) return
    try {
      const res = await api.get('/suppliers/', { signal })
      setSuppliers(res.data || [])
    } catch (e) {
      if (e.name === 'CanceledError' || e.code === 'ERR_CANCELED') return
      console.error('Failed to load suppliers', e)
      setSuppliers([])
    }
  }, [isAdmin])

  useEffect(() => {
    if (!id) return
    const ac = new AbortController()
    setLoading(true)
    Promise.all([
      loadIngredient(ac.signal),
      loadBottles(ac.signal),
      loadSuppliers(ac.signal),
    ]).finally(() => {
      if (!ac.signal.aborted) setLoading(false)
    })
    return () => ac.abort()
  }, [id, loadIngredient, loadBottles, loadSuppliers])

  const refreshAll = useCallback(() => {
    loadIngredient(undefined)
    loadBottles(undefined)
  }, [loadIngredient, loadBottles])

  // --- Ingredient name ---
  const startEditName = () => {
    setEditingName(true)
    setNameForm({
      name: (ingredient?.name || '').trim(),
      name_he: (ingredient?.name_he || '').trim(),
    })
  }

  const cancelEditName = () => {
    setEditingName(false)
    setNameForm({ name: '', name_he: '' })
  }

  const saveIngredientName = async () => {
    const nameEn = (nameForm.name || '').trim() || (nameForm.name_he || '').trim()
    if (!nameEn) {
      setError(t('ingredients.errors.nameRequired'))
      return
    }
    try {
      setSaving(true)
      setError('')
      await api.put(`/ingredients/${id}`, {
        name: nameEn,
        name_he: (nameForm.name_he || '').trim() || null,
      })
      setIngredient((prev) => ({ ...prev, name: nameEn, name_he: nameForm.name_he?.trim() || null }))
      cancelEditName()
    } catch (e) {
      setError(e?.response?.data?.detail || t('ingredients.errors.updateFailed'))
    } finally {
      setSaving(false)
    }
  }

  // --- Add bottle ---
  const openAddBottle = () => {
    setShowAddBottle(true)
    setAddBottleForm({
      name: '',
      name_he: '',
      volume_ml: '',
      supplier_id: '',
      price: '',
      submitting: false,
    })
  }

  const addBottle = async (e) => {
    e?.preventDefault()
    const nameEn = (addBottleForm.name || '').trim() || (addBottleForm.name_he || '').trim()
    const vol = parseInt(addBottleForm.volume_ml, 10)
    const price = parseFloat(addBottleForm.price)
    if (!nameEn || Number.isNaN(vol) || vol <= 0) {
      setError(t('ingredients.errors.invalidBottleFields'))
      return
    }
    try {
      setAddBottleForm((f) => ({ ...f, submitting: true }))
      setError('')
      const bottleRes = await api.post(`/ingredients/${id}/bottles`, {
        name: nameEn,
        name_he: (addBottleForm.name_he || '').trim() || null,
        volume_ml: vol,
        supplier_id: addBottleForm.supplier_id || null,
        is_default_cost: bottles.length === 0,
      })
      if (!Number.isNaN(price) && price > 0) {
        await api.post(`/ingredients/bottles/${bottleRes.data.id}/prices`, {
          price,
          currency: 'ILS',
        })
      }
      setShowAddBottle(false)
      loadBrandSuggestions()
      refreshAll()
    } catch (e) {
      setError(e?.response?.data?.detail || t('ingredients.errors.createBrandFailed'))
    } finally {
      setAddBottleForm((f) => ({ ...f, submitting: false }))
    }
  }
  const loadBrandSuggestions = useCallback(async () => {
    try {
      const res = await api.get('/brands/suggestions')
      setBrandSuggestions(res.data || [])
    } catch (e) {
      console.error('Failed to load brand suggestions', e)
      setBrandSuggestions([])
    }
  }, [])

  useEffect(() => {
    loadBrandSuggestions()
  }, [loadBrandSuggestions])

  // Set CSS variables for mobile card labels (i18n)
  useEffect(() => {
    const root = document.documentElement
    root.style.setProperty('--ingredient-detail-lbl-brand', `"${t('ingredients.brands.brandName')}"`)
    root.style.setProperty('--ingredient-detail-lbl-size', `"${t('ingredients.brands.sizeMlShort')}"`)
    root.style.setProperty('--ingredient-detail-lbl-price', `"${t('ingredients.brands.priceShort')}"`)
    root.style.setProperty('--ingredient-detail-lbl-supplier', `"${t('ingredientDetail.supplier', { defaultValue: 'Supplier' })}"`)
    root.style.setProperty('--ingredient-detail-lbl-actions', `"${t('common.actions', { defaultValue: 'Actions' })}"`)
    return () => {
      root.style.removeProperty('--ingredient-detail-lbl-brand')
      root.style.removeProperty('--ingredient-detail-lbl-size')
      root.style.removeProperty('--ingredient-detail-lbl-price')
      root.style.removeProperty('--ingredient-detail-lbl-supplier')
      root.style.removeProperty('--ingredient-detail-lbl-actions')
    }
  }, [t])

  // --- Edit bottle ---
  const startEditBottle = (bottle) => {
    setEditingBottle(bottle.id)
    const price = bottle.current_price?.price
    setEditBottleForm({
      name: (bottle.name || '').trim(),
      name_he: (bottle.name_he || '').trim(),
      volume_ml: bottle.volume_ml?.toString() || '',
      supplier_id: bottle.supplier_id || '',
      price: price != null ? String(price) : '',
      submitting: false,
    })
  }

  const cancelEditBottle = () => {
    setEditingBottle(null)
    setEditBottleForm({})
  }

  const saveBottle = async (bottleId) => {
    const f = editBottleForm
    const nameEn = (f.name || '').trim() || (f.name_he || '').trim()
    const vol = parseInt(f.volume_ml, 10)
    const price = parseFloat(f.price)
    if (!nameEn || Number.isNaN(vol) || vol <= 0) {
      setError(t('ingredients.errors.invalidBottleFields'))
      return
    }
    try {
      setEditBottleForm((prev) => ({ ...prev, submitting: true }))
      setError('')
      await api.put(`/ingredients/bottles/${bottleId}`, {
        name: nameEn,
        name_he: (f.name_he || '').trim() || null,
        volume_ml: vol,
        supplier_id: f.supplier_id || null,
      })
      if (!Number.isNaN(price) && price > 0) {
        await api.post(`/ingredients/bottles/${bottleId}/prices`, {
          price,
          currency: 'ILS',
        })
      }
      cancelEditBottle()
      refreshAll()
    } catch (e) {
      setError(e?.response?.data?.detail || t('ingredients.errors.updateBrandFailed'))
    } finally {
      setEditBottleForm((prev) => ({ ...prev, submitting: false }))
    }
  }

  // --- Delete bottle ---
  const requestDeleteBottle = (bottleId) => {
    setDeleteBottleId(bottleId)
    setDeleteConfirmOpen(true)
  }

  const confirmDeleteBottle = async () => {
    if (!deleteBottleId) return
    try {
      await api.delete(`/ingredients/bottles/${deleteBottleId}`)
      setDeleteConfirmOpen(false)
      setDeleteBottleId(null)
      refreshAll()
    } catch (e) {
      setError(e?.response?.data?.detail || t('ingredients.errors.deleteBrandFailed'))
    }
  }






  const displayName = (item, nameKey = 'name', nameHeKey = 'name_he') => {
    const n = item?.[nameKey] || ''
    const nh = item?.[nameHeKey] || ''
    return lang === 'he' ? ((nh || '').trim() || (n || '').trim()) : ((n || '').trim() || (nh || '').trim())
  }

  if (loading) {
    return <div className="loading" style={{ marginTop: 24 }}>{t('common.loading')}</div>
  }

  if (!ingredient) {
    return (
      <div className="card">
        <p className="error-message">{error || t('ingredients.errors.loadFailed')}</p>
        <Link to="/ingredients">{t('ingredients.backToList', { defaultValue: 'Back to ingredients' })}</Link>
      </div>
    )
  }

  return (
    <div className="card ingredient-detail-page">
      <div className="cocktail-title-row">
        <Link
          to="/ingredients"
          className="back-link"
          aria-label={t('ingredients.backToList', { defaultValue: 'Back to ingredients' })}
        >
          <span className="back-link-icon" aria-hidden="true">{lang === 'he' ? '→' : '←'}</span>
          <span className="back-link-text">
            {t('ingredients.backToList', { defaultValue: 'Back to ingredients' })}
          </span>
        </Link>
        <h1 className="cocktail-detail-title">
          {editingName ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
              <input
                type="text"
                className="form-input"
                value={nameForm.name}
                onChange={(e) => setNameForm((f) => ({ ...f, name: e.target.value }))}
                placeholder={t('common.ingredientName')}
                style={{ minWidth: 160 }}
              />
              <input
                type="text"
                className="form-input"
                value={nameForm.name_he}
                onChange={(e) => setNameForm((f) => ({ ...f, name_he: e.target.value }))}
                placeholder={t('common.ingredientName') + ' (HE)'}
                style={{ minWidth: 140 }}
              />
              <button type="button" className="button-primary" onClick={saveIngredientName} disabled={saving}>
                {saving ? t('common.saving') : t('common.save')}
              </button>
              <button type="button" className="button-edit" onClick={cancelEditName}>
                {t('common.cancel')}
              </button>
            </div>
          ) : (
            displayName(ingredient)
          )}
        </h1>
        {isAdmin && !editingName && (
          <div className="cocktail-actions-inline">
            <button
              type="button"
              className="button-edit"
              onClick={startEditName}
            >
              {t('common.edit')}
            </button>
          </div>
        )}
      </div>

      {error && <div className="error-message" style={{ marginTop: 12 }}>{error}</div>}

      <div style={{ marginTop: 24 }}>
        <div className="ingredient-detail-brands-title-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>{t('ingredients.brands.title')}</h3>
          {isAdmin && !showAddBottle && (
            <button type="button" className="button-primary" onClick={openAddBottle}>
              + {t('ingredients.brands.addTitle', { defaultValue: 'Add bottle' })}
            </button>
          )}
        </div>

        {showAddBottle && (
          <form onSubmit={addBottle} className="inventory-table ingredient-detail-add-form-wrap" style={{ marginBottom: 16, padding: 16, background: 'var(--surface-muted)', borderRadius: 8 }}>
            <div
              className="ingredient-detail-add-form"
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1.5fr minmax(70px, 1fr) 1.5fr minmax(70px, 1fr) minmax(140px, auto)',
                gap: 12,
                alignItems: 'end',
                width: '100%',
                minWidth: 0,
              }}
            >
              <div style={{ minWidth: 0 }}>
                <label className="muted" style={{ fontSize: '0.85em' }}>{t('ingredients.brands.brandName')}</label>
                <input
                  type="text"
                  className="form-input"
                  value={addBottleForm.name}
                  onChange={(e) => setAddBottleForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Name"
                  list="brand-suggestions-ingredient-detail"
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ minWidth: 0 }}>
                <label className="muted" style={{ fontSize: '0.85em' }}>Hebrew</label>
                <input
                  type="text"
                  className="form-input"
                  value={addBottleForm.name_he}
                  onChange={(e) => setAddBottleForm((f) => ({ ...f, name_he: e.target.value }))}
                  placeholder="שם"
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ minWidth: 0 }}>
                <label className="muted" style={{ fontSize: '0.85em' }}>{t('ingredients.brands.sizeMl')}</label>
                <input
                  type="number"
                  className="form-input"
                  value={addBottleForm.volume_ml}
                  onChange={(e) => setAddBottleForm((f) => ({ ...f, volume_ml: e.target.value }))}
                  placeholder="700"
                  min={1}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ minWidth: 0 }}>
                <label className="muted" style={{ fontSize: '0.85em' }}>{t('ingredientDetail.supplier', { defaultValue: 'Supplier' })}</label>
                <select
                  className="form-input"
                  value={addBottleForm.supplier_id}
                  onChange={(e) => setAddBottleForm((f) => ({ ...f, supplier_id: e.target.value }))}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                >
                  <option value="">—</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div style={{ minWidth: 0 }}>
                <label className="muted" style={{ fontSize: '0.85em' }}>{t('ingredients.brands.price')} (ILS)</label>
                <input
                  type="number"
                  className="form-input"
                  value={addBottleForm.price}
                  onChange={(e) => setAddBottleForm((f) => ({ ...f, price: e.target.value }))}
                  placeholder="0"
                  min={0}
                  step={0.01}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ display: 'flex', gap: 8, flexShrink: 0, justifyContent: 'flex-end' }}>
                <button type="submit" className="button-primary" disabled={addBottleForm.submitting}>
                  {addBottleForm.submitting ? t('common.saving') : t('ingredients.brands.add')}
                </button>
                <button type="button" className="button-edit" onClick={() => setShowAddBottle(false)}>
                  {t('common.cancel')}
                </button>
              </div>
            </div>
          </form>
        )}

        {bottles.length === 0 && !showAddBottle ? (
          <div className="empty-state">{t('ingredients.brands.empty')}</div>
        ) : (
          <div className="inventory-table ingredient-detail-bottles">
            <div className="inventory-table-header ingredient-detail-bottles-header" style={{ gridTemplateColumns: '2fr 1fr 1fr 1.5fr 1fr' }}>
              <div>{t('ingredients.brands.brandName')}</div>
              <div className="right">{t('ingredients.brands.sizeMlShort')}</div>
              <div className="right">{t('ingredients.brands.priceShort')}</div>
              <div>{t('ingredientDetail.supplier', { defaultValue: 'Supplier' })}</div>
              {isAdmin && <div className="right">{t('common.actions', { defaultValue: 'Actions' })}</div>}
            </div>
            {bottles.map((bottle) => (
              <div
                key={bottle.id}
                className="inventory-table-row ingredient-detail-bottles-row"
                style={{ gridTemplateColumns: isAdmin ? '2fr 1fr 1fr 1.5fr 1fr' : '2fr 1fr 1fr 1.5fr' }}
              >
                {editingBottle === bottle.id ? (
                  <>
                    <div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <input
                          type="text"
                          className="form-input"
                          value={editBottleForm.name}
                          onChange={(e) => setEditBottleForm((f) => ({ ...f, name: e.target.value }))}
                          style={{ width: '100%' }}
                          placeholder="Name"
                          list="brand-suggestions-ingredient-detail"
                        />
                        <input
                          type="text"
                          className="form-input"
                          value={editBottleForm.name_he}
                          onChange={(e) => setEditBottleForm((f) => ({ ...f, name_he: e.target.value }))}
                          style={{ width: '100%' }}
                          placeholder="שם"
                        />
                      </div>
                    </div>
                    <div>
                      <input
                        type="number"
                        className="form-input"
                        value={editBottleForm.volume_ml}
                        onChange={(e) => setEditBottleForm((f) => ({ ...f, volume_ml: e.target.value }))}
                        min={1}
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        className="form-input"
                        value={editBottleForm.price}
                        onChange={(e) => setEditBottleForm((f) => ({ ...f, price: e.target.value }))}
                        min={0}
                        step={0.01}
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <select
                        className="form-input"
                        value={editBottleForm.supplier_id}
                        onChange={(e) => setEditBottleForm((f) => ({ ...f, supplier_id: e.target.value }))}
                        style={{ width: '100%' }}
                      >
                        <option value="">—</option>
                        {suppliers.map((s) => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button type="button" className="button-primary" onClick={() => saveBottle(bottle.id)} disabled={editBottleForm.submitting}>
                        {editBottleForm.submitting ? t('common.saving') : t('common.save')}
                      </button>
                      <button type="button" className="button-edit" onClick={cancelEditBottle}>
                        {t('common.cancel')}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="name">{displayName(bottle)}</div>
                    <div className="right muted">{bottle.volume_ml} ml</div>
                    <div className="right muted">
                      {bottle.current_price != null
                        ? `₪ ${Number(bottle.current_price.price).toFixed(2)}`
                        : '—'}
                    </div>
                    <div className="muted">{bottle.supplier_name || '—'}</div>
                    {isAdmin && (
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button type="button" className="button-edit" onClick={() => startEditBottle(bottle)}>
                          {t('common.edit')}
                        </button>
                        <button type="button" className="button-edit" onClick={() => requestDeleteBottle(bottle.id)}>
                          {t('ingredients.brands.delete')}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteConfirmOpen}
        title={t('ingredientDetail.deleteBottleTitle', { defaultValue: 'Delete bottle?' })}
        message={t('ingredientDetail.deleteBottleMessage', { defaultValue: 'Are you sure? This cannot be undone.' })}
        onConfirm={confirmDeleteBottle}
        onCancel={() => { setDeleteConfirmOpen(false); setDeleteBottleId(null) }}
        confirmText={t('ingredients.deleteDialog.confirm')}
      />

      <datalist id="brand-suggestions-ingredient-detail">
        {(brandSuggestions || [])
          .map((n) => (n || '').trim())
          .filter(Boolean)
          .sort((a, b) => a.localeCompare(b))
          .map((name) => <option key={name} value={name} />)}
      </datalist>
    </div>
  )
}
