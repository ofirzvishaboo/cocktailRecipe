import { useState } from 'react'
import api from '../api'

function AddCocktailForm({ AddCocktail, initialCocktail, onCancel, isEdit = false }) {
    const [form, setForm] = useState({
        name: initialCocktail?.name || '',
        ingredientsMap: initialCocktail?.ingredients?.reduce((acc, ing) => {
            acc[ing.name] = { name: ing.name, ml: ing.ml }
            return acc
        }, {}) || {},
        newIngredientName: '',
        newIngredientMl: '',
        imageUrl: initialCocktail?.image_url || '',
        imagePreview: initialCocktail?.image_url || '',
        submitting: false,
    })

    const addIngredient = () => {
        if (!form.newIngredientName || form.newIngredientMl === '' || isNaN(Number(form.newIngredientMl))) return
        const ml = Number(form.newIngredientMl)
        setForm(prev => ({
            ...prev,
            ingredientsMap: {
                ...prev.ingredientsMap,
                [prev.newIngredientName]: { name: prev.newIngredientName, ml }
            },
            newIngredientName: '',
            newIngredientMl: '',
        }))
    }

    const removeIngredientByName = (ingredientName) => {
        setForm(prev => {
            const nextMap = { ...prev.ingredientsMap }
            delete nextMap[ingredientName]
            return { ...prev, ingredientsMap: nextMap }
        })
    }

    const handleImageChange = (e) => {
        const file = e.target.files[0]
        if (file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file')
                return
            }
            // Validate file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                alert('Image size should be less than 5MB')
                return
            }
            const reader = new FileReader()
            reader.onloadend = () => {
                const base64String = reader.result
                setForm(prev => ({
                    ...prev,
                    imageUrl: base64String,
                    imagePreview: base64String
                }))
            }
            reader.readAsDataURL(file)
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
        const ingredientsArray = Object.values(form.ingredientsMap)
        if (!form.name || ingredientsArray.length === 0) return

        const newCocktail = {
            name: form.name,
            ingredients: ingredientsArray,
            image_url: form.imageUrl || null
        }

        try {
            setForm(prev => ({ ...prev, submitting: true }))
            const id = isEdit ? initialCocktail.id : Date.now()
            const cocktailData = { ...newCocktail, id }

            if (isEdit) {
                await api.put(`/cocktail-recipes/${id}`, newCocktail)
            } else {
                await api.post(`/cocktail-recipes/`, newCocktail)
            }

            AddCocktail(cocktailData)
            setForm({ name: '', ingredientsMap: {}, newIngredientName: '', newIngredientMl: '', imageUrl: '', imagePreview: '', submitting: false })
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
                />
            </div>
            <div className="form-group">
                <label htmlFor="form-ingredient-name">Ingredient name</label>
                <div className="form-row">
                    <input
                        type="text"
                        placeholder="Ingredient name"
                        id="form-ingredient-name"
                        value={form.newIngredientName}
                        onChange={(e) => setForm(prev => ({ ...prev, newIngredientName: e.target.value }))}
                        className="form-input"
                    />
                    <input
                        type="number"
                        placeholder="ml"
                        value={form.newIngredientMl}
                        onChange={(e) => setForm(prev => ({ ...prev, newIngredientMl: e.target.value }))}
                        className="form-input form-input-small"
                    />
                    <button
                        type="button"
                        onClick={addIngredient}
                        className="button-secondary"
                    >
                        Add ingredient
                    </button>
                </div>
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
            {Object.values(form.ingredientsMap).length > 0 && (
                <div className="ingredients-preview">
                    <h4>Ingredients:</h4>
                    <ul className="ingredients-preview-list">
                        {Object.values(form.ingredientsMap).map((ing) => (
                            <li key={ing.name} className="ingredient-preview-item">
                                <span>{ing.name} - {ing.ml} ml</span>
                                <button
                                    type="button"
                                    onClick={() => removeIngredientByName(ing.name)}
                                    className="button-remove-small"
                                >
                                    Remove
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
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