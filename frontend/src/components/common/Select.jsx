import '../../styles/select.css'

export default function Select({
  id,
  label,
  value,
  onChange,
  options = [],
  placeholder,
  disabled = false,
  required = false,
  name,
  className = '',
  size = 'md', // md | sm | lg
  hint,
  error,
  ariaLabel,
}) {
  const selectId = id || name
  const sizeClass = size === 'sm' ? 'cr-select--sm' : size === 'lg' ? 'cr-select--lg' : ''

  return (
    <div className={`cr-select ${sizeClass} ${className}`.trim()}>
      {label && (
        <label className="cr-select__label" htmlFor={selectId}>
          {label}{required ? ' *' : ''}
        </label>
      )}
      <select
        id={selectId}
        name={name}
        className="cr-select__control"
        value={value ?? ''}
        onChange={(e) => onChange?.(e.target.value, e)}
        disabled={disabled}
        required={required}
        aria-label={ariaLabel || (label ? undefined : name)}
        aria-invalid={error ? 'true' : 'false'}
      >
        {placeholder !== undefined && (
          <option value="" disabled={required}>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={String(opt.value)} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error ? (
        <div className="cr-select__error">{error}</div>
      ) : hint ? (
        <div className="cr-select__hint">{hint}</div>
      ) : null}
    </div>
  )
}

