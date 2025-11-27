import { useState, useEffect } from 'react';
import '../styles/cocktailScaler.css';
import api from '../api';

export default function CocktailScaler() {
    const [recipeName, setRecipeName] = useState('');
    const [ingredients, setIngredients] = useState([{ name: '', amount: '' }]);
    const [desiredLiters, setDesiredLiters] = useState('');
    const [cocktails, setCocktails] = useState([]);
    const [filteredCocktails, setFilteredCocktails] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const addIngredient = () => {
        setIngredients([...ingredients, { name: '', amount: '' }]);
    };

    const removeIngredient = (index) => {
        if (ingredients.length > 1) {
            setIngredients(ingredients.filter((_, i) => i !== index));
        }
    };

    const handleIngredientChange = (index, field, value) => {
        const updatedIngredients = ingredients.map((ingredient, i) =>
            i === index ? { ...ingredient, [field]: value } : ingredient
        );
        setIngredients(updatedIngredients);
    };

    const calculateTotalVolume = () => {
        return ingredients.reduce((total, ingredient) => {
            const amount = parseFloat(ingredient.amount) || 0;
            return total + amount;
        }, 0);
    };

    const calculateScalingFactor = () => {
        const totalVolume = calculateTotalVolume();
        const desiredVolume = parseFloat(desiredLiters) * 1000; // Convert liters to ml
        return totalVolume > 0 ? desiredVolume / totalVolume : 0;
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
        setRecipeName(cocktail.name);
        if (cocktail.ingredients && cocktail.ingredients.length > 0) {
            const formattedIngredients = cocktail.ingredients.map(ing => ({
                name: ing.name,
                amount: ing.ml.toString()
            }));
            setIngredients(formattedIngredients);
        } else {
            setIngredients([{ name: '', amount: '' }]);
        }
    };

    const totalVolume = calculateTotalVolume();
    const scalingFactor = calculateScalingFactor();

    return (
        <div className="cocktail-scaler">
            <h2>Cocktail Recipe Scaler</h2>

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
                                            Add
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

            <div className="sections-container">
                <div className="ingredients-section">
                    <h3>Ingredients</h3>
                    {ingredients.map((ingredient, index) => (
                        <div key={index} className="ingredient-row">
                            <input
                                type="text"
                                placeholder="Ingredient name"
                                value={ingredient.name}
                                onChange={(e) => handleIngredientChange(index, 'name', e.target.value)}
                            />
                            <input
                                type="number"
                                placeholder="Amount (ml)"
                                value={ingredient.amount}
                                onChange={(e) => handleIngredientChange(index, 'amount', e.target.value)}
                                min="0"
                                step="0.1"
                            />
                            <button
                                type="button"
                                onClick={() => removeIngredient(index)}
                                className="remove-btn"
                                disabled={ingredients.length === 1}
                            >
                                Remove
                            </button>
                        </div>
                    ))}
                    <button type="button" onClick={addIngredient} className="add-btn">
                        Add Ingredient
                    </button>
                </div>

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
            </div>
        </div>
    );
}
