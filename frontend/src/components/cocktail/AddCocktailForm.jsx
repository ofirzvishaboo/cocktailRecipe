import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../../api'
import IngredientInputs from './IngredientInputs'
import Select from '../common/Select'
import { useAuth } from '../../contexts/AuthContext'

function AddCocktailForm({ AddCocktail, initialCocktail, onCancel, isEdit = false }) {
    const { t, i18n } = useTranslation()
    const lang = (i18n.language || 'en').split('-')[0]
    const { isAdmin } = useAuth()
    const [ingredientsCatalog, setIngredientsCatalog] = useState([])
    const [brandsByIngredientId, setBrandsByIngredientId] = useState({})
    const [glassTypes, setGlassTypes] = useState([])
    const [brandOptionsByIndex, setBrandOptionsByIndex] = useState(
        (initialCocktail?.recipe_ingredients || []).map(() => []) || [[]]
    )

    const [form, setForm] = useState({
        name: initialCocktail?.name || '',
        name_he: initialCocktail?.name_he || '',
        description: initialCocktail?.description || '',
        description_he: initialCocktail?.description_he || '',
        is_base: !!initialCocktail?.is_base,
        glass_type_id: initialCocktail?.glass_type_id || '',
        garnish_text: initialCocktail?.garnish_text || '',
        garnish_text_he: initialCocktail?.garnish_text_he || '',
        preparation_method: initialCocktail?.preparation_method || '',
        preparation_method_he: initialCocktail?.preparation_method_he || '',
        ingredients: (initialCocktail?.recipe_ingredients || []).map((ri) => ({
            name: ri.ingredient_name || '',
            name_he: ri.ingredient_name_he || '',
            ingredient_id: ri.ingredient_id || '',
            amount: ri.quantity !== undefined ? String(ri.quantity) : '',
            unit: ri.unit || 'ml',
            bottle_id: ri.bottle_id || '',
        })) || [{ name: '', name_he: '', ingredient_id: '', amount: '', unit: 'ml', bottle_id: '' }],
        imageUrl: initialCocktail?.picture_url || '',
        imagePreview: initialCocktail?.picture_url || '',
        submitting: false,
    })

    const ingredientNameSuggestions = useMemo(
        () => {
            const out = []
            for (const i of (ingredientsCatalog || [])) {
                const he = (i?.name_he || '').trim()
                const en = (i?.name || '').trim()
                const label = lang === 'he' ? (he || en) : (en || he)
                if (label) out.push(label)
            }
            return out
        },
        [ingredientsCatalog, lang]
    )

    useEffect(() => {
        const loadIngredientsCatalog = async () => {
            try {
                const res = await api.get('/ingredients/')
                setIngredientsCatalog(res.data || [])
            } catch (e) {
                console.error('Failed to load ingredients catalog', e)
            }
        }
        loadIngredientsCatalog()
    }, [])

    useEffect(() => {
        const loadGlassTypes = async () => {
            try {
                const res = await api.get('/glass-types')
                setGlassTypes(res.data || [])
            } catch (e) {
                console.error('Failed to load glass types', e)
                setGlassTypes([])
            }
        }
        loadGlassTypes()
    }, [])

    const findIngredientIdByName = (name) => {
        const n = (name || '').trim().toLowerCase()
        if (!n) return null
        const match = (ingredientsCatalog || []).find((i) => {
            const en = (i?.name || '').trim().toLowerCase()
            const he = (i?.name_he || '').trim().toLowerCase()
            return en === n || he === n
        })
        return match?.id || null
    }

    const ensureIngredientId = async (rawName, submitCache) => {
        const name = (rawName || '').trim()
        const key = name.toLowerCase()
        if (!name) return null

        // 1) Already in the loaded catalog
        const existingId = findIngredientIdByName(name)
        if (existingId) return existingId

        // 2) Already created during this submit
        if (submitCache.has(key)) return submitCache.get(key)

        // 3) Create new ingredient
        const res = await api.post('/ingredients/', { name })
        const created = res?.data
        if (!created?.id) throw new Error('Failed to create ingredient (missing id)')

        submitCache.set(key, created.id)
        setIngredientsCatalog((prev) => {
            const prevArr = Array.isArray(prev) ? prev : []
            // Avoid duplicating if backend returned an existing ingredient we didn't have locally.
            const already = prevArr.some((i) => (i?.id && i.id === created.id))
            return already ? prevArr : [...prevArr, created]
        })
        return created.id
    }

    const loadBrandsForIngredientId = async (ingredientId) => {
        if (!ingredientId) return []
        if (brandsByIngredientId[ingredientId]) return brandsByIngredientId[ingredientId]
        const res = await api.get(`/ingredients/${ingredientId}/bottles`)
        const bottles = res.data || []
        setBrandsByIngredientId((prev) => ({ ...prev, [ingredientId]: bottles }))
        return bottles
    }

    const syncBrandOptionsForRow = async (index, ingredientName) => {
        const ingredientId = findIngredientIdByName(ingredientName)
        if (!ingredientId) {
            setBrandOptionsByIndex((prev) => {
                const next = [...prev]
                next[index] = []
                return next
            })
            return
        }
        try {
            const brands = await loadBrandsForIngredientId(ingredientId)
            setBrandOptionsByIndex((prev) => {
                const next = [...prev]
                next[index] = brands
                return next
            })
        } catch (e) {
            console.error('Failed to load brands for ingredient', ingredientId, e)
        }
    }

    useEffect(() => {
        // When catalog loads or ingredients change, ensure brand options are loaded for rows with known ingredient names
        const run = async () => {
            const rows = form.ingredients || []
            await Promise.all(
                rows.map((row, idx) => syncBrandOptionsForRow(idx, row.name))
            )
        }
        if (ingredientsCatalog.length > 0) run()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [ingredientsCatalog])

    const addIngredient = () => {
        setForm(prev => ({
            ...prev,
            ingredients: [...prev.ingredients, { name: '', name_he: '', ingredient_id: '', amount: '', unit: 'ml', bottle_id: '' }]
        }))
        setBrandOptionsByIndex((prev) => [...prev, []])
    }

    const removeIngredient = (index) => {
        setForm(prev => {
            if (prev.ingredients.length <= 1) return prev
            const nextIngredients = prev.ingredients.filter((_, i) => i !== index)
            return { ...prev, ingredients: nextIngredients }
        })
        setBrandOptionsByIndex((prev) => prev.filter((_, i) => i !== index))
    }

    const handleIngredientChange = (index, field, value) => {
        setForm(prev => {
            const updated = prev.ingredients.map((ingredient, i) => {
                if (i !== index) return ingredient
                if (field === 'name' || field === 'name_he') {
                    const next = { ...ingredient, [field]: value, ingredient_id: '', bottle_id: '' }
                    // If user fills Hebrew name and English is still empty, auto-fill English to satisfy backend expectations.
                    if (field === 'name_he' && !(next?.name || '').trim() && (value || '').trim()) {
                        next.name = value
                    }
                    return next
                }
                return { ...ingredient, [field]: value }
            })
            return { ...prev, ingredients: updated }
        })

        if (field === 'name' || field === 'name_he') syncBrandOptionsForRow(index, value)
    }

    const handleImageChange = async (e) => {
        const file = e.target.files[0]
        if (file) {
            // Validate file type (iOS Safari sometimes provides an empty file.type)
            const fileType = String(file.type || '')
            const fileName = String(file.name || '')
            const ext = (fileName.split('.').pop() || '').toLowerCase()
            const looksLikeImageByExt = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'].includes(ext)
            const looksLikeImage = fileType.startsWith('image/') || looksLikeImageByExt
            if (!looksLikeImage) {
                alert(t('cocktailForm.alerts.imageNotFile'))
                return
            }
            // Validate file size (min 100 bytes, max 10MB)
            if (file.size < 100) {
                alert(t('cocktailForm.alerts.imageCorrupt'))
                return
            }
            if (file.size > 10 * 1024 * 1024) {
                alert(t('cocktailForm.alerts.imageTooLarge'))
                return
            }

            try {
                // Show preview immediately
                const reader = new FileReader()
                reader.onloadend = () => {
                    setForm(prev => ({
                        ...prev,
                        imagePreview: reader.result
                    }))
                }
                reader.readAsDataURL(file)

                // Upload to ImageKit via backend
                const formData = new FormData()
                formData.append('file', file)

                // IMPORTANT: do not set Content-Type manually; the browser must add the boundary.
                const response = await api.post('/images/upload', formData)

                console.log('ImageKit upload response:', response.data)

                if (response.data && response.data.url) {
                    // Update with ImageKit URL
                    setForm(prev => ({
                        ...prev,
                        imageUrl: response.data.url,
                        imagePreview: response.data.url
                    }))
                } else {
                    throw new Error('No URL returned from ImageKit upload')
                }
            } catch (error) {
                console.error('Failed to upload image:', error)
                const detail = error?.response?.data?.detail
                alert(detail ? String(detail) : t('cocktailForm.alerts.imageUploadFailed'))
                // Reset image selection
                setForm(prev => ({
                    ...prev,
                    imageUrl: '',
                    imagePreview: ''
                }))
            }
        }
    }

    const removeImage = () => {
        setForm(prev => ({
            ...prev,
            imageUrl: '',
            imagePreview: ''
        }))
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        const submitCache = new Map()

        const rows = (form.ingredients || [])
            .map((ing) => ({
                ...ing,
                name: (lang === 'he'
                    ? ((ing?.name_he || '').trim() || (ing?.name || '').trim())
                    : ((ing?.name || '').trim() || (ing?.name_he || '').trim())),
                amount: ing?.amount,
            }))
            .filter((ing) => ing.name && ing.amount !== '' && !isNaN(Number(ing.amount)))

        if (!form.name || rows.length === 0) return

        let ingredientIdsByIndex = []
        try {
            ingredientIdsByIndex = await Promise.all(
                rows.map(async (ing) => ing.ingredient_id || await ensureIngredientId(ing.name, submitCache))
            )
        } catch (err) {
            console.error('Failed to create missing ingredients', err)
            alert(t('cocktailForm.alerts.ingredientCreateFailed'))
            return
        }

        const ingredientsArray = rows.map((ing, idx) => ({
            ingredient_id: ingredientIdsByIndex[idx],
            quantity: Number(ing.amount),
            unit: (ing.unit || 'ml').toLowerCase(),
            bottle_id: ing.bottle_id ? ing.bottle_id : null,
            sort_order: idx + 1,
            is_garnish: false,
            is_optional: false,
        }))

        if (!form.name || ingredientsArray.length === 0) return

        const newCocktail = {
            name: (form.name || '').trim() || (form.name_he || '').trim(),
            name_he: (form.name_he || '').trim() || null,
            description: (form.description || '').trim() || null,
            description_he: (form.description_he || '').trim() || null,
            recipe_ingredients: ingredientsArray,
            picture_url: form.imageUrl || null,
            glass_type_id: form.glass_type_id || null,
            garnish_text: (form.garnish_text || '').trim() || null,
            garnish_text_he: (form.garnish_text_he || '').trim() || null,
            is_base: !!form.is_base,
            preparation_method: (form.preparation_method || '').trim() || null,
            preparation_method_he: (form.preparation_method_he || '').trim() || null,
        }

        try {
            setForm(prev => ({ ...prev, submitting: true }))
            const id = isEdit ? initialCocktail.id : Date.now()

            if (isEdit) {
                const response = await api.put(`/cocktail-recipes/${id}`, newCocktail)
                // Use the API response which includes all fields
                AddCocktail(response.data)
            } else {
                const response = await api.post(`/cocktail-recipes/`, newCocktail)
                // Use the API response which includes all fields
                AddCocktail(response.data)
            }

            if (!isEdit) {
                setForm({
                    name: '',
                    name_he: '',
                    description: '',
                    description_he: '',
                    is_base: false,
                    glass_type_id: '',
                    garnish_text: '',
                    garnish_text_he: '',
                    preparation_method: '',
                    preparation_method_he: '',
                    ingredients: [{ name: '', ingredient_id: '', amount: '', unit: 'ml', bottle_id: '' }],
                    imageUrl: '',
                    imagePreview: '',
                    submitting: false
                })
                setBrandOptionsByIndex([[]])
            }
        } catch (e) {
            if (e?.response?.status === 401) {
                alert(t('cocktailForm.alerts.sessionExpired'))
            } else {
                alert(t('cocktailForm.alerts.saveFailed'))
            }
            console.error('Failed to save cocktail', e)
        } finally {
            setForm(prev => ({ ...prev, submitting: false }))
        }
    }

    return (
        <form onSubmit={handleSubmit} className="cocktail-form">
            <div className="form-group">
                <label htmlFor="form-name">{t('cocktailForm.nameLabel')}</label>
                <input
                    type="text"
                    placeholder={t('cocktailForm.namePlaceholder')}
                    id="form-name"
                    value={lang === 'he' ? form.name_he : form.name}
                    onChange={(e) => setForm(prev => (lang === 'he' ? { ...prev, name_he: e.target.value } : { ...prev, name: e.target.value }))}
                    className="form-input"
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-classification">{t('cocktailForm.typeLabel')}</label>
                <Select
                    id="form-classification"
                    value={form.is_base ? 'CLASSIC' : 'SIGNATURE'}
                    onChange={(v) => setForm((prev) => ({ ...prev, is_base: v === 'CLASSIC' }))}
                    ariaLabel={t('cocktailForm.typeLabel')}
                    options={[
                        { value: 'SIGNATURE', label: t('cocktailForm.type.signature') },
                        { value: 'CLASSIC', label: t('cocktailForm.type.classic') },
                    ]}
                />
            </div>
            <div className="form-group">
                <label htmlFor="form-description">{t('cocktailForm.descriptionLabel')}</label>
                <textarea
                    id="form-description"
                    placeholder={t('cocktailForm.descriptionPlaceholder')}
                    value={lang === 'he' ? form.description_he : form.description}
                    onChange={(e) => setForm(prev => (lang === 'he' ? { ...prev, description_he: e.target.value } : { ...prev, description: e.target.value }))}
                    className="form-input form-textarea"
                    rows={4}
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-glass-type">{t('cocktailForm.glassLabel')}</label>
                <Select
                    id="form-glass-type"
                    value={form.glass_type_id}
                    onChange={(v) => setForm((prev) => ({ ...prev, glass_type_id: v }))}
                    ariaLabel={t('cocktailForm.glassLabel')}
                    placeholder={t('cocktailForm.glassPlaceholder')}
                    options={(glassTypes || []).map((g) => {
                        const label = (lang === 'he'
                            ? ((g?.name_he || '').trim() || (g?.name || '').trim())
                            : ((g?.name || '').trim() || (g?.name_he || '').trim()))
                        const suffix = g?.capacity_ml ? ` (${g.capacity_ml}ml)` : ''
                        return { value: g.id, label: `${label}${suffix}` }
                    })}
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-garnish">{t('cocktailForm.garnishLabel')}</label>
                <input
                    type="text"
                    id="form-garnish"
                    placeholder={t('cocktailForm.garnishPlaceholder')}
                    value={lang === 'he' ? form.garnish_text_he : form.garnish_text}
                    onChange={(e) => setForm((prev) => (lang === 'he' ? { ...prev, garnish_text_he: e.target.value } : { ...prev, garnish_text: e.target.value }))}
                    className="form-input"
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-preparation-method">{t('cocktailForm.preparationLabel')}</label>
                <textarea
                    id="form-preparation-method"
                    placeholder={t('cocktailForm.preparationPlaceholder')}
                    value={lang === 'he' ? form.preparation_method_he : form.preparation_method}
                    onChange={(e) => setForm((prev) => (lang === 'he' ? { ...prev, preparation_method_he: e.target.value } : { ...prev, preparation_method: e.target.value }))}
                    className="form-input form-textarea"
                    rows={3}
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-image">{t('cocktailForm.imageLabel')}</label>
                <input
                    type="file"
                    id="form-image"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="form-input"
                />
                {form.imagePreview && (
                    <div className="image-preview-container">
                        <img src={form.imagePreview} alt={t('cocktailForm.imagePreviewAlt')} className="image-preview" />
                        <button
                            type="button"
                            onClick={removeImage}
                            className="button-remove-small"
                        >
                            {t('cocktailForm.removeImage')}
                        </button>
                    </div>
                )}
            </div>
            <IngredientInputs
                ingredients={form.ingredients}
                lang={lang}
                onIngredientChange={handleIngredientChange}
                onAddIngredient={addIngredient}
                onRemoveIngredient={removeIngredient}
                minIngredients={1}
                amountStep="1"
                nameSuggestions={ingredientNameSuggestions}
                showBottleSelect={true}
                brandOptionsByIndex={brandOptionsByIndex}
                showPrices={!!isAdmin}
            />
            <div className="form-actions">
                <button
                    type="submit"
                    disabled={form.submitting}
                    className="button-primary"
                >
                    {isEdit ? t('cocktailForm.update') : t('cocktailForm.save')}
                </button>
                {isEdit && onCancel && (
                    <button
                        type="button"
                        onClick={onCancel}
                        className="button-secondary"
                    >
                        {t('common.cancel')}
                    </button>
                )}
            </div>
        </form>
    )
}

export default AddCocktailForm

