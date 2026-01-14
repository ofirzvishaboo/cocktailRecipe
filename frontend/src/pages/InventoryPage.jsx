import { useEffect, useMemo, useState } from 'react'
import api from '../api'
import { useAuth } from '../contexts/AuthContext'
import '../styles/inventory.css'

const LOCATIONS = ['ALL', 'BAR', 'WAREHOUSE']
const TABS = ['Stock', 'Items', 'Movements']

function formatNumber(n) {
  const x = Number(n)
  if (Number.isNaN(x)) return ''
  return x.toLocaleString(undefined, { maximumFractionDigits: 3 })
}

export default function InventoryPage() {
  const { isAdmin } = useAuth()

  const [location, setLocation] = useState('BAR')
  const [tab, setTab] = useState('Stock')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [stockRows, setStockRows] = useState([])
  const [stockByItemAndLoc, setStockByItemAndLoc] = useState({})
  const [items, setItems] = useState([])
  const [movements, setMovements] = useState([])

  const [itemType, setItemType] = useState('')
  const [q, setQ] = useState('')

  const [editingItemId, setEditingItemId] = useState(null)
  const [editForm, setEditForm] = useState({
    name: '',
    unit: '',
    min_level: '',
    reorder_level: '',
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
      const ak = (a?.kind_name || '').toLowerCase()
      const bk = (b?.kind_name || '').toLowerCase()
      if (ak !== bk) return ak.localeCompare(bk)
      const an = (a?.name || '').toLowerCase()
      const bn = (b?.name || '').toLowerCase()
      return an.localeCompare(bn)
    })
    return arr
  }, [filteredItems])

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
              name: base?.name || '',
              unit: base?.unit || '',
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
      setError('Failed to load stock')
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
      setError('Failed to load items')
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
      const res = await api.get(`/inventory/movements?${params.toString()}`)
      setMovements(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('Failed to load movements', e)
      setError('Failed to load movements')
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
  }, [tab, location, itemType])

  const startEditItem = (it) => {
    setEditingItemId(it.id)
    setEditForm({
      name: it.name ?? '',
      unit: it.unit ?? '',
      min_level: it.min_level ?? '',
      reorder_level: it.reorder_level ?? '',
      is_active: !!it.is_active,
      submitting: false,
    })
  }

  const cancelEditItem = () => {
    setEditingItemId(null)
    setEditForm({ name: '', unit: '', min_level: '', reorder_level: '', is_active: true, submitting: false })
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
      }
      await api.patch(`/inventory/items/${editingItemId}`, payload)
      cancelEditItem()
      await loadItems()
      if (tab === 'Stock') await loadStock()
    } catch (e) {
      console.error('Failed to update item', e)
      setError('Failed to update item')
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
      setError(detail ? String(detail) : 'Failed to create movement')
      setMovementForm((p) => ({ ...p, submitting: false }))
    }
  }

  return (
    <div className="card">
      <div className="inventory-header">
        <div className="inventory-controls">
          <div className="inventory-control">
            <label className="inventory-label">Location</label>
            <select className="form-input" value={location} onChange={(e) => setLocation(e.target.value)}>
              {LOCATIONS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>

          <div className="inventory-control">
            <label className="inventory-label">Type</label>
            <select className="form-input" value={itemType} onChange={(e) => setItemType(e.target.value)}>
              <option value="">All</option>
              <option value="BOTTLE">BOTTLE</option>
              <option value="GARNISH">GARNISH</option>
              <option value="GLASS">GLASS</option>
            </select>
          </div>

          {(tab === 'Items') && (
            <div className="inventory-control inventory-control-wide">
              <label className="inventory-label">Search</label>
              <input
                className="form-input"
                placeholder="Search items..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="inventory-tabs">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              className={`inventory-tab ${tab === t ? 'active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {loading && <div className="loading">Loading...</div>}

      {!loading && tab === 'Stock' && (
        <div className="inventory-section">
          <div className="inventory-table">
            {location === 'ALL' ? (
              <>
                <div className="inventory-table-header inventory-table-header-stock-all">
                  <div>Name</div>
                  <div className="right">BAR Qty</div>
                  <div className="right">WH Qty</div>
                  <div>Unit</div>
                </div>
                {(stockRows || []).map((r) => (
                  <div key={r.inventory_item_id} className="inventory-table-row inventory-table-row-stock-all">
                    <div className="name">{r.name}</div>
                    <div className="right">{formatNumber(r.quantity_bar)}</div>
                    <div className="right">{formatNumber(r.quantity_warehouse)}</div>
                    <div className="muted">{r.unit}</div>
                  </div>
                ))}
              </>
            ) : (
              <>
                <div className="inventory-table-header">
                  <div>Name</div>
                  <div className="right">Qty</div>
                  <div className="right">Reserved</div>
                  <div>Unit</div>
                </div>
                {(stockRows || []).map((r) => (
                  <div key={r.inventory_item_id} className="inventory-table-row">
                    <div className="name">{r.name}</div>
                    <div className="right">{formatNumber(r.quantity)}</div>
                    <div className="right">{formatNumber(r.reserved_quantity)}</div>
                    <div className="muted">{r.unit}</div>
                  </div>
                ))}
              </>
            )}
            {(stockRows || []).length === 0 && (
              <div className="empty-state">No stock rows yet (seed inventory items first).</div>
            )}
          </div>
        </div>
      )}

      {!loading && tab === 'Items' && (
        <div className="inventory-section">
          <div className="inventory-table">
            <div className={`inventory-table-header ${location === 'ALL' ? 'inventory-table-header-items-all' : 'inventory-table-header-items'}`}>
              <div>Name</div>
              <div>Unit</div>
              <div>Kind</div>
              {location === 'ALL' ? (
                <>
                  <div className="right">BAR Qty</div>
                  <div className="right">WH Qty</div>
                </>
              ) : (
                <div className="right">Qty ({location})</div>
              )}
              <div>Status</div>
              <div />
            </div>
            {(sortedItems || []).map((it) => {
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
                  <div className="muted">{it.kind_name || ''}</div>
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
                        Active
                      </label>
                    ) : (
                      <span className={`pill ${it.is_active ? 'pill-ok' : 'pill-muted'}`}>
                        {it.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    )}
                  </div>
                  <div className="actions">
                    {isAdmin && (
                      isEditing ? (
                        <>
                          <button type="button" className="button-primary" disabled={editForm.submitting} onClick={saveItem}>
                            Save
                          </button>
                          <button type="button" className="button-secondary" disabled={editForm.submitting} onClick={cancelEditItem}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button type="button" className="button-edit" onClick={() => startEditItem(it)}>
                          Edit
                        </button>
                      )
                    )}
                  </div>
                </div>
              )
            })}
            {(filteredItems || []).length === 0 && (
              <div className="empty-state">No items. Run the seed script to create items from bottles.</div>
            )}
          </div>

          {isAdmin && editingItemId && (
            <div className="inventory-subpanel">
              <div className="inventory-subpanel-title">Reorder settings</div>
              <div className="inventory-subpanel-grid">
                <div>
                  <label className="inventory-label">Min level</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.001"
                    value={editForm.min_level}
                    onChange={(e) => setEditForm((p) => ({ ...p, min_level: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="inventory-label">Reorder level</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.001"
                    value={editForm.reorder_level}
                    onChange={(e) => setEditForm((p) => ({ ...p, reorder_level: e.target.value }))}
                  />
                </div>
              </div>
              <div className="inventory-subpanel-actions">
                <button type="button" className="button-primary" disabled={editForm.submitting} onClick={saveItem}>
                  Save settings
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
                    Select <strong>BAR</strong> or <strong>WAREHOUSE</strong> to add a movement.
                  </div>
                )}
                <div className="inventory-control inventory-control-wide">
                  <label className="inventory-label">Item</label>
                  <select
                    className="form-input"
                    value={movementForm.inventory_item_id}
                    onChange={(e) => setMovementForm((p) => ({ ...p, inventory_item_id: e.target.value }))}
                    disabled={location === 'ALL'}
                  >
                    <option value="">Select item…</option>
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
                  <label className="inventory-label">Change</label>
                  <input
                    className="form-input"
                    type="number"
                    step="0.001"
                    placeholder="+/-"
                    value={movementForm.change}
                    onChange={(e) => setMovementForm((p) => ({ ...p, change: e.target.value }))}
                    disabled={location === 'ALL'}
                  />
                </div>

                <div className="inventory-control">
                  <label className="inventory-label">Reason</label>
                  <select
                    className="form-input"
                    value={movementForm.reason}
                    onChange={(e) => setMovementForm((p) => ({ ...p, reason: e.target.value }))}
                    disabled={location === 'ALL'}
                  >
                    <option value="PURCHASE">PURCHASE</option>
                    <option value="USAGE">USAGE</option>
                    <option value="WASTE">WASTE</option>
                    <option value="ADJUSTMENT">ADJUSTMENT</option>
                    <option value="TRANSFER">TRANSFER</option>
                  </select>
                </div>

                <button
                  type="submit"
                  className="button-primary"
                  disabled={location === 'ALL' || movementForm.submitting || !movementForm.inventory_item_id}
                >
                  Add movement
                </button>
              </div>
            </form>
          )}

          <div className="inventory-table">
            <div className={`inventory-table-header ${location === 'ALL' ? 'inventory-table-header-movements-all' : 'inventory-table-header-movements'}`}>
              <div>When</div>
              {location === 'ALL' && <div>Location</div>}
              <div>Item</div>
              <div className="right">Change</div>
              <div>Reason</div>
            </div>
            {(movements || []).map((m) => (
              <div key={m.id} className={`inventory-table-row ${location === 'ALL' ? 'inventory-table-row-movements-all' : 'inventory-table-row-movements'}`}>
                <div className="muted">{m.created_at ? new Date(m.created_at).toLocaleString() : ''}</div>
                {location === 'ALL' && <div className="muted">{m.location}</div>}
                <div className="name">{m.item_name || m.inventory_item_id}</div>
                <div className={`right ${Number(m.change) < 0 ? 'neg' : 'pos'}`}>{formatNumber(m.change)}</div>
                <div className="muted">{m.reason || ''}</div>
              </div>
            ))}
            {(movements || []).length === 0 && (
              <div className="empty-state">No movements yet.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

