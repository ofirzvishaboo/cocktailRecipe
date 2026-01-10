import { useMemo, useState, useEffect } from 'react';
import '../styles/cocktailScaler.css';
import api from '../api';
import IngredientInputs from '../components/cocktail/IngredientInputs';
import { useAuth } from '../contexts/AuthContext'

export default function CocktailScaler() {
    const { user, isAuthenticated, isAdmin } = useAuth()
    const [recipeName, setRecipeName] = useState('');
    const [ingredients, setIngredients] = useState([{ name: '', amount: '', unit: 'ml', bottle_id: '' }]);
    const [desiredLiters, setDesiredLiters] = useState('');
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
    const [ingredientsCatalog, setIngredientsCatalog] = useState([]);
    const [brandsByIngredientId, setBrandsByIngredientId] = useState({});
    const [brandOptionsByIndex, setBrandOptionsByIndex] = useState([]);
    const [savingBrands, setSavingBrands] = useState(false);

    const addIngredient = () => {
        setIngredients([...ingredients, { name: '', amount: '', unit: 'ml', bottle_id: '' }]);
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
            if (field === 'name') {
                return { ...ingredient, name: value, bottle_id: '' };
            }
            return { ...ingredient, [field]: value };
        });
        setIngredients(updatedIngredients);

        if (field === 'name') syncBrandOptionsForRow(index, value);
        if (field === 'bottle_id') persistBrandSelection(updatedIngredients);
    };

    const calculateTotalVolume = () => {
        return ingredients.reduce((total, ingredient) => {
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
                setError('Failed to load cocktails');
                console.error('Failed to load cocktails', e);
            } finally {
                setLoading(false);
            }
        };
        loadCocktails();
    }, []);

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

    const ingredientNameSuggestions = useMemo(
        () => (ingredientsCatalog || []).map((i) => i.name).filter(Boolean),
        [ingredientsCatalog]
    )

    const getIngredientNamesForCocktail = (cocktail) => {
        const ris = cocktail?.recipe_ingredients
        if (Array.isArray(ris) && ris.length > 0) {
            return ris.map((ri) => (ri.ingredient_name || '').trim()).filter(Boolean)
        }
        return []
    }

    const findIngredientIdByName = (name) => {
        const n = (name || '').trim().toLowerCase()
        if (!n) return null
        const match = (ingredientsCatalog || []).find((i) => (i.name || '').trim().toLowerCase() === n)
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

        const canEditSelectedCocktail = () => {
        return Boolean(isAuthenticated && user && selectedCocktail && (isAdmin || selectedCocktail.created_by_user_id === user.id))
    }

    const persistBrandSelection = async (currentIngredients) => {
        if (!selectedCocktailId || !selectedCocktail) return
        if (!canEditSelectedCocktail()) return

        // Use the cocktail's stored names/quantities as canonical; only apply bottle ids from UI
        const bottleByName = {}
        currentIngredients.forEach((ing) => {
            const key = (ing.name || '').trim().toLowerCase()
            if (key) bottleByName[key] = ing.bottle_id || ''
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
                    bottle_id: bottleByName[key] ? bottleByName[key] : null,
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
                name: ri.ingredient_name || '',
                amount: String(ri.quantity),
                unit: ri.unit || 'ml',
                bottle_id: ri.bottle_id || '',
            }))
            setIngredients(formattedIngredients.length ? formattedIngredients : [{ name: '', amount: '', unit: 'ml', bottle_id: '' }])
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
            if (!selectedCocktailId) {
                setCostData(null);
                setCostError('');
                return;
            }

            const scaleFactor = calculateScalingFactor();
            const scaleFactorForCost = scaleFactor > 0 ? scaleFactor : 1.0;

            const params = { scale_factor: scaleFactorForCost };

            try {
                setCostLoading(true);
                setCostError('');
                const response = await api.get(`/cocktail-recipes/${selectedCocktailId}/cost`, { params });
                setCostData(response.data);
            } catch (e) {
                setCostData(null);
                setCostError('Failed to load cost breakdown');
                console.error('Failed to load cost breakdown', e);
            } finally {
                setCostLoading(false);
            }
        };

        loadCost();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedCocktailId, desiredLiters, ingredients]);

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
                    const names = getIngredientNamesForCocktail(cocktail).map((n) => n.toLowerCase())
                    if (names.length === 0) return false;

                    // Check if all ingredient queries match (using startsWith)
                    // Each query must match at least one ingredient
                    return ingredientQueries.every(ingQuery => {
                        return names.some((n) => n.startsWith(ingQuery))
                    });
                });
                setFilteredCocktails(filtered);
            } else {
                // Search by cocktail name OR single ingredient
                const filtered = cocktails.filter(cocktail => {
                    // Check if name matches
                    const nameMatch = cocktail.name && cocktail.name.toLowerCase().startsWith(query);

                    // Check if any ingredient matches
                    const ingredientMatch = getIngredientNamesForCocktail(cocktail)
                        .some((n) => n.toLowerCase().startsWith(query));

                    return nameMatch || ingredientMatch;
                });
                setFilteredCocktails(filtered);
            }
        }
    }, [searchQuery, cocktails]);

    const handleAddCocktail = (cocktail) => {
        setSelectedCocktailId(cocktail.id);
        setSelectedCocktail(cocktail);
        setRecipeName(cocktail.name);
        const ris = cocktail.recipe_ingredients || []

        if (ris.length > 0) {
            const formattedIngredients = ris.map((ri) => ({
                name: ri.ingredient_name || '',
                amount: String(ri.quantity ?? ''),
                unit: ri.unit || 'ml',
                bottle_id: ri.bottle_id || '',
            }))
            setIngredients(formattedIngredients);
            setBrandOptionsByIndex(formattedIngredients.map(() => []));
            // Preload bottle options for each row
            formattedIngredients.forEach((row, idx) => {
                syncBrandOptionsForRow(idx, row.name);
            })
        } else {
            setIngredients([{ name: '', amount: '', unit: 'ml', bottle_id: '' }]);
            setBrandOptionsByIndex([[]]);
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
            <h2>Cocktail Recipe Scaler</h2>

            <div className="scaler-grid">
                <div className="scaler-left">
            <div className="cocktail-selector-section">
                <h3>Select from Existing Cocktails</h3>
                {loading && <div className="loading">Loading cocktails...</div>}
                {error && <div className="error-message">{error}</div>}
                {!loading && !error && (
                    <>
                        <div className="search-container-selector">
                            <input
                                type="text"
                                placeholder="Search by name or ingredients (e.g., vodka, lime)..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="search-input-selector"
                            />
                        </div>
                    <div className="cocktails-list-selector">
                            {filteredCocktails.length === 0 ? (
                                <p>
                                    {searchQuery.trim()
                                        ? `No cocktails found matching "${searchQuery}"`
                                        : cocktails.length === 0
                                            ? 'No cocktails available. Create some cocktails first!'
                                            : 'No cocktails match your search.'}
                                </p>
                        ) : (
                            <ul className="cocktail-selector-list">
                                    {filteredCocktails.map((cocktail) => (
                                    <li key={cocktail.id} className="cocktail-selector-item">
                                        <div className="cocktail-selector-info">
                                            <span className="cocktail-selector-name">{cocktail.name}</span>
                                            {getIngredientNamesForCocktail(cocktail).length > 0 && (
                                                <span className="cocktail-selector-ingredients">
                                                    {getIngredientNamesForCocktail(cocktail).length} ingredient{getIngredientNamesForCocktail(cocktail).length !== 1 ? 's' : ''}
                                                </span>
                                            )}
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => handleAddCocktail(cocktail)}
                                            className="add-cocktail-btn"
                                        >
                                                        Select
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
                    <label htmlFor="recipeName">Cocktail Name:</label>
                    <input
                        type="text"
                        id="recipeName"
                        value={recipeName}
                        onChange={(e) => setRecipeName(e.target.value)}
                        placeholder="Enter cocktail name"
                    />
                </div>

                <div className="input-group">
                    <label htmlFor="desiredLiters">Desired Liters to Produce:</label>
                    <input
                        type="number"
                        id="desiredLiters"
                        value={desiredLiters}
                        onChange={(e) => setDesiredLiters(e.target.value)}
                        placeholder="Enter liters"
                        min="0"
                        step="0.1"
                    />
                </div>
            </div>

                <IngredientInputs
                    ingredients={ingredients}
                    onIngredientChange={handleIngredientChange}
                    onAddIngredient={addIngredient}
                    onRemoveIngredient={removeIngredient}
                    minIngredients={1}
                    amountStep="0.1"
                        nameSuggestions={ingredientNameSuggestions}
                        showBottleSelect={true}
                        brandOptionsByIndex={brandOptionsByIndex}
                        bottlePlaceholder={savingBrands ? 'Saving...' : 'Bottle (optional)'}
                        brandDisabledByIndex={ingredients.map(() => selectedCocktailId ? !canEditSelectedCocktail() : false)}
                />
                </div>

                <div className="scaler-right">
                {totalVolume > 0 && desiredLiters && (
                    <div className="results-section">
                        <h3>Recipe Scaling Results</h3>
                        <div className="recipe-info">
                            <p><strong>Original Total Volume:</strong> {totalVolume} ml</p>
                            <p><strong>Desired Volume:</strong> {parseFloat(desiredLiters) * 1000} ml</p>
                            <p><strong>Scaling Factor:</strong> {scalingFactor.toFixed(3)}x</p>
                        </div>

                        <div className="quantities-display">
                            <div className="quantities-column">
                                <h4>Original Recipe</h4>
                                {ingredients.map((ingredient, index) => (
                                    <div key={index} className="quantity-item">
                                        <span className="ingredient-name">{ingredient.name || `Ingredient ${index + 1}`}</span>
                                        <span className="ingredient-amount">{ingredient.amount || 0} ml</span>
                                    </div>
                                ))}
                            </div>

                            <div className="quantities-column">
                                <h4>Scaled for {desiredLiters}L</h4>
                                {ingredients.map((ingredient, index) => (
                                    <div key={index} className="quantity-item">
                                        <span className="ingredient-name">{ingredient.name || `Ingredient ${index + 1}`}</span>
                                        <span className="ingredient-amount">{getScaledAmount(ingredient.amount)} ml</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                    {selectedCocktailId && (
                        <div className="results-section cost-section">
                            <h3>Cost Breakdown</h3>
                            {costLoading && <div className="loading">Loading costs...</div>}
                            {costError && <div className="error-message">{costError}</div>}

                            {!costLoading && !costError && costData && (
                                <>
                                    <div className="cost-breakdown">
                                        <div className="cost-row cost-header">
                                            <span>Ingredient</span>
                                            <span>Bottle</span>
                                            <span>Scaled</span>
                                            <span>Cost</span>
                                        </div>
                                        {Array.isArray(costData.lines) && costData.lines.map((line, idx) => (
                                            <div key={`${line.ingredient_name}-${idx}`} className="cost-row">
                                                <span className="cost-ingredient">{line.ingredient_name}</span>
                                                <span className="cost-brand">{line.bottle_name || '-'}</span>
                                                <span className="cost-ml">{Math.round((Number(line.scaled_quantity) || 0) * 100) / 100} {line.unit || ''}</span>
                                                <span className="cost-value">{formatMoney(line.ingredient_cost)}</span>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="cost-summary">
                                        <p><strong>Scaled Total Cost:</strong> {formatMoney(costData.scaled_total_cost)}</p>
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
