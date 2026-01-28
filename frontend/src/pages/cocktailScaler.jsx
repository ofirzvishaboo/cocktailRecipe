import { useMemo, useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import '../styles/cocktailScaler.css';
import api from '../api';
import IngredientInputs from '../components/cocktail/IngredientInputs';
import { useAuth } from '../contexts/AuthContext'

export default function CocktailScaler() {
    const { user, isAuthenticated, isAdmin } = useAuth()
    const { t, i18n } = useTranslation()
    const lang = (i18n.language || 'en').split('-')[0]
    const [recipeName, setRecipeName] = useState('');
    const [ingredients, setIngredients] = useState([{ ingredient_id: '', name: '', name_he: '', amount: '', unit: 'ml', bottle_id: '' }]);
    const [desiredLiters, setDesiredLiters] = useState('');
    const [batchType, setBatchType] = useState('batch'); // 'base' | 'batch'
    const [batchTypeUserOverride, setBatchTypeUserOverride] = useState(false);
    const [cocktails, setCocktails] = useState([]);
    const [filteredCocktails, setFilteredCocktails] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedCocktailId, setSelectedCocktailId] = useState(null);
    const [costData, setCostData] = useState(null);
    const [costLoading, setCostLoading] = useState(false);
    const [costError, setCostError] = useState('');
    const [selectedCocktail, setSelectedCocktail] = useState(null);
    const [originalIngredients, setOriginalIngredients] = useState([]); // Store full ingredient list
    const [ingredientsCatalog, setIngredientsCatalog] = useState([]);
    const [brandsByIngredientId, setBrandsByIngredientId] = useState({});
    const [brandOptionsByIndex, setBrandOptionsByIndex] = useState([]);
    const [savingBrands, setSavingBrands] = useState(false);

    const addIngredient = () => {
        setIngredients([...ingredients, { ingredient_id: '', name: '', name_he: '', amount: '', unit: 'ml', bottle_id: '' }]);
        setBrandOptionsByIndex((prev) => [...prev, []]);
    };

    const removeIngredient = (index) => {
        if (ingredients.length > 1) {
            setIngredients(ingredients.filter((_, i) => i !== index));
            setBrandOptionsByIndex((prev) => prev.filter((_, i) => i !== index));
        }
    };

    const handleIngredientChange = (index, field, value) => {
        const updatedIngredients = ingredients.map((ingredient, i) => {
            if (i !== index) return ingredient;
            if (field === 'name' || field === 'name_he') {
                const next = { ...ingredient, [field]: value, bottle_id: '' };
                // If user fills Hebrew and English is still empty, auto-fill English to keep downstream logic stable.
                if (field === 'name_he' && !(next?.name || '').trim() && (value || '').trim()) {
                    next.name = value
                }
                return next;
            }
            return { ...ingredient, [field]: value };
        });
        setIngredients(updatedIngredients);

        if (!batchTypeUserOverride) {
            const nextHasJuice = computeHasJuiceForIngredients(updatedIngredients)
            // Default is "batch"; only auto-switch to batch when juice is detected.
            if (nextHasJuice) setBatchType('batch')
        }

        if (field === 'name' || field === 'name_he') syncBrandOptionsForRow(index, value);
        if (field === 'bottle_id') persistBrandSelection(updatedIngredients);
    };

    const calculateTotalVolume = () => {
        return ingredientsForScaling.reduce((total, ingredient) => {
            const amount = parseFloat(ingredient.amount) || 0;
            return total + amount;
        }, 0);
    };

    const calculateScalingFactor = () => {
        const totalVolume = calculateTotalVolume();
        const desiredLitersNum = parseFloat(desiredLiters);
        if (!desiredLitersNum || desiredLitersNum <= 0 || totalVolume <= 0) return 0;
        const desiredVolume = desiredLitersNum * 1000; // Convert liters to ml
        return desiredVolume / totalVolume;
    };

    const getScaledAmount = (originalAmount) => {
        const scalingFactor = calculateScalingFactor();
        const scaled = (parseFloat(originalAmount) || 0) * scalingFactor;
        return Math.round(scaled * 100) / 100; // Round to 2 decimal places
    };

    useEffect(() => {
        const loadCocktails = async () => {
            try {
                setLoading(true);
                setError('');
                const response = await api.get('/cocktail-recipes/');
                setCocktails(response.data || []);
                setFilteredCocktails(response.data || []);
            } catch (e) {
                setError(t('scaler.errors.loadCocktailsFailed'));
                console.error('Failed to load cocktails', e);
            } finally {
                setLoading(false);
            }
        };
        loadCocktails();
    }, [t]);

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
    const findIngredientByName = (name) => {
        const n = (name || '').trim().toLowerCase()
        if (!n) return null
        return (ingredientsCatalog || []).find((i) => {
            const en = (i?.name || '').trim().toLowerCase()
            const he = (i?.name_he || '').trim().toLowerCase()
            return en === n || he === n
        }) || null
    }


    // Keep Base/Batch auto-defaulted based on ingredients, unless user explicitly overrides.
    useEffect(() => {
        if (batchTypeUserOverride) return
        const nextHasJuice = computeHasJuiceForIngredients(ingredients)
        // Default is "batch"; only auto-switch to batch when juice is detected.
        if (nextHasJuice) setBatchType('batch')
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [ingredientsCatalog])

    const ingredientNameSuggestions = useMemo(
        () => (ingredientsCatalog || []).map((i) => i.name).filter(Boolean),
        [ingredientsCatalog]
    )

    const computeHasJuiceForIngredients = (ings) => {
        return (ings || []).some((ing) => {
            const meta = findIngredientByName(ing?.name)
            return (meta?.subcategory_name || '').trim().toLowerCase() === 'juice'
        })
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
    const hasJuice = useMemo(() => computeHasJuiceForIngredients(ingredients), [ingredients, ingredientsCatalog])

    const filterOutJuiceIngredients = (ings) => {
        return (ings || []).filter((ing) => {
            const meta = findIngredientByName(ing?.name)
            return (meta?.subcategory_name || '').trim().toLowerCase() !== 'juice'
        })
    }

    // Ingredients to use for scaling calculations (exclude juice when batchType is 'base')
    const ingredientsForScaling = useMemo(() => {
        if (batchType === 'base') {
            return filterOutJuiceIngredients(ingredients)
        }
        return ingredients
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [batchType, ingredients, ingredientsCatalog])

    // Separate juice ingredients when batchType is 'base' (for display purposes)
    const juiceIngredients = useMemo(() => {
        if (batchType === 'base') {
            return (ingredients || []).filter((ing) => {
                const meta = findIngredientByName(ing?.name)
                return (meta?.subcategory_name || '').trim().toLowerCase() === 'juice'
            })
        }
        return []
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [batchType, ingredients, ingredientsCatalog])





    const expirationText = useMemo(() => {
        if (batchType === 'base') return t('scaler.expiration.forever')
        const d = new Date()
        d.setDate(d.getDate() + 7)
        return d.toLocaleDateString(lang === 'he' ? 'he-IL' : 'en-US')
    }, [batchType, lang, t])

    const displayCocktailName = useCallback((cocktail) => {
        const he = (cocktail?.name_he || '').trim()
        const en = (cocktail?.name || '').trim()
        return lang === 'he' ? (he || en) : (en || he)
    }, [lang])

    const getSearchableCocktailNames = useCallback((cocktail) => {
        const out = []
        const en = (cocktail?.name || '').trim()
        const he = (cocktail?.name_he || '').trim()
        if (en) out.push(en)
        if (he && he !== en) out.push(he)
        return out
    }, [])

    const getSearchableIngredientNames = useCallback((ri) => {
        const out = []
        // Supports recipe ingredients (ingredient_name / ingredient_name_he) and local rows (name / name_he)
        const en = (ri?.ingredient_name ?? ri?.name ?? '').trim()
        const he = (ri?.ingredient_name_he ?? ri?.name_he ?? '').trim()
        if (en) out.push(en)
        if (he && he !== en) out.push(he)
        return out
    }, [])

    const displayIngredientName = useCallback((ri) => {
        // Supports:
        // - Cocktail recipe ingredient objects: ingredient_name / ingredient_name_he
        // - Local UI rows: name / name_he
        // - Cost breakdown lines: ingredient_name / ingredient_name_he
        const he = (ri?.ingredient_name_he ?? ri?.name_he ?? '').trim()
        const en = (ri?.ingredient_name ?? ri?.name ?? '').trim()
        return lang === 'he' ? (he || en) : (en || he)
    }, [lang])

    const getIngredientNamesForCocktail = useCallback((cocktail) => {
        const ris = cocktail?.recipe_ingredients
        if (Array.isArray(ris) && ris.length > 0) {
            return ris.map((ri) => displayIngredientName(ri)).filter(Boolean)
        }
        return []
    }, [displayIngredientName])

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

    const loadBrandsForIngredientId = async (ingredientId) => {
        if (!ingredientId) return []
        if (brandsByIngredientId[ingredientId]) return brandsByIngredientId[ingredientId]
        const res = await api.get(`/ingredients/${ingredientId}/bottles`)
        const bottles = res.data || []
        setBrandsByIngredientId((prev) => ({ ...prev, [ingredientId]: bottles }))
        return bottles
    }

    const syncBrandOptionsForRow = async (index, ingredientName, ingredientIdOverride) => {
        const ingredientId = ingredientIdOverride || findIngredientIdByName(ingredientName)
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

        const canEditSelectedCocktail = () => {
        return Boolean(isAuthenticated && user && selectedCocktail && (isAdmin || selectedCocktail.created_by_user_id === user.id))
    }

    const persistBrandSelection = async (currentIngredients) => {
        if (!selectedCocktailId || !selectedCocktail) return
        if (!canEditSelectedCocktail()) return

        // Use the cocktail's stored names/quantities as canonical; only apply bottle ids from UI
        const bottleByName = {}
        const bottleByIngredientId = {}
        currentIngredients.forEach((ing) => {
            const keyEn = (ing?.name || '').trim().toLowerCase()
            const keyHe = (ing?.name_he || '').trim().toLowerCase()
            if (keyEn) bottleByName[keyEn] = ing.bottle_id || ''
            if (keyHe) bottleByName[keyHe] = ing.bottle_id || ''
            if (ing?.ingredient_id) bottleByIngredientId[ing.ingredient_id] = ing.bottle_id || ''
        })

        const payload = {
            name: selectedCocktail.name,
            description: selectedCocktail.description || null,
            picture_url: selectedCocktail.picture_url || null,
            recipe_ingredients: (selectedCocktail.recipe_ingredients || []).map((ri, idx) => {
                const key = (ri.ingredient_name || '').trim().toLowerCase()
                return {
                    ingredient_id: ri.ingredient_id,
                    quantity: ri.quantity,
                    unit: ri.unit,
                    bottle_id: bottleByIngredientId[ri.ingredient_id]
                        ? bottleByIngredientId[ri.ingredient_id]
                        : (bottleByName[key] ? bottleByName[key] : null),
                    sort_order: ri.sort_order ?? (idx + 1),
                    is_garnish: !!ri.is_garnish,
                    is_optional: !!ri.is_optional,
                }
            }),
        }

        try {
            setSavingBrands(true)
            const res = await api.put(`/cocktail-recipes/${selectedCocktailId}`, payload)
            const updated = res.data
            setSelectedCocktail(updated)
            // Keep local ingredient brand selections aligned with saved cocktail
            const formattedIngredients = (updated.recipe_ingredients || []).map((ri) => ({
                ingredient_id: ri.ingredient_id || '',
                name: ri.ingredient_name || '',
                name_he: ri.ingredient_name_he || '',
                amount: String(ri.quantity),
                unit: ri.unit || 'ml',
                bottle_id: ri.bottle_id || '',
            }))
            setIngredients(formattedIngredients.length ? formattedIngredients : [{ ingredient_id: '', name: '', name_he: '', amount: '', unit: 'ml', bottle_id: '' }])
            setBrandOptionsByIndex((prev) => {
                const next = formattedIngredients.map((_, idx) => prev[idx] || [])
                return next
            })
            // Update cocktails list cache
            setCocktails((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
            setFilteredCocktails((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
        } catch (e) {
            console.error('Failed to persist brand selection', e)
        } finally {
            setSavingBrands(false)
        }
    }

    useEffect(() => {
        const loadCost = async () => {
            if (!isAdmin) {
                setCostData(null);
                setCostError('');
                return;
            }
            if (!selectedCocktailId) {
                setCostData(null);
                setCostError('');
                return;
            }

            const scaleFactor = calculateScalingFactor();
            const scaleFactorForCost = scaleFactor > 0 ? scaleFactor : 1.0;

            const params = { scale_factor: scaleFactorForCost };
            const endpoint = batchType === 'base' ? 'no-juice-cost' : 'cost';

            try {
                setCostLoading(true);
                setCostError('');
                const response = await api.get(`/cocktail-recipes/${selectedCocktailId}/${endpoint}`, { params });
                setCostData(response.data);
            } catch (e) {
                setCostData(null);
                setCostError(t('scaler.errors.loadCostFailed'));
                console.error('Failed to load cost breakdown', e);
            } finally {
                setCostLoading(false);
            }
        };

        loadCost();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedCocktailId, desiredLiters, ingredients, batchType, isAdmin]);

    // Filter cocktails based on search query
    useEffect(() => {
        if (!searchQuery.trim()) {
            setFilteredCocktails(cocktails);
        } else {
            const query = searchQuery.toLowerCase().trim();

            // Check if query contains commas (multiple ingredient search)
            if (query.includes(',')) {
                // Split by comma and filter out empty strings
                const ingredientQueries = query.split(',').map(q => q.trim()).filter(q => q.length > 0);

                const filtered = cocktails.filter(cocktail => {
                    const names = (cocktail?.recipe_ingredients || [])
                        .flatMap((ri) => getSearchableIngredientNames(ri))
                        .map((n) => n.toLowerCase())
                    if (names.length === 0) return false;

                    // Each query must match at least one ingredient (substring match)
                    return ingredientQueries.every(ingQuery => {
                        return names.some((n) => n.includes(ingQuery))
                    });
                });
                setFilteredCocktails(filtered);
            } else {
                // Search by cocktail name OR single ingredient
                const filtered = cocktails.filter(cocktail => {
                    // Check if name matches
                    const nameMatch = getSearchableCocktailNames(cocktail).some((n) => n.toLowerCase().includes(query));

                    // Check if any ingredient matches
                    const ingredientMatch = (cocktail?.recipe_ingredients || []).some((ri) =>
                        getSearchableIngredientNames(ri).some((n) => n.toLowerCase().includes(query))
                    );

                    return nameMatch || ingredientMatch;
                });
                setFilteredCocktails(filtered);
            }
        }
    }, [searchQuery, cocktails, getSearchableCocktailNames, getSearchableIngredientNames]);

    const handleAddCocktail = (cocktail) => {
        setSelectedCocktailId(cocktail.id);
        setSelectedCocktail(cocktail);
        setRecipeName(displayCocktailName(cocktail));
        const ris = cocktail.recipe_ingredients || []

        if (ris.length > 0) {
            const formattedIngredients = ris.map((ri) => ({
                ingredient_id: ri.ingredient_id || '',
                name: ri.ingredient_name || '',
                name_he: ri.ingredient_name_he || '',
                amount: String(ri.quantity ?? ''),
                unit: ri.unit || 'ml',
                bottle_id: ri.bottle_id || '',
            }))
            // Store the original full ingredient list
            setOriginalIngredients(formattedIngredients);
            setIngredients(formattedIngredients);
            setBrandOptionsByIndex(formattedIngredients.map(() => []));
            // Preload bottle options for each row
            formattedIngredients.forEach((row, idx) => {
                syncBrandOptionsForRow(idx, row.name, row.ingredient_id);
            })

            // Use batch_type from model, or auto-compute if not set
            if (cocktail.batch_type) {
                setBatchType(cocktail.batch_type)
                setBatchTypeUserOverride(true) // Model has explicit value
                // If batch_type is 'base', filter out juice ingredients
                if (cocktail.batch_type === 'base') {
                    const baseOnly = formattedIngredients.filter((ing) => {
                        const ri = ris.find((r) => (r.ingredient_id && ing.ingredient_id) ? (r.ingredient_id === ing.ingredient_id) : (r.ingredient_name === ing.name))
                        return ri && (ri.subcategory_name || '').trim().toLowerCase() !== 'juice'
                    })
                    setIngredients(baseOnly.length ? baseOnly : [{ ingredient_id: '', name: '', name_he: '', amount: '', unit: 'ml', bottle_id: '' }])
                }
            } else {
                // No explicit batch_type saved on the cocktail → keep UI default as "batch".
                setBatchTypeUserOverride(false)
                setBatchType('batch')
                setIngredients(formattedIngredients)
            }
        } else {
            setOriginalIngredients([]);
            setIngredients([{ ingredient_id: '', name: '', name_he: '', amount: '', unit: 'ml', bottle_id: '' }]);
            setBrandOptionsByIndex([[]]);
            setBatchTypeUserOverride(false)
            setBatchType('batch')
        }
    };

    const totalVolume = calculateTotalVolume();
    const scalingFactor = calculateScalingFactor();

    const formatMoney = (value) => {
        const n = Number(value);
        if (Number.isNaN(n)) return '0.00';
        return n.toFixed(2);
    };

    return (
        <div className="cocktail-scaler">

            <div className="scaler-grid">
                <div className="scaler-left">
            <div className="cocktail-selector-section">
                <h3>{t('scaler.select.title')}</h3>
                {loading && <div className="loading">{t('scaler.select.loading')}</div>}
                {error && <div className="error-message">{error}</div>}
                {!loading && !error && (
                    <>
                        <div className="search-container-selector">
                            <input
                                type="text"
                                placeholder={t('cocktails.searchPlaceholder')}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="search-input-selector"
                            />
                        </div>
                    <div className="cocktails-list-selector">
                            {filteredCocktails.length === 0 ? (
                                <p>
                                    {searchQuery.trim()
                                        ? t('cocktails.empty.matching', { query: searchQuery })
                                        : cocktails.length === 0
                                            ? t('scaler.select.noneAvailable')
                                            : t('cocktails.empty.noSearchMatch')}
                                </p>
                        ) : (
                            <ul className="cocktail-selector-list">
                                    {filteredCocktails.map((cocktail) => (
                                    <li key={cocktail.id} className="cocktail-selector-item">
                                        <div className="cocktail-selector-info">
                                            <span className="cocktail-selector-name">{displayCocktailName(cocktail)}</span>
                                            {getIngredientNamesForCocktail(cocktail).length > 0 && (
                                                <span className="cocktail-selector-ingredients">
                                                    {t('scaler.select.ingredientsCount', { count: getIngredientNamesForCocktail(cocktail).length })}
                                                </span>
                                            )}
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => handleAddCocktail(cocktail)}
                                            className="add-cocktail-btn"
                                        >
                                                        {t('scaler.select.selectButton')}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                    </>
                )}
            </div>

            <div className="recipe-input">
                <div className="input-group">
                    <label htmlFor="recipeName">{t('scaler.inputs.cocktailName')}</label>
                    <input
                        type="text"
                        id="recipeName"
                        value={recipeName}
                        onChange={(e) => setRecipeName(e.target.value)}
                        placeholder={t('scaler.inputs.cocktailNamePlaceholder')}
                    />
                </div>

                <div className="input-group">
                    <label htmlFor="desiredLiters">{t('scaler.inputs.liters')}</label>
                    <input
                        type="number"
                        id="desiredLiters"
                        value={desiredLiters}
                        onChange={(e) => setDesiredLiters(e.target.value)}
                        placeholder={t('scaler.inputs.litersPlaceholder')}
                        min="0"
                        step="0.1"
                    />
                </div>

                <div className="input-group">
                    <label htmlFor="batchType">{t('scaler.inputs.type')}</label>
                    <select
                        id="batchType"
                        value={batchType}
                        onChange={(e) => {
                            const nextType = e.target.value
                            setBatchType(nextType)
                            setBatchTypeUserOverride(true)

                            if (nextType === 'base') {
                                // Filter out juice ingredients from originalIngredients
                                if (originalIngredients.length > 0) {
                                    const baseOnly = originalIngredients.filter((ing) => {
                                        if (selectedCocktail && Array.isArray(selectedCocktail.recipe_ingredients)) {
                                            const ri = selectedCocktail.recipe_ingredients.find((r) => r.ingredient_name === ing.name)
                                            return ri && (ri.subcategory_name || '').trim().toLowerCase() !== 'juice'
                                        }
                                        // Fall back to catalog lookup
                                        const meta = findIngredientByName(ing?.name)
                                        return (meta?.subcategory_name || '').trim().toLowerCase() !== 'juice'
                                    })
                                    setIngredients(
                                        baseOnly.length
                                            ? baseOnly
                                            : [{ name: '', amount: '', unit: 'ml', bottle_id: '' }]
                                    )
                                } else {
                                    // No originalIngredients -> fall back to catalog-based filtering
                                    setIngredients((prev) => filterOutJuiceIngredients(prev))
                                }
                            } else if (nextType === 'batch') {
                                // Restore all original ingredients when switching to batch
                                if (originalIngredients.length > 0) {
                                    setIngredients(originalIngredients)
                                }
                            }
                        }}
                    >
                        <option value="base">{t('cocktailForm.batchType.base')}</option>
                        <option value="batch">{t('cocktailForm.batchType.batch')}</option>
                    </select>


                    <div className="batch-expiration">
                        <span><strong>{t('scaler.expiration.label')}:</strong> {expirationText}</span>
                        {(batchType === 'base' && hasJuice) && (
                            <span className="batch-warning">
                                {t('scaler.expiration.juiceWarning')}
                            </span>
                        )}
                    </div>
                </div>
            </div>

                <IngredientInputs
                    ingredients={ingredients}
                    lang={lang}
                    onIngredientChange={handleIngredientChange}
                    onAddIngredient={addIngredient}
                    onRemoveIngredient={removeIngredient}
                    minIngredients={1}
                    amountStep="0.1"
                        nameSuggestions={ingredientNameSuggestions}
                        showBottleSelect={true}
                        brandOptionsByIndex={brandOptionsByIndex}
                        bottlePlaceholder={savingBrands ? t('common.saving') : t('common.bottleOptional')}
                        brandDisabledByIndex={ingredients.map(() => selectedCocktailId ? !canEditSelectedCocktail() : false)}
                        showPrices={!!isAdmin}
                />
                </div>

                <div className="scaler-right">
                {totalVolume > 0 && desiredLiters && (
                    <div className="results-section">
                        <h3>{t('scaler.results.title')}</h3>
                        <div className="recipe-info">
                            <p><strong>{t('scaler.results.originalTotal')}:</strong> {totalVolume} ml</p>
                            <p><strong>{t('scaler.results.desiredVolume')}:</strong> {parseFloat(desiredLiters) * 1000} ml</p>
                            <p><strong>{t('scaler.results.factor')}:</strong> {scalingFactor.toFixed(3)}x</p>
                        </div>

                        <div className="quantities-display">
                            <div className="quantities-column">
                                <h4>{t('scaler.results.originalRecipe')}</h4>
                                {ingredientsForScaling.map((ingredient, index) => (
                                    <div key={index} className="quantity-item">
                                        <span className="ingredient-name">{displayIngredientName(ingredient) || t('scaler.results.ingredientFallback', { n: index + 1 })}</span>
                                        <span className="ingredient-amount">{ingredient.amount || 0} {ingredient.unit || 'ml'}</span>
                                    </div>
                                ))}
                                {batchType === 'base' && juiceIngredients.length > 0 && (
                                    <>
                                        {juiceIngredients.map((ingredient, index) => (
                                            <div key={`juice-${index}`} className="quantity-item quantity-item-excluded">
                                                <span className="ingredient-name">{displayIngredientName(ingredient) || t('scaler.results.ingredientFallback', { n: index + 1 })}</span>
                                                <span className="ingredient-amount">{ingredient.amount || 0} {ingredient.unit || 'ml'} <em>({t('scaler.results.excludedFromBase')})</em></span>
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>

                            <div className="quantities-column">
                                <h4>{t('scaler.results.scaledFor', { liters: desiredLiters })}</h4>
                                {ingredientsForScaling.map((ingredient, index) => (
                                    <div key={index} className="quantity-item">
                                        <span className="ingredient-name">{displayIngredientName(ingredient) || t('scaler.results.ingredientFallback', { n: index + 1 })}</span>
                                        <span className="ingredient-amount">{getScaledAmount(ingredient.amount)} {ingredient.unit || 'ml'}</span>
                                    </div>
                                ))}
                                {batchType === 'base' && juiceIngredients.length > 0 && (
                                    <>
                                        {juiceIngredients.map((ingredient, index) => (
                                            <div key={`juice-${index}`} className="quantity-item quantity-item-excluded">
                                                <span className="ingredient-name">{displayIngredientName(ingredient) || t('scaler.results.ingredientFallback', { n: index + 1 })}</span>
                                                <span className="ingredient-amount"><em>({t('scaler.results.excluded')})</em></span>
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                    {isAdmin && selectedCocktailId && (
                        <div className="results-section cost-section">
                            <h3>{t('scaler.cost.title')}</h3>
                            {costLoading && <div className="loading">{t('scaler.cost.loading')}</div>}
                            {costError && <div className="error-message">{costError}</div>}

                            {!costLoading && !costError && costData && (
                                <>
                                    <div className="cost-breakdown">
                                        <div className="cost-row cost-header">
                                            <span>{t('scaler.cost.headers.ingredient')}</span>
                                            <span>{t('scaler.cost.headers.bottle')}</span>
                                            <span>{t('scaler.cost.headers.scaled')}</span>
                                            <span>{t('scaler.cost.headers.cost')}</span>
                                        </div>
                                        {Array.isArray(costData.lines) && costData.lines.map((line, idx) => (
                                            <div key={`${line.ingredient_name}-${idx}`} className="cost-row">
                                                <span className="cost-ingredient">{displayIngredientName(line)}</span>
                                                <span className="cost-brand">{line.bottle_name || '-'}</span>
                                                <span className="cost-ml">{Math.round((Number(line.scaled_quantity) || 0) * 100) / 100} {line.unit || ''}</span>
                                                <span className="cost-value">{formatMoney(line.ingredient_cost)}</span>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="cost-summary">
                                        <p><strong>{t('scaler.cost.scaledTotal')}:</strong> {formatMoney(costData.scaled_total_cost)}</p>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
