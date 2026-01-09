import { useEffect, useMemo, useState } from 'react'
import api from '../../api'
import IngredientInputs from './IngredientInputs'

function AddCocktailForm({ AddCocktail, initialCocktail, onCancel, isEdit = false }) {
    const [ingredientsCatalog, setIngredientsCatalog] = useState([])
    const [brandsByIngredientId, setBrandsByIngredientId] = useState({})
    const [brandOptionsByIndex, setBrandOptionsByIndex] = useState(
        initialCocktail?.ingredients?.map(() => []) || [[]]
    )

    const [form, setForm] = useState({
        name: initialCocktail?.name || '',
        description: initialCocktail?.description || '',
        ingredients: initialCocktail?.ingredients?.map((ing) => ({
            name: ing.name || '',
            amount: ing.ml !== undefined ? String(ing.ml) : '',
            ingredient_brand_id: ing.ingredient_brand_id || '',
        })) || [{ name: '', amount: '', ingredient_brand_id: '' }],
        imageUrl: initialCocktail?.image_url || '',
        imagePreview: initialCocktail?.image_url || '',
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

    const findIngredientIdByName = (name) => {
        const n = (name || '').trim().toLowerCase()
        if (!n) return null
        const match = (ingredientsCatalog || []).find((i) => (i.name || '').trim().toLowerCase() === n)
        return match?.id || null
    }

    const loadBrandsForIngredientId = async (ingredientId) => {
        if (!ingredientId) return []
        if (brandsByIngredientId[ingredientId]) return brandsByIngredientId[ingredientId]
        const res = await api.get(`/ingredients/${ingredientId}/brands`)
        const brands = res.data || []
        setBrandsByIngredientId((prev) => ({ ...prev, [ingredientId]: brands }))
        return brands
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
            ingredients: [...prev.ingredients, { name: '', amount: '', ingredient_brand_id: '' }]
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
                    return { ...ingredient, name: value, ingredient_brand_id: '' }
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
        const ingredientsArray = form.ingredients
            .filter(ing => ing.name.trim() && ing.amount !== '' && !isNaN(Number(ing.amount)))
            .map(ing => ({
                name: ing.name.trim(),
                ml: Number(ing.amount),
                ingredient_brand_id: ing.ingredient_brand_id ? ing.ingredient_brand_id : null,
            }))

        if (!form.name || ingredientsArray.length === 0) return

        const newCocktail = {
            name: form.name,
            description: form.description.trim() || null,
            ingredients: ingredientsArray,
            image_url: form.imageUrl || null
        }

        try {
            setForm(prev => ({ ...prev, submitting: true }))
            const id = isEdit ? initialCocktail.id : Date.now()

            if (isEdit) {
                const response = await api.put(`/cocktail-recipes/${id}`, newCocktail)
                // Use the API response which includes all fields (created_at, image_url, etc.)
                AddCocktail(response.data)
            } else {
                const response = await api.post(`/cocktail-recipes/`, newCocktail)
                // Use the API response which includes all fields (created_at, image_url, etc.)
                AddCocktail(response.data)
            }

            if (!isEdit) {
                setForm({
                    name: '',
                    description: '',
                    ingredients: [{ name: '', amount: '', ingredient_brand_id: '' }],
                    imageUrl: '',
                    imagePreview: '',
                    submitting: false
                })
                setBrandOptionsByIndex([[]])
            }
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
                showBrandSelect={true}
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

