import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import {
  DAY_KEYS,
  formatShortDateFromIso,
  toLocalDateStr,
} from '../utils/schedule'
import '../styles/schedule.css'

export default function ScheduleAvailabilityPage() {
  const { isAuthenticated, staffProfile, hasStaffProfile, loading: authLoading, fetchStaffProfile } = useAuth()
  const { t } = useTranslation()

  const profile = staffProfile
  const profileLoading = authLoading
  const [weekStartStr, setWeekStartStr] = useState('')
  const [meta, setMeta] = useState(null)
  const [days, setDays] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
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

  const loadAvailability = useCallback(async (weekStr) => {
    if (!profile?.staff_id || !weekStr) return
    try {
      setError('')
      const res = await api.get(`/schedule/weeks/current/availability?week_start=${weekStr}`)
      setDays(res.data || [])
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.loadFailed'))
    }
  }, [profile?.staff_id, t])

  useEffect(() => {
    if (!profile?.staff_id) return
    loadMeta().then((data) => {
      if (data?.default_week_start) {
        setWeekStartStr(data.default_week_start)
        loadAvailability(data.default_week_start)
      }
    })
  }, [profile?.staff_id, loadMeta, loadAvailability])

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

  const save = async () => {
    if (!profile?.staff_id || !meta?.can_submit || !weekStartStr) return
    try {
      setSaving(true)
      setError('')
      await api.put(`/schedule/weeks/current/availability?week_start=${weekStartStr}`, {
        entries: days.map((d) => ({
          staff_id: profile.staff_id,
          day_of_week: d.day_of_week,
          available: d.available,
          notes: d.notes || null,
        })),
      })
      setSaved(true)
      await loadMeta(weekStartStr)
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setError(detail ? String(detail) : t('schedule.errors.saveAvailabilityFailed'))
    } finally {
      setSaving(false)
    }
  }

  const canEdit = meta?.can_submit !== false

  if (authLoading || profileLoading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!profile) {
    return (
      <div className="card">
        <h2>{t('schedule.availability.title')}</h2>
        <p>{t('schedule.availability.noProfile')}</p>
        <Link to="/">{t('schedule.availability.backHome')}</Link>
      </div>
    )
  }

  return (
    <div className="card schedule-availability-page">
      <h2>{t('schedule.availability.title')}</h2>
      <p className="text-muted">
        {t('schedule.availability.greeting', { name: profile.display_name, role: t(`schedule.roles.${profile.role}`) })}
      </p>
      <p className="schedule-deadline-banner">
        {t('schedule.availability.deadline', {
          date: formatShortDateFromIso(meta?.availability_deadline),
        })}
      </p>

      {meta?.submitted && (
        <p className="schedule-submitted-badge">{t('schedule.availability.alreadySubmitted')}</p>
      )}

      {!canEdit && (
        <p className="schedule-gaps">{t('schedule.availability.deadlinePassed')}</p>
      )}

      {error && <p className="error-text">{error}</p>}
      {saved && canEdit && <p style={{ color: 'green' }}>{t('schedule.availability.saved')}</p>}

      <div className="schedule-availability-cards">
        {DAY_KEYS.map((key, day) => (
          <div key={key} className="schedule-avail-day-card">
            <label>
              <input
                type="checkbox"
                checked={days.find((d) => d.day_of_week === day)?.available ?? false}
                disabled={day === 6 || !canEdit}
                onChange={(e) => toggleDay(day, e.target.checked)}
              />
              {t(`schedule.days.${key}`)}
              {day === 6 && (
                <span className="text-muted"> ({t('schedule.closedSaturday')})</span>
              )}
            </label>
            {day !== 6 && (
              <input
                type="text"
                className="schedule-avail-notes input"
                placeholder={t('schedule.availability.notesPlaceholder')}
                value={days.find((d) => d.day_of_week === day)?.notes || ''}
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
        onClick={save}
        disabled={saving || !canEdit}
      >
        {saving ? t('common.saving') : t('schedule.availability.submit')}
      </button>
    </div>
  )
}
