import { AlertCircle, CheckCircle2, CircleHelp, Info } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'

export type ActionMessage = {
  message: string
  solution: string
  tone: 'danger' | 'warning' | 'success' | 'info'
} | null

export function ActionMessageDialog({
  notice,
  onDismiss,
}: {
  notice: ActionMessage
  onDismiss: () => void
}) {
  const titleId = useId()
  const messageId = useId()
  const solutionId = useId()
  const dismissRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!notice) return
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const background = Array.from(
      document.querySelectorAll<HTMLElement>('.sidebar, .app-main, .mobile-scrim'),
    )
    const previousInert = background.map((element) => element.inert)
    const previousBodyOverflow = document.body.style.overflow
    background.forEach((element) => { element.inert = true })
    document.body.style.overflow = 'hidden'
    dismissRef.current?.focus()

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onDismiss()
      } else if (event.key === 'Tab') {
        event.preventDefault()
        dismissRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('keydown', handleKey)
      background.forEach((element, index) => { element.inert = previousInert[index] })
      document.body.style.overflow = previousBodyOverflow
      window.requestAnimationFrame(() => previousFocus?.focus())
    }
  }, [notice, onDismiss])

  if (!notice) return null
  const isDanger = notice.tone === 'danger'
  const isWarning = notice.tone === 'warning'
  const isSuccess = notice.tone === 'success'
  const Icon = isDanger ? AlertCircle : isWarning ? CircleHelp : isSuccess ? CheckCircle2 : Info
  const eyebrow = isDanger ? 'Action needed' : isWarning ? 'Please review' : isSuccess ? 'Completed' : 'Status update'
  const title = isDanger
    ? 'Please correct this before continuing'
    : isWarning
      ? 'Please check this before continuing'
      : isSuccess
        ? 'Your update was completed'
        : 'Please review this information'
  const dismissLabel = isDanger
    ? 'Return and correct it'
    : isWarning
      ? 'Return and review'
      : 'Close and continue'
  const dialogRole = isDanger || isWarning ? 'alertdialog' : 'dialog'

  return (
    <div className="action-message-overlay" role="presentation">
      <section
        className={`action-message action-message--${notice.tone}`}
        role={dialogRole}
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={`${messageId} ${solutionId}`}
      >
        <div className="action-message__accent" aria-hidden="true" />
        <header>
          <span className="action-message__icon"><Icon size={28} /></span>
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2 id={titleId}>{title}</h2>
          </div>
        </header>
        <div className="action-message__body">
          <p id={messageId} className="action-message__problem">{notice.message}</p>
          <div className="action-message__solution">
            <span><CheckCircle2 size={20} /></span>
            <div>
              <strong>What to do</strong>
              <p id={solutionId}>{notice.solution}</p>
            </div>
          </div>
        </div>
        <footer>
          <button
            ref={dismissRef}
            className="button button--primary action-message__dismiss"
            type="button"
            onClick={onDismiss}
          >
            {dismissLabel}
          </button>
        </footer>
      </section>
    </div>
  )
}
