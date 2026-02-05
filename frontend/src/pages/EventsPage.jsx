import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import DatePicker, { registerLocale } from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import he from 'date-fns/locale/he'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import '../styles/events.css'

registerLocale('he', he)

export default function EventsPage() {
  const { isAdmin, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [events, setEvents] = useState([])

  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const loadEvents = async () => {
    try {
      setLoading(true)
      setError('')
      const params = new URLSearchParams()
      if (fromDate) params.set('from_date', fromDate)
      if (toDate) params.set('to_date', toDate)
      const qs = params.toString()
      const res = await api.get(`/events/${qs ? `?${qs}` : ''}`)
      setEvents(res.data || [])
    } catch (e) {
      console.error('Failed to load events', e)
      setError(t('events.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAdmin) return
    loadEvents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin])

  useEffect(() => {
    if (!isAdmin) return
    loadEvents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromDate, toDate])

  const deleteEvent = async (eventId) => {
    if (!eventId) return
    const ok = window.confirm(t('events.confirmDelete'))
    if (!ok) return
    try {
      setError('')
      await api.delete(`/events/${eventId}`)
      await loadEvents()
    } catch (err) {
      console.error('Failed to delete event', err)
      const detail = err?.response?.data?.detail || err?.message
      setError(detail ? String(detail) : t('events.errors.deleteFailed'))
    }
  }

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/" replace />

  return (
    <div className="card">
      <div className="events-header">
        <div className="events-header-title-row">
          <h2 style={{ margin: 0 }}>{t('events.title')}</h2>
          <Link to="/events/new" className="button-primary events-add-button" aria-label={t('events.actions.new')} title={t('events.actions.new')}>
            <span className="events-add-button-text">{t('events.actions.new')}</span>
            <span className="events-add-button-icon">+</span>
          </Link>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="events-filters">
        <div className="inventory-control">
          <label className="inventory-label" htmlFor="events-from-date">{t('common.from')}</label>
          <DatePicker
            id="events-from-date"
            className="form-input events-datepicker-input"
            dateFormat={lang === 'he' ? 'dd/MM/yyyy' : 'MM/dd/yyyy'}
            locale={lang === 'he' ? 'he' : 'en'}
            selected={fromDate ? new Date(fromDate + 'T12:00:00') : null}
            onChange={(d) => setFromDate(d ? d.toISOString().slice(0, 10) : '')}
            isClearable
            placeholderText={lang === 'he' ? 'dd/mm/yyyy' : 'mm/dd/yyyy'}
          />
        </div>
        <div className="inventory-control">
          <label className="inventory-label" htmlFor="events-to-date">{t('common.to')}</label>
          <DatePicker
            id="events-to-date"
            className="form-input events-datepicker-input"
            dateFormat={lang === 'he' ? 'dd/MM/yyyy' : 'MM/dd/yyyy'}
            locale={lang === 'he' ? 'he' : 'en'}
            selected={toDate ? new Date(toDate + 'T12:00:00') : null}
            onChange={(d) => setToDate(d ? d.toISOString().slice(0, 10) : '')}
            isClearable
            placeholderText={lang === 'he' ? 'dd/mm/yyyy' : 'mm/dd/yyyy'}
          />
        </div>
        <div className="events-filters-actions">
          <button type="button" className="button-primary" onClick={() => { setFromDate(''); setToDate('') }}>
            {t('common.clear')}
          </button>
          <button type="button" className="button-primary" onClick={loadEvents} disabled={loading}>
            {t('common.refresh')}
          </button>
        </div>
      </div>

      <div className="events-grid">
        <div className="events-panel">
          <div className="events-panel-title">{t('events.listTitle')}</div>
          {loading ? (
            <div className="loading">{t('common.loading')}</div>
          ) : (events || []).length === 0 ? (
            <div className="empty-state">{t('events.empty')}</div>
          ) : (
            <div className="events-list">
              {(events || []).map((ev) => {
                const title = (ev?.name || '').trim() || t('events.unnamed')
                const dateStr = ev?.event_date || ''
                const menu = ev?.menu_items || []
                return (
                  <div key={ev.id} className="events-list-item">
                    <div className="events-list-main">
                      <div className="name">{title}</div>
                      <div className="muted" style={{ marginTop: 4 }}>
                        {t('events.meta', { date: dateStr, people: ev.people })}
                      </div>
                      <div className="events-chips">
                        {menu.map((mi) => {
                          const cn = lang === 'he'
                            ? (mi?.cocktail_name_he || mi?.cocktail_name)
                            : (mi?.cocktail_name || mi?.cocktail_name_he)
                          return <span key={mi.id} className="pill pill-muted">{cn || mi.cocktail_recipe_id}</span>
                        })}
                      </div>
                    </div>
                    <div className="events-list-actions">
                      <Link className="button-edit" to={`/events/${ev.id}`}>
                        {t('events.actions.view')}
                      </Link>
                      <Link className="button-edit" to={`/events/${ev.id}/edit`}>
                        {t('common.edit')}
                      </Link>
                      <button type="button" className="button-danger" onClick={() => deleteEvent(ev.id)}>
                        {t('common.delete')}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

