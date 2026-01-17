import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import AddCocktailForm from '../components/cocktail/AddCocktailForm'
import { useAuth } from '../contexts/AuthContext'

const CreateCocktailPage = () => {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { t } = useTranslation()

  const handleCreateCocktail = (newCocktail) => {
    // Navigate to the detail page after successful creation
    // The form already handles the API call and passes the created cocktail
    navigate(`/cocktails/${newCocktail.id}`)
  }

  if (!isAuthenticated) {
    return (
      <div className="card">
        <div className="info-message">
          <p>{t('createCocktail.loginPrompt')} <Link to="/login">{t('createCocktail.loginLink')}</Link> {t('createCocktail.loginPromptSuffix')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h2>{t('createCocktail.title')}</h2>
      <AddCocktailForm AddCocktail={handleCreateCocktail} />
    </div>
  )
}

export default CreateCocktailPage

