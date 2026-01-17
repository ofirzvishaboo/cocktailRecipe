import { useEffect, useMemo, useState } from 'react'
import api from '../../api'
import IngredientInputs from './IngredientInputs'

function AddCocktailForm({ AddCocktail, initialCocktail, onCancel, isEdit = false }) {
    const [ingredientsCatalog, setIngredientsCatalog] = useState([])
    const [brandsByIngredientId, setBrandsByIngredientId] = useState({})
    const [glassTypes, setGlassTypes] = useState([])
    const [brandOptionsByIndex, setBrandOptionsByIndex] = useState(
        (initialCocktail?.recipe_ingredients || []).map(() => []) || [[]]
    )

    const [form, setForm] = useState({
        name: initialCocktail?.name || '',
        description: initialCocktail?.description || '',
        is_base: !!initialCocktail?.is_base,
        glass_type_id: initialCocktail?.glass_type_id || '',
        garnish_text: initialCocktail?.garnish_text || '',
        preparation_method: initialCocktail?.preparation_method || '',
        batch_type: initialCocktail?.batch_type || '',
        ingredients: (initialCocktail?.recipe_ingredients || []).map((ri) => ({
            name: ri.ingredient_name || '',
            ingredient_id: ri.ingredient_id || '',
            amount: ri.quantity !== undefined ? String(ri.quantity) : '',
            unit: ri.unit || 'ml',
            bottle_id: ri.bottle_id || '',
        })) || [{ name: '', ingredient_id: '', amount: '', unit: 'ml', bottle_id: '' }],
        imageUrl: initialCocktail?.picture_url || '',
        imagePreview: initialCocktail?.picture_url || '',
        submitting: false,
    })

    const ingredientNameSuggestions = useMemo(
        () => (ingredientsCatalog || []).map((i) => i.name).filter(Boolean),
        [ingredientsCatalog]
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
        const match = (ingredientsCatalog || []).find((i) => (i.name || '').trim().toLowerCase() === n)
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
            ingredients: [...prev.ingredients, { name: '', ingredient_id: '', amount: '', unit: 'ml', bottle_id: '' }]
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
                if (field === 'name') {
                    return { ...ingredient, name: value, ingredient_id: '', bottle_id: '' }
                }
                return { ...ingredient, [field]: value }
            })
            return { ...prev, ingredients: updated }
        })

        if (field === 'name') syncBrandOptionsForRow(index, value)
    }

    const handleImageChange = async (e) => {
        const file = e.target.files[0]
        if (file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file')
                return
            }
            // Validate file size (min 100 bytes, max 10MB)
            if (file.size < 100) {
                alert('Image file appears to be corrupted or too small')
                return
            }
            if (file.size > 10 * 1024 * 1024) {
                alert('Image size should be less than 10MB')
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

                const response = await api.post('/images/upload', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                })

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
                alert('Failed to upload image. Please try again.')
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
                name: (ing?.name || '').trim(),
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
            alert('Failed to create a new ingredient. Are you logged in?')
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
            name: form.name,
            description: form.description.trim() || null,
            recipe_ingredients: ingredientsArray,
            picture_url: form.imageUrl || null,
            glass_type_id: form.glass_type_id || null,
            garnish_text: (form.garnish_text || '').trim() || null,
            is_base: !!form.is_base,
            preparation_method: (form.preparation_method || '').trim() || null,
            batch_type: form.batch_type || null,
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
                    description: '',
                    is_base: false,
                    glass_type_id: '',
                    garnish_text: '',
                    preparation_method: '',
                    batch_type: '',
                    ingredients: [{ name: '', ingredient_id: '', amount: '', unit: 'ml', bottle_id: '' }],
                    imageUrl: '',
                    imagePreview: '',
                    submitting: false
                })
                setBrandOptionsByIndex([[]])
            }
        } catch (e) {
            if (e?.response?.status === 401) {
                alert('Your session expired. Please log in again, then retry saving.')
            } else {
                alert('Failed to save cocktail. Please try again.')
            }
            console.error('Failed to save cocktail', e)
        } finally {
            setForm(prev => ({ ...prev, submitting: false }))
        }
    }

    return (
        <form onSubmit={handleSubmit} className="cocktail-form">
            <div className="form-group">
                <label htmlFor="form-name">Cocktail name</label>
                <input
                    type="text"
                    placeholder="Cocktail name"
                    id="form-name"
                    value={form.name}
                    onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
                    className="form-input"
                    required
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-classification">Cocktail type</label>
                <select
                    id="form-classification"
                    value={form.is_base ? 'CLASSIC' : 'SIGNATURE'}
                    onChange={(e) => setForm((prev) => ({ ...prev, is_base: e.target.value === 'CLASSIC' }))}
                    className="form-input"
                >
                    <option value="SIGNATURE">Signature</option>
                    <option value="CLASSIC">Classic</option>
                </select>
            </div>
            <div className="form-group">
                <label htmlFor="form-description">Description (optional)</label>
                <textarea
                    id="form-description"
                    placeholder="Add a description for this cocktail..."
                    value={form.description}
                    onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
                    className="form-input form-textarea"
                    rows={4}
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-glass-type">Glass type (optional)</label>
                <select
                    id="form-glass-type"
                    value={form.glass_type_id}
                    onChange={(e) => setForm((prev) => ({ ...prev, glass_type_id: e.target.value }))}
                    className="form-input"
                >
                    <option value="">Select a glass…</option>
                    {(glassTypes || []).map((g) => (
                        <option key={g.id} value={g.id}>
                            {g.name}{g.capacity_ml ? ` (${g.capacity_ml}ml)` : ''}
                        </option>
                    ))}
                </select>
            </div>

            <div className="form-group">
                <label htmlFor="form-garnish">Garnish (optional)</label>
                <input
                    type="text"
                    id="form-garnish"
                    placeholder="e.g. Lime wedge, orange peel..."
                    value={form.garnish_text}
                    onChange={(e) => setForm((prev) => ({ ...prev, garnish_text: e.target.value }))}
                    className="form-input"
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-preparation-method">Preparation Method (optional)</label>
                <textarea
                    id="form-preparation-method"
                    placeholder="e.g. Shake with ice, strain into glass..."
                    value={form.preparation_method}
                    onChange={(e) => setForm((prev) => ({ ...prev, preparation_method: e.target.value }))}
                    className="form-input form-textarea"
                    rows={3}
                />
            </div>

            <div className="form-group">
                <label htmlFor="form-batch-type">Batch Type (optional)</label>
                <select
                    id="form-batch-type"
                    value={form.batch_type}
                    onChange={(e) => setForm((prev) => ({ ...prev, batch_type: e.target.value }))}
                    className="form-input"
                >
                    <option value="">Select batch type...</option>
                    <option value="base">Base (no juice, no expiration)</option>
                    <option value="batch">Batch (contains juice, expires in 7 days)</option>
                </select>
            </div>

            <div className="form-group">
                <label htmlFor="form-image">Cocktail Image</label>
                <input
                    type="file"
                    id="form-image"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="form-input"
                />
                {form.imagePreview && (
                    <div className="image-preview-container">
                        <img src={form.imagePreview} alt="Preview" className="image-preview" />
                        <button
                            type="button"
                            onClick={removeImage}
                            className="button-remove-small"
                        >
                            Remove Image
                        </button>
                    </div>
                )}
            </div>
            <IngredientInputs
                ingredients={form.ingredients}
                onIngredientChange={handleIngredientChange}
                onAddIngredient={addIngredient}
                onRemoveIngredient={removeIngredient}
                minIngredients={1}
                amountStep="1"
                addButtonLabel="Add Ingredient"
                nameSuggestions={ingredientNameSuggestions}
                showBottleSelect={true}
                brandOptionsByIndex={brandOptionsByIndex}
            />
            <div className="form-actions">
                <button
                    type="submit"
                    disabled={form.submitting}
                    className="button-primary"
                >
                    {isEdit ? 'Update cocktail' : 'Save cocktail'}
                </button>
                {isEdit && onCancel && (
                    <button
                        type="button"
                        onClick={onCancel}
                        className="button-secondary"
                    >
                        Cancel
                    </button>
                )}
            </div>
        </form>
    )
}

export default AddCocktailForm

