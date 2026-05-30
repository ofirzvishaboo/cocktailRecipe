import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import DatePicker, { registerLocale } from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import he from 'date-fns/locale/he'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import { toLocalDateStr } from '../utils/schedule'
import '../styles/checklist.css'

registerLocale('he', he)

function itemText(item, lang) {
  return lang === 'he' ? item.text_he : item.text_en
}

function sectionTitle(section, lang) {
  return lang === 'he' ? section.title_he : section.title_en
}

export default function ChecklistPage() {
  const { isAuthenticated, isAdmin, isBartender, staffProfile, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const canUseChecklist = isBartender || isAdmin

  const [checklistType, setChecklistType] = useState('opening')
  const [runDate, setRunDate] = useState(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    return d
  })
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [saveError, setSaveError] = useState('')
  const saveTimer = useRef(null)
  const pendingSave = useRef(null)

  const runDateStr = useMemo(() => toLocalDateStr(runDate), [runDate])
  const todayDow = runDate.getDay()

  const completionMap = useMemo(() => {
    const map = {}
    for (const c of run?.completions || []) {
      map[c.item_id] = c.completed
    }
    return map
  }, [run?.completions])

  // Compute progress locally so the bar updates instantly on checkbox toggle.
  // For daily_rotation sections, only today's item counts (matches backend logic).
  const { localTotal, localCompleted } = useMemo(() => {
    if (!run?.sections) return { localTotal: run?.total_items ?? 0, localCompleted: run?.completed_items ?? 0 }
    let total = 0
    let completed = 0
    for (const section of run.sections) {
      if (section.section_type === 'text_fields') continue
      for (const item of section.items) {
        if (section.section_type === 'daily_rotation' && item.day_of_week !== todayDow) continue
        total += 1
        if (completionMap[item.id]) completed += 1
      }
    }
    return { localTotal: total, localCompleted: completed }
  }, [run?.sections, completionMap, todayDow, run?.total_items, run?.completed_items])

  const loadRun = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get('/checklists/me/runs/today', {
        params: { type: checklistType, date: runDateStr },
      })
      setRun(res.data)
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setError(detail ? String(detail) : t('checklists.errors.loadFailed'))
      setRun(null)
    } finally {
      setLoading(false)
    }
  }, [checklistType, runDateStr, t])

  useEffect(() => {
    if (canUseChecklist) loadRun()
  }, [canUseChecklist, loadRun])

  const flushSave = useCallback(async (payload) => {
    if (!run?.id || !run.can_edit) return
    try {
      setSaving(true)
      setSaveError('')
      const res = await api.put(`/checklists/me/runs/${run.id}`, payload)
      setRun(res.data)
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setSaveError(detail ? String(detail) : t('checklists.errors.saveFailed'))
    } finally {
      setSaving(false)
      pendingSave.current = null
    }
  }, [run?.id, run?.can_edit, t])

  const scheduleSave = useCallback((payload) => {
    if (!run?.can_edit) return
    pendingSave.current = payload
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      if (pendingSave.current) flushSave(pendingSave.current)
    }, 600)
  }, [run?.can_edit, flushSave])

  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
  }, [])

  const toggleItem = (itemId, completed) => {
    if (!run?.can_edit) return
    const completions = (run.completions || []).map((c) =>
      c.item_id === itemId ? { ...c, completed } : c,
    )
    const exists = completions.some((c) => c.item_id === itemId)
    const nextCompletions = exists
      ? completions
      : [...completions, { item_id: itemId, completed }]
    setRun((prev) => ({ ...prev, completions: nextCompletions }))
    scheduleSave({ completions: nextCompletions.map(({ item_id, completed: done }) => ({ item_id, completed: done })) })
  }

  const setNote = (fieldKey, value) => {
    if (!run?.can_edit) return
    const notes = { ...(run.notes || {}), [fieldKey]: value }
    setRun((prev) => ({ ...prev, notes }))
    scheduleSave({ notes })
  }

  const submit = async () => {
    if (!run?.id || !run.can_edit) return
    try {
      setSubmitting(true)
      setError('')
      const res = await api.post(`/checklists/me/runs/${run.id}/submit`)
      setRun(res.data)
    } catch (e) {
      console.error(e)
      const detail = e?.response?.data?.detail
      setError(detail ? String(detail) : t('checklists.errors.submitFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  const progressPct = localTotal
    ? Math.round((localCompleted / localTotal) * 100)
    : 0

  if (authLoading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!canUseChecklist) {
    return (
      <div className="card">
        <h2>{t('checklists.title')}</h2>
        <p>{t('checklists.noAccess')}</p>
        <Link to="/">{t('checklists.backHome')}</Link>
      </div>
    )
  }

  return (
    <div className="card checklist-page">
      <h2>{t('checklists.title')}</h2>
      <p className="text-muted">
        {t('checklists.greeting', { name: staffProfile?.display_name || '' })}
      </p>

      <div className="checklist-tabs">
        <button
          type="button"
          className={`checklist-tab ${checklistType === 'opening' ? 'active' : ''}`}
          onClick={() => setChecklistType('opening')}
        >
          {t('checklists.opening')}
        </button>
        <button
          type="button"
          className={`checklist-tab ${checklistType === 'closing' ? 'active' : ''}`}
          onClick={() => setChecklistType('closing')}
        >
          {t('checklists.closing')}
        </button>
      </div>

      <div className="checklist-date-picker">
        <label>
          {t('checklists.date')}
          <DatePicker
            selected={runDate}
            onChange={(d) => d && setRunDate(d)}
            locale={lang === 'he' ? 'he' : undefined}
            dateFormat="dd/MM/yyyy"
            className="input"
          />
        </label>
      </div>

      {run && (
        <div className="checklist-progress">
          <div className="checklist-progress-bar">
            <div className="checklist-progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <span className="checklist-progress-label">
            {t('checklists.progress', { completed: localCompleted, total: localTotal })}
          </span>
        </div>
      )}

      {run?.status === 'submitted' && (
        <p className="checklist-submitted-badge">
          {t('checklists.submitted', {
            name: run.submitted_by_name || '—',
            date: run.submitted_at ? new Date(run.submitted_at).toLocaleString(lang === 'he' ? 'he-IL' : 'en-GB') : '',
          })}
        </p>
      )}

      {error && <p className="error-text">{error}</p>}
      {saveError && <p className="error-text">{saveError}</p>}
      {saving && <p className="text-muted checklist-saving">{t('checklists.saving')}</p>}

      {loading ? (
        <p>{t('common.loading')}</p>
      ) : run ? (
        <div className="checklist-sections">
          {(run.sections || []).map((section) => (
            <details key={section.id} className="checklist-section" open>
              <summary>{sectionTitle(section, lang)}</summary>
              <div className="checklist-section-body">
                {section.section_type === 'text_fields' ? (
                  section.items.map((item) => (
                    <label key={item.id} className="checklist-field">
                      <span className="checklist-field-label">{itemText(item, lang)}</span>
                      <textarea
                        className="input checklist-textarea"
                        value={run.notes?.[item.key] || ''}
                        disabled={!run.can_edit}
                        onChange={(e) => setNote(item.key, e.target.value)}
                        rows={2}
                      />
                    </label>
                  ))
                ) : (
                  section.items.map((item) => {
                    const isDaily = section.section_type === 'daily_rotation'
                    const isToday = isDaily && item.day_of_week === todayDow
                    const isOtherDay = isDaily && item.day_of_week !== todayDow
                    return (
                      <label
                        key={item.id}
                        className={`checklist-item ${isToday ? 'checklist-item--today' : ''} ${isOtherDay ? 'checklist-item--other-day' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={!!completionMap[item.id]}
                          disabled={!run.can_edit}
                          onChange={(e) => toggleItem(item.id, e.target.checked)}
                        />
                        <span>{itemText(item, lang)}</span>
                        {isToday && (
                          <span className="checklist-today-badge">{t('checklists.todaysTask')}</span>
                        )}
                      </label>
                    )
                  })
                )}
              </div>
            </details>
          ))}
        </div>
      ) : null}

      {run?.can_edit && (
        <button
          type="button"
          className="button-primary checklist-submit"
          onClick={submit}
          disabled={submitting || localCompleted < localTotal}
        >
          {submitting ? t('common.saving') : t('checklists.submit')}
        </button>
      )}
    </div>
  )
}
