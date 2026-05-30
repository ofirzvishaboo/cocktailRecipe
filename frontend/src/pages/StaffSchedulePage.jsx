import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import {
  DAY_KEYS,
  formatShortDateFromIso,
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

export default function StaffSchedulePage() {
  const {
    isAuthenticated,
    staffProfile,
    hasStaffProfile,
    loading: authLoading,
    fetchStaffProfile,
  } = useAuth()
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()

  const activeTab = searchParams.get('tab') === 'availability' ? 'availability' : 'schedule'
  const setTab = (tab) => setSearchParams(tab === 'schedule' ? {} : { tab })

  // ── Schedule tab ───────────────────────────────────────────────────
  const [weekDate, setWeekDate] = useState(() => getSunday(new Date()))
  const [schedule, setSchedule] = useState(null)
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [scheduleError, setScheduleError] = useState('')

  const weekStartStr = useMemo(() => toLocalDateStr(weekDate), [weekDate])
  const myStaffId = staffProfile?.staff_id ? String(staffProfile.staff_id) : null

  const loadSchedule = useCallback(
    async (weekStr) => {
      try {
        setScheduleLoading(true)
        setScheduleError('')
        const res = await api.get(`/schedule/weeks/public?week_start=${weekStr}`)
        setSchedule(res.data)
      } catch (e) {
        console.error(e)
        setScheduleError(t('schedule.errors.loadFailed'))
      } finally {
        setScheduleLoading(false)
      }
    },
    [t],
  )

  useEffect(() => {
    if (!isAuthenticated) return
    loadSchedule(weekStartStr)
  }, [isAuthenticated, weekStartStr, loadSchedule])

  // ── Availability tab ───────────────────────────────────────────────
  const [weekStartStrAv, setWeekStartStrAv] = useState('')
  const [meta, setMeta] = useState(null)
  const [days, setDays] = useState([])
  const [saving, setSaving] = useState(false)
  const [avError, setAvError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (isAuthenticated && !hasStaffProfile && !authLoading) {
      fetchStaffProfile?.()
    }
  }, [isAuthenticated, hasStaffProfile, authLoading, fetchStaffProfile])

  const loadMeta = useCallback(async (weekStr) => {
    try {
      const url = weekStr
        ? `/schedule/weeks/current/meta?week_start=${weekStr}`
        : '/schedule/weeks/current/meta'
      const res = await api.get(url)
      setMeta(res.data)
      return res.data
    } catch (e) {
      console.error(e)
      return null
    }
  }, [])

  const loadAvailability = useCallback(
    async (weekStr) => {
      if (!staffProfile?.staff_id || !weekStr) return
      try {
        setAvError('')
        const res = await api.get(
          `/schedule/weeks/current/availability?week_start=${weekStr}`,
        )
        setDays(res.data || [])
      } catch (e) {
        console.error(e)
        setAvError(t('schedule.errors.loadFailed'))
      }
    },
    [staffProfile?.staff_id, t],
  )

  useEffect(() => {
    if (!staffProfile?.staff_id) return
    loadMeta().then((data) => {
      if (data?.default_week_start) {
        setWeekStartStrAv(data.default_week_start)
        loadAvailability(data.default_week_start)
      }
    })
  }, [staffProfile?.staff_id, loadMeta, loadAvailability])

  const toggleDay = (dayOfWeek, available) => {
    if (!meta?.can_submit) return
    setDays((prev) =>
      prev.map((d) => (d.day_of_week === dayOfWeek ? { ...d, available } : d)),
    )
    setSaved(false)
  }

  const setNotes = (dayOfWeek, notes) => {
    if (!meta?.can_submit) return
    setDays((prev) =>
      prev.map((d) => (d.day_of_week === dayOfWeek ? { ...d, notes } : d)),
    )
    setSaved(false)
  }

  const saveAvailability = async () => {
    if (!staffProfile?.staff_id || !meta?.can_submit || !weekStartStrAv) return
    try {
      setSaving(true)
      setAvError('')
      await api.put(
        `/schedule/weeks/current/availability?week_start=${weekStartStrAv}`,
        {
          entries: days.map((d) => ({
            staff_id: staffProfile.staff_id,
            day_of_week: d.day_of_week,
            available: d.available,
            notes: d.notes || null,
          })),
        },
      )
      setSaved(true)
      await loadMeta(weekStartStrAv)
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setAvError(
        detail ? String(detail) : t('schedule.errors.saveAvailabilityFailed'),
      )
    } finally {
      setSaving(false)
    }
  }

  // ── Schedule navigation ────────────────────────────────────────────
  const prevWeek = () =>
    setWeekDate((d) => {
      const p = new Date(d)
      p.setDate(p.getDate() - 7)
      return p
    })
  const nextWeek = () =>
    setWeekDate((d) => {
      const n = new Date(d)
      n.setDate(n.getDate() + 7)
      return n
    })
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

  // ── Guards ─────────────────────────────────────────────────────────
  if (authLoading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />

  const canEdit = meta?.can_submit !== false
  const isNotCreated = schedule?.status === 'not_created'
  const isPublished = schedule?.status === 'published'
  const totalAssignments = schedule?.assignments?.length ?? 0
  const hasPendingAvailability = meta?.can_submit && !meta?.submitted

  return (
    <div className="card schedule-staff-page">
      {/* ── Tab bar ── */}
      <div className="schedule-staff-tabs">
        <button
          type="button"
          className={`schedule-staff-tab ${activeTab === 'schedule' ? 'active' : ''}`}
          onClick={() => setTab('schedule')}
        >
          {t('schedule.weekly.tabSchedule')}
        </button>
        <button
          type="button"
          className={`schedule-staff-tab ${activeTab === 'availability' ? 'active' : ''}`}
          onClick={() => setTab('availability')}
        >
          {t('schedule.weekly.tabAvailability')}
          {hasPendingAvailability && (
            <span className="schedule-staff-tab-dot" aria-hidden />
          )}
        </button>
      </div>

      {/* ── SCHEDULE TAB ── */}
      {activeTab === 'schedule' && (
        <div className="schedule-staff-tab-content">
          <div className="schedule-header">
            <h2 style={{ margin: 0 }}>{t('schedule.weekly.title')}</h2>
            <div className="schedule-week-nav">
              <button
                type="button"
                className="schedule-week-nav-btn"
                onClick={prevWeek}
                aria-label={t('schedule.weekly.prevWeek')}
              >
                ‹
              </button>
              <span className="schedule-week-nav-label">
                {formatWeekRange(weekDate)}
              </span>
              <button
                type="button"
                className="schedule-week-nav-btn"
                onClick={nextWeek}
                aria-label={t('schedule.weekly.nextWeek')}
              >
                ›
              </button>
              <button
                type="button"
                className="button-secondary schedule-week-nav-today"
                onClick={goToThisWeek}
              >
                {t('schedule.thisWeek')}
              </button>
            </div>
          </div>

          {schedule?.status && !isNotCreated && (
            <span
              className={`schedule-status ${isPublished ? 'published' : ''}`}
              style={{ display: 'inline-block', margin: '0.75rem 0' }}
            >
              {t(`schedule.status.${schedule.status}`, {
                defaultValue: schedule.status,
              })}
            </span>
          )}

          {myStaffId && myDays.size > 0 && (
            <div className="schedule-my-summary">
              {t('schedule.weekly.myShiftsCount', { count: myDays.size })}
            </div>
          )}

          {scheduleError && <p className="error-text">{scheduleError}</p>}
          {scheduleLoading && (
            <p className="text-muted">{t('common.loading')}</p>
          )}

          {!scheduleLoading && isNotCreated && (
            <p className="text-muted schedule-weekly-empty">
              {t('schedule.weekly.notCreated')}
            </p>
          )}
          {!scheduleLoading &&
            !isNotCreated &&
            !isPublished &&
            totalAssignments === 0 && (
              <p className="text-muted schedule-weekly-empty">
                {t('schedule.weekly.notPublished')}
              </p>
            )}

          {!scheduleLoading &&
            schedule &&
            !isNotCreated &&
            (totalAssignments > 0 || isPublished) && (
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
                      ]
                        .filter(Boolean)
                        .join(' ')}
                    >
                      <h4 className="schedule-day-card-header">
                        <span>{t(`schedule.days.${key}`)}</span>
                        <span className="schedule-day-date">
                          {dayLabel(weekDate, day)}
                        </span>
                        {hasMyShift && (
                          <span className="schedule-my-shift-badge">
                            {t('schedule.weekly.myShift')}
                          </span>
                        )}
                      </h4>
                      {isClosed ? (
                        <p
                          className="text-muted"
                          style={{ margin: 0, fontSize: '0.9rem' }}
                        >
                          {t('schedule.closedSaturday')}
                        </p>
                      ) : dayAssignments.length === 0 ? (
                        <p
                          className="text-muted"
                          style={{ margin: 0, fontSize: '0.9rem' }}
                        >
                          {t('schedule.noShifts')}
                        </p>
                      ) : (
                        <ul className="schedule-public-assignments">
                          {dayAssignments.map((a, i) => {
                            const isMe =
                              myStaffId &&
                              String(a.staff_id) === myStaffId
                            return (
                              <li
                                key={i}
                                className={[
                                  'schedule-public-assignment',
                                  isMe
                                    ? 'schedule-public-assignment--mine'
                                    : '',
                                ]
                                  .filter(Boolean)
                                  .join(' ')}
                              >
                                <span className="schedule-public-shift-time">
                                  {formatTime(a.start_time)}–
                                  {formatTime(a.end_time)}
                                </span>
                                <span className="schedule-public-shift-info">
                                  <span className="schedule-public-shift-name">
                                    {a.shift_name}
                                  </span>
                                  <span
                                    className={`schedule-public-staff-name ${isMe ? 'schedule-public-staff-name--mine' : ''}`}
                                  >
                                    {a.staff_name}
                                  </span>
                                  <span className="schedule-public-role">
                                    {t(`schedule.roles.${a.role}`, {
                                      defaultValue: a.role,
                                    })}
                                  </span>
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
      )}

      {/* ── AVAILABILITY TAB ── */}
      {activeTab === 'availability' && (
        <div className="schedule-staff-tab-content">
          {!hasStaffProfile ? (
            <>
              <h2>{t('schedule.availability.title')}</h2>
              <p>{t('schedule.availability.noProfile')}</p>
              <Link to="/">{t('schedule.availability.backHome')}</Link>
            </>
          ) : (
            <>
              <h2 style={{ marginTop: 0 }}>{t('schedule.availability.title')}</h2>
              <p className="text-muted">
                {t('schedule.availability.greeting', {
                  name: staffProfile.display_name,
                  role: t(`schedule.roles.${staffProfile.role}`),
                })}
              </p>
              <p className="schedule-deadline-banner">
                {t('schedule.availability.deadline', {
                  date: formatShortDateFromIso(meta?.availability_deadline),
                })}
              </p>

              {meta?.submitted && (
                <p className="schedule-submitted-badge">
                  {t('schedule.availability.alreadySubmitted')}
                </p>
              )}
              {!canEdit && (
                <p className="schedule-gaps">
                  {t('schedule.availability.deadlinePassed')}
                </p>
              )}
              {avError && <p className="error-text">{avError}</p>}
              {saved && canEdit && (
                <p style={{ color: 'green' }}>
                  {t('schedule.availability.saved')}
                </p>
              )}

              <div className="schedule-availability-cards">
                {DAY_KEYS.map((key, day) => (
                  <div key={key} className="schedule-avail-day-card">
                    <label>
                      <input
                        type="checkbox"
                        checked={
                          days.find((d) => d.day_of_week === day)?.available ??
                          false
                        }
                        disabled={day === 6 || !canEdit}
                        onChange={(e) => toggleDay(day, e.target.checked)}
                      />
                      {t(`schedule.days.${key}`)}
                      {day === 6 && (
                        <span className="text-muted">
                          {' '}
                          ({t('schedule.closedSaturday')})
                        </span>
                      )}
                    </label>
                    {day !== 6 && (
                      <input
                        type="text"
                        className="schedule-avail-notes input"
                        placeholder={t('schedule.availability.notesPlaceholder')}
                        value={
                          days.find((d) => d.day_of_week === day)?.notes || ''
                        }
                        disabled={!canEdit}
                        onChange={(e) => setNotes(day, e.target.value)}
                      />
                    )}
                  </div>
                ))}
              </div>

              <button
                type="button"
                className="button-primary"
                style={{ marginTop: '1rem', width: '100%' }}
                onClick={saveAvailability}
                disabled={saving || !canEdit}
              >
                {saving
                  ? t('common.saving')
                  : t('schedule.availability.submit')}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
