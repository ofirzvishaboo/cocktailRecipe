import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import '../styles/inventory.css'

const LOCATIONS = ['ALL', 'BAR', 'WAREHOUSE']
const TABS = ['Stock', 'Items', 'Movements']
const GROUP_ORDER = ['Spirit', 'Liqueur', 'Juice', 'Syrup', 'Garnish', 'Glass', 'Uncategorized']

function formatNumber(n) {
  const x = Number(n)
  if (Number.isNaN(x)) return ''
  return x.toLocaleString(undefined, { maximumFractionDigits: 3 })
}

function formatMoney(price, currency) {
  const x = Number(price)
  if (Number.isNaN(x)) return ''
  const cur = (currency || '').trim()
  return `${x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${cur ? ` ${cur}` : ''}`
}

export default function InventoryPage() {
  const { isAdmin } = useAuth()
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'en').split('-')[0]

  const [location, setLocation] = useState('BAR')
  const [tab, setTab] = useState('Stock')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [stockRows, setStockRows] = useState([])
  const [stockByItemAndLoc, setStockByItemAndLoc] = useState({})
  const [items, setItems] = useState([])
  const [movements, setMovements] = useState([])

  const [itemType, setItemType] = useState('')
  const [subcategoryFilter, setSubcategoryFilter] = useState('')
  const [q, setQ] = useState('')
  const [movementFromDate, setMovementFromDate] = useState('')
  const [movementToDate, setMovementToDate] = useState('')

  const [editingItemId, setEditingItemId] = useState(null)
  const [editForm, setEditForm] = useState({
    name: '',
    unit: '',
    min_level: '',
    reorder_level: '',
    price: '',
    currency: 'ILS',
    is_active: true,
    submitting: false,
  })

  const [movementForm, setMovementForm] = useState({
    inventory_item_id: '',
    change: '',
    reason: 'ADJUSTMENT',
    submitting: false,
  })

  const filteredItems = useMemo(() => {
    const query = (q || '').trim().toLowerCase()
    if (!query) return items
    return (items || []).filter((it) => (it?.name || '').toLowerCase().includes(query))
  }, [items, q])

  const sortedItems = useMemo(() => {
    const arr = [...(filteredItems || [])]
    arr.sort((a, b) => {
      const au = (a?.unit || '').toLowerCase()
      const bu = (b?.unit || '').toLowerCase()
      if (au !== bu) return au.localeCompare(bu)
      const ak = (a?.subcategory_name || '').toLowerCase()
      const bk = (b?.subcategory_name || '').toLowerCase()
      if (ak !== bk) return ak.localeCompare(bk)
      const an = (a?.name || '').toLowerCase()
      const bn = (b?.name || '').toLowerCase()
      return an.localeCompare(bn)
    })
    return arr
  }, [filteredItems])

  const groupKeyForRow = (row) => {
    const t = row?.item_type
    if (t === 'GLASS') return 'Glass'
    const sub = (row?.subcategory_name || '').trim()
    if (sub && GROUP_ORDER.includes(sub)) return sub
    return 'Uncategorized'
  }

  const displaySubcategory = (row) => {
    const key = groupKeyForRow(row)
    // Translate known group labels; fall back to raw key for anything unexpected.
    return t(`inventory.groups.${key}`, { defaultValue: key })
  }

  const displayPrice = (row) => {
    const price = row?.price
    const cur = row?.currency
    if (price === null || price === undefined) return ''
    return formatMoney(price, cur)
  }

  const groupItemsSections = useMemo(() => {
    const sections = {}
    for (const g of GROUP_ORDER) sections[g] = []
    for (const it of (sortedItems || [])) {
      const g = groupKeyForRow(it)
      sections[g].push(it)
    }
    const all = GROUP_ORDER.map((g) => ({ title: t(`inventory.groups.${g}`), key: g.toLowerCase(), items: sections[g] || [] }))
    if (subcategoryFilter) {
      return all.filter((s) => (s.key || '') === (subcategoryFilter || '').toLowerCase())
    }
    const isFiltered = !!((q || '').trim() || itemType)
    return isFiltered ? all.filter((s) => (s.items || []).length > 0) : all
  }, [sortedItems, subcategoryFilter, t, q, itemType])

  const groupStockSections = useMemo(() => {
    const sections = {}
    for (const g of GROUP_ORDER) sections[g] = []
    for (const r of (stockRows || [])) {
      const g = groupKeyForRow(r)
      sections[g].push(r)
    }
    const all = GROUP_ORDER.map((g) => ({ title: t(`inventory.groups.${g}`), key: g.toLowerCase(), items: sections[g] || [] }))
    if (subcategoryFilter) {
      return all.filter((s) => (s.key || '') === (subcategoryFilter || '').toLowerCase())
    }
    const isFiltered = !!(itemType)
    return isFiltered ? all.filter((s) => (s.items || []).length > 0) : all
  }, [stockRows, subcategoryFilter, t, itemType])

  const loadStock = async () => {
    setLoading(true)
    setError('')
    try {
      if (location === 'ALL') {
        const params = new URLSearchParams()
        if (itemType) params.set('item_type', itemType)
        const res = await api.get(`/inventory/stock/all?${params.toString()}`)
        const bar = Array.isArray(res.data?.BAR) ? res.data.BAR : []
        const wh = Array.isArray(res.data?.WAREHOUSE) ? res.data.WAREHOUSE : []

        const map = {}
        for (const r of bar) {
          map[r.inventory_item_id] = map[r.inventory_item_id] || {}
          map[r.inventory_item_id].BAR = r
        }
        for (const r of wh) {
          map[r.inventory_item_id] = map[r.inventory_item_id] || {}
          map[r.inventory_item_id].WAREHOUSE = r
        }
        setStockByItemAndLoc(map)

        // Build a combined view with two columns
        const allIds = Array.from(new Set([...bar.map((r) => r.inventory_item_id), ...wh.map((r) => r.inventory_item_id)]))
        const combined = allIds
          .map((id) => {
            const a = map[id]?.BAR
            const b = map[id]?.WAREHOUSE
            const base = a || b
            return {
              inventory_item_id: id,
              item_type: base?.item_type,
              name: base?.name || '',
              unit: base?.unit || '',
              subcategory_id: base?.subcategory_id ?? null,
              subcategory_name: base?.subcategory_name ?? null,
              price: base?.price ?? null,
              currency: base?.currency ?? null,
              quantity_bar: a?.quantity ?? 0,
              quantity_warehouse: b?.quantity ?? 0,
              reserved_bar: a?.reserved_quantity ?? 0,
              reserved_warehouse: b?.reserved_quantity ?? 0,
            }
          })
          .sort((x, y) => (x.name || '').localeCompare(y.name || ''))

        setStockRows(combined)
      } else {
        const params = new URLSearchParams()
        params.set('location', location)
        if (itemType) params.set('item_type', itemType)
        const res = await api.get(`/inventory/stock?${params.toString()}`)
        setStockRows(Array.isArray(res.data) ? res.data : [])
        setStockByItemAndLoc({})
      }
    } catch (e) {
      console.error('Failed to load stock', e)
      setError(t('inventory.errors.loadStockFailed'))
    } finally {
      setLoading(false)
    }
  }

  const loadItems = async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (location !== 'ALL') params.set('location', location)
      if (itemType) params.set('item_type', itemType)
      if ((q || '').trim()) params.set('q', q.trim())
      const res = await api.get(`/inventory/items?${params.toString()}`)
      setItems(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('Failed to load items', e)
      setError(t('inventory.errors.loadItemsFailed'))
    } finally {
      setLoading(false)
    }
  }

  const loadMovements = async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (location !== 'ALL') params.set('location', location)
      params.set('limit', '300')
      if (itemType) params.set('item_type', itemType)
      if (subcategoryFilter) params.set('subcategory', subcategoryFilter)
      if (movementFromDate) params.set('from_date', movementFromDate)
      if (movementToDate) params.set('to_date', movementToDate)
      const res = await api.get(`/inventory/movements?${params.toString()}`)
      setMovements(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('Failed to load movements', e)
      setError(t('inventory.errors.loadMovementsFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Keep the item list warm for dropdowns, regardless of tab.
    loadItems()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location, itemType])

  useEffect(() => {
    if (tab === 'Stock') loadStock()
    if (tab === 'Items') loadItems()
    if (tab === 'Movements') loadMovements()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, location, itemType, subcategoryFilter, movementFromDate, movementToDate])

  const startEditItem = (it) => {
    setEditingItemId(it.id)
    setEditForm({
      name: it.name ?? '',
      unit: it.unit ?? '',
      min_level: it.min_level ?? '',
      reorder_level: it.reorder_level ?? '',
      price: it.price ?? '',
      currency: it.currency ?? 'ILS',
      is_active: !!it.is_active,
      submitting: false,
    })
  }

  const cancelEditItem = () => {
    setEditingItemId(null)
    setEditForm({ name: '', unit: '', min_level: '', reorder_level: '', price: '', currency: 'ILS', is_active: true, submitting: false })
  }

  const saveItem = async () => {
    if (!editingItemId) return
    try {
      setEditForm((p) => ({ ...p, submitting: true }))
      const payload = {
        name: (editForm.name || '').trim() || undefined,
        unit: (editForm.unit || '').trim() || undefined,
        is_active: !!editForm.is_active,
        min_level: editForm.min_level === '' ? undefined : Number(editForm.min_level),
        reorder_level: editForm.reorder_level === '' ? undefined : Number(editForm.reorder_level),
        price: editForm.price === '' ? undefined : Number(editForm.price),
        currency: (editForm.currency || '').trim() || undefined,
      }
      await api.patch(`/inventory/items/${editingItemId}`, payload)
      cancelEditItem()
      await loadItems()
      if (tab === 'Stock') await loadStock()
    } catch (e) {
      console.error('Failed to update item', e)
      setError(t('inventory.errors.updateItemFailed'))
    } finally {
      setEditForm((p) => ({ ...p, submitting: false }))
    }
  }

  const createMovement = async (e) => {
    e.preventDefault()
    if (!movementForm.inventory_item_id) return
    const delta = Number(movementForm.change)
    if (Number.isNaN(delta) || delta === 0) return

    try {
      setMovementForm((p) => ({ ...p, submitting: true }))
      await api.post('/inventory/movements', {
        location,
        inventory_item_id: movementForm.inventory_item_id,
        change: delta,
        reason: (movementForm.reason || '').trim() || undefined,
      })
      setMovementForm((p) => ({ ...p, change: '', submitting: false }))
      await loadStock()
      await loadMovements()
      await loadItems()
    } catch (e2) {
      console.error('Failed to create movement', e2)
      const detail = e2?.response?.data?.detail
      setError(detail ? String(detail) : t('inventory.errors.createMovementFailed'))
      setMovementForm((p) => ({ ...p, submitting: false }))
    }
  }

  return (
    <div className="card">
      <div className="inventory-header">
        <div className="inventory-controls">
          <div className="inventory-control">
            <label className="inventory-label">{t('inventory.filters.location')}</label>
            <select className="form-input" value={location} onChange={(e) => setLocation(e.target.value)}>
              {LOCATIONS.map((l) => (
                <option key={l} value={l}>{t(`inventory.locations.${l}`)}</option>
              ))}
            </select>
          </div>

          <div className="inventory-control">
            <label className="inventory-label">{t('inventory.filters.type')}</label>
            <select className="form-input" value={itemType} onChange={(e) => setItemType(e.target.value)}>
              <option value="">{t('inventory.itemTypes.all')}</option>
              <option value="BOTTLE">{t('inventory.itemTypes.BOTTLE')}</option>
              <option value="GARNISH">{t('inventory.itemTypes.GARNISH')}</option>
              <option value="GLASS">{t('inventory.itemTypes.GLASS')}</option>
            </select>
          </div>

          <div className="inventory-control">
            <label className="inventory-label">{t('inventory.filters.subcategory')}</label>
            <select className="form-input" value={subcategoryFilter} onChange={(e) => setSubcategoryFilter(e.target.value)}>
              <option value="">{t('inventory.itemTypes.all')}</option>
              {GROUP_ORDER.map((g) => (
                <option key={g} value={g}>{t(`inventory.groups.${g}`)}</option>
              ))}
            </select>
          </div>

          {(tab === 'Movements') && (
            <>
              <div className="inventory-control">
                <label className="inventory-label">{t('common.from')}</label>
                <input
                  className="form-input"
                  type="date"
                  value={movementFromDate}
                  onChange={(e) => setMovementFromDate(e.target.value)}
                />
              </div>
              <div className="inventory-control">
                <label className="inventory-label">{t('common.to')}</label>
                <input
                  className="form-input"
                  type="date"
                  value={movementToDate}
                  onChange={(e) => setMovementToDate(e.target.value)}
                />
              </div>
            </>
          )}

          {(tab === 'Items') && (
            <div className="inventory-control inventory-control-wide">
              <label className="inventory-label">{t('common.search')}</label>
              <input
                className="form-input"
                placeholder={t('inventory.searchItemsPlaceholder')}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="inventory-tabs">
          {TABS.map((tabKey) => (
            <button
              key={tabKey}
              type="button"
              className={`inventory-tab ${tab === tabKey ? 'active' : ''}`}
              onClick={() => setTab(tabKey)}
            >
              {tabKey === 'Stock' ? t('inventory.tabs.stock') : tabKey === 'Items' ? t('inventory.tabs.items') : t('inventory.tabs.movements')}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {loading && <div className="loading">{t('common.loading')}</div>}

      {!loading && tab === 'Stock' && (
        <div className="inventory-section">
          {(groupStockSections || []).length === 0 ? (
            <div className="empty-state">{t('inventory.emptyGroup')}</div>
          ) : (groupStockSections || []).map((section) => (
            <div key={section.key} style={{ marginTop: section.key === 'spirit' ? 0 : 18 }}>
              <h3 style={{ margin: '0 0 10px 0' }}>{section.title}</h3>
              {(section.items || []).length === 0 ? (
                <div className="empty-state">{t('inventory.emptyGroup')}</div>
              ) : (
                <div className="inventory-table">
                  {location === 'ALL' ? (
                    <>
                      <div className="inventory-table-header inventory-table-header-stock-all">
                        <div>{t('inventory.columns.name')}</div>
                        <div>{t('inventory.columns.subcategory')}</div>
                        <div className="right">{t('inventory.columns.barQty')}</div>
                        <div className="right">{t('inventory.columns.whQty')}</div>
                        <div>{t('inventory.columns.unit')}</div>
                        <div className="right">{t('inventory.columns.price')}</div>
                      </div>
                      {(section.items || []).map((r) => (
                        <div key={r.inventory_item_id} className="inventory-table-row inventory-table-row-stock-all">
                          <div className="name">{r.name}</div>
                          <div className="muted">{displaySubcategory(r)}</div>
                          <div className="right">{formatNumber(r.quantity_bar)}</div>
                          <div className="right">{formatNumber(r.quantity_warehouse)}</div>
                          <div className="muted">{r.unit}</div>
                          <div className="right muted">{displayPrice(r)}</div>
                        </div>
                      ))}
                    </>
                  ) : (
                    <>
                      <div className="inventory-table-header inventory-table-header-stock">
                        <div>{t('inventory.columns.name')}</div>
                        <div>{t('inventory.columns.subcategory')}</div>
                        <div className="right">{t('inventory.columns.qty')}</div>
                        <div className="right">{t('inventory.columns.reserved')}</div>
                        <div>{t('inventory.columns.unit')}</div>
                        <div className="right">{t('inventory.columns.price')}</div>
                      </div>
                      {(section.items || []).map((r) => (
                        <div key={r.inventory_item_id} className="inventory-table-row inventory-table-row-stock">
                          <div className="name">{r.name}</div>
                          <div className="muted">{displaySubcategory(r)}</div>
                          <div className="right">{formatNumber(r.quantity)}</div>
                          <div className="right">{formatNumber(r.reserved_quantity)}</div>
                          <div className="muted">{r.unit}</div>
                          <div className="right muted">{displayPrice(r)}</div>
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && tab === 'Items' && (
        <div className="inventory-section">
          {(groupItemsSections || []).length === 0 ? (
            <div className="empty-state">{t('inventory.emptyGroup')}</div>
          ) : (
            (groupItemsSections || []).map((section) => (
              <div key={section.key} style={{ marginTop: section.key === 'spirit' ? 0 : 18 }}>
                <h3 style={{ margin: '0 0 10px 0' }}>{section.title}</h3>
                {(section.items || []).length === 0 ? (
                  <div className="empty-state">{t('inventory.emptyGroup')}</div>
                ) : (
                  <div className="inventory-table">
                  <div className={`inventory-table-header ${location === 'ALL' ? 'inventory-table-header-items-all' : 'inventory-table-header-items'}`}>
                    <div>{t('inventory.columns.name')}</div>
                    <div>{t('inventory.columns.unit')}</div>
                    <div>{t('inventory.columns.subcategory')}</div>
                    <div className="right">{t('inventory.columns.price')}</div>
                    {location === 'ALL' ? (
                      <>
                        <div className="right">{t('inventory.columns.barQty')}</div>
                        <div className="right">{t('inventory.columns.whQty')}</div>
                      </>
                    ) : (
                      <div className="right">{t('inventory.columns.qty')} ({t(`inventory.locations.${location}`)})</div>
                    )}
                    <div>{t('inventory.columns.status')}</div>
                    <div />
                  </div>
                  {(section.items || []).map((it) => {
                    const isEditing = editingItemId === it.id
                    const qty = it?.stock?.quantity ?? 0
                    const barQty = stockByItemAndLoc?.[it.id]?.BAR?.quantity ?? 0
                    const whQty = stockByItemAndLoc?.[it.id]?.WAREHOUSE?.quantity ?? 0
                    return (
                      <div key={it.id} className={`inventory-table-row ${location === 'ALL' ? 'inventory-table-row-items-all' : 'inventory-table-row-items'}`}>
                        <div className="name">
                          {isEditing ? (
                            <input
                              className="form-input"
                              value={editForm.name}
                              onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
                            />
                          ) : (
                            it.name
                          )}
                        </div>
                        <div>
                          {isEditing ? (
                            <input
                              className="form-input"
                              value={editForm.unit}
                              onChange={(e) => setEditForm((p) => ({ ...p, unit: e.target.value }))}
                            />
                          ) : (
                            <span className="muted">{it.unit}</span>
                          )}
                        </div>
                        <div className="muted">{displaySubcategory(it)}</div>
                        <div className="right muted">
                          {isEditing ? (
                            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                              <input
                                className="form-input"
                                style={{ width: 120 }}
                                type="number"
                                step="0.01"
                                value={editForm.price}
                                onChange={(e) => setEditForm((p) => ({ ...p, price: e.target.value }))}
                              />
                              <input
                                className="form-input"
                                style={{ width: 70 }}
                                value={editForm.currency}
                                onChange={(e) => setEditForm((p) => ({ ...p, currency: e.target.value }))}
                              />
                            </div>
                          ) : (
                            displayPrice(it)
                          )}
                        </div>
                        {location === 'ALL' ? (
                          <>
                            <div className="right">{formatNumber(barQty)}</div>
                            <div className="right">{formatNumber(whQty)}</div>
                          </>
                        ) : (
                          <div className="right">{formatNumber(qty)}</div>
                        )}
                        <div>
                          {isEditing ? (
                            <label className="inventory-toggle">
                              <input
                                type="checkbox"
                                checked={!!editForm.is_active}
                                onChange={(e) => setEditForm((p) => ({ ...p, is_active: e.target.checked }))}
                              />
                              {t('inventory.status.activeToggle')}
                            </label>
                          ) : (
                            <span className={`pill ${it.is_active ? 'pill-ok' : 'pill-muted'}`}>
                              {it.is_active ? t('inventory.status.active') : t('inventory.status.inactive')}
                            </span>
                          )}
                        </div>
                        <div className="actions">
                          {isAdmin && (
                            isEditing ? (
                              <>
                                <button type="button" className="button-primary" disabled={editForm.submitting} onClick={saveItem}>
                                  {t('common.save')}
                                </button>
                                <button type="button" className="button-secondary" disabled={editForm.submitting} onClick={cancelEditItem}>
                                  {t('common.cancel')}
                                </button>
                              </>
                            ) : (
                              <button type="button" className="button-edit" onClick={() => startEditItem(it)}>
                                {t('common.edit')}
                              </button>
                            )
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
                )}
              </div>
            ))
          )}

          {isAdmin && editingItemId && (
            <div className="inventory-subpanel">
              <div className="inventory-subpanel-title">{t('inventory.reorder.title')}</div>
              <div className="inventory-subpanel-grid">
                <div>
                  <label className="inventory-label">{t('inventory.reorder.minLevel')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.001"
                    value={editForm.min_level}
                    onChange={(e) => setEditForm((p) => ({ ...p, min_level: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="inventory-label">{t('inventory.reorder.reorderLevel')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.001"
                    value={editForm.reorder_level}
                    onChange={(e) => setEditForm((p) => ({ ...p, reorder_level: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="inventory-label">{t('inventory.reorder.price')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.01"
                    value={editForm.price}
                    onChange={(e) => setEditForm((p) => ({ ...p, price: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="inventory-label">{t('inventory.reorder.currency')}</label>
                  <input
                    className="form-input"
                    value={editForm.currency}
                    onChange={(e) => setEditForm((p) => ({ ...p, currency: e.target.value }))}
                  />
                </div>
              </div>
              <div className="inventory-subpanel-actions">
                <button type="button" className="button-primary" disabled={editForm.submitting} onClick={saveItem}>
                  {t('inventory.actions.saveSettings')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && tab === 'Movements' && (
        <div className="inventory-section">
          {isAdmin && (
            <form className="inventory-movement-form" onSubmit={createMovement}>
              <div className="inventory-movement-row">
                {location === 'ALL' && (
                  <div className="empty-state" style={{ gridColumn: '1 / -1', padding: '1rem' }}>
                    {t('inventory.movement.selectLocationHelp')}
                  </div>
                )}
                <div className="inventory-control inventory-control-wide">
                  <label className="inventory-label">{t('inventory.movement.item')}</label>
                  <select
                    className="form-input"
                    value={movementForm.inventory_item_id}
                    onChange={(e) => setMovementForm((p) => ({ ...p, inventory_item_id: e.target.value }))}
                    disabled={location === 'ALL'}
                  >
                    <option value="">{t('inventory.movement.selectItem')}</option>
                    {(items || [])
                      .filter((it) => it?.is_active)
                      .map((it) => (
                        <option key={it.id} value={it.id}>
                          {it.name} ({it.item_type})
                        </option>
                      ))}
                  </select>
                </div>

                <div className="inventory-control">
                  <label className="inventory-label">{t('inventory.columns.change')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.001"
                    placeholder={t('inventory.movement.changePlaceholder')}
                    value={movementForm.change}
                    onChange={(e) => setMovementForm((p) => ({ ...p, change: e.target.value }))}
                    disabled={location === 'ALL'}
                  />
                </div>

                <div className="inventory-control">
                  <label className="inventory-label">{t('inventory.movement.reason')}</label>
                  <select
                    className="form-input"
                    value={movementForm.reason}
                    onChange={(e) => setMovementForm((p) => ({ ...p, reason: e.target.value }))}
                    disabled={location === 'ALL'}
                  >
                    <option value="PURCHASE">{t('inventory.movementReasons.PURCHASE')}</option>
                    <option value="USAGE">{t('inventory.movementReasons.USAGE')}</option>
                    <option value="WASTE">{t('inventory.movementReasons.WASTE')}</option>
                    <option value="ADJUSTMENT">{t('inventory.movementReasons.ADJUSTMENT')}</option>
                    <option value="TRANSFER">{t('inventory.movementReasons.TRANSFER')}</option>
                  </select>
                </div>

                <button
                  type="submit"
                  className="button-primary"
                  disabled={location === 'ALL' || movementForm.submitting || !movementForm.inventory_item_id}
                >
                  {t('inventory.actions.addMovement')}
                </button>
              </div>
            </form>
          )}

          <div className="inventory-table">
            <div className={`inventory-table-header ${location === 'ALL' ? 'inventory-table-header-movements-all' : 'inventory-table-header-movements'}`}>
              <div>{t('inventory.columns.when')}</div>
              {location === 'ALL' && <div>{t('inventory.columns.location')}</div>}
              <div>{t('inventory.columns.item')}</div>
              <div>{t('inventory.columns.subcategory')}</div>
              <div className="right">{t('inventory.columns.change')}</div>
              <div>{t('inventory.columns.reason')}</div>
            </div>
            {(movements || []).map((m) => (
              <div key={m.id} className={`inventory-table-row ${location === 'ALL' ? 'inventory-table-row-movements-all' : 'inventory-table-row-movements'}`}>
                <div className="muted">{m.created_at ? new Date(m.created_at).toLocaleString(lang === 'he' ? 'he-IL' : 'en-US') : ''}</div>
                {location === 'ALL' && <div className="muted">{t(`inventory.locations.${m.location}`)}</div>}
                <div className="name">{m.item_name || m.inventory_item_id}</div>
                <div className="muted">
                  {(() => {
                    const raw = (m.subcategory_name || '').trim()
                    if (!raw) return ''
                    return t(`inventory.groups.${raw}`, { defaultValue: raw })
                  })()}
                </div>
                <div className={`right ${Number(m.change) < 0 ? 'neg' : 'pos'}`}>{formatNumber(m.change)}</div>
                <div className="muted">{m.reason || ''}</div>
              </div>
            ))}
            {(movements || []).length === 0 && (
              <div className="empty-state">{t('inventory.movementsEmpty')}</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

