import { useEffect, useRef } from 'react'

function IngredientInputs({
  ingredients,
  onIngredientChange,
  onAddIngredient,
  onRemoveIngredient,
  addButtonLabel = 'Add Ingredient',
  namePlaceholder = 'Ingredient name',
  amountPlaceholder = 'Amount (ml)',
  minIngredients = 1,
  amountStep = '0.1',
}) {
  const ingredientNameRefs = useRef([])
  const prevLengthRef = useRef(ingredients.length)
  const isAddingRef = useRef(false)

  useEffect(() => {
    ingredientNameRefs.current = ingredientNameRefs.current.slice(0, ingredients.length)
    if (isAddingRef.current && ingredients.length > 0) {
      isAddingRef.current = false
      const lastIndex = ingredients.length - 1
      requestAnimationFrame(() => {
        ingredientNameRefs.current[lastIndex]?.focus()
      })
    }
    prevLengthRef.current = ingredients.length
  }, [ingredients.length])

  return (
    <div className="ingredients-section">
      <h3>Ingredients</h3>
      {ingredients.map((ingredient, index) => (
        <div key={index} className="ingredient-row">
          <input
            type="text"
            placeholder={namePlaceholder}
            value={ingredient.name}
            onChange={(e) => onIngredientChange(index, 'name', e.target.value)}
            ref={(el) => {
              ingredientNameRefs.current[index] = el
            }}
          />
          <input
            type="number"
            placeholder={amountPlaceholder}
            value={ingredient.amount}
            onChange={(e) => onIngredientChange(index, 'amount', e.target.value)}
            min="0"
            step={amountStep}
          />
          <button
            type="button"
            onClick={() => onRemoveIngredient(index)}
            className="remove-btn"
            disabled={ingredients.length <= minIngredients}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => {
          isAddingRef.current = true
          onAddIngredient()
        }}
        className="add-btn"
      >
        {addButtonLabel}
      </button>
    </div>
  )
}

export default IngredientInputs

