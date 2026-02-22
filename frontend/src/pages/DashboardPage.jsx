import { useState, useEffect, useCallback } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import DatePicker, { registerLocale } from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import he from 'date-fns/locale/he'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import '../styles/events.css'

registerLocale('he', he)

const formatDate = (isoStr, lang) => {
  if (!isoStr) return ''
  const d = new Date(isoStr + 'T12:00:00')
  return lang === 'he'
    ? d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/** Get Sunday (start of week) for a given date. Sunday = first day. */
const getSundayOfWeek = (d) => {
  const date = new Date(d)
  const day = date.getDay() // 0=Sun, 1=Mon, ..., 6=Sat
  const daysSinceSunday = day === 0 ? 0 : day
  date.setDate(date.getDate() - daysSinceSunday)
  return date
}

const toYYYYMMDD = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const addDays = (d, n) => {
  const out = new Date(d)
  out.setDate(out.getDate() + n)
  return out
}

const DashboardPage = () => {
  const { isAdmin, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [weekStart, setWeekStart] = useState(() => toYYYYMMDD(getSundayOfWeek(new Date())))
  const [dashboard, setDashboard] = useState({
    events_data: [],
    orders_data: [],
    week_start: null,
    week_end: null,
    orders_total_minor: 0,
    orders_total_currency: 'ILS',
  })

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const params = new URLSearchParams()
      if (weekStart) params.set('from_date', weekStart)
      const qs = params.toString()
      const res = await api.get(`/dashboard/${qs ? `?${qs}` : ''}`)
      setDashboard({
        events_data: res.data?.events_data ?? [],
        orders_data: res.data?.orders_data ?? [],
        week_start: res.data?.week_start ?? null,
        week_end: res.data?.week_end ?? null,
        orders_total_minor: res.data?.orders_total_minor ?? 0,
        orders_total_currency: res.data?.orders_total_currency ?? 'ILS',
      })
    } catch (err) {
      console.error('Failed to load dashboard', err)
      setError(t('dashboard.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [weekStart, t])

  useEffect(() => {
    if (!isAdmin) return
    loadDashboard()
  }, [isAdmin, loadDashboard])

  const goPrevWeek = () => {
    const d = new Date(weekStart + 'T12:00:00')
    setWeekStart(toYYYYMMDD(addDays(d, -7)))
  }

  const goNextWeek = () => {
    const d = new Date(weekStart + 'T12:00:00')
    setWeekStart(toYYYYMMDD(addDays(d, 7)))
  }

  const handleWeekChange = (date) => {
    if (date) setWeekStart(toYYYYMMDD(getSundayOfWeek(date)))
  }

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/" replace />

  if (loading) return <div className="card"><div className="loading">{t('common.loading')}</div></div>
  if (error) return <div className="card"><div className="error-message">{error}</div></div>

  const { events_data, orders_data, week_start, week_end, orders_total_minor, orders_total_currency } = dashboard
  const weekLabel = week_start && week_end
    ? `${formatDate(week_start, lang)} – ${formatDate(week_end, lang)}`
    : ''
  const ordersTotalFormatted = orders_total_minor > 0
    ? `${(orders_total_minor / 100).toLocaleString(lang === 'he' ? 'he-IL' : 'en-US', { minimumFractionDigits: 2 })} ${orders_total_currency}`
    : null

  return (
    <div className="card">
      <h2 style={{ marginTop: 0, marginBottom: '1rem' }}>{t('dashboard.title')}</h2>

      <div className="dashboard-quick-actions">
        <Link to="/events/new" className="button-primary dashboard-action-btn">
          {t('dashboard.createEvent')}
        </Link>
        <Link to="/cocktail-scaler" className="button-secondary dashboard-action-btn">
          {t('dashboard.batchCalculator')}
        </Link>
      </div>

      <div className="dashboard-filters">
        <button type="button" className="button-secondary dashboard-nav-btn" onClick={goPrevWeek} aria-label={t('dashboard.prevWeek')}>
          ‹
        </button>
        <DatePicker
          selected={weekStart ? new Date(weekStart + 'T12:00:00') : null}
          onChange={handleWeekChange}
          dateFormat={lang === 'he' ? 'dd/MM/yyyy' : 'MM/dd/yyyy'}
          locale={lang === 'he' ? 'he' : 'en'}
          className="form-input dashboard-date-input"
          placeholderText={lang === 'he' ? 'בחר שבוע' : 'Select week'}
        />
        <button type="button" className="button-secondary dashboard-nav-btn" onClick={goNextWeek} aria-label={t('dashboard.nextWeek')}>
          ›
        </button>
        {weekLabel && <span className="dashboard-week-label">{weekLabel}</span>}
      </div>

      <div className="dashboard-sections">
        <section className="dashboard-section">
          <h3 className="dashboard-section-title">{t('dashboard.thisWeekEvents')}</h3>
          {events_data.length === 0 ? (
            <p className="text-muted">{t('dashboard.emptyEvents')}</p>
          ) : (
            <ul className="dashboard-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {events_data.map((ev) => (
                <li key={ev.id} className="dashboard-item">
                  <Link to={`/events/${ev.id}`} className="dashboard-link">
                    <span className="dashboard-item-name">{ev.event_name || t('events.unnamed')}</span>
                    <span className="dashboard-item-meta">
                      {formatDate(ev.event_date, lang)} • {t('dashboard.people', { count: ev.people })}
                      {ev.cocktail_names?.filter(Boolean).length > 0 && (
                        <> • {ev.cocktail_names.filter(Boolean).join(', ')}</>
                      )}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link to="/events" className="button-primary" style={{ marginTop: '0.75rem', display: 'inline-block' }}>
            {t('dashboard.viewEvents')}
          </Link>
        </section>

        <section className="dashboard-section">
          <h3 className="dashboard-section-title">{t('dashboard.thisWeekOrders')}</h3>
          {orders_total_minor > 0 && (
            <p className="dashboard-orders-total">
              {t('dashboard.ordersTotal')}: <strong>{ordersTotalFormatted}</strong>
            </p>
          )}
          {orders_data.length === 0 ? (
            <p className="text-muted">{t('dashboard.emptyOrders')}</p>
          ) : (
            <ul className="dashboard-list" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {orders_data.map((ord) => (
                <li key={ord.id} className="dashboard-item">
                  <Link to="/orders" className="dashboard-link">
                    <span className="dashboard-item-name">{ord.supplier || t('orders.supplier.unknown')}</span>
                    <span className="dashboard-item-meta">
                      {t(`orders.status.${ord.status || 'DRAFT'}`)} • {formatDate(ord.period_start, lang)}–{formatDate(ord.period_end, lang)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link to="/orders" className="button-primary" style={{ marginTop: '0.75rem', display: 'inline-block' }}>
            {t('dashboard.viewOrders')}
          </Link>
        </section>
      </div>
    </div>
  )
}

export default DashboardPage
