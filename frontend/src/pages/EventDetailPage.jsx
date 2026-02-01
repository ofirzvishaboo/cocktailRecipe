import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import '../styles/events.css'

const STATUSES = ['DRAFT', 'SENT', 'RECEIVED', 'CANCELLED']
const ALL_KEY = '__ALL__'

export default function EventDetailPage() {
  const { id } = useParams()
  const nav = useNavigate()
  const { isAdmin, loading: authLoading } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [event, setEvent] = useState(null)
  const [consuming, setConsuming] = useState(false)
  const [unconsuming, setUnconsuming] = useState(false)
  const [isConsumed, setIsConsumed] = useState(false)
  const [ordersLoading, setOrdersLoading] = useState(false)
  const [eventOrders, setEventOrders] = useState([])
  const [statusFilter, setStatusFilter] = useState('DRAFT')
  const [selectedSupplierKey, setSelectedSupplierKey] = useState(ALL_KEY)
  const [selectedOrderId, setSelectedOrderId] = useState('')
  const [saving, setSaving] = useState(false)

  const aggregateItems = useCallback((ordersList) => {
    const map = new Map()
    for (const o of ordersList || []) {
      for (const it of (o?.items || [])) {
        const isMl = it?.needed_ml != null || it?.requested_ml != null || it?.used_from_stock_ml != null
        const unitKey = isMl ? 'ml' : (it?.unit || it?.requested_unit || '').toLowerCase() || 'unit'
        const key = `${it.ingredient_id}:${unitKey}`

        const prev = map.get(key) || {
          ingredient_id: it.ingredient_id,
          ingredient_name: it.ingredient_name,
          ingredient_name_he: it.ingredient_name_he,
          requested_ml: 0,
          used_from_stock_ml: 0,
          needed_ml: 0,
          requested_quantity: 0,
          used_from_stock_quantity: 0,
          needed_quantity: 0,
          unit: unitKey,
          bottle_volume_ml: it.bottle_volume_ml,
        }

        const add = (field, v) => {
          const n = Number(v)
          if (Number.isNaN(n)) return
          prev[field] = Number(prev[field] || 0) + n
        }

        add('requested_ml', it.requested_ml)
        add('used_from_stock_ml', it.used_from_stock_ml)
        add('needed_ml', it.needed_ml)
        add('requested_quantity', it.requested_quantity)
        add('used_from_stock_quantity', it.used_from_stock_quantity)
        add('needed_quantity', it.needed_quantity)

        if (!prev.bottle_volume_ml && it.bottle_volume_ml) prev.bottle_volume_ml = it.bottle_volume_ml

        map.set(key, prev)
      }
    }
    const out = Array.from(map.values())
    out.sort((a, b) => String(a.ingredient_name || '').localeCompare(String(b.ingredient_name || '')))
    return out
  }, [])

  const loadEvent = async () => {
    if (!id) return
    try {
      setLoading(true)
      setError('')
      const res = await api.get(`/events/${id}`)
      setEvent(res.data || null)
    } catch (e) {
      console.error('Failed to load event', e)
      const detail = e?.response?.data?.detail || e?.message
      setError(detail ? String(detail) : t('events.errors.loadFailed'))
      setEvent(null)
    } finally {
      setLoading(false)
    }
  }

  const loadConsumption = async () => {
    if (!id) return
    try {
      const res = await api.get(`/inventory/events/${id}/consumption`)
      setIsConsumed(!!res?.data?.is_consumed)
    } catch {
      setIsConsumed(false)
    }
  }

  const loadOrdersForEvent = useCallback(async () => {
    if (!id) return
    try {
      setOrdersLoading(true)
      setError('')
      const params = new URLSearchParams()
      params.set('scope', 'EVENT')
      params.set('event_id', id)
      if (statusFilter) params.set('status', statusFilter)
      const res = await api.get(`/orders?${params.toString()}`)
      setEventOrders(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('Failed to load event orders', e)
      setEventOrders([])
    } finally {
      setOrdersLoading(false)
    }
  }, [id, statusFilter])

  useEffect(() => {
    if (!isAdmin) return
    loadEvent()
    loadConsumption()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, id])

  useEffect(() => {
    if (!isAdmin) return
    loadOrdersForEvent()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, id, statusFilter])

  useEffect(() => {
    setSelectedSupplierKey(ALL_KEY)
    setSelectedOrderId('')
  }, [id, statusFilter])

  const consume = async () => {
    if (!id || isConsumed) return
    try {
      setConsuming(true)
      setError('')
      await api.post('/inventory/consume-event', { event_id: id, location: 'ALL' })
      await loadConsumption()
    } catch (e) {
      console.error('Failed to consume event', e)
      const detail = e?.response?.data?.detail || e?.message
      setError(detail ? String(detail) : t('inventory.errors.consumeEventFailed'))
    } finally {
      setConsuming(false)
    }
  }

  const unconsume = async () => {
    if (!id || !isConsumed) return
    try {
      setUnconsuming(true)
      setError('')
      await api.post('/inventory/unconsume-event', { event_id: id, location: 'ALL' })
      await loadConsumption()
    } catch (e) {
      console.error('Failed to unconsume event', e)
      const detail = e?.response?.data?.detail || e?.message
      setError(detail ? String(detail) : t('inventory.errors.consumeEventFailed'))
    } finally {
      setUnconsuming(false)
    }
  }

  const groupedBySupplier = useMemo(() => {
    const map = new Map()
    for (const o of eventOrders || []) {
      const key = o?.supplier_id || 'UNKNOWN'
      const label = o?.supplier_name || t('orders.supplier.unknown')
      if (!map.has(key)) map.set(key, { key, label, orders: [] })
      map.get(key).orders.push(o)
    }
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label))
  }, [eventOrders, t])

  const aggregatedAllItems = useMemo(() => aggregateItems(eventOrders || []), [aggregateItems, eventOrders])

  const selectedOrder = useMemo(() => {
    if (!selectedOrderId) return null
    return (eventOrders || []).find((o) => String(o.id) === String(selectedOrderId)) || null
  }, [eventOrders, selectedOrderId])

  const updateOrderStatus = async (orderId, nextStatus) => {
    if (!orderId) return
    try {
      setSaving(true)
      setError('')
      await api.patch(`/orders/${orderId}`, { status: nextStatus })
      await loadOrdersForEvent()
    } catch (e) {
      console.error('Failed to update order', e)
      setError(t('orders.errors.updateFailed'))
    } finally {
      setSaving(false)
    }
  }

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/" replace />

  const title = (event?.name || '').trim() || t('events.unnamed')

  return (
    <div className="card">
      <div className="events-header">
        <div className="events-header-left">
          <div className="muted">
            <Link to="/events" className="link">{t('events.backToList')}</Link>
          </div>
          <h2 style={{ margin: '6px 0 0 0' }}>{title}</h2>
          {event?.event_date && (
            <div className="muted" style={{ marginTop: 6 }}>
              {t('events.meta', { date: event.event_date, people: event.people })}
            </div>
          )}
        </div>
        <div className="events-header-actions">
          <span className={`pill ${isConsumed ? 'pill-ok' : 'pill-muted'}`}>
            {isConsumed ? t('events.status.consumed') : t('events.status.notConsumed')}
          </span>
          <button
            type="button"
            className="button-edit"
            onClick={() => nav(`/events/${id}/edit`)}
            disabled={loading}
          >
            {t('common.edit')}
          </button>
          <button type="button" className="button-edit" onClick={() => nav('/inventory')} disabled={loading}>
            {t('events.actions.openInventory')}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {loading && <div className="loading">{t('common.loading')}</div>}

      {!loading && event && (
        <div className="events-grid">
          <div className="events-panel">
            <div className="events-panel-title">{t('events.detailsTitle')}</div>
            <div className="events-detail">
              <div className="events-detail-row">
                <div className="muted">{t('events.fields.date')}</div>
                <div className="name">{event.event_date}</div>
              </div>
              <div className="events-detail-row">
                <div className="muted">{t('events.fields.people')}</div>
                <div className="name">{event.people}</div>
              </div>
              <div className="events-detail-row">
                <div className="muted">{t('events.fields.servingsPerPerson')}</div>
                <div className="name">{event.servings_per_person}</div>
              </div>
              <div className="events-detail-row">
                <div className="muted">{t('events.fields.notes')}</div>
                <div className="name" style={{ whiteSpace: 'pre-wrap' }}>{event.notes || '—'}</div>
              </div>
            </div>
          </div>

          <div className="events-panel">
            <div className="events-panel-title">{t('events.menuTitle')}</div>
            <div className="events-chips">
              {(event.menu_items || []).map((mi) => {
                const cn = lang === 'he'
                  ? (mi?.cocktail_name_he || mi?.cocktail_name)
                  : (mi?.cocktail_name || mi?.cocktail_name_he)
                return (
                  <Link key={mi.id} className="pill pill-muted" to={`/cocktails/${mi.cocktail_recipe_id}`}>
                    {cn || mi.cocktail_recipe_id}
                  </Link>
                )
              })}
            </div>

            <div className="events-form-actions" style={{ marginTop: 14 }}>
              <button
                type="button"
                className="button-edit"
                disabled={!isConsumed || consuming || unconsuming}
                onClick={unconsume}
              >
                {unconsuming ? t('inventory.movement.unconsumingEvent') : t('inventory.movement.unconsumeEvent')}
              </button>
              <button
                type="button"
                className="button-primary"
                disabled={isConsumed || consuming || unconsuming}
                onClick={consume}
              >
                {isConsumed ? t('inventory.movement.consumed') : (consuming ? t('inventory.movement.consumingEvent') : t('inventory.movement.consumeEvent'))}
              </button>
            </div>

            <div className="muted" style={{ marginTop: 10 }}>
              {t('events.consumeHelp')}
            </div>
          </div>

          <div className="events-panel" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
              <div className="events-panel-title" style={{ marginBottom: 0 }}>{t('events.ordersTitle')}</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <label className="muted">{t('orders.filters.status')}</label>
                <select
                  className="form-input"
                  style={{ width: 220 }}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  disabled={ordersLoading || saving}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{t(`orders.status.${s}`, { defaultValue: s })}</option>
                  ))}
                </select>
                <button type="button" className="button-edit" onClick={loadOrdersForEvent} disabled={ordersLoading || saving}>
                  {t('common.refresh')}
                </button>
              </div>
            </div>

            {ordersLoading ? (
              <div className="loading" style={{ marginTop: 12 }}>{t('common.loading')}</div>
            ) : (eventOrders || []).length === 0 ? (
              <div className="empty-state" style={{ marginTop: 12 }}>
                {t('events.noOrdersForEvent')}
                <div style={{ marginTop: 10 }}>
                  <Link to="/orders" className="button-edit">{t('events.openOrdersToGenerate')}</Link>
                </div>
              </div>
            ) : (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <button
                    type="button"
                    className={`inventory-tab ${selectedSupplierKey === ALL_KEY ? 'active' : ''}`}
                    onClick={() => { setSelectedSupplierKey(ALL_KEY); setSelectedOrderId('') }}
                  >
                    {t('orders.all')}
                  </button>
                  {(groupedBySupplier || []).map((g) => (
                    <button
                      key={g.key}
                      type="button"
                      className={`inventory-tab ${selectedSupplierKey === g.key ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedSupplierKey(g.key)
                        setSelectedOrderId((g.orders || [])[0]?.id || '')
                      }}
                    >
                      {g.label}
                    </button>
                  ))}
                </div>

                {selectedSupplierKey === ALL_KEY ? (
                  <div style={{ marginTop: 12 }} className="inventory-table">
                    <div className="inventory-table-header" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
                      <div>{t('orders.columns.ingredient')}</div>
                      <div className="right">{t('orders.columns.requested')}</div>
                      <div className="right">{t('orders.columns.usedFromStock')}</div>
                      <div className="right">{t('orders.columns.shortfall')}</div>
                      <div className="right">{t('orders.columns.bottles')}</div>
                    </div>
                    {(aggregatedAllItems || []).map((it) => {
                      const name = lang === 'he'
                        ? ((it.ingredient_name_he || '').trim() || (it.ingredient_name || '').trim())
                        : ((it.ingredient_name || '').trim() || (it.ingredient_name_he || '').trim())

                      const requested = (Number(it.requested_ml || 0) > 0)
                        ? `${Number(it.requested_ml || 0).toFixed(0)} ml`
                        : `${Number(it.requested_quantity || 0).toFixed(2)} ${it.unit || ''}`

                      const used = (Number(it.used_from_stock_ml || 0) > 0)
                        ? `${Number(it.used_from_stock_ml || 0).toFixed(0)} ml`
                        : `${Number(it.used_from_stock_quantity || 0).toFixed(2)} ${it.unit || ''}`

                      const shortfall = (Number(it.needed_ml || 0) > 0)
                        ? `${Number(it.needed_ml || 0).toFixed(0)} ml`
                        : `${Number(it.needed_quantity || 0).toFixed(2)} ${it.unit || ''}`

                      const vol = Number(it.bottle_volume_ml || 0)
                      const bottles = vol > 0 && Number(it.needed_ml || 0) > 0 ? Math.ceil(Number(it.needed_ml || 0) / vol) : null

                      return (
                        <div key={`${it.ingredient_id}:${it.unit}`} className="inventory-table-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
                          <div className="name">{name || it.ingredient_id}</div>
                          <div className="right muted">{requested}</div>
                          <div className="right muted">{used}</div>
                          <div className="right">{shortfall}</div>
                          <div className="right">{bottles != null ? <span className="muted">{bottles}</span> : <span className="muted">-</span>}</div>
                        </div>
                      )
                    })}
                    {(aggregatedAllItems || []).length === 0 && (
                      <div className="empty-state">{t('orders.empty')}</div>
                    )}
                  </div>
                ) : !selectedOrder ? (
                  <div className="empty-state" style={{ marginTop: 12 }}>{t('orders.selectSupplierHelp')}</div>
                ) : (
                  <>
                    <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                      <div style={{ fontWeight: 900 }}>{selectedOrder?.supplier_name || t('orders.supplier.unknown')}</div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <label className="muted">{t('orders.filters.status')}</label>
                        <select
                          className="form-input"
                          value={selectedOrder.status}
                          onChange={(e) => updateOrderStatus(selectedOrder.id, e.target.value)}
                          disabled={saving}
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>{t(`orders.status.${s}`, { defaultValue: s })}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div style={{ marginTop: 12 }} className="inventory-table">
                      <div className="inventory-table-header" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
                        <div>{t('orders.columns.ingredient')}</div>
                        <div className="right">{t('orders.columns.requested')}</div>
                        <div className="right">{t('orders.columns.usedFromStock')}</div>
                        <div className="right">{t('orders.columns.shortfall')}</div>
                        <div className="right">{t('orders.columns.bottles')}</div>
                      </div>
                      {(selectedOrder.items || []).map((it) => {
                        const name = lang === 'he'
                          ? ((it.ingredient_name_he || '').trim() || (it.ingredient_name || '').trim())
                          : ((it.ingredient_name || '').trim() || (it.ingredient_name_he || '').trim())

                        const requested = (it.requested_ml != null)
                          ? `${Number(it.requested_ml).toFixed(0)} ml`
                          : `${Number(it.requested_quantity || 0).toFixed(2)} ${it.requested_unit || it.unit || ''}`

                        const used = (it.used_from_stock_ml != null)
                          ? `${Number(it.used_from_stock_ml).toFixed(0)} ml`
                          : `${Number(it.used_from_stock_quantity || 0).toFixed(2)} ${it.requested_unit || it.unit || ''}`

                        const shortfall = (it.needed_ml != null)
                          ? `${Number(it.needed_ml).toFixed(0)} ml`
                          : `${Number(it.needed_quantity || 0).toFixed(2)} ${it.unit || ''}`

                        return (
                          <div key={it.id || it.ingredient_id} className="inventory-table-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr' }}>
                            <div className="name">{name || it.ingredient_id}</div>
                            <div className="right muted">{requested}</div>
                            <div className="right muted">{used}</div>
                            <div className="right">{shortfall}</div>
                            <div className="right">{it.recommended_bottles != null ? <span className="muted">{it.recommended_bottles}</span> : <span className="muted">-</span>}</div>
                          </div>
                        )
                      })}
                      {(selectedOrder.items || []).length === 0 && (
                        <div className="empty-state">{t('orders.empty')}</div>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {!loading && !event && (
        <div className="empty-state">{t('events.errors.notFound')}</div>
      )}
    </div>
  )
}

