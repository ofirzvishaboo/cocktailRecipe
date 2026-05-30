import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import DatePicker, { registerLocale } from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import he from 'date-fns/locale/he'
import api from '../api'
import { toLocalDateStr } from '../utils/schedule'
import '../styles/checklist.css'

registerLocale('he', he)

function itemText(item, lang) {
  return lang === 'he' ? item.text_he : item.text_en
}

function sectionTitle(section, lang) {
  return lang === 'he' ? section.title_he : section.title_en
}

export default function ChecklistHistoryPage() {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 14)
    d.setHours(0, 0, 0, 0)
    return d
  })
  const [dateTo, setDateTo] = useState(() => new Date())
  const [typeFilter, setTypeFilter] = useState('')
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [reopening, setReopening] = useState(false)

  const dateFromStr = useMemo(() => toLocalDateStr(dateFrom), [dateFrom])
  const dateToStr = useMemo(() => toLocalDateStr(dateTo), [dateTo])

  const loadRuns = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const params = { date_from: dateFromStr, date_to: dateToStr }
      if (typeFilter) params.type = typeFilter
      const res = await api.get('/checklists/runs', { params })
      setRuns(res.data || [])
    } catch (e) {
      console.error(e)
      setError(t('checklists.errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [dateFromStr, dateToStr, typeFilter, t])

  useEffect(() => {
    loadRuns()
  }, [loadRuns])

  const loadDetail = async (runId) => {
    try {
      setDetailLoading(true)
      setError('')
      const res = await api.get(`/checklists/runs/${runId}`)
      setSelectedRun(res.data)
    } catch (e) {
      console.error(e)
      setError(t('checklists.errors.loadFailed'))
    } finally {
      setDetailLoading(false)
    }
  }

  const reopen = async () => {
    if (!selectedRun?.id) return
    try {
      setReopening(true)
      const res = await api.post(`/checklists/runs/${selectedRun.id}/reopen`)
      setSelectedRun(res.data)
      await loadRuns()
    } catch (e) {
      console.error(e)
      setError(t('checklists.errors.reopenFailed'))
    } finally {
      setReopening(false)
    }
  }

  const completionMap = useMemo(() => {
    const map = {}
    for (const c of selectedRun?.completions || []) {
      map[c.item_id] = c.completed
    }
    return map
  }, [selectedRun?.completions])

  return (
    <div className="card checklist-history-page">
      <h2>{t('checklists.history.title')}</h2>
      <p className="text-muted">{t('checklists.history.subtitle')}</p>

      <div className="checklist-history-filters">
        <label>
          {t('checklists.history.from')}
          <DatePicker
            selected={dateFrom}
            onChange={(d) => d && setDateFrom(d)}
            locale={lang === 'he' ? 'he' : undefined}
            dateFormat="dd/MM/yyyy"
            className="input"
          />
        </label>
        <label>
          {t('checklists.history.to')}
          <DatePicker
            selected={dateTo}
            onChange={(d) => d && setDateTo(d)}
            locale={lang === 'he' ? 'he' : undefined}
            dateFormat="dd/MM/yyyy"
            className="input"
          />
        </label>
        <label>
          {t('checklists.history.type')}
          <select
            className="input"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">{t('checklists.history.allTypes')}</option>
            <option value="opening">{t('checklists.opening')}</option>
            <option value="closing">{t('checklists.closing')}</option>
          </select>
        </label>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="checklist-history-layout">
        <div className="checklist-history-list">
          {loading ? (
            <p>{t('common.loading')}</p>
          ) : runs.length === 0 ? (
            <p className="text-muted">{t('checklists.history.empty')}</p>
          ) : (
            <table className="checklist-history-table">
              <thead>
                <tr>
                  <th>{t('checklists.history.dateCol')}</th>
                  <th>{t('checklists.history.typeCol')}</th>
                  <th>{t('checklists.history.statusCol')}</th>
                  <th>{t('checklists.history.progressCol')}</th>
                  <th>{t('checklists.history.submittedByCol')}</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className={selectedRun?.id === run.id ? 'selected' : ''}
                    onClick={() => loadDetail(run.id)}
                  >
                    <td>{run.run_date}</td>
                    <td>{t(`checklists.${run.type}`)}</td>
                    <td>{t(`checklists.status.${run.status}`)}</td>
                    <td>{run.completed_items}/{run.total_items}</td>
                    <td>{run.submitted_by_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="checklist-history-detail">
          {!selectedRun ? (
            <p className="text-muted">{t('checklists.history.selectRun')}</p>
          ) : detailLoading ? (
            <p>{t('common.loading')}</p>
          ) : (
            <>
              <div className="checklist-history-detail-header">
                <h3>
                  {t(`checklists.${selectedRun.type}`)} — {selectedRun.run_date}
                </h3>
                <p className="text-muted">
                  {t(`checklists.status.${selectedRun.status}`)}
                  {selectedRun.submitted_by_name && (
                    <> · {selectedRun.submitted_by_name}</>
                  )}
                </p>
                {selectedRun.status === 'submitted' && (
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={reopen}
                    disabled={reopening}
                  >
                    {reopening ? t('common.saving') : t('checklists.history.reopen')}
                  </button>
                )}
              </div>

              {(selectedRun.sections || []).map((section) => (
                <details key={section.id} className="checklist-section" open>
                  <summary>{sectionTitle(section, lang)}</summary>
                  <div className="checklist-section-body">
                    {section.section_type === 'text_fields' ? (
                      section.items.map((item) => (
                        <div key={item.id} className="checklist-field-readonly">
                          <strong>{itemText(item, lang)}</strong>
                          <p>{selectedRun.notes?.[item.key] || '—'}</p>
                        </div>
                      ))
                    ) : (
                      section.items.map((item) => (
                        <div
                          key={item.id}
                          className={`checklist-item-readonly ${completionMap[item.id] ? 'done' : ''}`}
                        >
                          <span className="checklist-item-check">{completionMap[item.id] ? '✓' : '○'}</span>
                          <span>{itemText(item, lang)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </details>
              ))}
            </>
          )}
        </div>
      </div>

      <Link to="/checklists" className="checklist-back-link">{t('checklists.history.backToChecklists')}</Link>
    </div>
  )
}
