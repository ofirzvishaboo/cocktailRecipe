import { useMemo, useState, useEffect } from 'react';
import '../styles/cocktailScaler.css';
import api from '../api';
import IngredientInputs from '../components/cocktail/IngredientInputs';
import { useAuth } from '../contexts/AuthContext'

export default function CocktailScaler() {
    const { user, isAuthenticated } = useAuth()
    const [recipeName, setRecipeName] = useState('');
    const [ingredients, setIngredients] = useState([{ name: '', amount: '', ingredient_brand_id: '' }]);
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
        setIngredients([...ingredients, { name: '', amount: '', ingredient_brand_id: '' }]);
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
                return { ...ingredient, name: value, ingredient_brand_id: '' };
            }
            return { ...ingredient, [field]: value };
        });
        setIngredients(updatedIngredients);

        if (field === 'name') syncBrandOptionsForRow(index, value);
        if (field === 'ingredient_brand_id') persistBrandSelection(updatedIngredients);
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

    const canEditSelectedCocktail = () => {
        return Boolean(isAuthenticated && user && selectedCocktail && selectedCocktail.user_id === user.id)
    }

    const persistBrandSelection = async (currentIngredients) => {
        if (!selectedCocktailId || !selectedCocktail) return
        if (!canEditSelectedCocktail()) return

        // Use the cocktail's stored names/ml as canonical; only apply brand ids from UI
        const brandByName = {}
        currentIngredients.forEach((ing) => {
            const key = (ing.name || '').trim().toLowerCase()
            if (key) brandByName[key] = ing.ingredient_brand_id || ''
        })

        const payload = {
            name: selectedCocktail.name,
            description: selectedCocktail.description || null,
            image_url: selectedCocktail.image_url || null,
            ingredients: (selectedCocktail.ingredients || []).map((ing) => {
                const key = (ing.name || '').trim().toLowerCase()
                return {
                    name: ing.name,
                    ml: ing.ml,
                    ingredient_brand_id: brandByName[key] ? brandByName[key] : null,
                }
            }),
        }

        try {
            setSavingBrands(true)
            const res = await api.put(`/cocktail-recipes/${selectedCocktailId}`, payload)
            const updated = res.data
            setSelectedCocktail(updated)
            // Keep local ingredient brand selections aligned with saved cocktail
            const formattedIngredients = (updated.ingredients || []).map((ing) => ({
                name: ing.name,
                amount: String(ing.ml),
                ingredient_brand_id: ing.ingredient_brand_id || '',
            }))
            setIngredients(formattedIngredients.length ? formattedIngredients : [{ name: '', amount: '', ingredient_brand_id: '' }])
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
                    // Skip cocktails without ingredients
                    if (!cocktail.ingredients || !Array.isArray(cocktail.ingredients) || cocktail.ingredients.length === 0) {
                        return false;
                    }

                    // Check if all ingredient queries match (using startsWith)
                    // Each query must match at least one ingredient
                    return ingredientQueries.every(ingQuery => {
                        return cocktail.ingredients.some(ing => {
                            if (!ing || !ing.name) return false;
                            return ing.name.toLowerCase().startsWith(ingQuery);
                        });
                    });
                });
                setFilteredCocktails(filtered);
            } else {
                // Search by cocktail name OR single ingredient
                const filtered = cocktails.filter(cocktail => {
                    // Check if name matches
                    const nameMatch = cocktail.name && cocktail.name.toLowerCase().startsWith(query);

                    // Check if any ingredient matches
                    const ingredientMatch = cocktail.ingredients && Array.isArray(cocktail.ingredients) &&
                        cocktail.ingredients.some(ing => {
                            if (!ing || !ing.name) return false;
                            return ing.name.toLowerCase().startsWith(query);
                        });

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
        if (cocktail.ingredients && cocktail.ingredients.length > 0) {
            const formattedIngredients = cocktail.ingredients.map(ing => ({
                name: ing.name,
                amount: ing.ml.toString(),
                ingredient_brand_id: ing.ingredient_brand_id || '',
            }));
            setIngredients(formattedIngredients);
            setBrandOptionsByIndex(formattedIngredients.map(() => []));
            // Preload brand options for each row
            formattedIngredients.forEach((row, idx) => {
                syncBrandOptionsForRow(idx, row.name);
            })
        } else {
            setIngredients([{ name: '', amount: '', ingredient_brand_id: '' }]);
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
                                            {cocktail.ingredients && cocktail.ingredients.length > 0 && (
                                                <span className="cocktail-selector-ingredients">
                                                    {cocktail.ingredients.length} ingredient{cocktail.ingredients.length !== 1 ? 's' : ''}
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
                        showBrandSelect={true}
                        brandOptionsByIndex={brandOptionsByIndex}
                        brandPlaceholder={savingBrands ? 'Saving...' : 'Brand bottle (optional)'}
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
                                            <span>Brand</span>
                                            <span>Scaled (ml)</span>
                                            <span>Cost</span>
                                        </div>
                                        {Array.isArray(costData.lines) && costData.lines.map((line, idx) => (
                                            <div key={`${line.ingredient_name}-${idx}`} className="cost-row">
                                                <span className="cost-ingredient">{line.ingredient_name}</span>
                                                <span className="cost-brand">{line.brand_name || '-'}</span>
                                                <span className="cost-ml">{Math.round((Number(line.scaled_ml) || 0) * 100) / 100}</span>
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
