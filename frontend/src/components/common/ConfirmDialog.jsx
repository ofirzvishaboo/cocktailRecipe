import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmText,
  cancelText,
  variant = 'danger', // 'danger' | 'primary'
  onConfirm,
  onCancel,
}) {
  const { t } = useTranslation()
  useEffect(() => {
    if (!open) return

    const onKeyDown = (e) => {
      if (e.key === 'Escape') onCancel?.()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onCancel])

  if (!open) return null

  const isPlainString = typeof message === 'string'
  const resolvedCancelText = cancelText ?? t('common.cancel')
  const resolvedConfirmText = confirmText ?? t('common.confirm')

  return (
    <div className="modal-overlay" role="presentation" onMouseDown={onCancel}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 id="confirm-dialog-title" className="modal-title">{title}</h3>
        </div>
        <div className="modal-body">
          {isPlainString ? (
            <p className="modal-text">{message}</p>
          ) : (
            <div className="modal-text">{message}</div>
          )}
        </div>
        <div className="modal-actions">
          <button type="button" className="button-secondary" onClick={onCancel}>
            {resolvedCancelText}
          </button>
          <button
            type="button"
            className={variant === 'danger' ? 'button-danger' : 'button-primary'}
            onClick={onConfirm}
          >
            {resolvedConfirmText}
          </button>
        </div>
      </div>
    </div>
  )
}


