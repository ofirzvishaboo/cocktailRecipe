import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'

const STATUSES = ['DRAFT', 'SENT', 'RECEIVED', 'CANCELLED']
const ALL_KEY = '__ALL__'

export default function OrdersPage() {
  const { isAdmin } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [orders, setOrders] = useState([])
  const [statusFilter, setStatusFilter] = useState('DRAFT')
  const [selectedOrderId, setSelectedOrderId] = useState('')
  const [selectedSupplierKey, setSelectedSupplierKey] = useState(ALL_KEY)
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
          bottle_id: it.bottle_id,
          bottle_name: it.bottle_name,
          bottle_name_he: it.bottle_name_he,
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

        if (!prev.bottle_id && it.bottle_id) {
          prev.bottle_id = it.bottle_id
          prev.bottle_name = it.bottle_name
          prev.bottle_name_he = it.bottle_name_he
          prev.bottle_volume_ml = it.bottle_volume_ml
        }

        map.set(key, prev)
      }
    }

    const out = Array.from(map.values())
    out.sort((a, b) => String(a.ingredient_name || '').localeCompare(String(b.ingredient_name || '')))
    return out
  }, [])

  const loadWeeklyOrders = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (statusFilter) params.set('status', statusFilter)
      params.set('scope', 'WEEKLY')
      const res = await api.get(`/orders?${params.toString()}`)
      setOrders(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('Failed to load orders', e)
      setError(t('orders.errors.loadFailed'))
      setOrders([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter, t])

  useEffect(() => {
    if (!isAdmin) return
    loadWeeklyOrders()
  }, [isAdmin, loadWeeklyOrders])

  useEffect(() => {
    // Reset selection when filters change
    setSelectedSupplierKey(ALL_KEY)
    setSelectedOrderId('')
  }, [statusFilter])

  const selectedOrder = useMemo(() => {
    if (!selectedOrderId) return null
    const list = orders || []
    return (list || []).find((o) => String(o.id) === String(selectedOrderId)) || null
  }, [orders, selectedOrderId])

  const groupedBySupplier = useMemo(() => {
    const map = new Map()
    const list = orders || []
    for (const o of list || []) {
      const key = o?.supplier_id || 'UNKNOWN'
      const label = o?.supplier_name || t('orders.supplier.unknown')
      if (!map.has(key)) map.set(key, { key, label, orders: [] })
      const entry = map.get(key)
      // Weekly: ensure we keep only one order per supplier (avoid duplicates from old data)
      if (!entry.orders[0]) entry.orders.push(o)
    }
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label))
  }, [orders, t])

  const allSuppliersOrders = useMemo(() => {
    return orders || []
  }, [orders])

  const aggregatedAllItems = useMemo(() => aggregateItems(allSuppliersOrders), [aggregateItems, allSuppliersOrders])

  const generateWeeklyByEvent = async () => {
    try {
      setSaving(true)
      setError('')
      const resp = await api.post('/orders/weekly-by-event', { location_scope: 'ALL' })
      await loadWeeklyOrders()
      void resp
    } catch (e) {
      console.error('Failed to generate weekly orders', e)
      const detail = e?.response?.data?.detail || t('orders.errors.generateFailed')
      setError(String(detail))
    } finally {
      setSaving(false)
    }
  }

  const updateOrderStatus = async (orderId, nextStatus) => {
    if (!orderId) return
    try {
      setSaving(true)
      setError('')
      await api.patch(`/orders/${orderId}`, { status: nextStatus })
      await loadWeeklyOrders()
    } catch (e) {
      console.error('Failed to update order', e)
      setError(t('orders.errors.updateFailed'))
    } finally {
      setSaving(false)
    }
  }

  const updateOrderItem = async (orderId, itemId, patch) => {
    if (!orderId || !itemId) return
    try {
      setSaving(true)
      setError('')
      await api.patch(`/orders/${orderId}/items/${itemId}`, patch)
      await loadWeeklyOrders()
    } catch (e) {
      console.error('Failed to update order item', e)
      setError(t('orders.errors.updateFailed'))
    } finally {
      setSaving(false)
    }
  }

  if (!isAdmin) {
    return (
      <div className="card">
        <div className="error-message">{t('orders.errors.notAllowed')}</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>{t('orders.title')}</h2>
        <button type="button" className="button-primary" onClick={generateWeeklyByEvent} disabled={saving}>
          {saving ? t('orders.actions.generating') : t('orders.actions.generateWeeklyByEvent')}
        </button>
      </div>

      <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <label style={{ fontWeight: 700 }}>{t('orders.filters.status')}</label>
        <select
          className="form-input"
          style={{ width: 220 }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          disabled={loading || saving}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{t(`orders.status.${s}`, { defaultValue: s })}</option>
          ))}
        </select>
      </div>

      {error && <div className="error-message" style={{ marginTop: 12 }}>{error}</div>}
      {loading && <div className="loading" style={{ marginTop: 12 }}>{t('common.loading')}</div>}

      {!loading && (
        <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 2fr', gap: 14 }}>
          <div className="inventory-subpanel" style={{ marginTop: 0 }}>
            <div className="inventory-subpanel-title">
              {t('orders.listTitle')}
            </div>

            {(groupedBySupplier || []).length === 0 ? (
              <div className="empty-state">{t('orders.empty')}</div>
            ) : (
              <>
                <button
                  type="button"
                  className={`inventory-tab ${selectedSupplierKey === ALL_KEY ? 'active' : ''}`}
                  style={{ justifyContent: 'space-between', display: 'flex' }}
                  onClick={() => {
                    setSelectedSupplierKey(ALL_KEY)
                    setSelectedOrderId('')
                  }}
                >
                  <span className="muted">{t('orders.allSuppliers')}</span>
                </button>

                {(groupedBySupplier || []).map((g) => (
                  <div key={g.key} style={{ marginTop: 12 }}>
                    <div style={{ fontWeight: 900, marginBottom: 6 }}>{g.label}</div>
                    <div style={{ display: 'grid', gap: 6 }}>
                      {(g.orders || []).map((o) => (
                        <button
                          key={o.id}
                          type="button"
                          className={`inventory-tab ${selectedSupplierKey === g.key && String(selectedOrderId) === String(o.id) ? 'active' : ''}`}
                          style={{ justifyContent: 'space-between', display: 'flex' }}
                          onClick={() => {
                            setSelectedSupplierKey(g.key)
                            setSelectedOrderId(o.id)
                          }}
                        >
                          <span>{t('orders.order')} #{String(o.id).slice(0, 6)}</span>
                          <span className="muted">{o.period_start} → {o.period_end}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>

          <div className="inventory-subpanel" style={{ marginTop: 0 }}>
            <div className="inventory-subpanel-title">{t('orders.detailsTitle')}</div>
            {selectedSupplierKey === ALL_KEY ? (
              <div style={{ marginTop: 12 }} className="inventory-table">
                <div className="inventory-table-header" style={{ gridTemplateColumns: '2fr 1fr 1fr' }}>
                  <div>{t('orders.columns.ingredient')}</div>
                  <div className="right">{t('orders.columns.needed')}</div>
                  <div className="right">{t('orders.columns.bottles')}</div>
                </div>
                {(aggregatedAllItems || []).map((it) => {
                  const name = lang === 'he'
                    ? ((it.ingredient_name_he || '').trim() || (it.ingredient_name || '').trim())
                    : ((it.ingredient_name || '').trim() || (it.ingredient_name_he || '').trim())
                  const needed = (Number(it.needed_ml || 0) > 0)
                    ? `${Number(it.needed_ml || 0).toFixed(0)} ml`
                    : `${Number(it.needed_quantity || 0).toFixed(2)} ${it.unit || ''}`
                  const vol = Number(it.bottle_volume_ml || 0)
                  const bottles = vol > 0 && Number(it.needed_ml || 0) > 0 ? Math.ceil(Number(it.needed_ml || 0) / vol) : null
                  return (
                    <div key={`${it.ingredient_id}:${it.unit}`} className="inventory-table-row" style={{ gridTemplateColumns: '2fr 1fr 1fr' }}>
                      <div className="name">{name || it.ingredient_id}</div>
                      <div className="right">{needed}</div>
                      <div className="right">{bottles != null ? <span className="muted">{bottles}</span> : <span className="muted">-</span>}</div>
                    </div>
                  )
                })}
                {(aggregatedAllItems || []).length === 0 && (
                  <div className="empty-state">{t('orders.empty')}</div>
                )}
              </div>
            ) : !selectedOrder ? (
              <div className="empty-state">{t('orders.selectHelp')}</div>
            ) : (
              <>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontWeight: 900 }}>
                    {selectedOrder?.supplier_name || t('orders.supplier.unknown')}
                    <span className="muted" style={{ marginInlineStart: 10 }}>
                      {selectedOrder.period_start} → {selectedOrder.period_end}
                    </span>
                  </div>
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
                  <div className="inventory-table-header" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr' }}>
                    <div>{t('orders.columns.ingredient')}</div>
                    <div className="right">{t('orders.columns.needed')}</div>
                    <div className="right">{t('orders.columns.bottles')}</div>
                    <div className="right">{t('orders.columns.actions')}</div>
                  </div>
                  {(selectedOrder.items || []).map((it) => {
                    const name = lang === 'he'
                      ? ((it.ingredient_name_he || '').trim() || (it.ingredient_name || '').trim())
                      : ((it.ingredient_name || '').trim() || (it.ingredient_name_he || '').trim())
                    const needed = (it.needed_ml != null)
                      ? `${Number(it.needed_ml).toFixed(0)} ml`
                      : `${Number(it.needed_quantity || 0).toFixed(2)} ${it.unit || ''}`
                    return (
                      <div key={it.id} className="inventory-table-row" style={{ gridTemplateColumns: '2fr 1fr 1fr 1fr' }}>
                        <div className="name">{name || it.ingredient_id}</div>
                        <div className="right muted">{needed}</div>
                        <div className="right">
                          {it.recommended_bottles != null ? (
                            <span className="muted">{it.recommended_bottles}</span>
                          ) : (
                            <span className="muted">-</span>
                          )}
                        </div>
                        <div className="right">
                          <button
                            type="button"
                            className="button-edit"
                            disabled={saving}
                            onClick={() => {
                              const next = prompt(t('orders.prompts.overrideNeededMl'), String(it.needed_ml ?? ''))
                              if (next === null) return
                              const num = Number(next)
                              if (Number.isNaN(num)) return
                              updateOrderItem(selectedOrder.id, it.id, { needed_ml: num })
                            }}
                          >
                            {t('orders.actions.editLine')}
                          </button>
                        </div>
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
        </div>
      )}
    </div>
  )
}

