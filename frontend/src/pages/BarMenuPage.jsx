import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { WINES, BEERS, SPIRITS } from '../data/barMenuData'
import api from '../api'
import '../styles/barMenu.css'

// Fetch all cocktails once, then filter client-side (backend has no menu filter param)
async function fetchAllCocktails(signal) {
  const res = await api.get('/cocktail-recipes/', { signal })
  return Array.isArray(res.data) ? res.data : []
}

function inMenu(cocktail, menuKey) {
  if (Array.isArray(cocktail?.menus) && cocktail.menus.length > 0) {
    return cocktail.menus.includes(menuKey)
  }
  // Legacy fallback: is_base → classic, else → signature
  if (menuKey === 'classic') return !!cocktail?.is_base
  if (menuKey === 'signature') return !cocktail?.is_base
  return false
}

// ── Sub-section renderers ─────────────────────────────────────────────────────

function PriceTag({ price }) {
  return <span className="bm-price">₪{price}</span>
}

function MenuItem({ item, lang }) {
  const displayName = lang === 'he' && item.nameHe ? item.nameHe : item.name
  return (
    <div className="bm-item">
      <div className="bm-item-left">
        <span className="bm-item-name">{displayName}</span>
        {item.origin && <span className="bm-item-sub">{item.origin}</span>}
        {item.note && <span className="bm-item-sub">{item.note}</span>}
      </div>
      <PriceTag price={item.priceIls} />
    </div>
  )
}

function SpiritSection({ titleEn, titleHe, items, lang }) {
  const title = lang === 'he' ? titleHe : titleEn
  if (!items || items.length === 0) return null
  return (
    <div className="bm-spirit-group">
      <h3 className="bm-spirit-title">{title}</h3>
      {items.map((item, i) => (
        <MenuItem key={i} item={item} lang={lang} />
      ))}
    </div>
  )
}

function CocktailCard({ cocktail, lang }) {
  const name = lang === 'he' && cocktail.name_he ? cocktail.name_he : cocktail.name
  const desc = lang === 'he' && cocktail.description_he ? cocktail.description_he : cocktail.description
  const garnish = lang === 'he' && cocktail.garnish_text_he ? cocktail.garnish_text_he : cocktail.garnish_text
  // API returns flat glass_type_name / glass_type_name_he
  const glass = lang === 'he' && cocktail.glass_type_name_he
    ? cocktail.glass_type_name_he
    : cocktail.glass_type_name

  const ingredients = cocktail.recipe_ingredients ?? []

  return (
    <div className="bm-cocktail-card">
      <div className="bm-cocktail-header">
        <h3 className="bm-cocktail-name">{name}</h3>
      </div>
      {desc && <p className="bm-cocktail-desc">{desc}</p>}
      {ingredients.length > 0 && (
        <div className="bm-cocktail-ingredients">
          {ingredients.map((ri, i) => {
            // API returns flat ingredient_name / ingredient_name_he fields
            const ingName = lang === 'he' && ri.ingredient_name_he
              ? ri.ingredient_name_he
              : (ri.ingredient_name ?? '')
            return (
              <span key={i} className="bm-cocktail-ing">
                {ingName}{i < ingredients.length - 1 ? ', ' : ''}
              </span>
            )
          })}
        </div>
      )}
      <div className="bm-cocktail-meta">
        {glass && <span className="bm-cocktail-glass">{glass}</span>}
        {garnish && <span className="bm-cocktail-garnish">{garnish}</span>}
      </div>
    </div>
  )
}

// ── Tab panels ────────────────────────────────────────────────────────────────

function WinesPanel({ lang }) {
  const [sub, setSub] = useState('white')

  const subTabs = [
    { key: 'white', en: 'White', he: 'לבן' },
    { key: 'rose', en: 'Rosé', he: 'רוזה' },
    { key: 'red', en: 'Red', he: 'אדום' },
  ]

  const wineMap = { white: WINES.white, rose: WINES.rose, red: WINES.red }

  return (
    <div className="bm-panel">
      <div className="bm-sub-tabs">
        {subTabs.map(({ key, en, he }) => (
          <button
            key={key}
            className={`bm-sub-tab${sub === key ? ' active' : ''}`}
            onClick={() => setSub(key)}
          >
            {lang === 'he' ? he : en}
          </button>
        ))}
      </div>
      <div className="bm-items-list">
        {wineMap[sub].map((item, i) => (
          <MenuItem key={i} item={item} lang={lang} />
        ))}
      </div>
      <p className="bm-note">{lang === 'he' ? '* מחיר לכוס' : '* Price per glass'}</p>
    </div>
  )
}

function BeersPanel({ lang }) {
  const [sub, setSub] = useState('tap')

  const subTabs = [
    { key: 'tap', en: 'Tap', he: 'שאיבה' },
    { key: 'bottle', en: 'Bottle', he: 'בקבוק' },
    { key: 'can', en: 'Can', he: 'פחית' },
    { key: 'sparkling', en: 'Sparkling', he: 'מבעבע' },
  ]

  const beerMap = { tap: BEERS.tap, bottle: BEERS.bottle, can: BEERS.can, sparkling: BEERS.sparkling }

  return (
    <div className="bm-panel">
      <div className="bm-sub-tabs">
        {subTabs.map(({ key, en, he }) => (
          <button
            key={key}
            className={`bm-sub-tab${sub === key ? ' active' : ''}`}
            onClick={() => setSub(key)}
          >
            {lang === 'he' ? he : en}
          </button>
        ))}
      </div>
      <div className="bm-items-list">
        {beerMap[sub].map((item, i) => (
          <MenuItem key={i} item={item} lang={lang} />
        ))}
      </div>
      {sub === 'can' && (
        <p className="bm-note">
          {lang === 'he'
            ? '* ניתן להגיש קר בדלי קרח לפי בקשה'
            : '* Can be served chilled in ice bucket upon request'}
        </p>
      )}
    </div>
  )
}

function CocktailsPanel({ allCocktails, loading, error, menuKey, lang }) {
  const cocktails = allCocktails.filter((c) => inMenu(c, menuKey))

  if (loading) {
    return (
      <div className="bm-panel bm-state">
        <div className="bm-spinner" />
      </div>
    )
  }
  if (error) {
    return (
      <div className="bm-panel bm-state">
        <p className="bm-error-msg">
          {lang === 'he' ? 'שגיאה בטעינת הקוקטיילים' : 'Failed to load cocktails'}
        </p>
      </div>
    )
  }
  if (cocktails.length === 0) {
    return (
      <div className="bm-panel bm-state">
        <p className="bm-empty-msg">
          {lang === 'he' ? 'אין קוקטיילים עדיין' : 'No cocktails yet'}
        </p>
      </div>
    )
  }

  return (
    <div className="bm-panel">
      <div className="bm-cocktails-grid">
        {cocktails.map((c) => (
          <CocktailCard key={c.id} cocktail={c} lang={lang} />
        ))}
      </div>
    </div>
  )
}

function AlcoholPanel({ lang }) {
  const sections = [
    { key: 'vodka',           en: 'Vodka',                he: 'וודקה' },
    { key: 'gin',             en: 'Gin',                  he: 'ג׳ין' },
    { key: 'rum',             en: 'Rum',                  he: 'רום' },
    { key: 'agave',           en: 'Agave',                he: 'אגב' },
    { key: 'whiskey',         en: 'Whiskey',              he: 'ויסקי' },
    { key: 'cognac',          en: 'Cognac',               he: 'קוניאק' },
    { key: 'aperitif',        en: 'Aperitif & Vermouth',  he: 'אפריטיף ווורמוט' },
    { key: 'liqueur',         en: 'Liqueur',              he: 'ליקר' },
    { key: 'homemadeLiqueur', en: 'House Liqueur',        he: 'ליקר ביתי' },
    { key: 'anise',           en: 'Anise',                he: 'אניס' },
    { key: 'addOns',          en: 'Add-ons',              he: 'תוספות' },
  ]

  return (
    <div className="bm-panel bm-alcohol-panel">
      {sections.map(({ key, en, he }) => (
        <SpiritSection
          key={key}
          titleEn={en}
          titleHe={he}
          items={SPIRITS[key]}
          lang={lang}
        />
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

const MAIN_TABS = [
  { key: 'signature', en: 'Signature',  he: 'סיגנצ׳ר' },
  { key: 'classic',   en: 'Classics',   he: 'קלאסיים' },
  { key: 'spritz',    en: 'Spritz',     he: 'ספריץ׳' },
  { key: 'wines',     en: 'Wines',      he: 'יינות' },
  { key: 'beers',     en: 'Beers',      he: 'בירות' },
  { key: 'alcohol',   en: 'Alcohol',    he: 'אלכוהול' },
]

export default function BarMenuPage() {
  const { i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]
  const isHe = lang === 'he'
  const [activeTab, setActiveTab] = useState('signature')

  // Fetch all cocktails once; panels filter client-side
  const [allCocktails, setAllCocktails] = useState([])
  const [cocktailsLoading, setCocktailsLoading] = useState(true)
  const [cocktailsError, setCocktailsError] = useState(false)
  const abortRef = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    abortRef.current = controller
    setCocktailsLoading(true)
    setCocktailsError(false)
    fetchAllCocktails(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setAllCocktails(data)
      })
      .catch((err) => {
        if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return
        setCocktailsError(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setCocktailsLoading(false)
      })
    return () => controller.abort()
  }, [])

  return (
    <div className={`bm-page${isHe ? ' rtl' : ''}`}>
      {/* Header */}
      <header className="bm-header">
        <div className="bm-logo-mark">✦</div>
        <h1 className="bm-title">The Cocktail Factory</h1>
        <p className="bm-subtitle">
          {isHe ? 'מיקסולוגיה בעבודת יד' : 'Crafted Mixology'}
        </p>
        <div className="bm-divider" />
      </header>

      {/* Main tabs */}
      <nav className="bm-tabs" role="tablist">
        {MAIN_TABS.map(({ key, en, he }) => (
          <button
            key={key}
            role="tab"
            aria-selected={activeTab === key}
            className={`bm-tab${activeTab === key ? ' active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            {isHe ? he : en}
          </button>
        ))}
      </nav>

      {/* Panel */}
      <main className="bm-content">
        {activeTab === 'signature' && (
          <CocktailsPanel
            allCocktails={allCocktails}
            loading={cocktailsLoading}
            error={cocktailsError}
            menuKey="signature"
            lang={lang}
          />
        )}
        {activeTab === 'classic' && (
          <CocktailsPanel
            allCocktails={allCocktails}
            loading={cocktailsLoading}
            error={cocktailsError}
            menuKey="classic"
            lang={lang}
          />
        )}
        {activeTab === 'spritz' && (
          <CocktailsPanel
            allCocktails={allCocktails}
            loading={cocktailsLoading}
            error={cocktailsError}
            menuKey="spritz"
            lang={lang}
          />
        )}
        {activeTab === 'wines'     && <WinesPanel lang={lang} />}
        {activeTab === 'beers'     && <BeersPanel lang={lang} />}
        {activeTab === 'alcohol'   && <AlcoholPanel lang={lang} />}
      </main>

      <footer className="bm-footer">
        <span>{isHe ? 'מיקסולוגיה בעבודת יד • נבנה עם תשוקה' : 'Crafted Mixology • Built with Passion'}</span>
      </footer>
    </div>
  )
}
