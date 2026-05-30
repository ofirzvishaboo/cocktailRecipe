import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import {
  DAY_KEYS,
  formatTime,
  getSunday,
  toLocalDateStr,
} from '../utils/schedule'
import '../styles/schedule.css'

function dayLabel(weekDate, dayIndex) {
  const d = new Date(weekDate)
  d.setDate(d.getDate() + dayIndex)
  return `${d.getDate()}/${d.getMonth() + 1}`
}

function formatWeekRange(weekDate) {
  const start = new Date(weekDate)
  const end = new Date(weekDate)
  end.setDate(end.getDate() + 5)
  return `${start.getDate()}/${start.getMonth() + 1} – ${end.getDate()}/${end.getMonth() + 1}`
}

export default function MySchedulePage() {
  const { isAuthenticated, staffProfile, loading: authLoading } = useAuth()
  const { t } = useTranslation()

  const [weekDate, setWeekDate] = useState(() => getSunday(new Date()))
  const [schedule, setSchedule] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const weekStartStr = useMemo(() => toLocalDateStr(weekDate), [weekDate])
  const myStaffId = staffProfile?.staff_id ? String(staffProfile.staff_id) : null

  const loadSchedule = useCallback(async (weekStr) => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get(`/schedule/weeks/public?week_start=${weekStr}`)
      setSchedule(res.data)
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    if (!isAuthenticated) return
    loadSchedule(weekStartStr)
  }, [isAuthenticated, weekStartStr, loadSchedule])

  const prevWeek = () => {
    setWeekDate((d) => {
      const prev = new Date(d)
      prev.setDate(prev.getDate() - 7)
      return prev
    })
  }

  const nextWeek = () => {
    setWeekDate((d) => {
      const next = new Date(d)
      next.setDate(next.getDate() + 7)
      return next
    })
  }

  const goToThisWeek = () => setWeekDate(getSunday(new Date()))

  const assignmentsForDay = (day) =>
    (schedule?.assignments || []).filter((a) => a.day_of_week === day)

  const myDays = useMemo(() => {
    if (!myStaffId || !schedule) return new Set()
    return new Set(
      (schedule.assignments || [])
        .filter((a) => String(a.staff_id) === myStaffId)
        .map((a) => a.day_of_week),
    )
  }, [myStaffId, schedule])

  if (authLoading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />

  const isNotCreated = schedule?.status === 'not_created'
  const isPublished = schedule?.status === 'published'
  const totalAssignments = schedule?.assignments?.length ?? 0

  return (
    <div className="card schedule-page">
      <div className="schedule-header">
        <h2>{t('schedule.weekly.title')}</h2>
        <div className="schedule-week-nav">
          <button type="button" className="schedule-week-nav-btn" onClick={prevWeek} aria-label={t('schedule.weekly.prevWeek')}>
            ‹
          </button>
          <span className="schedule-week-nav-label">{formatWeekRange(weekDate)}</span>
          <button type="button" className="schedule-week-nav-btn" onClick={nextWeek} aria-label={t('schedule.weekly.nextWeek')}>
            ›
          </button>
          <button type="button" className="button-secondary schedule-week-nav-today" onClick={goToThisWeek}>
            {t('schedule.thisWeek')}
          </button>
        </div>
      </div>

      {schedule?.status && !isNotCreated && (
        <span className={`schedule-status ${isPublished ? 'published' : ''}`} style={{ display: 'inline-block', marginBottom: '1rem' }}>
          {t(`schedule.status.${schedule.status}`, { defaultValue: schedule.status })}
        </span>
      )}

      {myStaffId && myDays.size > 0 && (
        <div className="schedule-my-summary">
          <span className="schedule-my-summary-icon">📅</span>
          <span>
            {t('schedule.weekly.myShiftsCount', { count: myDays.size })}
          </span>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {loading && <p className="text-muted">{t('common.loading')}</p>}

      {!loading && isNotCreated && (
        <p className="text-muted schedule-weekly-empty">{t('schedule.weekly.notCreated')}</p>
      )}

      {!loading && !isNotCreated && !isPublished && totalAssignments === 0 && (
        <p className="text-muted schedule-weekly-empty">{t('schedule.weekly.notPublished')}</p>
      )}

      {!loading && schedule && !isNotCreated && (totalAssignments > 0 || isPublished) && (
        <div className="schedule-days-grid">
          {DAY_KEYS.map((key, day) => {
            const isClosed = day === 6
            const dayAssignments = assignmentsForDay(day)
            const hasMyShift = myDays.has(day)

            return (
              <div
                key={key}
                className={[
                  'schedule-day-card',
                  isClosed ? 'closed' : '',
                  hasMyShift ? 'schedule-day-card--mine' : '',
                ].filter(Boolean).join(' ')}
              >
                <h4 className="schedule-day-card-header">
                  <span>{t(`schedule.days.${key}`)}</span>
                  <span className="schedule-day-date">{dayLabel(weekDate, day)}</span>
                  {hasMyShift && (
                    <span className="schedule-my-shift-badge">{t('schedule.weekly.myShift')}</span>
                  )}
                </h4>

                {isClosed ? (
                  <p className="text-muted" style={{ margin: 0, fontSize: '0.9rem' }}>
                    {t('schedule.closedSaturday')}
                  </p>
                ) : dayAssignments.length === 0 ? (
                  <p className="text-muted" style={{ margin: 0, fontSize: '0.9rem' }}>
                    {t('schedule.noShifts')}
                  </p>
                ) : (
                  <ul className="schedule-public-assignments">
                    {dayAssignments.map((a, i) => {
                      const isMe = myStaffId && String(a.staff_id) === myStaffId
                      return (
                        <li
                          key={i}
                          className={['schedule-public-assignment', isMe ? 'schedule-public-assignment--mine' : ''].filter(Boolean).join(' ')}
                        >
                          <span className="schedule-public-shift-time">
                            {formatTime(a.start_time)}–{formatTime(a.end_time)}
                          </span>
                          <span className="schedule-public-shift-info">
                            <span className="schedule-public-shift-name">{a.shift_name}</span>
                            <span className={`schedule-public-staff-name ${isMe ? 'schedule-public-staff-name--mine' : ''}`}>
                              {a.staff_name}
                            </span>
                            <span className="schedule-public-role">{t(`schedule.roles.${a.role}`, { defaultValue: a.role })}</span>
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
