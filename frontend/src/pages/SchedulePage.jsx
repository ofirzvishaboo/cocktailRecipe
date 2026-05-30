import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import DatePicker, { registerLocale } from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import he from 'date-fns/locale/he'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import {
  DAY_KEYS,
  formatShortDate,
  formatTime,
  getSunday,
  templateAllowedOnDay,
  toLocalDateStr,
} from '../utils/schedule'
import '../styles/schedule.css'

registerLocale('he', he)

const ROLES = ['bartender', 'cleaner', 'manager']

export default function SchedulePage() {
  const { isAdmin, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [weekDate, setWeekDate] = useState(() => getSunday(new Date()))
  const [week, setWeek] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [gaps, setGaps] = useState([])

  const [newStaffName, setNewStaffName] = useState('')
  const [newStaffRole, setNewStaffRole] = useState('bartender')
  const [newStaffUserId, setNewStaffUserId] = useState('')
  const [appUsers, setAppUsers] = useState([])

  const weekStartStr = useMemo(() => toLocalDateStr(weekDate), [weekDate])

  const loadAppUsers = useCallback(async () => {
    try {
      const res = await api.get('/schedule/users')
      setAppUsers(res.data || [])
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    loadAppUsers()
  }, [isAdmin, loadAppUsers])

  const userDisplayName = (u) => {
    const parts = [(u.first_name || '').trim(), (u.last_name || '').trim()].filter(Boolean)
    if (parts.length) return parts.join(' ')
    return u.email
  }

  const loadOrCreateWeek = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const from = weekStartStr
      const to = weekStartStr
      const listRes = await api.get(`/schedule/weeks?from_date=${from}&to_date=${to}`)
      let w = (listRes.data || [])[0]
      if (!w) {
        const createRes = await api.post('/schedule/weeks', { week_start: weekStartStr })
        w = createRes.data
      } else {
        const detailRes = await api.get(`/schedule/weeks/${w.id}`)
        w = detailRes.data
      }
      setWeek(w)
      setGaps(w.gaps || [])
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [weekStartStr, t])

  useEffect(() => {
    if (!isAdmin) return
    loadOrCreateWeek()
  }, [isAdmin, loadOrCreateWeek])

  const setAvailability = async (staffId, dayOfWeek, available) => {
    if (!week?.id) return
    try {
      await api.put(`/schedule/weeks/${week.id}/availability`, {
        entries: [{ staff_id: staffId, day_of_week: dayOfWeek, available, notes: null }],
      })
      setWeek((prev) => {
        if (!prev) return prev
        const availability = [...(prev.availability || [])]
        const idx = availability.findIndex(
          (a) => a.staff_id === staffId && a.day_of_week === dayOfWeek,
        )
        const staff = (prev.staff || []).find((s) => s.id === staffId)
        const row = {
          staff_id: staffId,
          staff_name: staff?.display_name || '',
          role: staff?.role || '',
          day_of_week: dayOfWeek,
          available,
          notes: null,
        }
        if (idx >= 0) availability[idx] = { ...availability[idx], ...row }
        else availability.push(row)
        return { ...prev, availability }
      })
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setError(detail ? String(detail) : t('schedule.errors.saveAvailabilityFailed'))
    }
  }

  const isAvailable = (staffId, day) => {
    const row = (week?.availability || []).find(
      (a) => a.staff_id === staffId && a.day_of_week === day,
    )
    return row?.available ?? false
  }

  const forceSetAllAvailable = async (staffId) => {
    if (!week?.id) return
    try {
      const entries = [0, 1, 2, 3, 4, 5].map((day) => ({
        staff_id: staffId,
        day_of_week: day,
        available: true,
        notes: null,
      }))
      const res = await api.put(`/schedule/weeks/${week.id}/availability?force=true`, { entries })
      setWeek((prev) => {
        if (!prev) return prev
        const staffMember = (prev.staff || []).find((s) => s.id === staffId)
        const kept = (prev.availability || []).filter((a) => a.staff_id !== staffId)
        const forced = [0, 1, 2, 3, 4, 5].map((day) => ({
          staff_id: staffId,
          staff_name: staffMember?.display_name || '',
          role: staffMember?.role || '',
          day_of_week: day,
          available: true,
          notes: null,
        }))
        const updatedSubs = (prev.submission_status || []).map((s) =>
          s.staff_id === staffId ? { ...s, submitted: true } : s,
        )
        return { ...prev, availability: [...kept, ...forced], submission_status: updatedSubs }
      })
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setError(detail ? String(detail) : t('schedule.errors.saveAvailabilityFailed'))
    }
  }

  const addStaff = async (e) => {
    e.preventDefault()
    if (!newStaffName.trim()) return
    try {
      setError('')
      await api.post('/schedule/staff', {
        display_name: newStaffName.trim(),
        role: newStaffRole,
        user_id: newStaffUserId.trim() || undefined,
      })
      setNewStaffName('')
      setNewStaffUserId('')
      await loadOrCreateWeek()
      await loadAppUsers()
    } catch (err) {
      console.error(err)
      setError(t('schedule.errors.saveStaffFailed'))
    }
  }

  const updateStaffLink = async (staffId, userId) => {
    try {
      setError('')
      await api.put(`/schedule/staff/${staffId}`, {
        user_id: userId || null,
      })
      await loadOrCreateWeek()
      await loadAppUsers()
    } catch (err) {
      console.error(err)
      const detail = err?.response?.data?.detail
      setError(detail ? String(detail) : t('schedule.errors.saveStaffFailed'))
    }
  }

  const usersForStaffLink = (currentStaffId, currentUserId) => {
    const linkedElsewhere = new Set(
      (week?.staff || [])
        .filter((s) => s.id !== currentStaffId && s.user_id)
        .map((s) => s.user_id),
    )
    return appUsers.filter(
      (u) => u.id === currentUserId || !linkedElsewhere.has(u.id),
    )
  }

  const removeStaff = async (staff) => {
    if (!staff?.id) return
    const ok = window.confirm(t('schedule.confirmRemoveStaff', { name: staff.display_name }))
    if (!ok) return
    try {
      setError('')
      await api.delete(`/schedule/staff/${staff.id}`)
      await loadOrCreateWeek()
    } catch (err) {
      console.error(err)
      setError(t('schedule.errors.removeStaffFailed'))
    }
  }

  const missingSelfSubmissions = useMemo(() => {
    return (week?.submission_status || []).filter((s) => s.must_self_submit && !s.submitted)
  }, [week?.submission_status])

  const generate = async () => {
    if (!week?.id) return
    if (missingSelfSubmissions.length > 0) {
      const names = missingSelfSubmissions.map((s) => s.display_name).join(', ')
      const ok = window.confirm(t('schedule.confirmGenerateMissing', { names }))
      if (!ok) return
    }
    try {
      setLoading(true)
      setError('')
      const res = await api.post(`/schedule/weeks/${week.id}/generate`)
      setGaps(res.data?.gaps || [])
      await loadOrCreateWeek()
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.generateFailed'))
    } finally {
      setLoading(false)
    }
  }

  const publish = async () => {
    if (!week?.id) return
    try {
      setLoading(true)
      const res = await api.post(`/schedule/weeks/${week.id}/publish`)
      setWeek(res.data)
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.publishFailed'))
    } finally {
      setLoading(false)
    }
  }

  const shareSchedule = async () => {
    if (!week?.id) return
    try {
      const res = await api.get(`/schedule/weeks/${week.id}/share-text?lang=${lang}`)
      const text = res.data?.text || ''
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        window.prompt(t('schedule.actions.share'), text)
      }
      const encoded = encodeURIComponent(text)
      const isMobile = /iPhone|iPad|Android/i.test(navigator.userAgent)
      if (isMobile) {
        window.open(`https://wa.me/?text=${encoded}`, '_blank', 'noopener')
      } else if (window.confirm(t('schedule.shareCopiedOpenWhatsApp'))) {
        window.open(`https://wa.me/?text=${encoded}`, '_blank', 'noopener')
      }
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.shareFailed'))
    }
  }

  const patchAssignment = async (dayOfWeek, shiftTemplateId, staffId) => {
    if (!week?.id) return
    try {
      await api.put(`/schedule/weeks/${week.id}/assignments`, {
        day_of_week: dayOfWeek,
        shift_template_id: shiftTemplateId,
        staff_id: staffId || null,
      })
      await loadOrCreateWeek()
    } catch (e) {
      console.error(e)
      setError(t('schedule.errors.saveAssignmentFailed'))
    }
  }

  const assignmentsForSlot = (day, templateId) =>
    (week?.assignments || []).filter(
      (a) => a.day_of_week === day && a.shift_template_id === templateId,
    )

  const dayLabel = (dayIndex) => {
    const d = new Date(weekDate)
    d.setDate(d.getDate() + dayIndex)
    return `${t(`schedule.days.${DAY_KEYS[dayIndex]}`)} ${d.getDate()}/${d.getMonth() + 1}`
  }

  const templates = week?.templates || []
  const deadlineLabel = week?.availability_deadline
    ? (() => {
        const [y, m, d] = week.availability_deadline.split('-').map(Number)
        return formatShortDate(new Date(y, m - 1, d))
      })()
    : null

  const submissionByStaff = useMemo(() => {
    const m = {}
    for (const s of week?.submission_status || []) {
      m[s.staff_id] = s
    }
    return m
  }, [week?.submission_status])

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/" replace />

  return (
    <div className="card schedule-page">
      <div className="schedule-header">
        <h2>{t('schedule.title')}</h2>
        <div className="schedule-actions">
          {week?.status && (
            <span className={`schedule-status ${week.status === 'published' ? 'published' : ''}`}>
              {t(`schedule.status.${week.status}`)}
            </span>
          )}
          <button type="button" className="button-secondary" onClick={generate} disabled={loading}>
            {t('schedule.actions.generate')}
          </button>
          <button type="button" className="button-primary" onClick={publish} disabled={loading}>
            {t('schedule.actions.publish')}
          </button>
          <button type="button" className="button-secondary" onClick={shareSchedule} disabled={!week?.id}>
            {t('schedule.actions.share')}
          </button>
        </div>
      </div>

      <p className="text-muted" style={{ marginTop: 0 }}>{t('schedule.subtitle')}</p>

      <div className="schedule-week-picker">
        <label>
          {t('schedule.weekOf')}
          <DatePicker
            selected={weekDate}
            onChange={(d) => d && setWeekDate(getSunday(d))}
            locale={lang === 'he' ? 'he' : undefined}
            dateFormat="dd/MM/yyyy"
            className="input"
          />
        </label>
        <button type="button" className="button-secondary" onClick={() => setWeekDate(getSunday(new Date()))}>
          {t('schedule.thisWeek')}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {gaps.length > 0 && (
        <div className="schedule-gaps">
          <strong>{t('schedule.gapsTitle')}</strong>
          <ul>
            {gaps.map((g, i) => (
              <li key={i}>
                {dayLabel(g.day_of_week)} — {t(`schedule.roles.${g.role}`)}: {t(`schedule.gapReasons.${g.reason}`, { defaultValue: g.reason })}
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && !week && <p>{t('common.loading')}</p>}

      {week && (
        <>
          <section className="schedule-section">
            <h3>{t('schedule.rosterTitle')}</h3>
            <form className="schedule-roster-form" onSubmit={addStaff}>
              <label>
                {t('schedule.fields.name')}
                <input value={newStaffName} onChange={(e) => setNewStaffName(e.target.value)} required />
              </label>
              <label>
                {t('schedule.fields.role')}
                <select value={newStaffRole} onChange={(e) => setNewStaffRole(e.target.value)}>
                  {ROLES.map((r) => (
                    <option key={r} value={r}>{t(`schedule.roles.${r}`)}</option>
                  ))}
                </select>
              </label>
              <label>
                {t('schedule.fields.linkUser')}
                <select
                  value={newStaffUserId}
                  onChange={(e) => setNewStaffUserId(e.target.value)}
                >
                  <option value="">{t('schedule.fields.noLinkedUser')}</option>
                  {usersForStaffLink(null, newStaffUserId || null).map((u) => (
                    <option key={u.id} value={u.id}>
                      {userDisplayName(u)} ({u.email})
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className="button-primary">{t('schedule.actions.addStaff')}</button>
            </form>
            <div className="schedule-staff-list">
              {(week.staff || []).map((s) => (
                <div key={s.id} className="schedule-staff-chip">
                  <span className="schedule-staff-chip-label">
                    {s.display_name}
                    <span className="role">{t(`schedule.roles.${s.role}`)}</span>
                  </span>
                  <select
                    className="schedule-staff-link-select"
                    value={s.user_id || ''}
                    onChange={(e) => updateStaffLink(s.id, e.target.value || null)}
                    aria-label={t('schedule.fields.linkUser')}
                  >
                    <option value="">{t('schedule.fields.noLinkedUser')}</option>
                    {usersForStaffLink(s.id, s.user_id).map((u) => (
                      <option key={u.id} value={u.id}>
                        {userDisplayName(u)} ({u.email})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="schedule-staff-remove"
                    onClick={() => removeStaff(s)}
                    aria-label={t('schedule.actions.removeStaff', { name: s.display_name })}
                    title={t('schedule.actions.removeStaff', { name: s.display_name })}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="schedule-section">
            <h3>{t('schedule.availabilityTitle')}</h3>
            {deadlineLabel && (
              <p className="schedule-deadline-banner">
                {t('schedule.availabilityDeadline', { date: deadlineLabel })}
              </p>
            )}
            <p className="text-muted" style={{ marginTop: 0 }}>{t('schedule.availabilitySelfOnly')}</p>
            <div className="schedule-availability-wrap">
              <table className="schedule-availability-table">
                <thead>
                  <tr>
                    <th>{t('schedule.fields.staff')}</th>
                    <th>{t('schedule.fields.submitted')}</th>
                    {DAY_KEYS.map((k) => (
                      <th key={k}>{t(`schedule.days.${k}`)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(week.staff || []).map((s) => {
                    const sub = submissionByStaff[s.id]
                    const selfOnly = !!s.user_id
                    return (
                      <tr key={s.id}>
                        <td>{s.display_name}</td>
                        <td>
                          {selfOnly ? (
                            sub?.submitted ? (
                              <span className="schedule-submitted-ok">{t('schedule.submittedYes')}</span>
                            ) : (
                              <span className="schedule-submitted-missing">
                                {t('schedule.submittedNo')}
                                <button
                                  type="button"
                                  className="schedule-force-avail-btn"
                                  title={t('schedule.forceAvailabilityTitle')}
                                  onClick={() => forceSetAllAvailable(s.id)}
                                >
                                  {t('schedule.forceAvailability')}
                                </button>
                              </span>
                            )
                          ) : (
                            <span className="text-muted">{t('schedule.submittedAdmin')}</span>
                          )}
                        </td>
                        {DAY_KEYS.map((_, day) => (
                          <td key={day}>
                            {day === 6 ? (
                              <span aria-hidden>—</span>
                            ) : (
                              <input
                                type="checkbox"
                                checked={isAvailable(s.id, day)}
                                disabled={selfOnly && !sub?.submitted}
                                onChange={(e) => setAvailability(s.id, day, e.target.checked)}
                                aria-label={`${s.display_name} ${t(`schedule.days.${DAY_KEYS[day]}`)}`}
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="schedule-section">
            <h3>{t('schedule.gridTitle')}</h3>
            <div className="schedule-days-grid">
              {DAY_KEYS.map((_, day) => {
                const closed = day === 6
                const dayTemplates = templates.filter(
                  (tpl) => tpl.active && templateAllowedOnDay(tpl, day),
                )
                return (
                  <div key={day} className={`schedule-day-card ${closed ? 'closed' : ''}`}>
                    <h4>{dayLabel(day)}</h4>
                    {closed ? (
                      <p className="text-muted">{t('schedule.closedSaturday')}</p>
                    ) : dayTemplates.length === 0 ? (
                      <p className="text-muted">{t('schedule.noShifts')}</p>
                    ) : (
                      dayTemplates.map((tpl) => {
                        const assigned = assignmentsForSlot(day, tpl.id)
                        return (
                          <div key={tpl.id} className="schedule-shift-row">
                            <div className="schedule-shift-label">
                              {tpl.name} ({formatTime(tpl.start_time)}–{formatTime(tpl.end_time)})
                            </div>
                            <div className="schedule-shift-assignments">
                              {assigned.map((a) => (
                                <select
                                  key={a.id}
                                  className="schedule-assign-select"
                                  value={a.staff_id}
                                  onChange={(e) => {
                                    patchAssignment(day, tpl.id, e.target.value || null)
                                  }}
                                >
                                  <option value={a.staff_id}>
                                    {a.staff_name} ({t(`schedule.roles.${a.role}`)})
                                  </option>
                                  {(week.staff || [])
                                    .filter((s) => s.id !== a.staff_id)
                                    .map((s) => (
                                      <option key={s.id} value={s.id}>
                                        {s.display_name}
                                      </option>
                                    ))}
                                  <option value="">{t('schedule.actions.clear')}</option>
                                </select>
                              ))}
                              <select
                                className="schedule-assign-select"
                                value=""
                                onChange={(e) => {
                                  if (e.target.value) patchAssignment(day, tpl.id, e.target.value)
                                }}
                              >
                                <option value="">{t('schedule.actions.addAssignment')}</option>
                                {(week.staff || []).map((s) => (
                                  <option key={s.id} value={s.id}>
                                    {s.display_name} ({t(`schedule.roles.${s.role}`)})
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>
                        )
                      })
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
