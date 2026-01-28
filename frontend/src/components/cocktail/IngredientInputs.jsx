import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'

function IngredientInputs({
  ingredients,
  lang,
  onIngredientChange,
  onAddIngredient,
  onRemoveIngredient,
  addButtonLabel,
  namePlaceholder,
  amountPlaceholder,
  minIngredients = 1,
  amountStep = '0.1',
  nameSuggestions = [],
  showBottleSelect = false,
  brandOptionsByIndex = [],
  bottlePlaceholder,
  brandDisabledByIndex = [],
  showPrices = true,
}) {
  const { t } = useTranslation()
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

  const resolvedAddButtonLabel = addButtonLabel ?? t('common.addIngredient')
  const resolvedNamePlaceholder = namePlaceholder ?? t('common.ingredientName')
  const resolvedAmountPlaceholder = amountPlaceholder ?? t('common.quantity')
  const resolvedBottlePlaceholder = bottlePlaceholder ?? t('common.bottleOptional')

  return (
    <div className="ingredients-section">
      <h3>{t('common.ingredients')}</h3>
      {ingredients.map((ingredient, index) => (
        <div key={index} className="ingredient-row">
          <input
            type="text"
            placeholder={resolvedNamePlaceholder}
            value={
              lang === 'he'
                ? (ingredient?.name_he ?? '')
                : (ingredient?.name ?? '')
            }
            onChange={(e) => onIngredientChange(index, lang === 'he' ? 'name_he' : 'name', e.target.value)}
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
            placeholder={resolvedAmountPlaceholder}
            value={ingredient.amount}
            onChange={(e) => onIngredientChange(index, 'amount', e.target.value)}
            min="0"
            step={amountStep}
          />
          {showBottleSelect && (
            <select
              value={ingredient.bottle_id || ''}
              onChange={(e) => onIngredientChange(index, 'bottle_id', e.target.value)}
              className="brand-select"
              disabled={brandDisabledByIndex[index] === true}
            >
              <option value="">{resolvedBottlePlaceholder}</option>
              {(brandOptionsByIndex[index] || []).map((b) => (
                <option key={b.id} value={b.id}>
                  {(lang === 'he' ? ((b?.name_he || '').trim() || (b?.name || '').trim()) : ((b?.name || '').trim() || (b?.name_he || '').trim()))}
                  {' '}
                  ({b.volume_ml}ml{showPrices ? ` / ${b.current_price?.price ?? '-'} ${b.current_price?.currency ?? ''}` : ''})
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
            {t('common.remove')}
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
        {resolvedAddButtonLabel}
      </button>
    </div>
  )
}

export default IngredientInputs

