import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import ConfirmDialog from '../components/common/ConfirmDialog'
import Select from '../components/common/Select'
const INGREDIENT_GROUP_ORDER = ['Spirit', 'Liqueur', 'Juice', 'Syrup', 'Sparkling', 'Garnish']

function IngredientsPage() {
  const { isAdmin, isAuthenticated } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]
  const [ingredients, setIngredients] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [taxonomy, setTaxonomy] = useState({
    loading: false,
    error: '',
    ingredientKind: null,
    subcategories: [],
    subcategoryById: {},
    subcategoryIdByNameLower: {},
  })
  const [brandSuggestions, setBrandSuggestions] = useState([])
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [pendingDeleteIngredientId, setPendingDeleteIngredientId] = useState(null)
  const [pendingDeleteUsedBy, setPendingDeleteUsedBy] = useState({ loading: false, error: '', cocktails: [] })
  const [editingIngredient, setEditingIngredient] = useState(null)
  const [editingIngredientName, setEditingIngredientName] = useState(null)
  const [editingNameForm, setEditingNameForm] = useState({ name: '', name_he: '' })
  const [showAddForm, setShowAddForm] = useState(false)
  const [expandedIngredientIds, setExpandedIngredientIds] = useState(() => new Set())
  const [brandsByIngredientId, setBrandsByIngredientId] = useState({})
  const [brandFormByIngredientId, setBrandFormByIngredientId] = useState({})
  const [editingBrandById, setEditingBrandById] = useState({})
  const [form, setForm] = useState({
    name: '',
    name_he: '',
    subcategory_id: '',
    brand_name: '',
    bottle_size_ml: '',
    bottle_price: '',
    submitting: false,
  })

  useEffect(() => {
    const loadTaxonomy = async () => {
      try {
        setTaxonomy((p) => ({ ...p, loading: true, error: '' }))
        const kindsRes = await api.get('/kinds/')
        const kinds = Array.isArray(kindsRes.data) ? kindsRes.data : []
        const ingredientKind = kinds.find((k) => (k?.name || '').trim().toLowerCase() === 'ingredient') || null
        if (!ingredientKind?.id) {
          setTaxonomy((p) => ({ ...p, loading: false, ingredientKind: null, subcategories: [], subcategoryById: {}, subcategoryIdByNameLower: {} }))
          return
        }
        const subsRes = await api.get(`/subcategories/?kind_id=${ingredientKind.id}`)
        const subcategories = Array.isArray(subsRes.data) ? subsRes.data : []
        const subcategoryById = {}
        const subcategoryIdByNameLower = {}
        for (const s of subcategories) {
          if (!s?.id) continue
          subcategoryById[s.id] = s
          const key = (s.name || '').trim().toLowerCase()
          if (key) subcategoryIdByNameLower[key] = s.id
        }
        setTaxonomy({
          loading: false,
          error: '',
          ingredientKind,
          subcategories,
          subcategoryById,
          subcategoryIdByNameLower,
        })
      } catch (e) {
        console.error('Failed to load taxonomy', e)
        setTaxonomy((p) => ({ ...p, loading: false, error: t('ingredients.errors.loadTaxonomyFailed') }))
      }
    }
    loadTaxonomy()
  }, [t])

  const loadBrandSuggestions = async () => {
    try {
      const res = await api.get('/brands/suggestions')
      setBrandSuggestions(res.data || [])
    } catch (e) {
      console.error('Failed to load brand suggestions', e)
      setBrandSuggestions([])
    }
  }

  useEffect(() => {
    loadBrandSuggestions()
  }, [])

  const loadIngredients = useCallback(async () => {
    try {
      setLoading(true)
      const res = await api.get('/ingredients/')
      setIngredients(res.data || [])
      setError('')
    } catch (e) {
      setError(t('ingredients.errors.loadFailed'))
      console.error('Failed to load ingredients', e)
    } finally {
      setLoading(false)
    }
  }, [t])



  const subcategoryLabel = (name) => {
    const raw = (name || '').trim()
    if (!raw) return ''
    return t(`ingredients.subcategorySelect.${raw}`, { defaultValue: raw })
  }

  const displayName = (obj) => {
    const he = (obj?.name_he || '').trim()
    const en = (obj?.name || '').trim()
    return lang === 'he' ? (he || en) : (en || he)
  }

  useEffect(() => {
    loadIngredients()
  }, [loadIngredients])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return

    try {
      setForm(prev => ({ ...prev, submitting: true }))

      if (editingIngredient) {
        // Update existing ingredient
        const nameEn = (form.name || '').trim() || (form.name_he || '').trim()
        await api.put(`/ingredients/${editingIngredient.id}`, { name: nameEn, name_he: form.name_he || null })
        const updatedIngredients = ingredients.map(ing =>
          ing.id === editingIngredient.id
            ? { ...ing, name: nameEn, name_he: form.name_he || null }
            : ing
        )
        setIngredients(updatedIngredients)
        setEditingIngredient(null)
      } else {
        // Create new ingredient
        const res = await api.post('/ingredients/', {
          name: (form.name || '').trim() || (form.name_he || '').trim(),
          name_he: (form.name_he || '').trim() || null,
          // ensure the Kind is set to our Ingredient taxonomy kind if present
          kind_id: taxonomy.ingredientKind?.id || undefined,
          subcategory_id: form.subcategory_id ? form.subcategory_id : null,
        })
        const updatedIngredients = [...ingredients, res.data]
        setIngredients(updatedIngredients)

        // Optional: create initial bottle + price (normalized schema)
        const bottleName = (form.brand_name || '').trim()
        const bottleSizeMl = parseInt(form.bottle_size_ml, 10)
        const bottlePrice = parseFloat(form.bottle_price)
        const hasBottleFields = bottleName || form.bottle_size_ml || form.bottle_price
        if (hasBottleFields) {
          if (!bottleName || Number.isNaN(bottleSizeMl) || Number.isNaN(bottlePrice)) {
            throw new Error(t('ingredients.errors.invalidBottleFields'))
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
          await loadBrandSuggestions()
          // Refresh cache for this ingredient if user expands later
          setBrandsByIngredientId((prev) => ({
            ...prev,
            [res.data.id]: { loading: false, error: '', brands: [] },
          }))
        }
      }

      setForm({ name: '', name_he: '', subcategory_id: '', brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
      setShowAddForm(false)
    } catch (e) {
      setError(editingIngredient ? t('ingredients.errors.updateFailed') : t('ingredients.errors.createFailed'))
      console.error('Failed to save ingredient', e)
    } finally {
      setForm(prev => ({ ...prev, submitting: false }))
    }
  }

  const requestRemoveIngredient = async (ingredientId) => {
    setPendingDeleteIngredientId(ingredientId)
    setPendingDeleteUsedBy({ loading: true, error: '', cocktails: [] })
    setDeleteConfirmOpen(true)
    try {
      const res = await api.get(`/ingredients/${ingredientId}/used-by`)
      setPendingDeleteUsedBy({ loading: false, error: '', cocktails: res.data || [] })
    } catch (e) {
      console.error('Failed to load ingredient usage', e)
      setPendingDeleteUsedBy({
        loading: false,
        error: t('ingredients.errors.loadUsageFailed'),
        cocktails: [],
      })
    }
  }

  const removeIngredient = async () => {
    const ingredientId = pendingDeleteIngredientId
    if (!ingredientId) return

    try {
      await api.delete(`/ingredients/${ingredientId}`)
      const updatedIngredients = ingredients.filter(ing => ing.id !== ingredientId)
      setIngredients(updatedIngredients)
    } catch (e) {
      setError(t('ingredients.errors.deleteFailed'))
      console.error('Failed to delete ingredient', e)
    } finally {
      setDeleteConfirmOpen(false)
      setPendingDeleteIngredientId(null)
      setPendingDeleteUsedBy({ loading: false, error: '', cocktails: [] })
    }
  }

  const editIngredient = (ingredient) => {
    setEditingIngredient(ingredient)
    setForm({ name: ingredient.name, name_he: ingredient.name_he || '', subcategory_id: ingredient.subcategory_id || '', brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
  }

  const startEditIngredientName = (ingredient) => {
    setEditingIngredientName(ingredient.id)
    setEditingNameForm({ name: ingredient.name || '', name_he: ingredient.name_he || '' })
  }

  const cancelEditIngredientName = () => {
    setEditingIngredientName(null)
    setEditingNameForm({ name: '', name_he: '' })
  }

  const saveIngredientName = async (ingredientId) => {
    try {
      const nameEn = (editingNameForm.name || '').trim() || (editingNameForm.name_he || '').trim()
      const nameHeTrimmed = (editingNameForm.name_he || '').trim()

      if (!nameEn) {
        setError('Ingredient name is required')
        return
      }

      const payload = {
        name: nameEn,
      }

      // Only include name_he if it has a value, otherwise send null explicitly
      if (nameHeTrimmed) {
        payload.name_he = nameHeTrimmed
      } else {
        payload.name_he = null
      }

      await api.put(`/ingredients/${ingredientId}`, payload)

      const updatedIngredients = ingredients.map(ing =>
        ing.id === ingredientId
          ? { ...ing, name: nameEn, name_he: nameHeTrimmed || null }
          : ing
      )
      setIngredients(updatedIngredients)
      cancelEditIngredientName()
    } catch (e) {
      console.error('Failed to update ingredient name', e)
      const errorMsg = e?.response?.data?.detail || e?.message || t('ingredients.errors.updateFailed')
      setError(errorMsg)
    }
  }

  const cancelEdit = () => {
    setEditingIngredient(null)
    setForm({ name: '', name_he: '', subcategory_id: '', brand_name: '', bottle_size_ml: '', bottle_price: '', submitting: false })
    setShowAddForm(false)
  }

  const setIngredientSubcategory = async (ingredientId, subcategoryIdOrEmpty) => {
    try {
      const subcategory_id = subcategoryIdOrEmpty ? subcategoryIdOrEmpty : null
      await api.put(`/ingredients/${ingredientId}`, {
        kind_id: taxonomy.ingredientKind?.id || undefined,
        subcategory_id,
      })
      const patch = (ing) => (ing.id === ingredientId ? { ...ing, subcategory_id } : ing)
      const updatedIngredients = ingredients.map(patch)
      setIngredients(updatedIngredients)
    } catch (e) {
      console.error('Failed to update ingredient subcategory', e)
      setError(t('ingredients.errors.updateGroupFailed'))
    }
  }

  const filteredIngredients = useMemo(() => {
    const query = (searchQuery || '').trim().toLowerCase()
    if (!query) return ingredients || []
    return (ingredients || []).filter((ing) =>
      (ing?.name || '').toLowerCase().includes(query) ||
      (ing?.name_he || '').toLowerCase().includes(query)
    )
  }, [ingredients, searchQuery])

  // 1) Select options (value = UUID; plus All + Uncategorized)
const subcategoryOptions = useMemo(() => {
  const subs = Array.isArray(taxonomy.subcategories) ? taxonomy.subcategories : []

  // Order by INGREDIENT_GROUP_ORDER first (match by name), then the rest
  const byNameLower = new Map(subs.map((s) => [(s?.name || '').trim().toLowerCase(), s]))
  const used = new Set()

  const ordered = []
  for (const name of INGREDIENT_GROUP_ORDER) {
    const sc = byNameLower.get(name.toLowerCase())
    if (sc?.id && !used.has(sc.id)) {
      used.add(sc.id)
      ordered.push(sc)
    }
  }

  const rest = subs
    .filter((s) => s?.id && !used.has(s.id))
    .slice()
    .sort((a, b) => {
      const al = t(`inventory.groups.${a.name}`, { defaultValue: a.name || '' })
      const bl = t(`inventory.groups.${b.name}`, { defaultValue: b.name || '' })
      return String(al).localeCompare(String(bl))
    })

  const base = [...ordered, ...rest].map((sc) => ({
    value: sc.id, // ✅ UUID
    label: t(`inventory.groups.${sc.name}`, { defaultValue: sc.name }),
  }))

  return [
    ...base,
    { value: '__none__', label: t('ingredients.uncategorized') }, // Uncategorized (last)
  ]
}, [taxonomy.subcategories, t])

// 2) Filter list by selectedSubcategoryId (UUID / '' / '__none__')
const subcategoryFilteredIngredients = useMemo(() => {
  const items = Array.isArray(filteredIngredients) ? filteredIngredients : []

  if (!selectedSubcategoryId) return items // All
  if (selectedSubcategoryId === '__none__') {
    return items.filter((ing) => !ing.subcategory_id)
  }
  return items.filter((ing) => ing.subcategory_id === selectedSubcategoryId)
}, [filteredIngredients, selectedSubcategoryId])

// 3) Build sections using subcategory_id as the key (NO duplicates, header always matches)
const ingredientSections = useMemo(() => {
  const list = Array.isArray(subcategoryFilteredIngredients) ? subcategoryFilteredIngredients : []

  // If user picked a specific subcategory -> show ONE section with the correct title
  if (selectedSubcategoryId) {
    const title =
      selectedSubcategoryId === '__none__'
        ? t('ingredients.uncategorized')
        : t(
            `inventory.groups.${taxonomy.subcategoryById?.[selectedSubcategoryId]?.name || ''}`,
            { defaultValue: taxonomy.subcategoryById?.[selectedSubcategoryId]?.name || '' }
          )

    // Even if empty, you probably want to show the header; remove this filter if you want empty section hidden
    return [{ key: selectedSubcategoryId, title, items: list }]
  }

  // No filter -> group into multiple sections (keys are IDs)
  const buckets = {}
  for (const sc of (taxonomy.subcategories || [])) {
    if (sc?.id) buckets[sc.id] = []
  }
  buckets.__none__ = []

  for (const ing of list) {
    const k = ing.subcategory_id || '__none__'
    ;(buckets[k] ?? buckets.__none__).push(ing)
  }

  // Follow the same order as the select (skip "All")
  const valuesInOrder = subcategoryOptions.map((o) => o.value).filter((v) => v && v !== '')

  const sections = valuesInOrder.map((val) => {
    const title =
      val === '__none__'
        ? t('ingredients.uncategorized')
        : t(
            `inventory.groups.${taxonomy.subcategoryById?.[val]?.name || ''}`,
            { defaultValue: taxonomy.subcategoryById?.[val]?.name || '' }
          )
    return { key: val, title, items: buckets[val] || [] }
  })

  // Hide empty categories
  return sections.filter((s) => (s.items || []).length > 0)
}, [subcategoryFilteredIngredients, selectedSubcategoryId, taxonomy.subcategoryById, taxonomy.subcategories, subcategoryOptions, t])



  const sortedIngredients = useMemo(() => {
    const arr = [...(subcategoryFilteredIngredients || [])]
    arr.sort((a, b) => {
      const ak = (a?.subcategory_name || '').toLowerCase()
      const bk = (b?.subcategory_name || '').toLowerCase()
      if (ak !== bk) return ak.localeCompare(bk)

      const an = (a?.name || '').toLowerCase()
      const bn = (b?.name || '').toLowerCase()
      return an.localeCompare(bn)
    })
    return arr
  }, [subcategoryFilteredIngredients])


  const groupKeyForIngredient = (ing) => {
    const sub = (ing?.subcategory_name || '').trim()
    if (sub && INGREDIENT_GROUP_ORDER.includes(sub)) return sub
    return 'Uncategorized'
  }

  const displayIngredientSubcategory = (ing) => {
    const key = groupKeyForIngredient(ing)
    if (key === 'Uncategorized') return t('ingredients.uncategorized')
    return t(`inventory.groups.${key}`, { defaultValue: key })
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
        brand_name_he: b.name_he,
        bottle_size_ml: b.volume_ml,
        bottle_price: isAdmin ? (b.current_price?.price ?? '') : '',
      }))
      setBrandsByIngredientId((prev) => ({
        ...prev,
        [ingredientId]: { loading: false, error: '', brands },
      }))
    } catch (e) {
      setBrandsByIngredientId((prev) => ({
        ...prev,
        [ingredientId]: { loading: false, error: t('ingredients.errors.loadBrandsFailed'), brands: prev?.[ingredientId]?.brands || [] },
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
        brand_name_he: prev?.[ingredientId]?.brand_name_he ?? '',
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
    const brandNameHe = (bf.brand_name_he || '').trim()
    const bottleSizeMl = parseInt(bf.bottle_size_ml, 10)
    const bottlePrice = parseFloat(bf.bottle_price)
    const nameEn = brandName || brandNameHe
    if (!nameEn || Number.isNaN(bottleSizeMl) || Number.isNaN(bottlePrice)) return

    try {
      updateBrandForm(ingredientId, { submitting: true })
      const bottleRes = await api.post(`/ingredients/${ingredientId}/bottles`, {
        name: nameEn,
        name_he: brandNameHe || null,
        volume_ml: bottleSizeMl,
        is_default_cost: false,
      })
      await api.post(`/ingredients/bottles/${bottleRes.data.id}/prices`, {
        price: bottlePrice,
        currency: 'ILS',
      })
      await api.post(`/inventory/items`, {
        item_type: 'BOTTLE',
        bottle_id: bottleRes.data.id,
        name: nameEn,
        unit: 'ml',
      })
      updateBrandForm(ingredientId, { brand_name: '', brand_name_he: '', bottle_size_ml: '', bottle_price: '', submitting: false })
      await loadBrands(ingredientId)
      await loadBrandSuggestions()
    } catch (e) {
      updateBrandForm(ingredientId, { submitting: false })
      setError(t('ingredients.errors.createBrandFailed'))
      console.error('Failed to create brand', e)
    }
  }


  const startEditBrand = (brand) => {
    setEditingBrandById((prev) => ({
      ...prev,
      [brand.id]: {
        brand_name: brand.brand_name ?? '',
        brand_name_he: brand.brand_name_he ?? '',
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
    const brandNameHe = (eb.brand_name_he || '').trim()
    const bottleSizeMl = parseInt(eb.bottle_size_ml, 10)
    const bottlePrice = parseFloat(eb.bottle_price)
    const nameEn = brandName || brandNameHe
    if (!nameEn || Number.isNaN(bottleSizeMl) || Number.isNaN(bottlePrice)) return

    try {
      updateEditingBrand(brandId, { submitting: true })
      await api.put(`/ingredients/bottles/${brandId}`, {
        name: nameEn,
        name_he: brandNameHe || null,
        volume_ml: bottleSizeMl,
      })
      // Add a new price record (simple approach)
      await api.post(`/ingredients/bottles/${brandId}/prices`, {
        price: bottlePrice,
        currency: 'ILS',
      })
      cancelEditBrand(brandId)
      await loadBrands(ingredientId)
      await loadBrandSuggestions()
    } catch (e) {
      updateEditingBrand(brandId, { submitting: false })
      setError(t('ingredients.errors.updateBrandFailed'))
      console.error('Failed to update brand', e)
    }
  }

  const deleteBrand = async (brandId, ingredientId) => {
    try {
      await api.delete(`/ingredients/bottles/${brandId}`)
      await loadBrands(ingredientId)
    } catch (e) {
      setError(t('ingredients.errors.deleteBrandFailed'))
      console.error('Failed to delete brand', e)
    }
  }

  return (
    <div className="card">
      <div className="ingredients-header">
        <div className="ingredients-header-row">
          <div className={`search-container ${!isAdmin ? 'search-container-full' : ''}`}>
            <input
              type="text"
              placeholder={t('ingredients.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
        </div>
        {isAdmin && !editingIngredient && (
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="button-primary ingredients-add-button"
            aria-label={showAddForm ? t('common.cancel') : t('ingredients.addIngredient')}
            title={showAddForm ? t('common.cancel') : t('ingredients.addIngredient')}
          >
            <span className="ingredients-add-button-text">
              {showAddForm ? t('common.cancel') : t('ingredients.addIngredient')}
            </span>
            <span className="ingredients-add-button-icon">{showAddForm ? '×' : '+'}</span>
          </button>
        )}
      </div>
      <div className="ingredients-filters">
        <Select
          name="subcategory"
          value={selectedSubcategoryId}
          onChange={(val) => setSelectedSubcategoryId(val)}
          options={subcategoryOptions}
          placeholder={t('ingredients.subcategorySelect.allSubcategories')}
        />
      </div>

      {isAdmin && (
        <>
          {showAddForm && !editingIngredient && (
            <form onSubmit={handleSubmit} className="ingredient-form">
              <div className="form-row">
                <input
                  type="text"
                  placeholder={t('common.ingredientName')}
                  value={lang === 'he' ? form.name_he : form.name}
                  onChange={(e) => setForm(prev => (lang === 'he' ? { ...prev, name_he: e.target.value } : { ...prev, name: e.target.value }))}
                  className="form-input"
                />


                {isAdmin && taxonomy.subcategories.length > 0 && (
                  <select
                    className="form-input form-input-small"
                    value={form.subcategory_id}
                    onChange={(e) => setForm(prev => ({ ...prev, subcategory_id: e.target.value }))}
                  >
                    <option value="">{t('ingredients.groupPlaceholder')}</option>
                    {taxonomy.subcategories.map((s) => (
                      <option key={s.id} value={s.id}>{subcategoryLabel(s.name)}</option>
                    ))}
                  </select>
                )}
                <input
                  type="text"
                  placeholder={t('ingredients.brands.brandName')}
                  value={form.brand_name}
                  onChange={(e) => setForm(prev => ({ ...prev, brand_name: e.target.value }))}
                  list="brand-suggestions-global"
                  className="form-input form-input-small"
                />
                <input
                  type="number"
                  placeholder={t('ingredients.brands.sizeMl')}
                  value={form.bottle_size_ml}
                  onChange={(e) => setForm(prev => ({ ...prev, bottle_size_ml: e.target.value }))}
                  className="form-input form-input-small"
                  min="1"
                  step="1"
                />
                <input
                  type="number"
                  placeholder={t('ingredients.brands.price')}
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
                  {t('ingredients.addIngredient')}
                </button>
              </div>
            </form>
          )}
          {editingIngredient && (
            <form onSubmit={handleSubmit} className="ingredient-form">
              <div className="form-row">
                <input
                  type="text"
                  placeholder={t('common.ingredientName')}
                  value={lang === 'he' ? form.name_he : form.name}
                  onChange={(e) => setForm(prev => (lang === 'he' ? { ...prev, name_he: e.target.value } : { ...prev, name: e.target.value }))}
                  className="form-input"
                />
                <button
                  type="submit"
                  disabled={form.submitting || !form.name.trim()}
                  className="button-primary"
                >
                  {t('ingredients.updateIngredient')}
                </button>
                <button
                  type="button"
                  onClick={cancelEdit}
                  className="button-secondary"
                >
                  {t('common.cancel')}
                </button>
              </div>
            </form>
          )}
        </>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="ingredients-list">
        {loading && <div className="loading">{t('common.loading')}</div>}
        {!loading && (
          <div>
            {filteredIngredients.length === 0 ? (
              <div className="empty-state">
                {searchQuery.trim()
                  ? t('ingredients.empty.matching', { query: searchQuery })
                  : ingredients.length === 0
                    ? (isAdmin ? t('ingredients.empty.noneYet') : t('ingredients.empty.noneYetAdminsOnly'))
                    : t('ingredients.empty.noSearchMatch')}
              </div>
            ) : (
              ingredientSections.map((section) => (
                <div key={section.key} style={{ marginTop: section.key === 'spirit' ? 0 : 18 }}>
                  <h3 style={{ margin: '0 0 10px 0' }}>{section.title}</h3>
                  <ul>
                    {section.items.map((ing) => (
                      <li key={ing.id} className="ingredient-item">
                  <div className="ingredient-item-content">
                    <div className="ingredient-name-section">
                      {editingIngredientName === ing.id ? (
                        <div className="ingredient-name-edit">
                          <input
                            className="form-input"
                            type="text"
                            value={editingNameForm.name}
                            onChange={(e) => setEditingNameForm(prev => ({ ...prev, name: e.target.value }))}
                            placeholder="English name"
                          />
                          <input
                            className="form-input"
                            type="text"
                            value={editingNameForm.name_he}
                            onChange={(e) => setEditingNameForm(prev => ({ ...prev, name_he: e.target.value }))}
                            placeholder="Hebrew name"
                          />
                          <button
                            type="button"
                            className="button-primary"
                            onClick={() => saveIngredientName(ing.id)}
                          >
                            {t('common.save')}
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={cancelEditIngredientName}
                          >
                            {t('common.cancel')}
                          </button>
                        </div>
                      ) : (
                        <>
                          <strong>{displayName(ing)}</strong>
                          {isAdmin && taxonomy.subcategories.length > 0 && (
                            <select
                              className="button-secondary"
                              value={ing.subcategory_id || ''}
                              onChange={(e) => setIngredientSubcategory(ing.id, e.target.value)}
                            >
                              <option value="">{t('ingredients.subcategorySelect.uncategorized')}</option>
                              {taxonomy.subcategories.map((s) => (
                                <option key={s.id} value={s.id}>{subcategoryLabel(s.name)}</option>
                              ))}
                            </select>
                          )}
                          {isAuthenticated && (
                            <button
                              onClick={() => toggleBrands(ing.id)}
                              className="button-secondary button-brands"
                              type="button"
                            >
                              {expandedIngredientIds.has(ing.id) ? t('ingredients.brands.toggleHide') : t('ingredients.brands.toggleShow')}
                            </button>
                          )}
                        </>
                      )}
                    </div>
                    <div className="ingredient-actions">
                      {isAdmin && (
                        <div className="ingredient-admin-actions">
                          <button
                            onClick={() => startEditIngredientName(ing)}
                            className="button-edit"
                            type="button"
                          >
                            {t('ingredients.actions.edit')}
                          </button>
                          <button
                            onClick={() => requestRemoveIngredient(ing.id)}
                            className="button-remove"
                            type="button"
                          >
                            {t('ingredients.actions.remove')}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {expandedIngredientIds.has(ing.id) && (
                    <div className="brands-panel">
                      <div className="brands-header">
                        <h4>{t('ingredients.brands.title')}</h4>
                        <button type="button" className="button-secondary" onClick={() => loadBrands(ing.id)}>
                          {t('ingredients.brands.refresh')}
                        </button>
                      </div>

                      {brandsByIngredientId?.[ing.id]?.loading && <div className="loading">{t('ingredients.brands.loading')}</div>}
                      {brandsByIngredientId?.[ing.id]?.error && (
                        <div className="error-message">{brandsByIngredientId[ing.id].error}</div>
                      )}

                      {!brandsByIngredientId?.[ing.id]?.loading && (
                        <div className="brands-list">
                          {(brandsByIngredientId?.[ing.id]?.brands || []).length === 0 ? (
                            <div className="empty-state">{t('ingredients.brands.empty')}</div>
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
                                        value={eb.brand_name || ''}
                                        onChange={(e) => updateEditingBrand(b.id, { brand_name: e.target.value })}
                                        placeholder="English name"
                                        list="brand-suggestions-global"
                                      />
                                      <input
                                        className="form-input"
                                        value={eb.brand_name_he || ''}
                                        onChange={(e) => updateEditingBrand(b.id, { brand_name_he: e.target.value })}
                                        placeholder="Hebrew name"
                                      />
                                      <input
                                        className="form-input form-input-small"
                                        value={eb.bottle_size_ml}
                                        onChange={(e) => updateEditingBrand(b.id, { bottle_size_ml: e.target.value })}
                                        placeholder={t('ingredients.brands.sizeMlShort')}
                                        type="number"
                                        min="1"
                                        step="1"
                                      />
                                      <input
                                        className="form-input form-input-small"
                                        value={eb.bottle_price}
                                        onChange={(e) => updateEditingBrand(b.id, { bottle_price: e.target.value })}
                                        placeholder={t('ingredients.brands.priceShort')}
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
                                            {t('common.save')}
                                          </button>
                                          <button
                                            type="button"
                                            className="button-secondary"
                                            disabled={eb.submitting}
                                            onClick={() => cancelEditBrand(b.id)}
                                          >
                                            {t('common.cancel')}
                                          </button>
                                        </div>
                                      )}
                                    </>
                                  ) : (
                                    <>
                                      <div className="brand-display">
                                        <strong>{lang === 'he' ? ((b.brand_name_he || '').trim() || (b.brand_name || '').trim()) : ((b.brand_name || '').trim() || (b.brand_name_he || '').trim())}</strong>
                                        <span>{b.bottle_size_ml} ml</span>
                                        {isAdmin && <span>{b.bottle_price}</span>}
                                      </div>
                                      {isAdmin && (
                                        <div className="brand-actions">
                                          <button type="button" className="button-edit" onClick={() => startEditBrand(b)}>
                                            {t('common.edit')}
                                          </button>
                                          <button
                                            type="button"
                                            className="button-remove"
                                            onClick={() => deleteBrand(b.id, ing.id)}
                                          >
                                            {t('ingredients.brands.delete')}
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
                          <h4>{t('ingredients.brands.addTitle')}</h4>
                          <div className="brand-row">
                            <input
                              className="form-input"
                              value={brandFormByIngredientId?.[ing.id]?.brand_name ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { brand_name: e.target.value })}
                              placeholder="English name"
                              list="brand-suggestions-global"
                            />
                            <input
                              className="form-input"
                              value={brandFormByIngredientId?.[ing.id]?.brand_name_he ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { brand_name_he: e.target.value })}
                              placeholder="Hebrew name"
                            />
                            <input
                              className="form-input form-input-small"
                              value={brandFormByIngredientId?.[ing.id]?.bottle_size_ml ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { bottle_size_ml: e.target.value })}
                              placeholder={t('ingredients.brands.sizeMl')}
                              type="number"
                              min="1"
                              step="1"
                            />
                            <input
                              className="form-input form-input-small"
                              value={brandFormByIngredientId?.[ing.id]?.bottle_price ?? ''}
                              onChange={(e) => updateBrandForm(ing.id, { bottle_price: e.target.value })}
                              placeholder={t('ingredients.brands.price')}
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
                              {t('ingredients.brands.add')}
                            </button>
                          </div>
                        </div>
                    )}
                  </div>
                  )}
                </li>
                      ))}
                  </ul>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteConfirmOpen}
        title={t('ingredients.deleteDialog.title')}
        message={
          <div>
            <div style={{ marginBottom: 8 }}>
              {t('ingredients.deleteDialog.usedBy')}
            </div>
            {pendingDeleteUsedBy.loading ? (
              <div style={{ marginBottom: 12 }}>{t('ingredients.deleteDialog.loading')}</div>
            ) : pendingDeleteUsedBy.error ? (
              <div style={{ marginBottom: 12 }}>{pendingDeleteUsedBy.error}</div>
            ) : Array.isArray(pendingDeleteUsedBy.cocktails) && pendingDeleteUsedBy.cocktails.length > 0 ? (
              <ul style={{ marginTop: 0, marginBottom: 12, paddingLeft: 18 }}>
                {pendingDeleteUsedBy.cocktails.map((c) => (
                  <li key={c.id}>{c.name}</li>
                ))}
              </ul>
            ) : (
              <div style={{ marginBottom: 12 }}>{t('ingredients.deleteDialog.noCocktails')}</div>
            )}
            <div>
              {t('ingredients.deleteDialog.confirmQuestion', { name: ingredients.find(i => i.id === pendingDeleteIngredientId)?.name || '' })}
            </div>
          </div>
        }
        confirmText={t('ingredients.deleteDialog.confirm')}
        cancelText={t('common.cancel')}
        variant="danger"
        onCancel={() => {
          setDeleteConfirmOpen(false)
          setPendingDeleteIngredientId(null)
          setPendingDeleteUsedBy({ loading: false, error: '', cocktails: [] })
        }}
        onConfirm={removeIngredient}
      />

      {/* Global brand suggestions for all brand inputs (Add Ingredient / Add Brand / Edit Brand) */}
      <datalist id="brand-suggestions-global">
        {(brandSuggestions || [])
          .map((n) => (n || '').trim())
          .filter(Boolean)
          .sort((a, b) => a.localeCompare(b))
          .map((name) => <option key={name} value={name} />)}
      </datalist>
    </div>
  )
}

export default IngredientsPage

