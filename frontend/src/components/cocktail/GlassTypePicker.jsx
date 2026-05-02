import { useEffect, useMemo, useRef, useState } from 'react'

export default function GlassTypePicker({
  id,
  value,
  onChange,
  options = [],
  placeholder = 'Select…',
  ariaLabel,
  dir = 'ltr',
}) {
  const rootRef = useRef(null)
  const inputRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const selected = useMemo(
    () => (options || []).find((o) => String(o.value) === String(value)) || null,
    [options, value],
  )

  const filtered = useMemo(() => {
    const q = (query || '').trim().toLowerCase()
    if (!q) return options || []
    return (options || []).filter((o) => String(o.label || '').toLowerCase().includes(q))
  }, [options, query])

  useEffect(() => {
    if (!open) return
    const onDocMouseDown = (e) => {
      if (!rootRef.current) return
      if (!rootRef.current.contains(e.target)) setOpen(false)
    }
    const onDocKeyDown = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocMouseDown)
    document.addEventListener('keydown', onDocKeyDown)
    return () => {
      document.removeEventListener('mousedown', onDocMouseDown)
      document.removeEventListener('keydown', onDocKeyDown)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    // Delay to next tick so the input exists.
    const t = setTimeout(() => inputRef.current?.focus?.(), 0)
    return () => clearTimeout(t)
  }, [open])

  const commit = (nextValue) => {
    onChange?.(nextValue)
    setOpen(false)
    setQuery('')
  }

  return (
    <div ref={rootRef} className="cr-combobox" dir={dir}>
      <button
        id={id}
        type="button"
        className="cr-combobox__control"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open ? 'true' : 'false'}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={`cr-combobox__value ${selected ? '' : 'is-placeholder'}`.trim()}>
          {selected ? selected.label : placeholder}
        </span>
        <span className="cr-combobox__chevron" aria-hidden="true">▾</span>
      </button>

      {open && (
        <div className="cr-combobox__popover" role="dialog" aria-label={ariaLabel || 'Select'}>
          <input
            ref={inputRef}
            className="cr-combobox__search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search…"
            aria-label="Search"
          />
          <div className="cr-combobox__list" role="listbox" aria-label={ariaLabel}>
            <button
              type="button"
              className="cr-combobox__option"
              role="option"
              aria-selected={!value ? 'true' : 'false'}
              onClick={() => commit('')}
            >
              {placeholder}
            </button>
            {(filtered || []).map((o) => (
              <button
                key={String(o.value)}
                type="button"
                className={`cr-combobox__option ${String(o.value) === String(value) ? 'is-selected' : ''}`.trim()}
                role="option"
                aria-selected={String(o.value) === String(value) ? 'true' : 'false'}
                onClick={() => commit(o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

