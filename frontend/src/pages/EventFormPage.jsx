import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import Select from '../components/common/Select'
import '../styles/events.css'

function toLocalDateInputValue(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export default function EventFormPage() {
  const { id } = useParams()
  const isNew = !id
  const nav = useNavigate()
  const { isAdmin, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [cocktails, setCocktails] = useState([])

  const [form, setForm] = useState({
    name: '',
    notes: '',
    event_date: toLocalDateInputValue(),
    people: 30,
    servings_per_person: 3,
    cocktail_ids: ['', '', '', ''],
    submitting: false,
  })

  const cocktailById = useMemo(() => {
    const m = new Map()
    for (const c of cocktails || []) m.set(c.id, c)
    return m
  }, [cocktails])

  const cocktailOptions = useMemo(() => {
    const arr = [...(cocktails || [])]
    arr.sort((a, b) => {
      const an = (a?.name || a?.name_he || '').toLowerCase()
      const bn = (b?.name || b?.name_he || '').toLowerCase()
      return an.localeCompare(bn)
    })
    return arr.map((c) => {
      const label = (lang === 'he' ? (c?.name_he || c?.name) : (c?.name || c?.name_he)) || c.id
      return { value: c.id, label }
    })
  }, [cocktails, lang])

  const loadCocktails = async () => {
    try {
      const res = await api.get('/cocktail-recipes/')
      setCocktails(res.data || [])
    } catch (e) {
      console.error('Failed to load cocktails', e)
    }
  }

  const loadEvent = async () => {
    if (!id) return
    try {
      setLoading(true)
      setError('')
      const res = await api.get(`/events/${id}`)
      const ev = res.data
      const menu = ev?.menu_items || []
      setForm({
        name: ev?.name || '',
        notes: ev?.notes || '',
        event_date: ev?.event_date || toLocalDateInputValue(),
        people: ev?.people ?? 30,
        servings_per_person: ev?.servings_per_person ?? 3,
        cocktail_ids: menu.slice(0, 4).map((mi) => mi.cocktail_recipe_id).concat(['', '', '', '']).slice(0, 4),
        submitting: false,
      })
    } catch (e) {
      console.error('Failed to load event', e)
      const detail = e?.response?.data?.detail || e?.message
      setError(detail ? String(detail) : t('events.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdmin) return
    loadCocktails()
    if (!isNew) loadEvent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, id])

  const save = async (e) => {
    e.preventDefault()
    const ids = (form.cocktail_ids || []).filter(Boolean)
    if (ids.length !== 4) {
      setError(t('events.errors.exactlyFourCocktails'))
      return
    }
    const cocktail_names = ids.map((cid) => {
      const c = cocktailById.get(cid)
      return (c?.name || c?.name_he || '').trim()
    })
    if (cocktail_names.some((n) => !n)) {
      setError(t('events.errors.exactlyFourCocktails'))
      return
    }

    try {
      setForm((p) => ({ ...p, submitting: true }))
      setError('')
      if (isNew) {
        const res = await api.post('/events/', {
          name: (form.name || '').trim() || null,
          notes: (form.notes || '').trim() || null,
          event_date: form.event_date,
          people: Number(form.people),
          servings_per_person: Number(form.servings_per_person),
          cocktail_names,
        })
        const newId = res?.data?.id
        nav(newId ? `/events/${newId}` : '/events')
        return
      }
      await api.patch(`/events/${id}`, {
        name: (form.name || '').trim() || null,
        notes: (form.notes || '').trim() || null,
        event_date: form.event_date || null,
        people: Number(form.people),
        servings_per_person: Number(form.servings_per_person),
        cocktail_names,
      })
      nav(`/events/${id}`)
    } catch (err) {
      console.error('Failed to save event', err)
      const detail = err?.response?.data?.detail || err?.message
      setError(detail ? String(detail) : (isNew ? t('events.errors.createFailed') : t('events.errors.updateFailed')))
    } finally {
      setForm((p) => ({ ...p, submitting: false }))
    }
  }

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/" replace />

  return (
    <div className="card">
      <div className="events-header">
        <div className="events-header-left">
          <div className="muted">
            <Link to="/events" className="link">{t('events.backToList')}</Link>
          </div>
          <h2 style={{ margin: '6px 0 0 0' }}>
            {isNew ? t('events.createTitle') : t('events.editTitle')}
          </h2>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {loading && <div className="loading">{t('common.loading')}</div>}

      <div className="events-panel">
        <div className="events-panel-title">{t('events.detailsTitle')}</div>
        <form onSubmit={save} className="events-form">
          <div className="events-form-row">
            <div>
              <label className="inventory-label">{t('events.fields.name')}</label>
              <input
                className="form-input"
                value={form.name}
                onChange={(e2) => setForm((p) => ({ ...p, name: e2.target.value }))}
                placeholder={t('events.placeholders.name')}
              />
            </div>
            <div>
              <label className="inventory-label">{t('events.fields.date')}</label>
              <input
                className="form-input"
                type="date"
                value={form.event_date}
                onChange={(e2) => setForm((p) => ({ ...p, event_date: e2.target.value }))}
                required
              />
            </div>
          </div>

          <div className="events-form-row">
            <div>
              <label className="inventory-label">{t('events.fields.people')}</label>
              <input
                className="form-input"
                type="number"
                step="1"
                min="1"
                value={form.people}
                onChange={(e2) => setForm((p) => ({ ...p, people: e2.target.value }))}
                required
              />
            </div>
            <div>
              <label className="inventory-label">{t('events.fields.servingsPerPerson')}</label>
              <input
                className="form-input"
                type="number"
                step="0.5"
                min="0"
                value={form.servings_per_person}
                onChange={(e2) => setForm((p) => ({ ...p, servings_per_person: e2.target.value }))}
                required
              />
            </div>
          </div>

          <div>
            <label className="inventory-label">{t('events.fields.cocktails')}</label>
            <div className="events-cocktails-grid">
              {[0, 1, 2, 3].map((idx) => (
                <Select
                  key={idx}
                  id={`ev-form-cocktail-${idx}`}
                  value={form.cocktail_ids[idx] || ''}
                  onChange={(v) => setForm((p) => {
                    const next = [...(p.cocktail_ids || ['', '', '', ''])]
                    next[idx] = v || ''
                    return { ...p, cocktail_ids: next }
                  })}
                  ariaLabel={t('events.fields.cocktailN', { n: idx + 1 })}
                  placeholder={t('events.placeholders.selectCocktail')}
                  options={cocktailOptions}
                />
              ))}
            </div>
          </div>

          <div>
            <label className="inventory-label">{t('events.fields.notes')}</label>
            <textarea
              className="form-input"
              rows={3}
              value={form.notes}
              onChange={(e2) => setForm((p) => ({ ...p, notes: e2.target.value }))}
              placeholder={t('events.placeholders.notes')}
            />
          </div>

          <div className="events-form-actions">
            <button type="submit" className="button-primary" disabled={form.submitting}>
              {isNew ? t('events.actions.create') : t('common.save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

