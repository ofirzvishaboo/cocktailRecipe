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

    const handleSubmit = async (e) => {
        e.preventDefault()
        const ingredientsArray = Object.values(form.ingredientsMap)
        if (!form.name || ingredientsArray.length === 0) return

        const newCocktail = {
            name: form.name,
            ingredients: ingredientsArray
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
            setForm({ name: '', ingredientsMap: {}, newIngredientName: '', newIngredientMl: '', submitting: false })
        } finally {
            setForm(prev => ({ ...prev, submitting: false }))
        }
    }

    return (
        <form onSubmit={handleSubmit}>
            <div>
                <input type="text" placeholder="Cocktail name" value={form.name} onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))} />
            </div>
            <div>
                <input type="text" placeholder="Ingredient name" value={form.newIngredientName} onChange={(e) => setForm(prev => ({ ...prev, newIngredientName: e.target.value }))} />
                <input type="number" placeholder="ml" value={form.newIngredientMl} onChange={(e) => setForm(prev => ({ ...prev, newIngredientMl: e.target.value }))} />
                <button type="button" onClick={addIngredient}>Add ingredient</button>
            </div>
            <ul>
                {Object.values(form.ingredientsMap).map((ing) => (
                    <li key={ing.name}>
                        {ing.name} - {ing.ml} ml
                        <button type="button" onClick={() => removeIngredientByName(ing.name)}>remove</button>
                    </li>
                ))}
            </ul>
            <button type="submit" disabled={form.submitting}>
                {isEdit ? 'Update cocktail' : 'Save cocktail'}
            </button>
            {isEdit && onCancel && (
                <button type="button" onClick={onCancel} style={{ marginLeft: '10px' }}>
                    Cancel
                </button>
            )}
        </form>
    )
}

export default AddCocktailForm