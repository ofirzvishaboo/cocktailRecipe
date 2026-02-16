import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import AddCocktailForm from '../components/cocktail/AddCocktailForm'
import ConfirmDialog from '../components/common/ConfirmDialog'

const CocktailDetailPage = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, isAuthenticated, isAdmin } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]
  const [cocktail, setCocktail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [costData, setCostData] = useState(null)
  const [costLoading, setCostLoading] = useState(false)
  const [costError, setCostError] = useState('')
  const [glassTypesById, setGlassTypesById] = useState({})
  const [metaEdit, setMetaEdit] = useState({ glass: false, garnish: false })
  const [metaDraft, setMetaDraft] = useState({ glass_name_he: '', garnish_text_he: '' })
  const [metaSaving, setMetaSaving] = useState(false)
  const [metaSaveError, setMetaSaveError] = useState('')
  const [ingredientsByNameLower, setIngredientsByNameLower] = useState({})

  useEffect(() => {
    const loadCocktail = async () => {
      try {
        setLoading(true)
        setError('')
        const response = await api.get(`/cocktail-recipes/${id}`)
        setCocktail(response.data)
      } catch (e) {
        if (e.response?.status === 404) {
          setError(t('cocktailDetail.errors.notFound'))
        } else {
          setError(t('cocktailDetail.errors.loadFailed'))
          console.error('Failed to load cocktail', e)
        }
      } finally {
        setLoading(false)
      }
    }
    loadCocktail()
  }, [id, t])

  useEffect(() => {
    const loadGlassTypes = async () => {
      try {
        const res = await api.get('/glass-types')
        const map = {}
        for (const g of res.data || []) {
          map[String(g.id)] = g
        }
        setGlassTypesById(map)
      } catch (e) {
        console.error('Failed to load glass types', e)
        setGlassTypesById({})
      }
    }
    loadGlassTypes()
  }, [])

  useEffect(() => {
    // If garnish has no explicit Hebrew field, try to map garnish_text to an Ingredient.name_he
    // so that translations added via the Ingredients page can still show up here.
    const shouldLoad =
      lang === 'he' &&
      !!(cocktail?.garnish_text || '').trim() &&
      !(cocktail?.garnish_text_he || '').trim()

    if (!shouldLoad) return

    const load = async () => {
      try {
        const res = await api.get('/ingredients/')
        const list = Array.isArray(res.data) ? res.data : []
        const byLower = {}
        for (const ing of list) {
          const en = (ing?.name || '').trim().toLowerCase()
          const he = (ing?.name_he || '').trim().toLowerCase()
          if (en) byLower[en] = ing
          if (he) byLower[he] = ing
        }
        setIngredientsByNameLower(byLower)
      } catch (e) {
        console.error('Failed to load ingredients for garnish translation', e)
        setIngredientsByNameLower({})
      }
    }

    load()
  }, [cocktail?.garnish_text, cocktail?.garnish_text_he, lang])

  useEffect(() => {
    const loadCost = async () => {
      if (!id) return
      if (!isAdmin) {
        setCostData(null)
        setCostError('')
        return
      }
      try {
        setCostLoading(true)
        setCostError('')
        const res = await api.get(`/cocktail-recipes/${id}/cost`, { params: { scale_factor: 1.0 } })
        setCostData(res.data)
      } catch (e) {
        setCostData(null)
        setCostError(t('cocktailDetail.errors.costLoadFailed'))
        console.error('Failed to load cost', e)
      } finally {
        setCostLoading(false)
      }
    }
    loadCost()
  }, [id, t, isAdmin])

  useEffect(() => {
    // Keep inline edit drafts in sync with loaded data
    const glassTypeId = cocktail?.glass_type_id ? String(cocktail.glass_type_id) : ''
    const glassType = glassTypeId ? glassTypesById[glassTypeId] : null
    setMetaDraft({
      glass_name_he: glassType?.name_he || '',
      garnish_text_he: cocktail?.garnish_text_he || '',
    })
    setMetaSaveError('')
    setMetaEdit({ glass: false, garnish: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cocktail?.id, cocktail?.glass_type_id, glassTypesById])

  const displayUnit = (unit) => {
    const key = (unit || '').trim().toLowerCase()
    if (!key) return ''
    return t(`common.units.${key}`, { defaultValue: unit })
  }

  const displayCurrency = (currency) => {
    const key = (currency || '').trim().toUpperCase()
    if (!key) return t('common.currencies.ILS', { defaultValue: 'ILS' })
    return t(`common.currencies.${key}`, { defaultValue: key })
  }

  const formatMoney = (value, currency) => {
    const n = Number(value)
    if (Number.isNaN(n)) return '-'
    const c = displayCurrency(currency || 'ILS')
    return `${n.toFixed(2)} ${c}`
  }

  const handleDelete = async () => {
    try {
      await api.delete(`/cocktail-recipes/${id}`)
      navigate('/')
    } catch (e) {
      setError(t('cocktailDetail.errors.deleteFailed'))
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
      setError(t('cocktailDetail.errors.updateFailed'))
      console.error('Failed to update cocktail', e)
    }
  }

  const isOwner = () => {
    return isAuthenticated && user && cocktail && (isAdmin || cocktail.created_by_user_id === user.id)
  }

  const buildCocktailUpdatePayload = (overrides = {}) => {
    const ris = Array.isArray(cocktail?.recipe_ingredients) ? cocktail.recipe_ingredients : []
    return {
      name: (cocktail?.name || '').trim() || (cocktail?.name_he || '').trim(),
      name_he: (cocktail?.name_he || '').trim() || null,
      description: (cocktail?.description || '').trim() || null,
      description_he: (cocktail?.description_he || '').trim() || null,
      picture_url: cocktail?.picture_url || null,
      garnish_text: (cocktail?.garnish_text || '').trim() || null,
      garnish_text_he: (cocktail?.garnish_text_he || '').trim() || null,
      glass_type_id: cocktail?.glass_type_id || null,
      base_recipe_id: cocktail?.base_recipe_id || null,
      is_base: !!cocktail?.is_base,
      menus: Array.isArray(cocktail?.menus) ? cocktail.menus : (cocktail?.is_base ? ['classic'] : ['signature']),
      preparation_method: (cocktail?.preparation_method || '').trim() || null,
      preparation_method_he: (cocktail?.preparation_method_he || '').trim() || null,
      batch_type: cocktail?.batch_type || null,
      recipe_ingredients: ris.map((ri, idx) => ({
        ingredient_id: ri.ingredient_id,
        quantity: Number(ri.quantity || 0),
        unit: (ri.unit || 'ml').toLowerCase(),
        bottle_id: ri.bottle_id || null,
        is_garnish: !!ri.is_garnish,
        is_optional: !!ri.is_optional,
        sort_order: ri.sort_order ?? (idx + 1),
      })),
      ...overrides,
    }
  }


  if (loading) {
    return (
      <div className="card">
        <div className="loading">{t('cocktailDetail.loading')}</div>
      </div>
    )
  }

  if (error && !cocktail) {
    return (
      <div className="card">
        <div className="error-message">{error}</div>
        <Link to="/" className="button-primary">{t('cocktailDetail.backToCocktails')}</Link>
      </div>
    )
  }

  if (!cocktail) {
    return null
  }

  const glassTypeId = cocktail.glass_type_id ? String(cocktail.glass_type_id) : ''
  const glassType = glassTypeId ? glassTypesById[glassTypeId] : null
  const displayCocktailName = () => {
    const he = (cocktail?.name_he || '').trim()
    const en = (cocktail?.name || '').trim()
    return lang === 'he' ? (he || en) : (en || he)
  }

  const displayCocktailText = (enValue, heValue) => {
    const he = (heValue || '').trim()
    const en = (enValue || '').trim()
    return lang === 'he' ? (he || en) : (en || he)
  }

  const displayGarnish = () => {
    const he = (cocktail?.garnish_text_he || '').trim()
    const en = (cocktail?.garnish_text || '').trim()
    if (lang !== 'he') return (en || he)
    if (he) return he
    if (!en) return ''
    const key = en.toLowerCase()
    const mapped = ingredientsByNameLower?.[key]
    const mappedHe = (mapped?.name_he || '').trim()
    return mappedHe || en
  }

  const glassTypeName = displayCocktailText(
    glassType?.name || cocktail?.glass_type_name,
    glassType?.name_he || cocktail?.glass_type_name_he,
  )

  const glassTypeLabel = glassTypeName
    ? `${glassTypeName}${glassType?.capacity_ml ? ` (${glassType.capacity_ml} ${displayUnit('ml')})` : ''}`
    : (glassTypeId ? t('cocktailDetail.glass.unknown') : '-')

  if (editing) {
    return (
      <div className="card">
        <h2>{t('cocktailDetail.editTitle')}</h2>
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
      <div className="cocktail-title-row">
        <Link to="/" className="back-link" aria-label={t('cocktailDetail.backToCocktails')}>
          <span className="back-link-icon" aria-hidden="true">{lang === 'he' ? '→' : '←'}</span>
          <span className="back-link-text">{t('cocktailDetail.backToCocktails')}</span>
        </Link>
        <h1 className="cocktail-detail-title">{displayCocktailName()}</h1>
        {isOwner() && (
          <div className="cocktail-actions-inline">
            <button
              onClick={() => setEditing(true)}
              className="button-edit"
            >
              {t('cocktailDetail.actions.edit')}
            </button>
            <button
              onClick={() => setDeleteConfirmOpen(true)}
              className="button-remove"
            >
              {t('cocktailDetail.actions.delete')}
            </button>
          </div>
        )}
      </div>
      <div className="cocktail-detail-header" />

      <div className="cocktail-detail-content">
        <div className="cocktail-detail-image">
          {cocktail.picture_url && !imageError ? (
            <img
              src={cocktail.picture_url}
              alt={displayCocktailName()}
              className="cocktail-detail-image-large"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="cocktail-image-placeholder-large">
              {cocktail.picture_url ? t('cocktailDetail.image.invalid') : t('cocktailDetail.image.none')}
            </div>
          )}
        </div>

        <div className="cocktail-detail-info">
          {displayCocktailText(cocktail.description, cocktail.description_he) && (
            <div className="cocktail-description cocktail-description--desc">
              <p>{displayCocktailText(cocktail.description, cocktail.description_he)}</p>
            </div>
          )}

          {displayCocktailText(cocktail.preparation_method, cocktail.preparation_method_he) && (
            <div className="cocktail-description cocktail-description--prep">
              <p>{displayCocktailText(cocktail.preparation_method, cocktail.preparation_method_he)}</p>
            </div>
          )}

          <div className="cocktail-meta">
            <div className="meta-grid">
              <div className="meta-row">
                <span className="meta-label">{t('cocktailDetail.meta.glass')}</span>
                <span className="meta-value">
                  {glassTypeLabel}
                </span>
              </div>
              <div className="meta-row">
                <span className="meta-label">{t('cocktailDetail.meta.garnish')}</span>
                <span className="meta-value">
                  {displayGarnish() || '-'}
                </span>
              </div>
            </div>
          </div>
          {metaSaveError && <div className="error-message" style={{ marginTop: 10 }}>{metaSaveError}</div>}

          <div className="cocktail-ingredients-section detail-section">
            <div className="detail-section-header">
              <h2>{t('cocktailDetail.sections.ingredients')}</h2>
            </div>
            {(cocktail.recipe_ingredients && cocktail.recipe_ingredients.length > 0) ? (
              <ul className="ingredients-list-detailed">
                {cocktail.recipe_ingredients.map((ri, i) => (
                  <li key={`${ri.ingredient_id}-${i}`} className="ingredient-item-detailed">
                    <span className="ingredient-name">{displayCocktailText(ri.ingredient_name, ri.ingredient_name_he) || t('cocktailDetail.unknown')}</span>
                    <span className="ingredient-brand">{displayCocktailText(ri.bottle_name, ri.bottle_name_he) || '-'}</span>
                    <span className="ingredient-amount">{ri.quantity} {displayUnit(ri.unit)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>{t('cocktailDetail.ingredients.none')}</p>
            )}
          </div>

          {isAdmin && (
            <div className="cocktail-ingredients-section detail-section">
              <div className="detail-section-header">
                <h2>{t('cocktailDetail.sections.cost')}</h2>
                {costData && !costLoading && !costError && (
                  <div className="cost-pill">
                    {t('cocktailDetail.cost.total')}: {formatMoney(
                      costData.total_cocktail_cost,
                      costData?.lines?.find((l) => l?.currency)?.currency || 'ILS'
                    )}
                  </div>
                )}
              </div>
              {costLoading ? (
                <p>{t('cocktailDetail.cost.loading')}</p>
              ) : costError ? (
                <p className="error-message">{costError}</p>
              ) : costData ? (
                <>
                  {(costData.lines && costData.lines.length > 0) ? (
                    <ul className="ingredients-list-detailed">
                      {costData.lines.map((line, i) => (
                        <li key={`${line.ingredient_name}-${i}`} className="ingredient-item-detailed">
                          <span className="ingredient-name">{displayCocktailText(line.ingredient_name, line.ingredient_name_he) || t('cocktailDetail.unknown')}</span>
                          <span className="ingredient-brand">{displayCocktailText(line.bottle_name, line.bottle_name_he) || '-'}</span>
                          <span className="ingredient-amount">{formatMoney(line.ingredient_cost, line.currency || 'ILS')}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>{t('cocktailDetail.cost.noneLines')}</p>
                  )}
                </>
              ) : (
                <p>{t('cocktailDetail.cost.notAvailable')}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <ConfirmDialog
        open={deleteConfirmOpen}
        title={t('cocktails.deleteDialog.title')}
        message={t('cocktails.deleteDialog.message', { name: displayCocktailName() })}
        confirmText={t('cocktails.deleteDialog.confirm')}
        cancelText={t('common.cancel')}
        variant="danger"
        onCancel={() => setDeleteConfirmOpen(false)}
        onConfirm={handleDelete}
      />
    </div>
  )
}

export default CocktailDetailPage

