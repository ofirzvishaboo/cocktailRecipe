import { useMemo } from 'react'

export default function InventorySearchInput({
  id,
  label,
  value,
  onValueChange,
  placeholder,
  disabled = false,
  options = [], // [{ value: string, label: string }]
  onSelectValue, // (value: string) => void
  className = '',
  inputClassName = 'form-input',
  labelClassName = 'inventory-label',
}) {
  const optionByLabel = useMemo(() => {
    const m = new Map()
    for (const opt of options || []) {
      if (!opt?.label) continue
      m.set(opt.label, opt.value)
    }
    return m
  }, [options])

  const datalistId = options?.length ? `${id}-datalist` : undefined

  return (
    <div className={`inventory-control-stack ${className}`.trim()}>
      {label && (
        <label className={labelClassName} htmlFor={id}>
          {label}
        </label>
      )}
      <input
        id={id}
        className={inputClassName}
        type="text"
        value={value}
        onChange={(e) => {
          const next = e.target.value
          onValueChange?.(next)
          if (onSelectValue) {
            const selected = optionByLabel.get(next)
            onSelectValue(selected || '')
          }
        }}
        list={datalistId}
        placeholder={placeholder}
        disabled={disabled}
      />
      {datalistId && (
        <datalist id={datalistId}>
          {(options || []).map((opt) => (
            <option key={String(opt.value)} value={opt.label} />
          ))}
        </datalist>
      )}
    </div>
  )
}

