import { useNavigate, Link } from 'react-router-dom'
import AddCocktailForm from '../components/cocktail/AddCocktailForm'
import { useAuth } from '../contexts/AuthContext'

const CreateCocktailPage = () => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  const handleCreateCocktail = (newCocktail) => {
    // Navigate to the detail page after successful creation
    // The form already handles the API call and passes the created cocktail
    navigate(`/cocktails/${newCocktail.id}`)
  }

  if (!isAuthenticated) {
    return (
      <div className="card">
        <div className="info-message">
          <p>Please <Link to="/login">log in</Link> to create cocktail recipes.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h2>Create New Cocktail</h2>
      <AddCocktailForm AddCocktail={handleCreateCocktail} />
    </div>
  )
}

export default CreateCocktailPage

