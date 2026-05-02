import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import IngredientPicker from './IngredientPicker'

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
  ingredientOptions = [],
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
          <div
            ref={(el) => {
              ingredientNameRefs.current[index] = el
            }}
            style={{ width: '100%', minWidth: 0 }}
          >
            <IngredientPicker
              id={`ingredient-picker-${index}`}
              value={ingredient.ingredient_id || ''}
              onChange={(nextId) => {
                const id = String(nextId || '')
                if (!id) {
                  onIngredientChange(index, 'name', '')
                  onIngredientChange(index, 'name_he', '')
                  onIngredientChange(index, 'ingredient_id', '')
                  onIngredientChange(index, 'bottle_id', '')
                  return
                }
                const opt = (ingredientOptions || []).find((o) => String(o.value) === id)
                const en = opt?.en ?? ''
                const he = opt?.he ?? ''
                // Set names first (will clear ingredient_id/bottle_id by design), then set ingredient_id.
                onIngredientChange(index, 'name', en)
                onIngredientChange(index, 'name_he', he)
                onIngredientChange(index, 'ingredient_id', id)
                onIngredientChange(index, 'bottle_id', '')
              }}
              options={ingredientOptions}
              placeholder={resolvedNamePlaceholder}
              ariaLabel={resolvedNamePlaceholder}
              dir={lang === 'he' ? 'rtl' : 'ltr'}
              searchPlaceholder={t('common.search')}
            />
          </div>
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

