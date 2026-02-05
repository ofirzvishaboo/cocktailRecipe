import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import DatePicker, { registerLocale } from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import he from 'date-fns/locale/he'
import api from '../api'

registerLocale('he', he)
import { useAuth } from '../contexts/AuthContext'
import Select from '../components/common/Select'
import InventorySearchInput from '../components/inventory/InventorySearchInput'
import '../styles/inventory.css'

const LOCATIONS = ['ALL', 'BAR', 'WAREHOUSE']
const TABS = ['Stock', 'Items', 'Movements']
const GROUP_ORDER = ['Spirit', 'Liqueur', 'Juice', 'Syrup', 'Sparkling', 'Garnish', 'Glass', 'Uncategorized']
const SUBCATEGORY_FILTER_HIDDEN = new Set(['Garnish', 'Glass', 'Bottle', 'Bottles'])
const SUBCATEGORY_FILTER_ORDER = GROUP_ORDER.filter((g) => !SUBCATEGORY_FILTER_HIDDEN.has(g))

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
  const showPrices = !!isAdmin
  const showMovements = !!isAdmin
  const MIN_VISIBLE_STOCK_QTY = 1 // show only items with quantity >= 1
  const [filtersOpen, setFiltersOpen] = useState(false)

  const [location, setLocation] = useState('ALL')
  const [tab, setTab] = useState('Stock')
  const [movementLocation, setMovementLocation] = useState('WAREHOUSE')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [stockRows, setStockRows] = useState([])
  const [stockByItemAndLoc, setStockByItemAndLoc] = useState({})
  const [items, setItems] = useState([])
  const [movements, setMovements] = useState([])

  const [itemType, setItemType] = useState('')
  const [subcategoryFilter, setSubcategoryFilter] = useState('')
  const [q, setQ] = useState('')
  const [stockSearch, setStockSearch] = useState('')
  const [movementFromDate, setMovementFromDate] = useState('')
  const [movementToDate, setMovementToDate] = useState('')
  const [movementItemSearch, setMovementItemSearch] = useState('')
  const [movementEvents, setMovementEvents] = useState([])
  const [movementEventId, setMovementEventId] = useState('')
  const [consumingEvent, setConsumingEvent] = useState(false)
  const [unconsumingEvent, setUnconsumingEvent] = useState(false)
  const [eventConsumed, setEventConsumed] = useState(false)

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
    reason: 'PURCHASE',
    submitting: false,
  })
  const [movementStock, setMovementStock] = useState(null)
  const [eventConsumeExpanded, setEventConsumeExpanded] = useState(false)

  const filteredItems = useMemo(() => {
    const query = (q || '').trim().toLowerCase()
    if (!query) return items
    return (items || []).filter((it) => {
      const name = (it?.name || '').toLowerCase()
      const ingredientName = (it?.ingredient_name || '').toLowerCase()
      const ingredientNameHe = (it?.ingredient_name_he || '').toLowerCase()
      return name.includes(query) || ingredientName.includes(query) || ingredientNameHe.includes(query)
    })
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

  const displayIngredient = (row) => {
    const en = (row?.ingredient_name || '').trim()
    const he = (row?.ingredient_name_he || '').trim()
    if (lang === 'he') return he || en
    return en || he
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
    // Hide empty categories in Inventory.
    return all.filter((s) => (s.items || []).length > 0)
  }, [sortedItems, subcategoryFilter, t])

  const groupStockSections = useMemo(() => {
    const query = (stockSearch || '').trim().toLowerCase()
    const hasStock = (r) => {
      if (!r) return false
      if (location === 'ALL') {
        const total = Number(r?.quantity_bar || 0) + Number(r?.quantity_warehouse || 0)
        return total >= MIN_VISIBLE_STOCK_QTY
      }
      return Number(r?.quantity || 0) >= MIN_VISIBLE_STOCK_QTY
    }

    const base = (stockRows || []).filter(hasStock)
    const rows = query
      ? base.filter((r) => {
          const name = (r?.name || '').toLowerCase()
          const ingredientName = (r?.ingredient_name || '').toLowerCase()
          const ingredientNameHe = (r?.ingredient_name_he || '').toLowerCase()
          return name.includes(query) || ingredientName.includes(query) || ingredientNameHe.includes(query)
        })
      : base
    const sections = {}
    for (const g of GROUP_ORDER) sections[g] = []
    for (const r of rows) {
      const g = groupKeyForRow(r)
      sections[g].push(r)
    }
    const all = GROUP_ORDER.map((g) => ({ title: t(`inventory.groups.${g}`), key: g.toLowerCase(), items: sections[g] || [] }))
    if (subcategoryFilter) {
      return all.filter((s) => (s.key || '') === (subcategoryFilter || '').toLowerCase())
    }
    // Hide empty categories in Inventory.
    return all.filter((s) => (s.items || []).length > 0)
  }, [stockRows, stockSearch, subcategoryFilter, t, location])

  const movementItemOptions = useMemo(() => {
    const query = (movementItemSearch || '').trim().toLowerCase()
    const all = (items || []).filter((it) => it?.is_active)
    const filtered = query
      ? all.filter((it) => {
          const name = (it?.name || '').toLowerCase()
          const ingredientName = (it?.ingredient_name || '').toLowerCase()
          const ingredientNameHe = (it?.ingredient_name_he || '').toLowerCase()
          return name.startsWith(query) || ingredientName.includes(query) || ingredientNameHe.includes(query)
        })
      : all
    return filtered.map((it) => ({ value: it.id, label: `${it.name}` }))
  }, [items, movementItemSearch])

  const visibleMovements = useMemo(() => {
    const query = (movementItemSearch || '').trim().toLowerCase()
    if (!query) return movements || []
    return (movements || []).filter((m) => {
      const name = (m?.item_name || '').toLowerCase()
      const reason = (m?.reason || '').toLowerCase()
      const sub = (m?.subcategory_name || '').toLowerCase()
      const loc = (m?.location || '').toLowerCase()
      return name.includes(query) || reason.includes(query) || sub.includes(query) || loc.includes(query)
    })
  }, [movements, movementItemSearch])

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
    if (!showMovements) {
      setMovements([])
      return
    }
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

  const loadMovementEvents = async () => {
    if (!showMovements) {
      setMovementEvents([])
      return
    }
    try {
      const res = await api.get('/events')
      setMovementEvents(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('Failed to load movement events', e)
      // Don't block the page if events fail; show error toast/message
      setError(t('inventory.errors.loadEventsFailed'))
      setMovementEvents([])
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
    if (tab === 'Movements') {
      if (showMovements) loadMovements()
      else setTab('Stock')
      if (showMovements) loadMovementEvents()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, location, itemType, subcategoryFilter, movementFromDate, movementToDate, showMovements])

  const visibleTabs = showMovements ? TABS : ['Stock', 'Items']

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
    const effectiveLocation = location === 'ALL' ? movementLocation : location
    let delta = Math.trunc(Number(movementForm.change))
    if (Number.isNaN(delta) || delta === 0) return

    try {
      setMovementForm((p) => ({ ...p, submitting: true }))
      const reason = (movementForm.reason || '').trim() || undefined
      const reasonUpper = (reason || '').toUpperCase()
      if (reasonUpper === 'USAGE' || reasonUpper === 'WASTE') {
        delta = -Math.abs(delta)
      }
      if (reason === 'TRANSFER') {
        const from_location = effectiveLocation
        const to_location = effectiveLocation === 'BAR' ? 'WAREHOUSE' : 'BAR'
        const qty = Math.abs(delta)
        if (!qty) return
        await api.post('/inventory/transfers', {
          from_location,
          to_location,
          inventory_item_id: movementForm.inventory_item_id,
          quantity: qty,
          reason: reason,
        })
      } else {
        await api.post('/inventory/movements', {
          location: effectiveLocation,
          inventory_item_id: movementForm.inventory_item_id,
          change: delta,
          reason: reason,
        })
      }
      setMovementForm((p) => ({ ...p, change: '', submitting: false }))
      if (movementForm.inventory_item_id) {
        try {
          const s = await api.get(`/inventory/stock/item/${movementForm.inventory_item_id}`)
          setMovementStock(s.data || null)
        } catch {
          // ignore
        }
      }
      await loadStock()
      await loadMovements()
      await loadItems()
    } catch (e2) {
      console.error('Failed to create movement', e2)
      const detail = e2?.response?.data?.detail || e2?.message
      setError(detail ? String(detail) : t('inventory.errors.createMovementFailed'))
      setMovementForm((p) => ({ ...p, submitting: false }))
    }
  }

  const consumeEvent = async () => {
    if (!movementEventId) return
    if (eventConsumed) return
    try {
      setConsumingEvent(true)
      setError('')
      await api.post('/inventory/consume-event', {
        event_id: movementEventId,
        location,
      })
      await loadStock()
      await loadMovements()
      setEventConsumed(true)
    } catch (e) {
      console.error('Failed to consume event', e)
      const detail = e?.response?.data?.detail || e?.message
      setError(detail ? String(detail) : t('inventory.errors.consumeEventFailed'))
    } finally {
      setConsumingEvent(false)
    }
  }

  const unconsumeEvent = async () => {
    if (!movementEventId) return
    try {
      setUnconsumingEvent(true)
      setError('')
      await api.post('/inventory/unconsume-event', {
        event_id: movementEventId,
        location: 'ALL',
      })
      await loadStock()
      await loadMovements()
      setEventConsumed(false)
    } catch (e) {
      console.error('Failed to unconsume event', e)
      const detail = e?.response?.data?.detail || e?.message
      setError(detail ? String(detail) : t('inventory.errors.consumeEventFailed'))
    } finally {
      setUnconsumingEvent(false)
    }
  }

  // Load consumption status so we can require "unconsume" before re-consuming.
  useEffect(() => {
    const id = movementEventId
    if (!id) {
      setEventConsumed(false)
      return
    }
    let cancelled = false
    const load = async () => {
      try {
        const res = await api.get(`/inventory/events/${id}/consumption`)
        if (!cancelled) setEventConsumed(!!res?.data?.is_consumed)
      } catch {
        if (!cancelled) setEventConsumed(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [movementEventId])

  useEffect(() => {
    const id = movementForm.inventory_item_id
    if (!id) {
      setMovementStock(null)
      return
    }
    const load = async () => {
      try {
        const res = await api.get(`/inventory/stock/item/${id}`)
        setMovementStock(res.data || null)
      } catch {
        setMovementStock(null)
      }
    }
    load()
  }, [movementForm.inventory_item_id])

  // When a specific location is selected, keep the movement location in sync.
  useEffect(() => {
    if (location !== 'ALL') setMovementLocation(location)
  }, [location])

  return (
    <div className="card">
      <div className="inventory-header">
        <div className="inventory-header-top">
          {visibleTabs.map((tabKey) => (
            <button
              key={tabKey}
              type="button"
              className={`inventory-tab ${tab === tabKey ? 'active' : ''}`}
              onClick={() => setTab(tabKey)}
            >
              {tabKey === 'Stock' ? t('inventory.tabs.stock') : tabKey === 'Items' ? t('inventory.tabs.items') : t('inventory.tabs.movements')}
            </button>
          ))}
          <button
            type="button"
            className={`inventory-tab inventory-tab-filter ${filtersOpen ? 'active' : ''}`}
            onClick={() => setFiltersOpen((p) => !p)}
            aria-label={filtersOpen ? t('inventory.filters.hide') : t('inventory.filters.show')}
            title={filtersOpen ? t('inventory.filters.hide') : t('inventory.filters.show')}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M2 4h12M4 8h8M6 12h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {(tab === 'Items') && (
          <div className="inventory-control inventory-control-wide" style={{ marginTop: '0.75rem' }}>
            <InventorySearchInput
              id="inv-items-search"
              label={t('common.search')}
              value={q}
              onValueChange={(v) => setQ(v)}
              placeholder={t('inventory.searchItemsPlaceholder')}
            />
          </div>
        )}

        {(tab === 'Stock') && (
          <div className="inventory-control inventory-control-wide" style={{ marginTop: '0.75rem' }}>
            <InventorySearchInput
              id="inv-stock-search"
              label={t('common.search')}
              value={stockSearch}
              onValueChange={(v) => setStockSearch(v)}
              placeholder={t('inventory.searchItemsPlaceholder')}
            />
          </div>
        )}

        {filtersOpen && (
          <div className="inventory-controls">
            <div className="inventory-control">
              <label className="inventory-label" htmlFor="inv-location">{t('inventory.filters.location')}</label>
              <Select
                id="inv-location"
                value={location}
                onChange={(v) => setLocation(v)}
                ariaLabel={t('inventory.filters.location')}
                options={LOCATIONS.map((l) => ({ value: l, label: t(`inventory.locations.${l}`) }))}
              />
            </div>

            <div className="inventory-control">
              <label className="inventory-label" htmlFor="inv-type">{t('inventory.filters.type')}</label>
              <Select
                id="inv-type"
                value={itemType}
                onChange={(v) => setItemType(v)}
                ariaLabel={t('inventory.filters.type')}
                placeholder={t('inventory.itemTypes.all')}
                options={[
                  { value: 'BOTTLE', label: t('inventory.itemTypes.BOTTLE') },
                  { value: 'GARNISH', label: t('inventory.itemTypes.GARNISH') },
                  { value: 'GLASS', label: t('inventory.itemTypes.GLASS') },
                ]}
              />
            </div>

            <div className="inventory-control">
              <label className="inventory-label" htmlFor="inv-subcategory">{t('inventory.filters.subcategory')}</label>
              <Select
                id="inv-subcategory"
                value={subcategoryFilter}
                onChange={(v) => setSubcategoryFilter(v)}
                ariaLabel={t('inventory.filters.subcategory')}
                placeholder={t('inventory.itemTypes.all')}
                options={SUBCATEGORY_FILTER_ORDER.map((g) => ({ value: g, label: t(`inventory.groups.${g}`) }))}
              />
            </div>

            {(tab === 'Movements') && (
              <div className="inventory-control inventory-control-wide inventory-dates-row">
                <div className="inventory-control">
                  <label className="inventory-label">{t('common.from')}</label>
                  <DatePicker
                    id="movement-from-date"
                    className="form-input inventory-datepicker-input"
                    dateFormat={lang === 'he' ? 'dd/MM/yyyy' : 'MM/dd/yyyy'}
                    locale={lang === 'he' ? 'he' : 'en'}
                    selected={movementFromDate ? new Date(movementFromDate + 'T12:00:00') : null}
                    onChange={(d) => setMovementFromDate(d ? d.toISOString().slice(0, 10) : '')}
                    isClearable
                    placeholderText={lang === 'he' ? 'dd/mm/yyyy' : 'mm/dd/yyyy'}
                  />
                </div>
                <div className="inventory-control">
                  <label className="inventory-label">{t('common.to')}</label>
                  <DatePicker
                    id="movement-to-date"
                    className="form-input inventory-datepicker-input"
                    dateFormat={lang === 'he' ? 'dd/MM/yyyy' : 'MM/dd/yyyy'}
                    locale={lang === 'he' ? 'he' : 'en'}
                    selected={movementToDate ? new Date(movementToDate + 'T12:00:00') : null}
                    onChange={(d) => setMovementToDate(d ? d.toISOString().slice(0, 10) : '')}
                    isClearable
                    placeholderText={lang === 'he' ? 'dd/mm/yyyy' : 'mm/dd/yyyy'}
                  />
                </div>
                <button type="button" className="button-primary inventory-dates-row-btn" onClick={() => { setMovementFromDate(''); setMovementToDate('') }}>
                  {t('common.clear')}
                </button>
                <button type="button" className="button-primary inventory-dates-row-btn" onClick={loadMovements} disabled={loading}>
                  {t('common.refresh')}
                </button>
              </div>
            )}
          </div>
        )}
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
                      <div className={`inventory-table-header ${showPrices ? 'inventory-table-header-stock-all' : 'inventory-table-header-stock-all-noprice'}`}>
                        <div>{t('inventory.columns.name')}</div>
                        <div>{t('inventory.columns.ingredient')}</div>
                        <div className="right">{t('inventory.columns.barQty')}</div>
                        <div className="right">{t('inventory.columns.whQty')}</div>
                        <div>{t('inventory.columns.unit')}</div>
                        {showPrices && <div className="right">{t('inventory.columns.price')}</div>}
                      </div>
                      {(section.items || []).map((r) => (
                        <div key={r.inventory_item_id} className={`inventory-table-row ${showPrices ? 'inventory-table-row-stock-all' : 'inventory-table-row-stock-all-noprice'}`}>
                          <div className="name">{r.name}</div>
                          <div className="muted">{displayIngredient(r)}</div>
                          <div className="right">{formatNumber(r.quantity_bar)}</div>
                          <div className="right">{formatNumber(r.quantity_warehouse)}</div>
                          <div className="muted">{r.unit}</div>
                          {showPrices && <div className="right muted">{displayPrice(r)}</div>}
                        </div>
                      ))}
                    </>
                  ) : (
                    <>
                      <div className={`inventory-table-header ${showPrices ? 'inventory-table-header-stock' : 'inventory-table-header-stock-noprice'}`}>
                        <div>{t('inventory.columns.name')}</div>
                        <div>{t('inventory.columns.ingredient')}</div>
                        <div className="right">{t('inventory.columns.qty')}</div>
                        <div className="right">{t('inventory.columns.reserved')}</div>
                        <div>{t('inventory.columns.unit')}</div>
                        {showPrices && <div className="right">{t('inventory.columns.price')}</div>}
                      </div>
                      {(section.items || []).map((r) => (
                        <div key={r.inventory_item_id} className={`inventory-table-row ${showPrices ? 'inventory-table-row-stock' : 'inventory-table-row-stock-noprice'}`}>
                          <div className="name">{r.name}</div>
                          <div className="muted">{displayIngredient(r)}</div>
                          <div className="right">{formatNumber(r.quantity)}</div>
                          <div className="right">{formatNumber(r.reserved_quantity)}</div>
                          <div className="muted">{r.unit}</div>
                          {showPrices && <div className="right muted">{displayPrice(r)}</div>}
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
                  <div
                    className={`inventory-table-header ${
                      showPrices
                        ? (location === 'ALL' ? 'inventory-table-header-items-all' : 'inventory-table-header-items')
                        : (location === 'ALL' ? 'inventory-table-header-items-all-view' : 'inventory-table-header-items-view')
                    }`}
                  >
                    <div>{t('inventory.columns.name')}</div>
                    <div>{t('inventory.columns.unit')}</div>
                    <div>{t('inventory.columns.ingredient')}</div>
                    {showPrices && <div className="right">{t('inventory.columns.price')}</div>}
                    {location === 'ALL' ? (
                      <>
                        <div className="right">{t('inventory.columns.barQty')}</div>
                        <div className="right">{t('inventory.columns.whQty')}</div>
                      </>
                    ) : (
                      <div className="right">{t('inventory.columns.qty')} ({t(`inventory.locations.${location}`)})</div>
                    )}
                    <div>{t('inventory.columns.status')}</div>
                    {isAdmin && <div />}
                  </div>
                  {(section.items || []).map((it) => {
                    const isEditing = editingItemId === it.id
                    const qty = it?.stock?.quantity ?? 0
                    const barQty = stockByItemAndLoc?.[it.id]?.BAR?.quantity ?? 0
                    const whQty = stockByItemAndLoc?.[it.id]?.WAREHOUSE?.quantity ?? 0
                    return (
                      <div
                        key={it.id}
                        className={`inventory-table-row ${
                          showPrices
                            ? (location === 'ALL' ? 'inventory-table-row-items-all' : 'inventory-table-row-items')
                            : (location === 'ALL' ? 'inventory-table-row-items-all-view' : 'inventory-table-row-items-view')
                        }`}
                      >
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
                        <div className="muted">{displayIngredient(it)}</div>
                        {showPrices && (
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
                        )}
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
                        {isAdmin && (
                          <div className="actions">
                            {isEditing ? (
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
                            )}
                          </div>
                        )}
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
                    step="1"
                    value={editForm.min_level}
                    onChange={(e) => setEditForm((p) => ({ ...p, min_level: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="inventory-label">{t('inventory.reorder.reorderLevel')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="1"
                    value={editForm.reorder_level}
                    onChange={(e) => setEditForm((p) => ({ ...p, reorder_level: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="inventory-label">{t('inventory.reorder.price')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="1"
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

      {!loading && tab === 'Movements' && showMovements && (
        <div className="inventory-section">
          {isAdmin && (
            <>
              <div style={{ marginBottom: '0.75rem' }}>
                <button
                  type="button"
                  className="inventory-tab"
                  onClick={() => setEventConsumeExpanded((p) => !p)}
                  style={{ marginBottom: eventConsumeExpanded ? '0.75rem' : 0 }}
                >
                  {eventConsumeExpanded ? '▲' : '▼'} {t('inventory.movement.eventConsume')}
                </button>
              </div>
              {eventConsumeExpanded && (
                <div className="inventory-movement-event-panel">
                <div className="inventory-control">
                  <label className="inventory-label">{t('inventory.movement.event')}</label>
                  <Select
                    id="inv-movement-event"
                    value={movementEventId}
                    onChange={(v) => setMovementEventId(v)}
                    ariaLabel={t('inventory.movement.event')}
                    placeholder={t('inventory.movement.selectEvent')}
                    disabled={consumingEvent}
                    options={(movementEvents || []).map((ev) => ({
                      value: ev.id,
                      label: `${ev.name || t('inventory.movement.unnamedEvent')} (${ev.event_date})`,
                    }))}
                  />
                </div>
                <div className="inventory-control">
                  <label className="inventory-label">{t('inventory.movement.consumeFrom')}</label>
                  <div className="muted" style={{ padding: '0.6rem 0.75rem' }}>
                    {location === 'ALL' ? t('inventory.locations.ALL') : t(`inventory.locations.${location}`)}
                  </div>
                </div>
                <div className="inventory-control">
                  <label className="inventory-label">&nbsp;</label>
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="button-edit"
                      disabled={!movementEventId || !eventConsumed || consumingEvent || unconsumingEvent}
                      onClick={unconsumeEvent}
                    >
                      {unconsumingEvent ? t('inventory.movement.unconsumingEvent') : t('inventory.movement.unconsumeEvent')}
                    </button>
                    <button
                      type="button"
                      className="button-primary"
                      disabled={consumingEvent || unconsumingEvent || !movementEventId || eventConsumed}
                      onClick={consumeEvent}
                    >
                      {eventConsumed ? t('inventory.movement.consumed') : (consumingEvent ? t('inventory.movement.consumingEvent') : t('inventory.movement.consumeEvent'))}
                    </button>
                  </div>
                </div>
              </div>
              )}

              <form className="inventory-movement-form" onSubmit={createMovement}>
                <div className="inventory-movement-row">
                  {location === 'ALL' && (
                    <div className="inventory-control">
                      <label className="inventory-label">{t('inventory.movement.applyToLocation')}</label>
                      <Select
                        id="inv-movement-location"
                        value={movementLocation}
                        onChange={(v) => setMovementLocation(v)}
                        ariaLabel={t('inventory.movement.applyToLocation')}
                        options={['BAR', 'WAREHOUSE'].map((l) => ({ value: l, label: t(`inventory.locations.${l}`) }))}
                      />
                    </div>
                  )}

                  <div className="inventory-control inventory-control-wide inventory-control-stack">
                  <InventorySearchInput
                    id="inv-movement-item"
                    label={t('inventory.movement.item')}
                    value={movementItemSearch}
                    onValueChange={(v) => setMovementItemSearch(v)}
                    placeholder={t('common.search')}
                    options={movementItemOptions}
                    onSelectValue={(id) => setMovementForm((p) => ({ ...p, inventory_item_id: id || '' }))}
                    className=""
                  />
                  {movementStock && (
                    <div className="inventory-movement-stock">
                      <div className="inventory-movement-stock-title">{t('inventory.movement.currentStock')}</div>
                      <div className="inventory-movement-stock-grid">
                        <div className="inventory-movement-stock-cell">
                          <span className="muted">{t('inventory.locations.BAR')}</span>
                          <span className="name">{formatNumber(movementStock?.BAR?.quantity ?? 0)}</span>
                        </div>
                        <div className="inventory-movement-stock-cell">
                          <span className="muted">{t('inventory.locations.WAREHOUSE')}</span>
                          <span className="name">{formatNumber(movementStock?.WAREHOUSE?.quantity ?? 0)}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="inventory-control">
                  <label className="inventory-label">{t('inventory.columns.change')}</label>
                  <input
                    className="form-input"
                    type="number"
                    step="1"
                    placeholder={t('inventory.movement.changePlaceholder')}
                    value={movementForm.change}
                    onChange={(e) => setMovementForm((p) => ({ ...p, change: e.target.value }))}
                  />
                </div>

                <div className="inventory-control">
                  <label className="inventory-label">{t('inventory.movement.reason')}</label>
                  <Select
                    id="inv-movement-reason"
                    value={movementForm.reason}
                    onChange={(v) => setMovementForm((p) => ({ ...p, reason: v }))}
                    ariaLabel={t('inventory.movement.reason')}
                    options={[
                      { value: 'PURCHASE', label: t('inventory.movementReasons.PURCHASE') },
                      { value: 'USAGE', label: t('inventory.movementReasons.USAGE') },
                      { value: 'WASTE', label: t('inventory.movementReasons.WASTE') },
                      { value: 'ADJUSTMENT', label: t('inventory.movementReasons.ADJUSTMENT') },
                      { value: 'TRANSFER', label: t('inventory.movementReasons.TRANSFER') },
                    ]}
                  />
                </div>

                <button
                  type="submit"
                  className="button-primary"
                  disabled={movementForm.submitting || !movementForm.inventory_item_id}
                >
                  {t('inventory.actions.addMovement')}
                </button>
              </div>
            </form>
            </>
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
            {(visibleMovements || []).map((m) => (
              <div key={m.id} className={`inventory-table-row ${location === 'ALL' ? 'inventory-table-row-movements-all' : 'inventory-table-row-movements'}`}>
                <div className="muted">{m.created_at ? new Date(m.created_at).toLocaleDateString(lang === 'he' ? 'he-IL' : 'en-US') : ''}</div>
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
            {(visibleMovements || []).length === 0 && (
              <div className="empty-state">{t('inventory.movementsEmpty')}</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

