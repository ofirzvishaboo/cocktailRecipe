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
  nameSuggestions = [],
  showBrandSelect = false,
  brandOptionsByIndex = [],
  brandPlaceholder = 'Brand bottle (optional)',
  brandDisabledByIndex = [],
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
            list={nameSuggestions.length ? 'ingredient-suggestions' : undefined}
            ref={(el) => {
              ingredientNameRefs.current[index] = el
            }}
          />
          {nameSuggestions.length > 0 && index === 0 && (
            <datalist id="ingredient-suggestions">
              {nameSuggestions.map((n) => (
                <option key={n} value={n} />
              ))}
            </datalist>
          )}
          <input
            type="number"
            placeholder={amountPlaceholder}
            value={ingredient.amount}
            onChange={(e) => onIngredientChange(index, 'amount', e.target.value)}
            min="0"
            step={amountStep}
          />
          {showBrandSelect && (
            <select
              value={ingredient.ingredient_brand_id || ''}
              onChange={(e) => onIngredientChange(index, 'ingredient_brand_id', e.target.value)}
              className="brand-select"
              disabled={brandDisabledByIndex[index] === true}
            >
              <option value="">{brandPlaceholder}</option>
              {(brandOptionsByIndex[index] || []).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.brand_name} ({b.bottle_size_ml}ml / {b.bottle_price})
                </option>
              ))}
            </select>
          )}
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

