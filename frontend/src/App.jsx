import { useState, useEffect } from 'react'
import './App.css'
import AddCocktailForm from './components/addCocktailForm'
import api from './api'

function App() {
  const [cocktails, setCocktails] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingCocktail, setEditingCocktail] = useState(null)

  const AddCocktail = (cocktail) => {
    setCocktails([...cocktails, cocktail])
  }

  const removeCocktail = async (cocktailId) => {
    try {
      await api.delete(`/cocktail-recipes/${cocktailId}`)
      setCocktails(cocktails.filter(c => c.id !== cocktailId))
    } catch (e) {
      setError('Failed to delete cocktail')
      console.error('Failed to delete cocktail', e)
    }
  }

  const editCocktail = (cocktail) => {
    if (!cocktail.id) {
      setError('Cannot edit cocktail without ID')
      return
    }
    setEditingCocktail(cocktail)
  }

  const updateCocktail = async (updatedCocktail) => {
    try {
      await api.put(`/cocktail-recipes/${updatedCocktail.id}`, updatedCocktail)
      setCocktails(cocktails.map(c => c.id === updatedCocktail.id ? updatedCocktail : c))
      setEditingCocktail(null)
    } catch (e) {
      setError('Failed to update cocktail')
      console.error('Failed to update cocktail', e)
    }
  }

  const cancelEdit = () => {
    setEditingCocktail(null)
  }

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const res = await api.get('/cocktail-recipes')
        setCocktails(res.data || [])
      } catch (e) {
        setError('Failed to load cocktails')
        console.error('Failed to load cocktails', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <>
      <h1>Cocktail Menu</h1>
      <div className="card">
        {editingCocktail ? (
          <div>
            <h3>Edit Cocktail</h3>
            <AddCocktailForm
              AddCocktail={updateCocktail}
              initialCocktail={editingCocktail}
              onCancel={cancelEdit}
              isEdit={true}
            />
          </div>
        ) : (
          <AddCocktailForm AddCocktail={AddCocktail} />
        )}
        <div style={{ textAlign: 'left', marginTop: 16 }}>
          <h3>Cocktails</h3>
          {loading && <div>Loading...</div>}
          {error && <div style={{ color: 'red' }}>{error}</div>}
          {!loading && !error && (
            <ul>
              {cocktails.map((c, idx) => (
                <li key={`${c.name}-${idx}`}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{c.name}</strong>
                    <div>
                      <button
                        onClick={() => editCocktail(c)}
                        style={{ marginRight: '10px', color: 'blue' }}
                        disabled={!c.id}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => removeCocktail(c.id || idx)}
                        style={{ color: 'red' }}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                  <ul>
                    {(c.ingredients || []).map((ing, i) => (
                      <li key={`${ing.name}-${i}`}>{ing.name} - {ing.ml} ml</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}

export default App
