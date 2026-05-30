import { useState, useEffect, useCallback, useMemo } from 'react'
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
    ? d.toLocaleDateString('he-IL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    : d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
}

const formatShortDate = (isoStr) => {
  if (!isoStr) return ''
  const parts = isoStr.split('-').map(Number)
  return `${parts[2]}/${parts[1]}`
}

const getSundayOfWeek = (d) => {
  const date = new Date(d)
  const day = date.getDay()
  date.setDate(date.getDate() - day)
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

const DAY_KEYS_HE = ['א׳', 'ב׳', 'ג׳', 'ד׳', 'ה׳', 'ו׳', 'ש׳']
const DAY_KEYS_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const ROLE_COLORS = {
  bartender: { bg: 'rgba(47,127,247,0.1)', color: 'var(--primary,#2f7ff7)' },
  manager: { bg: 'rgba(40,167,69,0.1)', color: '#28a745' },
  cleaner: { bg: 'rgba(108,117,125,0.1)', color: '#6c757d' },
}

function KpiCard({ label, value, sub, accent }) {
  return (
    <div className={`db-kpi-card ${accent ? `db-kpi-card--${accent}` : ''}`}>
      <span className="db-kpi-value">{value}</span>
      <span className="db-kpi-label">{label}</span>
      {sub && <span className="db-kpi-sub">{sub}</span>}
    </div>
  )
}

function RoleBadge({ role, t }) {
  const style = ROLE_COLORS[role] || ROLE_COLORS.cleaner
  return (
    <span className="db-role-badge" style={style}>
      {t(`schedule.roles.${role}`, { defaultValue: role })}
    </span>
  )
}

const DashboardPage = () => {
  const { isAdmin, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [weekStart, setWeekStart] = useState(
    () => toYYYYMMDD(getSundayOfWeek(new Date())),
  )
  const [dashboard, setDashboard] = useState(null)

  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const params = new URLSearchParams()
      if (weekStart) params.set('from_date', weekStart)
      const qs = params.toString()
      const res = await api.get(`/dashboard/${qs ? `?${qs}` : ''}`)
      setDashboard(res.data)
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

  // ── KPI calculations ───────────────────────────────────────────────
  const kpi = useMemo(() => {
    if (!dashboard) return null

    const todayStaff = (dashboard.today_shifts || []).length

    const clRuns = dashboard.checklist_week || []
    const clSubmitted = clRuns.filter((r) => r.status === 'submitted').length
    const clTotal = clRuns.length

    const avList = dashboard.availability_next_week || []
    const avSubmitted = avList.filter((s) => s.submitted).length
    const avTotal = avList.length

    const ordersTotal =
      dashboard.orders_total_minor > 0
        ? `${(dashboard.orders_total_minor / 100).toLocaleString(
            lang === 'he' ? 'he-IL' : 'en-US',
            { minimumFractionDigits: 2 },
          )} ${dashboard.orders_total_currency}`
        : null

    return { todayStaff, clSubmitted, clTotal, avSubmitted, avTotal, ordersTotal }
  }, [dashboard, lang])

  // ── Checklist table: group by date, show opening + closing per row ─
  const checklistByDate = useMemo(() => {
    if (!dashboard) return []
    const runs = dashboard.checklist_week || []
    const map = {}
    for (const r of runs) {
      if (!map[r.run_date]) map[r.run_date] = {}
      map[r.run_date][r.type] = r
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b))
  }, [dashboard])

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/" replace />
  if (loading)
    return (
      <div className="card">
        <div className="loading">{t('common.loading')}</div>
      </div>
    )
  if (error)
    return (
      <div className="card">
        <div className="error-message">{error}</div>
      </div>
    )

  const {
    events_data = [],
    orders_data = [],
    week_start,
    week_end,
    orders_total_minor,
    today_shifts = [],
    availability_next_week = [],
    target_week_start,
  } = dashboard || {}

  const weekLabel =
    week_start && week_end
      ? `${formatDate(week_start, lang)} – ${formatDate(week_end, lang)}`
      : ''

  const ordersTotalFormatted = kpi?.ordersTotal

  const dayLabel = (dayIndex) => {
    const keys = lang === 'he' ? DAY_KEYS_HE : DAY_KEYS_EN
    return keys[dayIndex] || ''
  }

  return (
    <div className="card db-page">
      {/* ── Header ── */}
      <div className="db-header">
        <h2 style={{ margin: 0 }}>{t('dashboard.title')}</h2>
        <div className="dashboard-quick-actions">
          <Link to="/events/new" className="button-primary dashboard-action-btn">
            {t('dashboard.createEvent')}
          </Link>
          <Link
            to="/schedule"
            className="button-secondary dashboard-action-btn"
          >
            {t('dashboard.publishSchedule')}
          </Link>
          <Link
            to="/cocktail-scaler"
            className="button-secondary dashboard-action-btn"
          >
            {t('dashboard.batchCalculator')}
          </Link>
        </div>
      </div>

      {/* ── KPI row ── */}
      {kpi && (
        <div className="db-kpi-row">
          <KpiCard
            label={t('dashboard.kpi.todayStaff')}
            value={kpi.todayStaff}
            accent={kpi.todayStaff === 0 ? 'warn' : undefined}
          />
          <KpiCard
            label={t('dashboard.kpi.checklistsWeek')}
            value={`${kpi.clSubmitted}/${kpi.clTotal}`}
            accent={kpi.clSubmitted < kpi.clTotal && kpi.clTotal > 0 ? 'warn' : undefined}
          />
          <KpiCard
            label={t('dashboard.kpi.availability')}
            value={`${kpi.avSubmitted}/${kpi.avTotal}`}
            sub={kpi.avTotal > 0 && kpi.avSubmitted < kpi.avTotal
              ? `${kpi.avTotal - kpi.avSubmitted} ${lang === 'he' ? 'לא שלחו' : 'missing'}`
              : undefined}
            accent={kpi.avTotal > 0 && kpi.avSubmitted < kpi.avTotal ? 'warn' : undefined}
          />
          {ordersTotalFormatted && (
            <KpiCard
              label={t('dashboard.kpi.pendingOrders')}
              value={ordersTotalFormatted}
            />
          )}
        </div>
      )}

      {/* ── Today's shifts + Checklists (side by side) ── */}
      <div className="dashboard-sections" style={{ marginBottom: '1.5rem' }}>
        {/* Today's shifts */}
        <section className="dashboard-section">
          <h3 className="dashboard-section-title">
            {t('dashboard.todayShifts.title')}
          </h3>
          {today_shifts.length === 0 ? (
            <p className="text-muted">{t('dashboard.todayShifts.empty')}</p>
          ) : (
            <ul className="db-shift-list">
              {today_shifts.map((s, i) => (
                <li key={i} className="db-shift-item">
                  <span className="db-shift-time">
                    {s.start_time}–{s.end_time}
                  </span>
                  <span className="db-shift-info">
                    <span className="db-shift-staff">{s.staff_name}</span>
                    <RoleBadge role={s.role} t={t} />
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link
            to="/schedule"
            className="button-secondary"
            style={{ marginTop: '0.75rem', display: 'inline-block', fontSize: '0.85rem' }}
          >
            {t('nav.schedule')}
          </Link>
        </section>

        {/* Checklists this week */}
        <section className="dashboard-section">
          <h3 className="dashboard-section-title">
            {t('dashboard.checklists.title')}
          </h3>
          {checklistByDate.length === 0 ? (
            <p className="text-muted">{t('dashboard.checklists.empty')}</p>
          ) : (
            <table className="db-cl-table">
              <thead>
                <tr>
                  <th>{t('common.from')}</th>
                  <th>{t('dashboard.checklists.opening')}</th>
                  <th>{t('dashboard.checklists.closing')}</th>
                </tr>
              </thead>
              <tbody>
                {checklistByDate.map(([dateStr, runs]) => {
                  const dow = new Date(dateStr + 'T12:00:00').getDay()
                  return (
                    <tr key={dateStr}>
                      <td className="db-cl-date">
                        {dayLabel(dow)} {formatShortDate(dateStr)}
                      </td>
                      <td>
                        {runs.opening ? (
                          <span
                            className={`db-cl-status ${runs.opening.status === 'submitted' ? 'db-cl-status--ok' : 'db-cl-status--wip'}`}
                          >
                            {runs.opening.status === 'submitted'
                              ? `✓ ${runs.opening.submitted_by_name || ''}`
                              : `${runs.opening.completed_items}/${runs.opening.total_items}`}
                          </span>
                        ) : (
                          <span className="db-cl-status db-cl-status--none">—</span>
                        )}
                      </td>
                      <td>
                        {runs.closing ? (
                          <span
                            className={`db-cl-status ${runs.closing.status === 'submitted' ? 'db-cl-status--ok' : 'db-cl-status--wip'}`}
                          >
                            {runs.closing.status === 'submitted'
                              ? `✓ ${runs.closing.submitted_by_name || ''}`
                              : `${runs.closing.completed_items}/${runs.closing.total_items}`}
                          </span>
                        ) : (
                          <span className="db-cl-status db-cl-status--none">—</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          <Link
            to="/checklists/history"
            className="button-secondary"
            style={{ marginTop: '0.75rem', display: 'inline-block', fontSize: '0.85rem' }}
          >
            {t('nav.checklistHistory')}
          </Link>
        </section>
      </div>

      {/* ── Availability next week ── */}
      {availability_next_week.length > 0 && (
        <section className="dashboard-section" style={{ marginBottom: '1.5rem' }}>
          <div className="db-section-header">
            <h3 className="dashboard-section-title" style={{ margin: 0 }}>
              {t('dashboard.availability.title')}
            </h3>
            {target_week_start && (
              <span className="db-section-sub">
                {t('dashboard.availability.targetWeek', {
                  date: formatShortDate(target_week_start),
                })}
              </span>
            )}
          </div>
          <div className="db-av-progress" style={{ marginBottom: '0.75rem' }}>
            <div
              className="db-av-progress-bar"
              style={{
                width: `${availability_next_week.length > 0 ? Math.round((availability_next_week.filter((s) => s.submitted).length / availability_next_week.length) * 100) : 0}%`,
              }}
            />
          </div>
          <div className="db-av-staff-list">
            {availability_next_week.map((s) => (
              <span
                key={s.staff_id}
                className={`db-av-chip ${s.submitted ? 'db-av-chip--ok' : 'db-av-chip--missing'}`}
              >
                {s.display_name}
              </span>
            ))}
          </div>
          <Link
            to="/schedule"
            className="button-secondary"
            style={{ marginTop: '0.75rem', display: 'inline-block', fontSize: '0.85rem' }}
          >
            {t('nav.schedule')}
          </Link>
        </section>
      )}

      {/* ── Week filter ── */}
      <div className="dashboard-filters">
        <button
          type="button"
          className="button-secondary dashboard-nav-btn"
          onClick={goPrevWeek}
          aria-label={t('dashboard.prevWeek')}
        >
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
        <button
          type="button"
          className="button-secondary dashboard-nav-btn"
          onClick={goNextWeek}
          aria-label={t('dashboard.nextWeek')}
        >
          ›
        </button>
        {weekLabel && (
          <span className="dashboard-week-label">{weekLabel}</span>
        )}
      </div>

      {/* ── Events + Orders ── */}
      <div className="dashboard-sections">
        <section className="dashboard-section">
          <h3 className="dashboard-section-title">
            {t('dashboard.thisWeekEvents')}
          </h3>
          {events_data.length === 0 ? (
            <p className="text-muted">{t('dashboard.emptyEvents')}</p>
          ) : (
            <ul
              className="dashboard-list"
              style={{ listStyle: 'none', padding: 0, margin: 0 }}
            >
              {events_data.map((ev) => (
                <li key={ev.id} className="dashboard-item">
                  <Link to={`/events/${ev.id}`} className="dashboard-link">
                    <span className="dashboard-item-name">
                      {ev.event_name || t('events.unnamed')}
                    </span>
                    <span className="dashboard-item-meta">
                      {formatDate(ev.event_date, lang)} •{' '}
                      {t('dashboard.people', { count: ev.people })}
                      {ev.cocktail_names?.filter(Boolean).length > 0 && (
                        <> • {ev.cocktail_names.filter(Boolean).join(', ')}</>
                      )}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link
            to="/events"
            className="button-primary"
            style={{ marginTop: '0.75rem', display: 'inline-block' }}
          >
            {t('dashboard.viewEvents')}
          </Link>
        </section>

        <section className="dashboard-section">
          <h3 className="dashboard-section-title">
            {t('dashboard.thisWeekOrders')}
          </h3>
          {orders_total_minor > 0 && (
            <p className="dashboard-orders-total">
              {t('dashboard.ordersTotal')}:{' '}
              <strong>{ordersTotalFormatted}</strong>
            </p>
          )}
          {orders_data.length === 0 ? (
            <p className="text-muted">{t('dashboard.emptyOrders')}</p>
          ) : (
            <ul
              className="dashboard-list"
              style={{ listStyle: 'none', padding: 0, margin: 0 }}
            >
              {orders_data.map((ord) => (
                <li key={ord.id} className="dashboard-item">
                  <Link to="/orders" className="dashboard-link">
                    <span className="dashboard-item-name">
                      {ord.supplier || t('orders.supplier.unknown')}
                    </span>
                    <span className="dashboard-item-meta">
                      {t(`orders.status.${ord.status || 'DRAFT'}`)} •{' '}
                      {formatDate(ord.period_start, lang)}–
                      {formatDate(ord.period_end, lang)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link
            to="/orders"
            className="button-primary"
            style={{ marginTop: '0.75rem', display: 'inline-block' }}
          >
            {t('dashboard.viewOrders')}
          </Link>
        </section>
      </div>
    </div>
  )
}

export default DashboardPage
