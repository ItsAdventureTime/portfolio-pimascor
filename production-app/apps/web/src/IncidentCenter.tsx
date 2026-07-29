import {
  AlertTriangle,
  CircleHelp,
  Send,
  RefreshCw,
  ShieldCheck,
  X,
} from 'lucide-react'
import {
  Component,
  useEffect,
  useRef,
  useState,
  type ErrorInfo,
  type ReactNode,
} from 'react'
import { ApiError, reportDetectedIncident, reportIncident } from './api'
import type { ApiIncident, ApiIncidentReport } from './types'


type IncidentDescriptor = {
  message: string
  recovery: string
  canContinue: boolean
  operation: string
  code: string
  status: number | null
  requestMethod: string | null
  requestPath: string | null
  correlationId: string | null
  technicalSummary: string | null
  existingIncidentId: string | null
  existingIncidentReference: string | null
}

type IncidentView = {
  descriptor: IncidentDescriptor
  clientReportId: string
  incident: ApiIncident | null
  reporting: boolean
  reportFailed: boolean
}

function randomId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `${Date.now().toString(16).padStart(12, '0')}-0000-4000-8000-${Math.random().toString(16).slice(2, 14).padEnd(12, '0')}`
}

function clientRuntime() {
  const agent = navigator.userAgent
  const engine = /Firefox\//.test(agent)
    ? 'Gecko'
    : /AppleWebKit/.test(agent) && !/Chrome|Chromium|Edg\//.test(agent)
      ? 'WebKit'
      : /Chrome|Chromium|Edg\//.test(agent)
        ? 'Blink'
        : 'Other browser engine'
  return `${engine}; ${navigator.onLine ? 'online' : 'offline'}`
}

function pagePath() {
  return `${window.location.pathname}${window.location.hash}`.slice(0, 240)
}

function fromApiError(error: ApiError): IncidentDescriptor {
  return {
    message: error.message,
    recovery: error.recovery,
    canContinue: error.canContinue,
    operation: error.operation,
    code: error.code,
    status: error.status,
    requestMethod: error.requestMethod,
    requestPath: error.requestPath,
    correlationId: error.correlationId,
    technicalSummary: `${error.name}; ${error.code}; HTTP ${error.status}; browser online=${navigator.onLine}`,
    existingIncidentId: error.incidentId,
    existingIncidentReference: error.incidentReference,
  }
}

function fromRuntimeError(reason: unknown): IncidentDescriptor {
  const error = reason instanceof Error ? reason : new Error('Browser operation failed')
  return {
    message: 'This part of the page stopped before the action could finish.',
    recovery: 'Stop and return to a safe page. Check the relevant list before trying again.',
    canContinue: false,
    operation: 'Use the current PIMASCOR page',
    code: 'BROWSER_RUNTIME_ERROR',
    status: null,
    requestMethod: null,
    requestPath: null,
    correlationId: null,
    technicalSummary: `${error.name}\n${(error.stack ?? 'No browser stack was available').slice(0, 3500)}`,
    existingIncidentId: null,
    existingIncidentReference: null,
  }
}

function reportPayload(
  descriptor: IncidentDescriptor,
  clientReportId: string,
): ApiIncidentReport {
  return {
    client_report_id: clientReportId,
    severity: descriptor.canContinue ? 'RECOVERABLE' : 'BLOCKING',
    operation: descriptor.operation,
    user_action: `The user was trying to ${descriptor.operation.toLowerCase()}.`,
    user_message: descriptor.message,
    recovery_suggestion: descriptor.recovery,
    can_continue: descriptor.canContinue,
    page_path: pagePath(),
    request_method: descriptor.requestMethod,
    request_path: descriptor.requestPath,
    http_status: descriptor.status,
    error_code: descriptor.code,
    technical_summary: descriptor.technicalSummary,
    client_runtime: clientRuntime(),
    correlation_id: descriptor.correlationId,
  }
}

export function IncidentCenter({
  enabled,
}: {
  enabled: boolean
}) {
  const [view, setView] = useState<IncidentView | null>(null)
  const active = useRef(false)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const dialogRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (view) titleRef.current?.focus()
  }, [view])

  useEffect(() => {
    if (!view) return
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const background = Array.from(
      document.querySelectorAll<HTMLElement>('.sidebar, .app-main, .mobile-scrim'),
    )
    const previousInert = background.map((element) => element.inert)
    background.forEach((element) => { element.inert = true })
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !view.reporting) {
        event.preventDefault()
        active.current = false
        setView(null)
        return
      }
      if (event.key !== 'Tab') return
      const controls = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), summary, [href], [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      )
      if (!controls.length) return
      const first = controls[0]
      const last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('keydown', handleKey)
      background.forEach((element, index) => { element.inert = previousInert[index] })
      window.requestAnimationFrame(() => previousFocus?.focus())
    }
  }, [view])

  useEffect(() => {
    const open = (descriptor: IncidentDescriptor) => {
      if (!enabled || active.current) return
      active.current = true
      setView({
        descriptor,
        clientReportId: randomId(),
        incident: null,
        reporting: false,
        reportFailed: false,
      })
    }

    const onIncident = (event: Event) => open(fromApiError((event as CustomEvent<ApiError>).detail))
    const onError = (event: ErrorEvent) => open(fromRuntimeError(event.error ?? event.message))
    const onRejection = (event: PromiseRejectionEvent) => open(fromRuntimeError(event.reason))
    window.addEventListener('pimascor:incident', onIncident)
    window.addEventListener('error', onError)
    window.addEventListener('unhandledrejection', onRejection)
    return () => {
      window.removeEventListener('pimascor:incident', onIncident)
      window.removeEventListener('error', onError)
      window.removeEventListener('unhandledrejection', onRejection)
    }
  }, [enabled])

  if (!view) return null

  const close = () => {
    active.current = false
    setView(null)
  }
  const sendReport = async () => {
    setView((current) => current ? { ...current, reporting: true, reportFailed: false } : current)
    try {
      const incident = view.descriptor.existingIncidentId
        ? await reportDetectedIncident(view.descriptor.existingIncidentId)
        : await reportIncident(reportPayload(view.descriptor, view.clientReportId))
      const delivered = Boolean(
        incident.email_admin_sent_at && incident.email_developer_sent_at,
      )
      if (delivered) {
        close()
      } else {
        setView((current) => current
          ? { ...current, incident, reporting: false, reportFailed: true }
          : current)
      }
    } catch {
      setView((current) => current
        ? { ...current, reporting: false, reportFailed: true }
        : current)
    }
  }
  const reference = view.incident?.reference
    ?? view.descriptor.existingIncidentReference

  return (
    <div className="incident-overlay" role="presentation">
      <section ref={dialogRef} className="incident-dialog" role="alertdialog" aria-modal="true" aria-labelledby="incident-title" aria-describedby="incident-message">
        <div className="incident-dialog__glow" aria-hidden="true" />
        <header>
          <span className="incident-dialog__mark"><AlertTriangle size={27} /></span>
          <div>
            <p className="eyebrow">Protected recovery</p>
            <h2 id="incident-title" ref={titleRef} tabIndex={-1}>Something needs your attention</h2>
          </div>
        </header>

        <div className="incident-dialog__body">
          <p id="incident-message" className="incident-dialog__message">{view.descriptor.message}</p>
          <div className="incident-recovery">
            <span><CircleHelp size={19} /></span>
            <div><strong>What to do next</strong><p>{view.descriptor.recovery}</p></div>
          </div>
          <div className="incident-report-state" role="status" aria-live="polite">
            {view.reporting
              ? <><RefreshCw className="spin" size={18} /><span><strong>Sending your private report…</strong><small>Please keep this message open while delivery is confirmed.</small></span></>
              : view.reportFailed
                ? <><AlertTriangle size={18} /><span><strong>The report was not fully delivered.</strong><small>Try again, or dismiss this message without sending anything else.</small></span></>
                : <><ShieldCheck size={18} /><span><strong>Nothing has been sent.</strong><small>Select Report for investigation only if you want Bridge PH Admin and the Developer to receive a private report.</small></span></>}
          </div>
          <details className="incident-details">
            <summary>Report details</summary>
            <dl><div><dt>Operation</dt><dd>{view.descriptor.operation}</dd></div><div><dt>Error reference</dt><dd>{reference ?? 'Created only if you report this problem'}</dd></div><div><dt>Information excluded</dt><dd>Passwords, email codes, bank details, documents, form entries, and secret keys</dd></div></dl>
          </details>
        </div>

        <footer>
          <button className="button button--secondary" type="button" onClick={close} disabled={view.reporting}>
            <X size={16} /> Dismiss
          </button>
          <div>
            <button className="button button--primary" type="button" onClick={() => void sendReport()} disabled={view.reporting}>
              {view.reporting ? <RefreshCw className="spin" size={17} /> : <Send size={17} />}
              {view.reporting ? 'Sending report…' : view.reportFailed ? 'Try reporting again' : 'Report for investigation'}
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}


export class ApplicationErrorBoundary extends Component<
  { children: ReactNode },
  {
    failed: boolean
    descriptor: IncidentDescriptor | null
    clientReportId: string
    reporting: boolean
    reportFailed: boolean
  }
> {
  state = {
    failed: false,
    descriptor: null as IncidentDescriptor | null,
    clientReportId: randomId(),
    reporting: false,
    reportFailed: false,
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    const descriptor = fromRuntimeError(error)
    this.setState({
      descriptor: {
        ...descriptor,
        technicalSummary: `${descriptor.technicalSummary ?? ''}\nReact component path:\n${(info.componentStack ?? 'Not available').slice(0, 1800)}`,
      },
    })
  }

  static getDerivedStateFromError(error: Error) {
    return { failed: true, descriptor: fromRuntimeError(error) }
  }

  private reportAndReopen = async () => {
    if (!this.state.descriptor) return
    this.setState({ reporting: true, reportFailed: false })
    try {
      const incident = await reportIncident(
        reportPayload(this.state.descriptor, this.state.clientReportId),
      )
      if (!incident.email_admin_sent_at || !incident.email_developer_sent_at) {
        this.setState({ reporting: false, reportFailed: true })
        return
      }
      window.location.reload()
    } catch {
      this.setState({ reporting: false, reportFailed: true })
    }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return <main className="fatal-recovery"><section><span><AlertTriangle size={32} /></span><p className="eyebrow">Protected recovery</p><h1>This page needs to restart</h1><p>Before repeating an accounting or payment action, reopen the workspace and check its list to see whether the action was saved.</p><div className="incident-report-state"><ShieldCheck size={18} /><span><strong>{this.state.reportFailed ? 'The report was not fully delivered.' : 'Nothing has been sent.'}</strong><small>{this.state.reportFailed ? 'Try again, or reopen without reporting.' : 'You decide whether to send a private report to Bridge PH Admin and the Developer.'}</small></span></div><div className="fatal-recovery__actions"><button className="button button--secondary" disabled={this.state.reporting} onClick={() => window.location.reload()}><RefreshCw size={17} /> Reopen without reporting</button><button className="button button--primary" disabled={this.state.reporting} onClick={() => void this.reportAndReopen()}>{this.state.reporting ? <RefreshCw className="spin" size={17} /> : <Send size={17} />}{this.state.reporting ? 'Sending report…' : this.state.reportFailed ? 'Try reporting again' : 'Report and reopen'}</button></div></section></main>
  }
}
