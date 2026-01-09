import { useEffect } from 'react'

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger', // 'danger' | 'primary'
  onConfirm,
  onCancel,
}) {
  useEffect(() => {
    if (!open) return

    const onKeyDown = (e) => {
      if (e.key === 'Escape') onCancel?.()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onCancel])

  if (!open) return null

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
          <p className="modal-text">{message}</p>
        </div>
        <div className="modal-actions">
          <button type="button" className="button-secondary" onClick={onCancel}>
            {cancelText}
          </button>
          <button
            type="button"
            className={variant === 'danger' ? 'button-danger' : 'button-primary'}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}


