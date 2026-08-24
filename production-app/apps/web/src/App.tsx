import {
  Activity,
  AlertCircle,
  Archive,
  ArrowRight,
  Banknote,
  Bell,
  BookOpen,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  CircleHelp,
  ClipboardCheck,
  Clock3,
  CreditCard,
  Download,
  Eye,
  FileCheck2,
  FileText,
  FolderOpen,
  Gauge,
  HandCoins,
  LayoutDashboard,
  Landmark,
  LogOut,
  Megaphone,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  ReceiptText,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Ship,
  TrendingUp,
  Upload,
  UserRound,
  UsersRound,
  X,
  XCircle,
  type LucideIcon,
} from 'lucide-react'
import { useCallback, useEffect, useId, useMemo, useRef, useState, type FormEvent, type ReactNode, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import {
  attentionByRole,
  budgetRequests as initialBudgetRequests,
  pageMeta,
  roleDescriptions,
  toneForStatus,
} from './data'
import type { BudgetRequest, PageId, Role, Tone } from './types'
import type { ApiActivityCategory, ApiAdminActivity, ApiBackupCatalogItem, ApiBilling, ApiBudgetRequest, ApiClient, ApiClientPayment, ApiCreditMemo, ApiDataExport, ApiDocument, ApiExpenseRequest, ApiExpenseType, ApiFundingSource, ApiLiquidation, ApiPaymentQueueItem, ApiQuotation, ApiQuotationLine, ApiReleaseUpdate, ApiShipmentProfitability, ApiSupportTicket, ApiSupportTicketStatus, ApiTaxProfile, ApiUser } from './types'
import { ApiError, acknowledgeReleaseUpdate, addSupportTicketMessage, closeLiquidation, completeActivation, completePasswordReset, createAdditionalBudget, createBillingDraft, createBillingReplacement, createBudgetRequest, createClientPayment, createCreditMemo, createExpenseRequest, createFundingSource, createQuotation, createSupportTicket, createTaxProfile, decideBilling, decideBudgetRequest, decideCreditMemo, decideExpenseRequest, decideQuotation, downloadDataExport, downloadDocument, emitApiIncident, finalizeBilling, getAdminActivity, getBackups, getBilling, getBudgetApprovalQueue, getBudgetRequests, getBudgetReviewQueue, getClientPayments, getClients, getCreditMemos, getDataExports, getDocumentBlob, getDocuments, getExpenseApprovalQueue, getExpenseRequests, getFundingSources, getLiquidations, getMe, getPayments, getQuotations, getReceivables, getReleaseUpdate, getShipmentProfitability, getSupportTickets, getTaxProfiles, overrideBudgetAsDcs, overrideQuotationAsDcs, recordPayment, recordQuotationAcceptance, requestDataExport, returnBudgetFromReview, reviewBudgetRequest, saveLiquidation, signOut, startActivation, startDemoSession, startPassword, startPasswordReset, submitBilling, submitBudgetRequest, submitExpenseRequest, submitLiquidation, submitQuotation, updateBillingDraft, updateBudgetRequest, updateFundingSource, updatePayment, updateSupportTicket, uploadLiquidationEvidence, uploadPaymentProof, verifyEmailCode, voidBilling } from './api'
import { IncidentCenter } from './IncidentCenter'
import { ActionMessageDialog, type ActionMessage } from './ActionMessageDialog'
import { SupportPortalPage, readSupportPortalLink } from './SupportPortal'

type Notify = (message: string, tone?: Tone, solution?: string) => void

function suggestedNextStep(message: string, tone: Tone) {
  const normalized = message.toLowerCase()
  if (normalized.includes('buying amount') && normalized.includes('selling amount')) {
    return 'Enter an amount greater than zero in at least one Buying field and one Selling field, then select Save as Draft or Submit for Approval again.'
  }
  if (normalized.includes('additional buying amount')) {
    return 'Enter an amount greater than zero in at least one Additional Buying field, then save or submit the Additional Budget again.'
  }
  if (normalized.includes('funding source') && normalized.includes('already')) {
    return 'Use the approved funding source that is already listed, or enter a different approved display name.'
  }
  if (normalized.includes('could not load') || normalized.includes('could not reach')) {
    return 'Check the connection, dismiss this message, and select Refresh. If it happens again, stop and inform Bridge PH.'
  }
  if (normalized.includes('could not save') || normalized.includes('could not submit') || normalized.includes('could not record')) {
    return 'Review the required fields and correct any missing information. Before trying again, check the relevant list to confirm that no record was already saved.'
  }
  if (normalized.includes('awaiting dcs') || normalized.includes('pending dcs')) {
    return 'No correction is needed from you. DCS must record the payment decision before this request can move to the next step.'
  }
  if (normalized.includes('awaiting gm') || normalized.includes('pending gm') || normalized.includes('submitted to gm')) {
    return 'No correction is needed from you. The GM must record an approval decision before the next controlled step becomes available.'
  }
  if (tone === 'success') {
    return 'The change was saved. Review the updated record, then continue with your next task.'
  }
  if (tone === 'info') {
    return 'Review the current status, then close this message when you are ready to continue.'
  }
  return 'Review the information on the form, correct the item described above, and try the action again.'
}

function formatBusinessMessage(message: string) {
  return message
    .replace(/\bdcs\b/gi, 'DCS')
    .replace(/\bgm\b/gi, 'GM')
    .replace(/\bopex\b/gi, 'OPEX')
}

function notifyLocalFailure(error: unknown, fallback: string, notify: Notify) {
  if (error instanceof ApiError) return
  notify(error instanceof Error ? error.message : fallback, 'danger')
}

type NavItem = {
  id: PageId
  label: string
  icon: LucideIcon
  roles: Role[]
  roleLabels?: Partial<Record<Role, string>>
}

const brandLogoUrl = `${import.meta.env.BASE_URL}pimascor-logo.jpg`
const brandIconUrl = `${import.meta.env.BASE_URL}pimascor-app-icon.jpg`

// Demo-only controls are enabled only by an explicit deployment marker. The
// build scripts pass VITE_DEPLOYMENT_TIER=demo for the hosted demo and
// VITE_DEPLOYMENT_TIER=production for production, so a missing build argument
// fails closed and cannot expose demo controls accidentally.
const deploymentTier = String(import.meta.env.VITE_DEPLOYMENT_TIER ?? '').toLowerCase()
const appEnvironment = String(import.meta.env.VITE_APP_ENV ?? '').toLowerCase()
const isDemoBuild = deploymentTier === 'demo'
  || appEnvironment === 'demo'

const navigation: { label: string; items: NavItem[] }[] = [
  {
    label: 'Control room',
  items: [{ id: 'dashboard', label: 'Shipment Profitability', icon: LayoutDashboard, roles: ['Admin', 'Requester', 'GM', 'DCS', 'Mich'] }],
  },
  {
    label: 'Shipments',
    items: [
      { id: 'quotations', label: 'Sales Quotations', icon: FileCheck2, roles: ['Admin', 'Requester', 'GM', 'DCS', 'Mich'] },
      { id: 'budget-requests', label: 'Budget Requests', icon: Ship, roles: ['Admin', 'Requester', 'GM', 'DCS', 'Mich'], roleLabels: { Requester: 'My Budget Requests' } },
      { id: 'approvals', label: 'Approval', icon: ClipboardCheck, roles: ['Admin', 'GM', 'DCS', 'Mich'], roleLabels: { Mich: 'Budget Review', DCS: 'Approval Visibility' } },
      { id: 'releases', label: 'DCS for Payment', icon: HandCoins, roles: ['Admin', 'DCS', 'GM', 'Mich'] },
      { id: 'liquidation', label: 'Liquidations', icon: ReceiptText, roles: ['Admin', 'Requester', 'GM', 'DCS', 'Mich'], roleLabels: { Requester: 'My Liquidations', Mich: 'Liquidations to Review' } },
      { id: 'billing', label: 'Billing', icon: FileCheck2, roles: ['Admin', 'Requester', 'GM', 'DCS', 'Mich'], roleLabels: { Requester: 'My Billing', Mich: 'Prepare Billing' } },
      { id: 'collections', label: 'Client Payments', icon: CreditCard, roles: ['Admin', 'GM', 'DCS', 'Mich'] },
    ],
  },
  {
    label: 'Expenses',
    items: [
      { id: 'payment-requests', label: 'Request for Payment', icon: BriefcaseBusiness, roles: ['Admin', 'GM', 'DCS', 'Mich'] },
    ],
  },
  {
    label: 'Records',
    items: [
      { id: 'accounting', label: 'Accounting Export', icon: BookOpen, roles: ['Admin', 'GM', 'DCS', 'Mich'] },
      { id: 'clients-documents', label: 'Clients & Documents', icon: FolderOpen, roles: ['Admin', 'GM', 'DCS', 'Mich'] },
      { id: 'admin', label: 'Administration', icon: Settings, roles: ['Admin'] },
    ],
  },
]

function defaultPageForRole(role: Role): PageId {
  return navigation.flatMap((group) => group.items).find((item) => item.roles.includes(role))?.id ?? 'dashboard'
}

const validPages = new Set(Object.keys(pageMeta))

function pageFromHash(): PageId {
  const value = window.location.hash.replace('#', '')
  if (value === 'opex' || value === 'marketing' || value === 'loan-payments') return 'payment-requests'
  return validPages.has(value) ? (value as PageId) : 'dashboard'
}

function money(value: number) {
  return new Intl.NumberFormat('en-PH', {
    style: 'currency',
    currency: 'PHP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function moneyInCurrency(value: number, currency: 'PHP' | 'USD' | string) {
  return new Intl.NumberFormat('en-PH', {
    style: 'currency',
    currency: currency === 'USD' ? 'USD' : 'PHP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

type AnimatedNumberKind = 'money' | 'integer' | 'percent'

function formatAnimatedNumber(value: number, kind: AnimatedNumberKind) {
  if (kind === 'money') return money(value)
  if (kind === 'percent') return `${value.toFixed(2)}%`
  return new Intl.NumberFormat('en-PH', { maximumFractionDigits: 0 }).format(Math.round(value))
}

function AnimatedNumber({
  value,
  kind = 'money',
}: {
  value: number
  kind?: AnimatedNumberKind
}) {
  const currentRef = useRef(0)
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) {
      currentRef.current = value
      setDisplayed(value)
      return
    }
    const from = currentRef.current
    const distance = value - from
    const startedAt = window.performance.now()
    const duration = 720
    let frame = 0
    const update = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      const next = from + distance * eased
      currentRef.current = next
      setDisplayed(next)
      if (progress < 1) frame = window.requestAnimationFrame(update)
    }
    frame = window.requestAnimationFrame(update)
    return () => window.cancelAnimationFrame(frame)
  }, [kind, value])

  return <span className="animated-number"><span className="sr-only">{formatAnimatedNumber(value, kind)}</span><span aria-hidden="true">{formatAnimatedNumber(displayed, kind)}</span></span>
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

function downloadCsv(fileName: string, rows: (string | number)[][]) {
  const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

async function printDocument(bodyClass: string, selector: string) {
  const cleanup = () => {
    document.body.classList.remove(bodyClass)
    window.removeEventListener('afterprint', cleanup)
  }
  document.body.classList.add(bodyClass)
  window.addEventListener('afterprint', cleanup)
  const images = Array.from(document.querySelectorAll<HTMLImageElement>(`${selector} img`))
  await Promise.all(images.map((image) => image.complete ? Promise.resolve() : image.decode().catch(() => undefined)))
  await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  window.print()
  window.setTimeout(cleanup, 1500)
}

function printOfficialDocument() { return printDocument('printing-official-document', '.print-document-host') }
function printQuotationDocument() { return printDocument('printing-quotation-document', '.print-quotation-host') }

const apiRoleToRole: Record<ApiUser['role'], Role> = {
  ADMIN: 'Admin',
  REQUESTER: 'Requester',
  GM: 'GM',
  DCS: 'DCS',
  MICH: 'Mich',
}

const documentedRoles: readonly Role[] = ['Admin', 'Requester', 'GM', 'DCS', 'Mich']
const roleWorkspaceIcons: Record<Role, LucideIcon> = {
  Admin: ShieldCheck,
  Requester: UserRound,
  GM: ClipboardCheck,
  DCS: HandCoins,
  Mich: BookOpen,
}

function apiBudgetToRow(item: ApiBudgetRequest): BudgetRequest {
  const approval = {
    DRAFT: 'Draft',
    PENDING_REVIEW: 'Pending Mich Review',
    PENDING_APPROVAL: 'Pending Approval',
    APPROVED: 'Approved',
    REJECTED: 'Rejected',
    PARTIALLY_RELEASED: 'Approved',
    RELEASED: 'Approved',
    CANCELLED: 'Cancelled',
  }[item.status]
  const release = item.status === 'RELEASED' ? 'Released' : item.status === 'PARTIALLY_RELEASED' ? 'Partially released' : 'Unreleased'
  return {
    id: item.id,
    reference: item.reference,
    kind: item.budget_kind,
    parentReference: item.parent_budget_id,
    additionalReason: item.additional_reason,
    relatedExpenseDescription: item.related_expense_description,
    relatedExpenseAmount: item.related_expense_amount,
    date: new Date(`${item.request_date}T00:00:00`).toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: 'numeric' }),
    client: item.client.name,
    shipment: item.shipment_reference,
    requester: item.requester.display_name,
    buying: Number(item.buying_total),
    selling: Number(item.selling_total),
    approval,
    release,
    liquidation: 'Not started',
    billing: approval === 'Approved' ? 'Ready to bill' : 'Not billed',
    updated: new Date(item.updated_at).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' }),
    version: item.version,
    paymentStatus: item.payment_status,
    source: item,
  }
}

function Button({
  children,
  tone = 'primary',
  icon: Icon,
  onClick,
  type = 'button',
  disabled = false,
  className = '',
}: {
  children: ReactNode
  tone?: 'primary' | 'secondary' | 'ghost' | 'danger'
  icon?: LucideIcon
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  className?: string
}) {
  return (
    <button className={`button button--${tone} ${className}`} onClick={onClick} type={type} disabled={disabled}>
      {Icon ? <Icon size={17} aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  )
}

function HelpTip({ label, children }: { label: string; children: ReactNode }) {
  const id = useId()
  return <span className="help-tip"><button type="button" aria-label={label} aria-describedby={id}><CircleHelp size={16} /></button><span id={id} role="tooltip">{children}</span></span>
}

function Status({ children, tone }: { children: ReactNode; tone?: Tone }) {
  const resolvedTone = tone ?? toneForStatus(String(children))
  return <span className={`status status--${resolvedTone}`}>{children}</span>
}

function OwnerBadge({ children }: { children: ReactNode }) {
  return <span className="owner-badge"><UserRound size={13} />{children}</span>
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>
}

function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="section-header">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {action ? <div className="section-header__action">{action}</div> : null}
    </div>
  )
}

function EmptyState({ icon: Icon, title, detail }: { icon: LucideIcon; title: string; detail: string }) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon"><Icon size={22} /></span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  )
}

const openDialogStack: HTMLElement[] = []

function useDialogKeyboard(
  open: boolean,
  onClose: () => void,
  dialogRef: RefObject<HTMLElement | null>,
) {
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  useEffect(() => {
    const dialog = dialogRef.current
    if (!open || !dialog) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousBodyOverflow = document.body.style.overflow
    openDialogStack.push(dialog)
    document.body.style.overflow = 'hidden'

    const focusable = () => Array.from(dialog.querySelectorAll<HTMLElement>(
      'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex]:not([tabindex="-1"])',
    )).filter((element) => !element.hasAttribute('hidden'))

    window.requestAnimationFrame(() => focusable()[0]?.focus())
    const onKey = (event: KeyboardEvent) => {
      if (openDialogStack.at(-1) !== dialog) return
      if (event.key === 'Escape') {
        event.preventDefault()
        closeRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const controls = focusable()
      if (!controls.length) {
        event.preventDefault()
        dialog.focus()
        return
      }
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
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      const index = openDialogStack.lastIndexOf(dialog)
      if (index >= 0) openDialogStack.splice(index, 1)
      document.body.style.overflow = previousBodyOverflow
      window.requestAnimationFrame(() => previousFocus?.focus())
    }
  }, [open, dialogRef])
}

function Drawer({ title, eyebrow, open, onClose, children, className = '' }: { title: string; eyebrow?: string; open: boolean; onClose: () => void; children: ReactNode; className?: string }) {
  const dialogRef = useRef<HTMLElement>(null)
  useDialogKeyboard(open, onClose, dialogRef)

  if (!open) return null
  return (
    <div className="overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside ref={dialogRef} className={`drawer ${className}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1}>
        <div className="drawer__header">
          <div>
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            <h2>{title}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close panel"><X size={20} /></button>
        </div>
        <div className="drawer__body">{children}</div>
      </aside>
    </div>
  )
}

function Modal({ title, open, onClose, children, className = '' }: { title: string; open: boolean; onClose: () => void; children: ReactNode; className?: string }) {
  const dialogRef = useRef<HTMLDivElement>(null)
  useDialogKeyboard(open, onClose, dialogRef)

  if (!open) return null
  return (
    <div className="overlay overlay--center" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div ref={dialogRef} className={`modal ${className}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1}>
        <div className="drawer__header">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20} /></button>
        </div>
        <div className="drawer__body">{children}</div>
      </div>
    </div>
  )
}

type PwaInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

const PWA_INSTALL_DISMISSAL_KEY = 'pimascor:pwa-install-dismissed-until'
const PWA_INSTALL_DISMISSAL_MS = 14 * 24 * 60 * 60 * 1000

function isRunningAsInstalledApp() {
  const displayModes = ['standalone', 'fullscreen', 'minimal-ui', 'window-controls-overlay']
  const hasInstalledDisplayMode = displayModes.some((mode) => window.matchMedia(`(display-mode: ${mode})`).matches)
  const iosStandalone = Boolean((navigator as Navigator & { standalone?: boolean }).standalone)
  return hasInstalledDisplayMode || iosStandalone
}

function ReleaseUpdateModal({ update, open, onAcknowledged }: { update: ApiReleaseUpdate | null; open: boolean; onAcknowledged: () => void }) {
  const [busy, setBusy] = useState(false)

  if (!update) return null

  async function acknowledge() {
    if (busy) return
    setBusy(true)
    // Close immediately so a temporary acknowledgement failure never blocks
    // access to the workspace. The API will show the update again next login
    // if the acknowledgement could not be saved.
    onAcknowledged()
    try {
      await acknowledgeReleaseUpdate()
    } catch {
      // Keep the next-login retry behaviour without interrupting the workflow.
    } finally {
      setBusy(false)
    }
  }

  const kindLabel: Record<ApiReleaseUpdate['changes'][number]['kind'], string> = {
    new: 'New',
    improved: 'Improved',
    changed: 'Updated',
    removed: 'Removed',
  }
  const releasedOn = new Date(`${update.released_on}T00:00:00`).toLocaleDateString('en-PH', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  return <Modal title="What's new in PIMASCOR" open={open} onClose={() => void acknowledge()}>
    <div className="release-update">
      <div className="release-update__heading">
        <p className="eyebrow">Released {releasedOn}</p>
        <h3>{update.title}</h3>
        <p>{update.summary}</p>
      </div>
      <div className="release-update__list" role="list" aria-label="Latest PIMASCOR updates">
        {update.changes.map((change) => <article className="release-update__item" key={`${change.kind}-${change.title}`} role="listitem">
          <span className={`release-update__tag release-update__tag--${change.kind}`}>{kindLabel[change.kind]}</span>
          <div><strong>{change.title}</strong><p>{change.description}</p></div>
        </article>)}
      </div>
      <Button type="button" onClick={() => void acknowledge()} disabled={busy}>{busy ? 'Saving…' : 'Continue to workspace'}</Button>
    </div>
  </Modal>
}

function PwaInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<PwaInstallPromptEvent | null>(null)
  const [installed, setInstalled] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const [installBusy, setInstallBusy] = useState(false)
  const [platform, setPlatform] = useState<'ios' | 'android' | 'desktop'>('desktop')

  useEffect(() => {
    setInstalled(isRunningAsInstalledApp())
    try {
      setDismissed(Number(window.localStorage.getItem(PWA_INSTALL_DISMISSAL_KEY) ?? 0) > Date.now())
    } catch {
      // Storage may be unavailable in private browsing; keep the reminder visible.
    }
    const userAgent = navigator.userAgent
    const isIos = /iPad|iPhone|iPod/.test(userAgent)
      || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
    setPlatform(isIos ? 'ios' : /Android/.test(userAgent) ? 'android' : 'desktop')

    const capturePrompt = (event: Event) => {
      event.preventDefault()
      setDeferredPrompt(event as PwaInstallPromptEvent)
    }
    const markInstalled = () => {
      setInstalled(true)
      setDeferredPrompt(null)
    }
    window.addEventListener('beforeinstallprompt', capturePrompt)
    window.addEventListener('appinstalled', markInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', capturePrompt)
      window.removeEventListener('appinstalled', markInstalled)
    }
  }, [])

  function dismissReminder() {
    setDismissed(true)
    try {
      window.localStorage.setItem(PWA_INSTALL_DISMISSAL_KEY, String(Date.now() + PWA_INSTALL_DISMISSAL_MS))
    } catch {
      // The reminder remains dismissed for this render even without storage.
    }
  }

  async function installNow() {
    if (!deferredPrompt) {
      setGuideOpen(true)
      return
    }
    setInstallBusy(true)
    try {
      await deferredPrompt.prompt()
      const choice = await deferredPrompt.userChoice
      if (choice.outcome === 'accepted') setInstalled(true)
    } catch {
      // Browser install prompts can reject when the browser closes or changes
      // state; keep the manual instructions available instead of trapping the
      // button in a busy state.
      setGuideOpen(true)
    } finally {
      setDeferredPrompt(null)
      setInstallBusy(false)
    }
  }

  if (installed || dismissed) return null

  const platformLabel = platform === 'ios' ? 'iPhone or iPad' : platform === 'android' ? 'Android phone' : 'your device'
  return <>
    <section className="pwa-install" aria-label="Install PIMASCOR">
      <span className="pwa-install__icon"><Download size={20} aria-hidden="true" /></span>
      <div className="pwa-install__copy">
        <p className="eyebrow">A better way to work</p>
        <strong>Install PIMASCOR on {platformLabel}</strong>
        <p>Open your protected workspace from the Home Screen with a focused, app-like layout.</p>
      </div>
      <div className="pwa-install__actions">
        <Button tone="secondary" icon={Download} onClick={() => void installNow()} disabled={installBusy}>
          {installBusy ? 'Opening…' : deferredPrompt ? 'Install app' : 'How to install'}
        </Button>
        <button type="button" className="text-button" onClick={dismissReminder}>Maybe later</button>
      </div>
    </section>
    <Modal title="Install PIMASCOR as an app" open={guideOpen} onClose={() => setGuideOpen(false)}>
      <div className="pwa-guide">
        <p className="pwa-guide__intro">Installing PIMASCOR keeps it one tap away and opens it in a focused workspace. Your sign-in and security controls remain the same.</p>
        <section className={platform === 'ios' ? 'pwa-guide__step pwa-guide__step--active' : 'pwa-guide__step'}>
          <div><span className="pwa-guide__number">1</span><h3>iPhone or iPad</h3></div>
          <p>Open this page in <strong>Safari</strong>, tap <strong>Share</strong>, choose <strong>Add to Home Screen</strong>, enable <strong>Open as Web App</strong> if shown, then tap <strong>Add</strong>.</p>
        </section>
        <section className={platform === 'android' ? 'pwa-guide__step pwa-guide__step--active' : 'pwa-guide__step'}>
          <div><span className="pwa-guide__number">2</span><h3>Android</h3></div>
          <p>Open this page in <strong>Chrome</strong>, tap the <strong>⋮</strong> menu, choose <strong>Add to home screen</strong> or <strong>Install app</strong>, then confirm <strong>Install</strong>.</p>
        </section>
        <section className={platform === 'desktop' ? 'pwa-guide__step pwa-guide__step--active' : 'pwa-guide__step'}>
          <div><span className="pwa-guide__number">3</span><h3>Desktop browser</h3></div>
          <p>In a compatible Chromium browser, use the install icon in the address bar or the browser menu. If no install option appears, keep using PIMASCOR in the browser.</p>
        </section>
        <div className="callout callout--info"><CircleHelp size={18} /><span>Only install from the official HTTPS address: <strong>{window.location.origin}{import.meta.env.BASE_URL}</strong>.</span></div>
      </div>
    </Modal>
  </>
}

type ConfidentialDocumentItem = {
  id: string
  name: string
  contentType: string | null
}

function ConfidentialDocumentViewer({ item, onClose, canDownload = false }: { item: ConfidentialDocumentItem | null; onClose: () => void; canDownload?: boolean }) {
  const [objectUrl, setObjectUrl] = useState('')
  const [contentType, setContentType] = useState('')
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    if (!item) {
      setObjectUrl('')
      setContentType('')
      setState('loading')
      return
    }
    const controller = new AbortController()
    let allocatedUrl = ''
    setObjectUrl('')
    setContentType('')
    setState('loading')
    void getDocumentBlob(item.id, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return
        allocatedUrl = URL.createObjectURL(result.blob)
        setContentType(result.contentType)
        setObjectUrl(allocatedUrl)
      })
      .catch((reason) => {
        if (controller.signal.aborted || (reason instanceof DOMException && reason.name === 'AbortError')) return
        setState('error')
      })
    return () => {
      controller.abort()
      if (allocatedUrl) URL.revokeObjectURL(allocatedUrl)
    }
  }, [item, retryKey])

  const renderFailed = () => {
    if (!item || state === 'error') return
    setState('error')
    emitApiIncident(new ApiError({
      message: 'The confidential document arrived, but this browser could not display it.',
      status: 0,
      code: 'DOCUMENT_RENDER_FAILED',
      recovery: 'Dismiss this report, close the viewer, and try the document once more. If it stays blank, report it for investigation.',
      canContinue: true,
      operation: 'Open a supporting document',
      requestMethod: 'GET',
      requestPath: `/documents/${item.id}/view`,
    }))
  }
  const isImage = contentType === 'image/jpeg' || contentType === 'image/png'
  const isPdf = contentType === 'application/pdf'
  async function saveCopy() {
    if (!item) return
    const result = await downloadDocument(item.id)
    const url = URL.createObjectURL(result.blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = result.fileName
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return <Modal title={item?.name ?? 'Confidential document'} open={Boolean(item)} onClose={onClose}>
    {item ? <div className="secure-viewer">
      <div className="callout callout--info"><ShieldCheck size={18} /><span>{canDownload ? 'Protected record. Authorized downloads are recorded in the audit trail.' : 'View-only confidential record. Download permission is limited to authorized roles.'}</span>{canDownload ? <Button tone="secondary" onClick={() => void saveCopy()}>Download authorised copy</Button> : null}</div>
      <div className={`secure-viewer__stage secure-viewer__stage--${state}`} aria-live="polite" aria-busy={state === 'loading'}>
        {state === 'loading' ? <div className="secure-viewer__status"><RefreshCw className="spin" size={24} /><strong>Preparing protected preview…</strong><span>Keep this viewer open while the file is checked.</span></div> : null}
        {state === 'error' ? <div className="secure-viewer__status secure-viewer__status--error"><AlertCircle size={26} /><strong>This document did not load.</strong><span>Check your connection, then try the protected preview again. The original file has not been changed.</span><button className="button button--primary" type="button" onClick={() => setRetryKey((value) => value + 1)}><RefreshCw size={16} /> Try again</button></div> : null}
        {objectUrl && isImage ? <img
          className="secure-viewer__image"
          src={objectUrl}
          alt={`Confidential document: ${item.name}`}
          decoding="async"
          draggable={false}
          onLoad={() => setState('ready')}
          onError={renderFailed}
          onContextMenu={(event) => event.preventDefault()}
        /> : null}
        {objectUrl && isPdf ? <iframe
          className="secure-viewer__pdf"
          title={`Confidential document: ${item.name}`}
          src={`${objectUrl}#toolbar=0&navpanes=0`}
          referrerPolicy="no-referrer"
          onLoad={() => setState('ready')}
          onError={renderFailed}
        /> : null}
      </div>
    </div> : null}
  </Modal>
}

function DashboardPage({ role, displayName, navigate }: { role: Role; displayName: string; navigate: (page: PageId) => void }) {
  const [dashboard, setDashboard] = useState<ApiShipmentProfitability | null>(null)
  const [month, setMonth] = useState(() => {
    const parts = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', timeZone: 'Asia/Manila' }).formatToParts(new Date())
    return `${parts.find((part) => part.type === 'year')?.value}-${parts.find((part) => part.type === 'month')?.value}`
  })
  const [shipmentStatus, setShipmentStatus] = useState('ALL')
  const [comparisonView, setComparisonView] = useState<'bars' | 'figures'>('bars')
  const [error, setError] = useState('')
  const today = new Intl.DateTimeFormat('en-PH', { dateStyle: 'full', timeZone: 'Asia/Manila' }).format(new Date())
  const managementView = role === 'Admin' || role === 'GM' || role === 'DCS'
  const monthOptions = useMemo(() => Array.from({ length: 12 }, (_, index) => {
    const current = new Date()
    current.setDate(1)
    current.setMonth(current.getMonth() - index)
    return {
      value: `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`,
      label: new Intl.DateTimeFormat('en-PH', { month: 'long', year: 'numeric', timeZone: 'Asia/Manila' }).format(current),
    }
  }), [])
  useEffect(() => {
    setDashboard(null)
    setError('')
    getShipmentProfitability(month)
      .then(setDashboard)
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load shipment profitability.'))
  }, [month])
  const visibleRows = (dashboard?.rows ?? []).filter((item) => {
    if (shipmentStatus === 'LIQUIDATION_OPEN') return item.liquidation_status !== 'Closed'
    if (shipmentStatus === 'LIQUIDATION_CLOSED') return item.liquidation_status === 'Closed'
    if (shipmentStatus === 'RECEIVABLES_OPEN') return Number(item.outstanding_receivable) > 0
    if (shipmentStatus === 'COLLECTED') return item.collection_status === 'Fully Collected'
    if (shipmentStatus === 'NEEDS_ATTENTION') return item.liquidation_status !== 'Closed' || Number(item.outstanding_receivable) > 0
    return true
  })
  const maxComparison = Math.max(
    1,
    ...visibleRows.flatMap((item) => [Number(item.selling_amount), Number(item.actual_spending)]),
  )
  const paymentSummary = dashboard?.request_for_payment_summary
  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow eyebrow--light">{today} • Asia/Manila</p>
          <h2>Welcome, {displayName}.</h2>
          <p>Review shipment earnings, spending, liquidation, and collections in one connected view.</p>
        </div>
        <div className="hero-panel__mark" aria-hidden="true"><Ship size={36} /></div>
      </section>

      {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
      <div className="explanation-banner"><span><TrendingUp size={20} /></span><div><strong>Profitability per Shipment</strong><p>Selling comes from approved Budget Requests. Actual spending comes from Liquidations. Collections and aging come from finalized Billing records and allocated client payments.</p></div></div>

      {managementView ? <Card className="dashboard-controls">
        <div>
          <label className="select-field"><span>Reporting month</span><select value={month} onChange={(event) => setMonth(event.target.value)}>{monthOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label className="select-field"><span>Shipment status</span><select value={shipmentStatus} onChange={(event) => setShipmentStatus(event.target.value)}><option value="ALL">All shipment statuses</option><option value="NEEDS_ATTENTION">Needs attention</option><option value="LIQUIDATION_OPEN">Liquidation open</option><option value="LIQUIDATION_CLOSED">Liquidation closed</option><option value="RECEIVABLES_OPEN">Receivables open</option><option value="COLLECTED">Fully collected</option></select></label>
        </div>
        <p><strong>{visibleRows.length}</strong> of {dashboard?.shipment_count ?? 0} shipments shown for the selected month.</p>
      </Card> : null}

      <div className="kpi-grid">
        <Card className="kpi"><div className="kpi__top"><span>Shipments</span><Ship size={17} /></div><strong>{dashboard ? <AnimatedNumber value={dashboard.shipment_count} kind="integer" /> : '—'}</strong><p>Visible to your role</p></Card>
        <Card className="kpi"><div className="kpi__top"><span>Total selling</span><TrendingUp size={17} /></div><strong>{dashboard ? <AnimatedNumber value={Number(dashboard.total_selling)} /> : '—'}</strong><p>Approved Budget Requests</p></Card>
        <Card className={`kpi ${dashboard && Number(dashboard.total_profit) < 0 ? 'kpi--danger' : 'kpi--success'}`}><div className="kpi__top"><span>Total profit</span><CircleDollarSign size={17} /></div><strong>{dashboard ? <AnimatedNumber value={Number(dashboard.total_profit)} /> : '—'}</strong><p>{dashboard?.overall_margin_percentage === null || !dashboard ? 'Margin unavailable' : <><AnimatedNumber value={Number(dashboard.overall_margin_percentage)} kind="percent" /> margin</>}</p></Card>
        <Card className="kpi kpi--warning"><div className="kpi__top"><span>Outstanding receivables</span><Clock3 size={17} /></div><strong>{dashboard ? <AnimatedNumber value={Number(dashboard.total_outstanding_receivable)} /> : '—'}</strong><p>Finalized Billing less collections</p></Card>
      </div>

      {managementView ? <Card className="payment-summary-card">
        <SectionHeader eyebrow="Request for Payment" title="Monthly payment request summary" description="OPEX, Marketing, Loan Payment, and Other requests recorded for the selected month. Cancelled requests are excluded." action={<Button icon={ArrowRight} onClick={() => navigate('payment-requests')}>Open Request for Payment</Button>} />
        <div className="payment-type-grid">
          <div><span>OPEX</span><strong>{paymentSummary ? <AnimatedNumber value={Number(paymentSummary.opex_total)} /> : '—'}</strong><small>{paymentSummary?.opex_count ?? 0} request{paymentSummary?.opex_count === 1 ? '' : 's'}</small></div>
          <div><span>Marketing</span><strong>{paymentSummary ? <AnimatedNumber value={Number(paymentSummary.marketing_total)} /> : '—'}</strong><small>{paymentSummary?.marketing_count ?? 0} request{paymentSummary?.marketing_count === 1 ? '' : 's'}</small></div>
          <div><span>Loan Payments</span><strong>{paymentSummary ? <AnimatedNumber value={Number(paymentSummary.loan_payment_total)} /> : '—'}</strong><small>{paymentSummary?.loan_payment_count ?? 0} request{paymentSummary?.loan_payment_count === 1 ? '' : 's'}</small></div>
          <div><span>Other</span><strong>{paymentSummary ? <AnimatedNumber value={Number(paymentSummary.other_total)} /> : '—'}</strong><small>{paymentSummary?.other_count ?? 0} request{paymentSummary?.other_count === 1 ? '' : 's'}</small></div>
          <div className="payment-type-grid__total"><span>Total requests</span><strong>{paymentSummary ? <AnimatedNumber value={Number(paymentSummary.grand_total)} /> : '—'}</strong><small>{paymentSummary?.total_count ?? 0} records</small></div>
        </div>
      </Card> : null}

      <Card className="chart-card">
        <SectionHeader eyebrow="Budget Request comparison" title="Selling versus actual spending" description={managementView ? 'Choose an animated bar comparison or exact figures. The control table remains available below.' : 'Each pair represents one shipment. The table below provides the same figures without relying on color.'} action={managementView ? <div className="view-switch" role="group" aria-label="Comparison view"><button type="button" className={comparisonView === 'bars' ? 'active' : ''} aria-pressed={comparisonView === 'bars'} onClick={() => setComparisonView('bars')}><LayoutDashboard size={16} />Bar chart</button><button type="button" className={comparisonView === 'figures' ? 'active' : ''} aria-pressed={comparisonView === 'figures'} onClick={() => setComparisonView('figures')}><BookOpen size={16} />Figures</button></div> : undefined} />
        {comparisonView === 'bars' ? <div className="chart-legend"><span><i className="legend-dot legend-dot--gold" />Selling</span><span><i className="legend-dot legend-dot--navy" />Actual spending</span></div> : null}
        {visibleRows.length && comparisonView === 'bars' ? <div className="shipment-bars" aria-label="Selling and actual spending per shipment">
          {visibleRows.slice(0, 12).map((item, index) => (
            <div className="shipment-bars__row" key={item.budget_request_id}>
              <span><strong>{item.reference}</strong><small>{item.shipment_reference}</small></span>
              <div className="shipment-bars__tracks">
                <span className="shipment-bar shipment-bar--selling" style={{ width: `${Number(item.selling_amount) > 0 ? Math.max(2, (Number(item.selling_amount) / maxComparison) * 100) : 0}%`, animationDelay: `${index * 55}ms` }}><i><AnimatedNumber value={Number(item.selling_amount)} /></i></span>
                <span className="shipment-bar shipment-bar--actual" style={{ width: `${Number(item.actual_spending) > 0 ? Math.max(2, (Number(item.actual_spending) / maxComparison) * 100) : 0}%`, animationDelay: `${index * 55 + 90}ms` }}><i><AnimatedNumber value={Number(item.actual_spending)} /></i></span>
              </div>
            </div>
          ))}
        </div> : null}
        {visibleRows.length && comparisonView === 'figures' ? <div className="shipment-figures" aria-label="Exact shipment profitability figures">{visibleRows.slice(0, 12).map((item) => <article key={item.budget_request_id}><header><strong>{item.reference}</strong><small>{item.client_name} • {item.shipment_reference}</small></header><dl><div><dt>Selling</dt><dd><AnimatedNumber value={Number(item.selling_amount)} /></dd></div><div><dt>Actual spending</dt><dd><AnimatedNumber value={Number(item.actual_spending)} /></dd></div><div><dt>Profit</dt><dd className={Number(item.profit) < 0 ? 'danger-text' : 'number--positive'}><AnimatedNumber value={Number(item.profit)} /></dd></div><div><dt>Margin</dt><dd>{item.profit_margin_percentage === null ? '—' : <AnimatedNumber value={Number(item.profit_margin_percentage)} kind="percent" />}</dd></div></dl></article>)}</div> : null}
        {!visibleRows.length ? <EmptyState icon={Ship} title="No shipments match this view" detail="Choose another month or shipment status." /> : null}
      </Card>

      <Card>
        <SectionHeader eyebrow="Shipment control table" title="Profitability, liquidation, and collection status" description="Profit equals selling less actual spending. Margin is profit divided by selling." action={role !== 'Requester' ? <Button tone="ghost" onClick={() => navigate('collections')}>Open Client Payments</Button> : undefined} />
        <div className="table-wrap"><table><thead><tr><th>Shipment</th><th>Selling</th><th>Actual spending</th><th>Profit</th><th>Margin</th><th>Liquidation</th><th>Collection</th><th>Aging</th></tr></thead><tbody>
          {visibleRows.map((item) => <tr key={item.budget_request_id}><td data-label="Shipment"><strong>{item.reference}</strong><small>{item.client_name} • {item.shipment_reference}</small></td><td data-label="Selling" className="number"><AnimatedNumber value={Number(item.selling_amount)} /></td><td data-label="Actual spending" className="number"><AnimatedNumber value={Number(item.actual_spending)} /></td><td data-label="Profit" className={`number ${Number(item.profit) < 0 ? 'danger-text' : 'number--emphasis'}`}><AnimatedNumber value={Number(item.profit)} /></td><td data-label="Margin">{item.profit_margin_percentage === null ? '—' : <AnimatedNumber value={Number(item.profit_margin_percentage)} kind="percent" />}</td><td data-label="Liquidation"><Status>{item.liquidation_status}</Status></td><td data-label="Collection"><Status>{item.collection_status}</Status>{Number(item.outstanding_receivable) > 0 ? <small><AnimatedNumber value={Number(item.outstanding_receivable)} /> outstanding</small> : null}</td><td data-label="Aging">{item.receivables_aging_days === null ? '—' : <><AnimatedNumber value={item.receivables_aging_days} kind="integer" /> days</>}</td></tr>)}
        </tbody></table></div>
      </Card>

      <div className="attention-grid">
        {attentionByRole[role].slice(0, 3).map((item) => (
          <button className={`attention-card attention-card--${item.tone}`} key={item.id} onClick={() => navigate(item.page)}>
            <div className="attention-card__top"><span className="attention-card__eyebrow">{item.eyebrow}</span><span className="attention-card__age">{item.age}</span></div>
            <strong>{item.title}</strong><p>{item.detail}</p><span className="attention-card__action">{item.action}<ArrowRight size={15} /></span>
          </button>
        ))}
      </div>
    </div>
  )
}

const commonChargeTypes = [
  ['Brokerage Fee', 'SERVICE_CHARGE'],
  ['Handling (OT)', 'SERVICE_CHARGE'],
  ['Documentation (OT)', 'SERVICE_CHARGE'],
  ['Processing Expense (OT)', 'SERVICE_CHARGE'],
  ['CNIU Clearance', 'SERVICE_CHARGE'],
  ['Overtime Releasing (OT)', 'SERVICE_CHARGE'],
  ['Duties and Taxes', 'PASS_THROUGH'],
  ['Storage', 'PASS_THROUGH'],
  ['Forwarding Charges', 'PASS_THROUGH'],
  ['Shipping Line Charges', 'PASS_THROUGH'],
  ['Trucking', 'PASS_THROUGH'],
  ['Logistics Support Service', 'PASS_THROUGH'],
  ['Transportation', 'PASS_THROUGH'],
  ['Food', 'PASS_THROUGH'],
] as const

type BudgetFormLine = { description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; buying: string; selling: string }

function budgetLinesFromApi(source: ApiBudgetRequest): BudgetFormLine[] {
  const grouped = new Map<string, BudgetFormLine>()
  source.items.forEach((item) => {
    const key = `${item.description}\u0000${item.classification}`
    const line = grouped.get(key) ?? {
      description: item.description,
      classification: item.classification,
      buying: '',
      selling: '',
    }
    if (item.kind === 'BUYING') line.buying = item.amount
    else line.selling = item.amount
    grouped.set(key, line)
  })
  return [...grouped.values()]
}

function BudgetLineEditor({ lines, setLines }: { lines: BudgetFormLine[]; setLines: (lines: BudgetFormLine[]) => void }) {
  const update = (index: number, values: Partial<BudgetFormLine>) => setLines(lines.map((line, row) => row === index ? { ...line, ...values } : line))
  return <fieldset className="line-editor"><legend>Buying and selling line items</legend><p className="helper-copy">Choose a familiar charge. Select Others to enter a precise description. Buying is PIMASCOR's expected cost; Selling is the amount intended for the client.</p>{lines.map((line, index) => { const custom = !commonChargeTypes.some(([name]) => name === line.description); return <div className="line-editor__row" key={index}>
    <label>Charge type<select value={custom ? '__OTHER__' : line.description} onChange={(event) => { const selected = commonChargeTypes.find(([name]) => name === event.target.value); update(index, { description: selected?.[0] ?? 'Other', classification: selected?.[1] ?? 'SERVICE_CHARGE' }) }}>{commonChargeTypes.map(([name]) => <option key={name}>{name}</option>)}<option value="__OTHER__">Others — enter a custom charge</option></select>{custom ? <input aria-label="Custom charge type" value={line.description === 'Other' ? '' : line.description} onChange={(event) => update(index, { description: event.target.value })} placeholder="Enter the charge name" required /> : null}</label>
    <label>Classification<select value={line.classification} onChange={(event) => update(index, { classification: event.target.value as BudgetFormLine['classification'] })}><option value="SERVICE_CHARGE">Service charge</option><option value="PASS_THROUGH">Pass-through cost</option></select></label>
    <label>Buying<input type="number" min="0" step="0.01" value={line.buying} onChange={(event) => update(index, { buying: event.target.value })} /></label>
    <label>Selling<input type="number" min="0" step="0.01" value={line.selling} onChange={(event) => update(index, { selling: event.target.value })} /></label>
    <button type="button" className="icon-button" aria-label={`Remove ${line.description}`} disabled={lines.length === 1} onClick={() => setLines(lines.filter((_, row) => row !== index))}><X size={17} /></button>
  </div>})}<Button tone="ghost" icon={Plus} onClick={() => setLines([...lines, { description: 'Brokerage Fee', classification: 'SERVICE_CHARGE', buying: '', selling: '' }])}>Add line item</Button></fieldset>
}

type QuotationLineDraft = {
  section: 'ORIGIN_FREIGHT' | 'DESTINATION_CLEARANCE'
  description: string
  currency: 'PHP' | 'USD'
  amount: string
  billed_by: 'PIMASCOR' | 'BOC'
}

const revisedQuotationTerms = `1. Duties and taxes are pass-through costs subject to the actual Bureau of Customs assessment.
2. Storage, demurrage, detention, stripping, and similar charges are excluded unless agreed in writing; actual charges are for the client's account.
3. Unreceipted expenses require client approval before disbursement.
4. Duties and taxes are payable before BOC lodgment; service fees are payable upon delivery.
Penalty interests: Any amount due and payable in favor of PIMASCOR is subject to a three percent (3%) monthly compounded penalty interest.`

function QuotationPrintDocument({ quotation, printCopy = false }: { quotation: ApiQuotation; printCopy?: boolean }) {
  const originLines = quotation.lines.filter((line) => line.section === 'ORIGIN_FREIGHT')
  const destinationLines = quotation.lines.filter((line) => line.section === 'DESTINATION_CLEARANCE')
  const total = (lines: ApiQuotationLine[], currency: 'PHP' | 'USD', billedBy?: 'PIMASCOR' | 'BOC') => lines
    .filter((line) => line.currency === currency && (!billedBy || line.billed_by === billedBy))
    .reduce((sum, line) => sum + Number(line.amount), 0)
  const currencyTotals = (lines: ApiQuotationLine[], billedBy?: 'PIMASCOR' | 'BOC') => (['USD', 'PHP'] as const)
    .map((currency) => ({ currency, amount: total(lines, currency, billedBy) }))
    .filter((item) => item.amount > 0)
  const formatDate = new Date(quotation.created_at).toLocaleDateString('en-PH', { month: 'long', day: 'numeric', year: 'numeric' })
  const originCurrencyTotals = currencyTotals(originLines)
  const destinationCurrencyTotals = currencyTotals(destinationLines)
  const destinationPimascorTotals = currencyTotals(destinationLines, 'PIMASCOR')
  const destinationBocTotals = currencyTotals(destinationLines, 'BOC')

  return <article className={`official-billing official-quotation ${printCopy ? 'official-quotation--print' : 'official-quotation--preview'}`}>
    {quotation.status !== 'CLIENT_ACCEPTED' ? <div className="official-billing__watermark">{quotation.status.replaceAll('_', ' ')}</div> : null}
    <header className="official-billing__letterhead">
      <img src={brandIconUrl} alt="PIMASCOR" />
      <div><strong>Philippine Interactive Maritime and Arrastre Services</strong><span>DELIVER | CONVERGE | SUPPLY</span></div>
      <p><small>Quotation No.</small><b>{quotation.reference}</b></p>
    </header>
    <section className="official-quotation__meta">
      <p><b>Date:</b> {formatDate}</p><p><b>Attention:</b> {quotation.client.name}</p><p><b>Client Ref. No.:</b> {quotation.client.code}</p><p><b>Project Ref:</b> {quotation.shipment_reference}</p>
    </section>
    <section className="official-quotation__shipment">
      <h2>I. Shipment summary</h2>
      <ul><li><b>Mode of Transport:</b> {quotation.mode_of_transport || '—'}</li><li><b>Container:</b> {quotation.container_type || '—'}</li><li><b>Origin:</b> {quotation.origin || '—'}</li><li><b>Destination:</b> {quotation.destination || '—'}</li><li><b>Incoterms:</b> {quotation.incoterms || '—'}</li><li><b>Cargo Details:</b> {quotation.cargo_details || '—'}</li></ul>
    </section>
    <section className="official-quotation__charge-section">
      <h2>II. Section A: Origin &amp; International Freight</h2><p>Charges related to pick up at origin, export documentation, and transit to the Philippines.</p>
      <table className="official-billing__charges"><colgroup><col /><col className="official-billing__currency-col" /><col className="official-billing__amount-col" /></colgroup><thead><tr><th>Description</th><th>Currency</th><th>Total amount</th></tr></thead><tbody>{originLines.length ? originLines.map((line) => <tr key={line.id}><td>{line.description}</td><td>{line.currency}</td><td>{moneyInCurrency(Number(line.amount), line.currency)}</td></tr>) : <tr><td colSpan={3}>No origin or international freight charges entered.</td></tr>}{originCurrencyTotals.map((item) => <tr className="official-billing__calculation-row official-billing__calculation-row--total" key={`origin-total-${item.currency}`}><th colSpan={2}>Total Section A (origin &amp; freight) - {item.currency}</th><td>{moneyInCurrency(item.amount, item.currency)}</td></tr>)}</tbody></table>
    </section>
    <section className="official-quotation__charge-section">
      <h2>III. Section B: Destination &amp; Customs Clearance</h2><p>Charges related to arrival, brokerage, and legal processing in the Philippines.</p>
      <table className="official-billing__charges"><colgroup><col /><col className="official-billing__currency-col" /><col className="official-billing__amount-col" /></colgroup><thead><tr><th>Description</th><th>Currency</th><th>Total amount</th></tr></thead><tbody>{destinationLines.length ? destinationLines.map((line) => <tr key={line.id}><td>{line.description}{line.billed_by === 'BOC' ? <small className="official-quotation__boc">To be billed by BOC</small> : null}</td><td>{line.currency}</td><td>{moneyInCurrency(Number(line.amount), line.currency)}</td></tr>) : <tr><td colSpan={3}>No destination or clearance charges entered.</td></tr>}{destinationCurrencyTotals.map((item) => <tr className="official-billing__calculation-row official-billing__calculation-row--total" key={`destination-total-${item.currency}`}><th colSpan={2}>Total Section B (destination &amp; clearance) - {item.currency}</th><td>{moneyInCurrency(item.amount, item.currency)}</td></tr>)}</tbody></table>
    </section>
    <section className="official-quotation__terms">
      <h2>IV. Grand total summary</h2><ul className="official-quotation__totals"><li><b>Total origin &amp; international freight:</b>{originCurrencyTotals.map((item) => <span key={`origin-summary-${item.currency}`}>{moneyInCurrency(item.amount, item.currency)}</span>)}</li><li><b>Total destination &amp; local services:</b>{destinationPimascorTotals.map((item) => <span key={`pimascor-summary-${item.currency}`}>{moneyInCurrency(item.amount, item.currency)} <small>(To be billed by PIMASCOR)</small></span>)}{destinationBocTotals.map((item) => <span key={`boc-summary-${item.currency}`}>{moneyInCurrency(item.amount, item.currency)} <small>(To be billed by BOC)</small></span>)}</li></ul>
      <h2>V. Terms and conditions</h2><div className="official-quotation__terms-copy"><p>{quotation.terms_and_conditions}</p><p><b>Validity:</b> This quotation shall be valid for {quotation.validity_hours} hours from receipt hereof.</p><p><b>Term of payment:</b> {quotation.payment_terms || 'To be agreed with the client.'}</p><p><b>Conformity:</b> Upon your conformity hereunder, this quotation shall serve as our agreement on the matter.</p></div>
      <div className="official-quotation__signatures"><div><b>WITH MY CONFORMITY:</b><span></span><small>Signature over printed Name</small><small>DULY AUTHORIZED FOR THE PURPOSE</small></div><div><p><b>Prepared by:</b> {quotation.created_by.display_name}</p><p><b>Approved by:</b> {quotation.approved_by?.display_name || 'Pending GM approval'}</p></div></div>
    </section>
    <footer><span>PIMASCOR • Sales quotation</span><span>{quotation.reference}</span></footer>
  </article>
}

function QuotationsPage({ role, notify }: { role: Role; notify: Notify }) {
  const [rows, setRows] = useState<ApiQuotation[] | null>(null)
  const [clients, setClients] = useState<ApiClient[]>([])
  const [selected, setSelected] = useState<ApiQuotation | null>(null)
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [quotationLines, setQuotationLines] = useState<QuotationLineDraft[]>([])
  const [previewZoom, setPreviewZoom] = useState(() => window.innerWidth <= 760 ? 50 : 85)
  const [viewingDocument, setViewingDocument] = useState<ConfidentialDocumentItem | null>(null)

  const load = useCallback(() => {
    Promise.all([getQuotations(), getClients()])
      .then(([quotations, configuredClients]) => { setRows(quotations); setClients(configuredClients); setSelected((current) => current ? quotations.find((item) => item.id === current.id) ?? null : null) })
      .catch((error) => notifyLocalFailure(error, 'Could not load Sales Quotations.', notify))
  }, [])

  useEffect(() => { load() }, [load])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      const phpTotal = quotationLines.filter((line) => line.currency === 'PHP').reduce((sum, line) => sum + Number(line.amount || 0), 0)
      const usdTotal = quotationLines.filter((line) => line.currency === 'USD').reduce((sum, line) => sum + Number(line.amount || 0), 0)
      if (!quotationLines.length || (!phpTotal && !usdTotal)) throw new Error('Add at least one PHP or USD quotation charge.')
      let item = await createQuotation({
        client_id: String(data.get('client_id')),
        shipment_reference: String(data.get('shipment_reference')),
        quoted_amount: (phpTotal || usdTotal).toFixed(2),
        currency: phpTotal ? 'PHP' : 'USD',
        terms_and_conditions: revisedQuotationTerms,
        mode_of_transport: String(data.get('mode_of_transport') || ''), container_type: String(data.get('container_type') || ''), origin: String(data.get('origin') || ''), destination: String(data.get('destination') || ''), incoterms: String(data.get('incoterms') || ''), cargo_details: String(data.get('cargo_details') || ''), payment_terms: String(data.get('payment_terms') || ''), validity_hours: Number(data.get('validity_hours') || 48),
        lines: quotationLines.map((line) => ({ ...line, amount: Number(line.amount).toFixed(2) })),
      })
      if ((event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-action') === 'submit') item = await submitQuotation(item.id, item.version)
      setCreating(false)
      notify(`${item.reference} ${item.status === 'PENDING_APPROVAL' ? 'sent to the GM for approval' : 'saved as a draft'}.`, 'success')
      load()
    } catch (error) { notifyLocalFailure(error, 'Could not save the Sales Quotation.', notify) } finally { setBusy(false) }
  }

  async function submit(item: ApiQuotation) {
    setBusy(true)
    try { await submitQuotation(item.id, item.version); notify(`${item.reference} sent to the GM for approval.`, 'success'); load() }
    catch (error) { notifyLocalFailure(error, 'Could not submit the Sales Quotation.', notify) } finally { setBusy(false) }
  }

  async function decide(item: ApiQuotation, approve: boolean) {
    if (!approve && !note.trim()) { notify('Enter the correction the Sales Executive must make.', 'danger'); return }
    setBusy(true)
    try {
      if (role === 'DCS') {
        if (note.trim().length < 10) throw new Error('Explain why the GM is unavailable before using the DCS override.')
        await overrideQuotationAsDcs(item.id, item.version, note)
      } else await decideQuotation(item.id, item.version, approve, note)
      notify(`${item.reference} ${role === 'DCS' ? 'approved using the recorded DCS override' : approve ? 'approved' : 'returned for correction'}.`, approve ? 'success' : 'warning')
      setNote(''); load()
    } catch (error) { notifyLocalFailure(error, 'Could not save the quotation decision.', notify) } finally { setBusy(false) }
  }

  async function accept(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    const data = new FormData(event.currentTarget)
    const file = data.get('document')
    if (!(file instanceof File) || !file.name) return
    setBusy(true)
    try {
      await recordQuotationAcceptance(selected.id, selected.version, String(data.get('accepted_on')), String(data.get('client_signatory')), file)
      notify(`${selected.reference} now has a client-accepted contract copy and can be linked to a Budget Request.`, 'success')
      setSelected(null); load()
    } catch (error) { notifyLocalFailure(error, 'Could not record client acceptance.', notify) } finally { setBusy(false) }
  }

  function beginCreate() {
    setQuotationLines([{ section: 'ORIGIN_FREIGHT', description: 'International Freight (Air/Sea)', currency: 'USD', amount: '', billed_by: 'PIMASCOR' }, { section: 'DESTINATION_CLEARANCE', description: 'Customs Duties & Taxes', currency: 'PHP', amount: '', billed_by: 'BOC' }])
    setCreating(true)
  }

  function openQuotation(item: ApiQuotation) { setSelected(item); setNote(''); setPreviewZoom(window.innerWidth <= 760 ? 50 : 85) }

  return <div className="page-stack">
    <div className="explanation-banner"><span><FileCheck2 size={20} /></span><div><strong>The accepted quotation is the shipment contract.</strong><p>Sales prepares it, the GM approves it, and the signed client copy stays linked from Budget Request through collection.</p></div></div>
    <Card>
      <SectionHeader eyebrow="Contract-first control" title="Sales Quotations" description="Prepare the PHP and USD charge schedule, review it in the printable contract format, then send it to the GM." action={(role === 'Requester' || role === 'Admin') ? <Button icon={Plus} onClick={beginCreate}>Create Sales Quotation</Button> : undefined} />
      {rows === null ? <EmptyState icon={RefreshCw} title="Loading quotations" detail="Opening the quotation register." /> : <div className="table-wrap"><table><thead><tr><th>Quotation</th><th>Client / shipment</th><th>Currency totals</th><th>Prepared by</th><th>Status</th><th></th></tr></thead><tbody>{rows.map((item) => { const php = item.lines.filter((line) => line.currency === 'PHP').reduce((sum, line) => sum + Number(line.amount), 0); const usd = item.lines.filter((line) => line.currency === 'USD').reduce((sum, line) => sum + Number(line.amount), 0); return <tr key={item.id}><td data-label="Quotation"><strong>{item.reference}</strong><small>{new Date(item.created_at).toLocaleDateString('en-PH')}</small></td><td data-label="Client / shipment"><strong>{item.client.name}</strong><small>{item.shipment_reference}</small></td><td data-label="Currency totals" className="number"><strong>{moneyInCurrency(php, 'PHP')}</strong><small>{moneyInCurrency(usd, 'USD')}</small></td><td data-label="Prepared by">{item.created_by.display_name}</td><td data-label="Status"><Status>{item.status.replaceAll('_', ' ')}</Status></td><td><Button tone="ghost" onClick={() => openQuotation(item)}>Open</Button></td></tr> })}</tbody></table></div>}
    </Card>
    <Drawer className="drawer--document" open={Boolean(selected)} onClose={() => setSelected(null)} eyebrow="Sales quotation / shipment contract" title={selected?.reference ?? ''}>{selected ? <div className="record-stack"><div className="billing-preview-toolbar" role="group" aria-label="Quotation print preview zoom controls"><strong>Print preview</strong><button type="button" onClick={() => setPreviewZoom((value) => Math.max(40, value - 10))} aria-label="Zoom out">−</button><label><span className="visually-hidden">Preview zoom</span><input type="range" min="40" max="160" step="10" value={previewZoom} onChange={(event) => setPreviewZoom(Number(event.target.value))} /></label><output aria-live="polite">{previewZoom}%</output><button type="button" onClick={() => setPreviewZoom((value) => Math.min(160, value + 10))} aria-label="Zoom in">+</button><button type="button" className="billing-preview-toolbar__reset" onClick={() => setPreviewZoom(window.innerWidth <= 760 ? 50 : 85)}>Fit</button></div><div className="billing-preview-stage" tabIndex={0} aria-label="Scrollable Sales Quotation print preview"><div className="billing-preview-stage__document" style={{ zoom: `${previewZoom}%` }}><QuotationPrintDocument quotation={selected} /></div></div>{selected.signed_file_name ? <DocumentItem name={selected.signed_file_name} meta={`Client accepted by ${selected.client_signatory} • ${selected.client_accepted_at}`} available={Boolean(selected.signed_size_bytes && selected.signed_sha256)} onOpen={() => setViewingDocument({ id: `quotation:${selected.id}`, name: selected.signed_file_name!, contentType: selected.signed_content_type })} /> : null}{(role === 'Requester' || role === 'Admin') && (selected.status === 'DRAFT' || selected.status === 'REJECTED') ? <Button onClick={() => submit(selected)} disabled={busy}>Submit to GM</Button> : null}{(role === 'GM' || role === 'Admin' || role === 'DCS') && selected.status === 'PENDING_APPROVAL' ? <><label>Decision note<textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} placeholder={role === 'DCS' ? 'Required reason for exceptional override' : 'Required when returning'} /></label><div className="drawer-actions">{role !== 'DCS' ? <Button tone="danger" onClick={() => decide(selected, false)}>Return</Button> : null}<Button onClick={() => decide(selected, true)}>{role === 'DCS' ? 'Use DCS Override' : 'Approve Quotation'}</Button></div></> : null}{(role === 'Requester' || role === 'Admin') && selected.status === 'APPROVED' ? <form className="form-stack" onSubmit={accept}><SectionHeader title="Record client acceptance" description="Attach the signed or otherwise accepted quotation before creating the Budget Request." /><label>Acceptance date<input name="accepted_on" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label>Client signatory<input name="client_signatory" required /></label><label>Signed quotation<input name="document" type="file" accept=".pdf,.jpg,.jpeg,.png" required /></label><Button type="submit" disabled={busy}>Save Client-Accepted Contract</Button></form> : null}<div className="drawer-actions"><Button tone="secondary" icon={FileText} onClick={printQuotationDocument}>Print Quotation / Save PDF</Button></div></div> : null}</Drawer>
    <ConfidentialDocumentViewer item={viewingDocument} onClose={() => setViewingDocument(null)} canDownload={!isDemoBuild && ['Admin', 'GM', 'DCS', 'Mich'].includes(role)} />
    {selected ? createPortal(<div className="print-quotation-host"><QuotationPrintDocument quotation={selected} printCopy /></div>, document.body) : null}
    <Modal open={creating} onClose={() => setCreating(false)} title="Create Sales Quotation"><form className="form-stack quotation-form" onSubmit={create}><label>Client<select name="client_id" required>{clients.map((client) => <option value={client.id} key={client.id}>{client.name}</option>)}</select></label><label>Shipment reference<input name="shipment_reference" placeholder="Example: ACT-172" required /></label><div className="form-grid form-grid--three"><label>Mode of transport<input name="mode_of_transport" placeholder="SEA / AIR" /></label><label>Container<input name="container_type" placeholder="FCL / LCL" /></label><label>Incoterms<input name="incoterms" placeholder="EXW / FOB / FCA" /></label><label>Origin<input name="origin" /></label><label>Destination<input name="destination" /></label><label>Cargo details<input name="cargo_details" placeholder="Weight / dimensions" /></label></div><SectionHeader title="Charge schedule" description="Use USD for origin/international freight and PHP for destination/customs items. Mark Bureau of Customs charges separately for the print summary." />{quotationLines.map((line, index) => <div className="quotation-line-editor" key={`${line.section}-${index}`}><label>Description<input value={line.description} onChange={(event) => setQuotationLines((current) => current.map((item, row) => row === index ? { ...item, description: event.target.value } : item))} required /></label><label>Section<select value={line.section} onChange={(event) => setQuotationLines((current) => current.map((item, row) => row === index ? { ...item, section: event.target.value as QuotationLineDraft['section'], currency: event.target.value === 'ORIGIN_FREIGHT' ? 'USD' : 'PHP' } : item))}><option value="ORIGIN_FREIGHT">Origin &amp; freight</option><option value="DESTINATION_CLEARANCE">Destination &amp; clearance</option></select></label><label>Currency<select value={line.currency} onChange={(event) => setQuotationLines((current) => current.map((item, row) => row === index ? { ...item, currency: event.target.value as 'PHP' | 'USD' } : item))}><option value="USD">USD</option><option value="PHP">PHP</option></select></label><label>Amount<input type="number" min="0.01" step="0.01" value={line.amount} onChange={(event) => setQuotationLines((current) => current.map((item, row) => row === index ? { ...item, amount: event.target.value } : item))} required /></label><label>Billing<select value={line.billed_by} onChange={(event) => setQuotationLines((current) => current.map((item, row) => row === index ? { ...item, billed_by: event.target.value as 'PIMASCOR' | 'BOC' } : item))}><option value="PIMASCOR">PIMASCOR</option><option value="BOC">BOC</option></select></label><button type="button" className="icon-button" aria-label="Remove quotation charge" onClick={() => setQuotationLines((current) => current.filter((_, row) => row !== index))}><X size={16} /></button></div>)}<div className="drawer-actions"><Button type="button" tone="secondary" onClick={() => setQuotationLines((current) => [...current, { section: 'ORIGIN_FREIGHT', description: '', currency: 'USD', amount: '', billed_by: 'PIMASCOR' }])}>Add USD origin charge</Button><Button type="button" tone="secondary" onClick={() => setQuotationLines((current) => [...current, { section: 'DESTINATION_CLEARANCE', description: '', currency: 'PHP', amount: '', billed_by: 'PIMASCOR' }])}>Add PHP local charge</Button></div><label>Terms and conditions<textarea name="terms_and_conditions" rows={5} minLength={10} required defaultValue="Duties and taxes are pass-through costs subject to actual assessment. Storage, demurrage, detention, and stripping charges are excluded unless agreed in writing." /></label><label>Payment terms<input name="payment_terms" defaultValue="Duties and taxes prior to BOC lodgment; service fees upon delivery." /></label><label>Quotation validity (hours)<input name="validity_hours" type="number" min="1" max="720" defaultValue="48" required /></label><div className="modal-actions"><Button tone="secondary" onClick={() => setCreating(false)}>Cancel</Button><button className="button button--secondary" type="submit">Save as Draft</button><button className="button button--primary" type="submit" data-action="submit">Submit to GM</button></div></form></Modal>
  </div>
}

function BudgetRequestsPage({ role, notify }: { role: Role; notify: Notify }) {
  const [rows, setRows] = useState<BudgetRequest[]>(initialBudgetRequests)
  const [clients, setClients] = useState<ApiClient[]>([])
  const [quotations, setQuotations] = useState<ApiQuotation[]>([])
  const [quotationId, setQuotationId] = useState('')
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<BudgetRequest | null>(null)
  const [creating, setCreating] = useState(false)
  const [additionalFor, setAdditionalFor] = useState<BudgetRequest | null>(null)
  const [editing, setEditing] = useState<BudgetRequest | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All statuses')
  const [budgetLines, setBudgetLines] = useState<BudgetFormLine[]>([
    { description: 'Brokerage Fee', classification: 'SERVICE_CHARGE', buying: '', selling: '' },
  ])
  const [additionalLines, setAdditionalLines] = useState<BudgetFormLine[]>([
    { description: 'Storage', classification: 'PASS_THROUGH', buying: '', selling: '' },
  ])
  const [editLines, setEditLines] = useState<BudgetFormLine[]>([])

  useEffect(() => {
    let active = true
    Promise.all([getBudgetRequests(), getClients(), getQuotations()])
      .then(([budgetRows, clientRows, quotationRows]) => {
        if (!active) return
        setRows(budgetRows.map(apiBudgetToRow))
        setClients(clientRows)
        const accepted = quotationRows.filter((item) => item.status === 'CLIENT_ACCEPTED')
        setQuotations(accepted)
        setQuotationId((current) => current || accepted[0]?.id || '')
      })
      .catch((error) => notifyLocalFailure(error, 'Could not load Budget Requests.', notify))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  const visibleRows = rows.filter((row) => {
    const matchesText = `${row.reference} ${row.client} ${row.requester} ${row.shipment}`.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = status === 'All statuses' || row.approval === status
    return matchesText && matchesStatus
  })

  async function addDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const quotation = quotations.find((item) => item.id === quotationId)
    if (!quotation) {
      notify('Choose a client-accepted Sales Quotation first.', 'danger', 'Open Sales Quotations, complete GM approval and client acceptance, then return to create the Budget Request.')
      return
    }
    const items = budgetLines.flatMap((line) => [
      ...(Number(line.buying) > 0 ? [{ kind: 'BUYING' as const, description: line.description, classification: line.classification, amount: Number(line.buying).toFixed(2) }] : []),
      ...(Number(line.selling) > 0 ? [{ kind: 'SELLING' as const, description: line.description, classification: line.classification, amount: Number(line.selling).toFixed(2) }] : []),
    ])
    if (!items.some((item) => item.kind === 'BUYING') || !items.some((item) => item.kind === 'SELLING')) {
      notify(
        'Enter at least one Buying amount and one Selling amount.',
        'danger',
        'Enter an amount greater than zero in at least one Buying field and one Selling field, then select Save as Draft or Submit for Approval again.',
      )
      return
    }
    try {
      let created = await createBudgetRequest({
        client_id: quotation.client.id,
        quotation_id: quotation.id,
        shipment_reference: quotation.shipment_reference,
        request_date: new Date().toISOString().slice(0, 10),
        currency: 'PHP',
        notes: String(data.get('notes') || '') || null,
        items,
      })
      const shouldSubmit = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-action') === 'submit'
      if (shouldSubmit) created = await submitBudgetRequest(created.id, created.version)
      const newRow = apiBudgetToRow(created)
      setRows((current) => [newRow, ...current])
      setCreating(false)
      setBudgetLines([{ description: 'Brokerage Fee', classification: 'SERVICE_CHARGE', buying: '', selling: '' }])
      notify(`${newRow.reference} ${shouldSubmit ? 'submitted for Approval' : 'saved as a draft'}.`, 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not save the Budget Request.', notify)
    }
  }

  async function submitRow(row: BudgetRequest) {
    if (!row.version) return
    try {
      const updated = apiBudgetToRow(await submitBudgetRequest(row.id, row.version))
      setRows((current) => current.map((item) => item.id === row.id ? updated : item))
      setSelected(updated)
      notify(`${row.reference} submitted to Mich for initial review.`, 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not submit this request.', notify)
    }
  }

  function beginEdit(row: BudgetRequest) {
    if (!row.source) return
    setEditLines(budgetLinesFromApi(row.source))
    setEditing(row)
    setSelected(null)
  }

  async function saveEditedDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editing?.source || !editing.version) return
    const data = new FormData(event.currentTarget)
    const items = editLines.flatMap((line) => [
      ...(Number(line.buying) > 0 ? [{ kind: 'BUYING' as const, description: line.description, classification: line.classification, amount: Number(line.buying).toFixed(2) }] : []),
      ...(Number(line.selling) > 0 ? [{ kind: 'SELLING' as const, description: line.description, classification: line.classification, amount: Number(line.selling).toFixed(2) }] : []),
    ])
    const isAdditional = editing.kind === 'ADDITIONAL'
    if (!items.some((item) => item.kind === 'BUYING') || (!isAdditional && !items.some((item) => item.kind === 'SELLING'))) {
      notify(
        isAdditional ? 'Enter at least one Additional Buying amount.' : 'Enter at least one Buying amount and one Selling amount.',
        'danger',
        isAdditional
          ? 'Enter an amount greater than zero in an Additional Buying field, then save again.'
          : 'Enter an amount greater than zero in at least one Buying field and one Selling field, then save again.',
      )
      return
    }
    const relatedAmount = String(data.get('related_expense_amount') || '')
    try {
      let updated = await updateBudgetRequest(editing.id, {
        expected_version: editing.version,
        client_id: isAdditional ? null : String(data.get('client')),
        shipment_reference: isAdditional ? null : String(data.get('shipment')),
        request_date: editing.source.request_date,
        currency: editing.source.currency,
        notes: String(data.get('notes') || '') || null,
        reason: isAdditional ? String(data.get('reason')) : null,
        related_expense_description: isAdditional ? String(data.get('related_expense_description') || '') || null : null,
        related_expense_amount: isAdditional ? relatedAmount || null : null,
        items,
      })
      const shouldSubmit = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-action') === 'submit'
      if (shouldSubmit) updated = await submitBudgetRequest(updated.id, updated.version)
      const updatedRow = apiBudgetToRow(updated)
      setRows((current) => current.map((item) => item.id === updatedRow.id ? updatedRow : item))
      setEditing(null)
      notify(`${updatedRow.reference} ${shouldSubmit ? 'updated and submitted for Approval' : 'draft updated'}.`, 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not update the Budget Request.', notify)
    }
  }

  async function addAdditionalDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!additionalFor) return
    const data = new FormData(event.currentTarget)
    const items = additionalLines.flatMap((line) => [
      ...(Number(line.buying) > 0 ? [{ kind: 'BUYING' as const, description: line.description, classification: line.classification, amount: Number(line.buying).toFixed(2) }] : []),
      ...(Number(line.selling) > 0 ? [{ kind: 'SELLING' as const, description: line.description, classification: line.classification, amount: Number(line.selling).toFixed(2) }] : []),
    ])
    if (!items.some((item) => item.kind === 'BUYING')) {
      notify(
        'Enter at least one Additional Buying amount.',
        'danger',
        'Enter an amount greater than zero in at least one Additional Buying field, then save or submit the Additional Budget again.',
      )
      return
    }
    const relatedAmount = String(data.get('related_expense_amount') || '')
    try {
      let created = await createAdditionalBudget(additionalFor.id, {
        request_date: new Date().toISOString().slice(0, 10),
        reason: String(data.get('reason')),
        related_expense_description: String(data.get('related_expense_description') || '') || null,
        related_expense_amount: relatedAmount || null,
        items,
      })
      const shouldSubmit = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-action') === 'submit'
      if (shouldSubmit) created = await submitBudgetRequest(created.id, created.version)
      const newRow = apiBudgetToRow(created)
      setRows((current) => [newRow, ...current])
      setAdditionalFor(null)
      setAdditionalLines([{ description: 'Storage', classification: 'PASS_THROUGH', buying: '', selling: '' }])
      notify(`${newRow.reference} linked to ${additionalFor.reference} and ${shouldSubmit ? 'submitted for Approval' : 'saved as a draft'}.`, 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not create the Additional Budget.', notify)
    }
  }

  return (
    <div className="page-stack">
      <Card>
        <SectionHeader
          eyebrow="Requester workspace"
          title="Budget Requests"
          description="Buying is expected company cost. Selling is the amount intended for the client."
          action={(role === 'Requester' || role === 'Admin') ? <Button icon={Plus} onClick={() => setCreating(true)}>Create Budget Request</Button> : undefined}
        />
        <div className="filters">
          <label className="search-field"><Search size={17} /><span className="sr-only">Search Budget Requests</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search BR, client, shipment, or Requester" /></label>
          <label className="select-field"><CalendarDays size={16} /><select aria-label="Budget Request month"><option>July 2026</option><option>June 2026</option><option>All months</option></select></label>
          <label className="select-field"><select aria-label="Approval status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Draft</option><option>Pending Approval</option><option>Approved</option><option>Rejected</option></select></label>
          <Button tone="ghost" icon={Download} onClick={() => downloadCsv('pimascor-budget-requests.csv', [['Reference', 'Client', 'Shipment', 'Requester', 'Buying', 'Selling', 'Approval', 'Release'], ...visibleRows.map((row) => [row.reference, row.client, row.shipment, row.requester, row.buying, row.selling, row.approval, row.release])])}>Export CSV</Button>
        </div>
        {loading ? <div className="empty-state"><RefreshCw size={22} /><strong>Loading Budget Requests…</strong></div> : <div className="table-wrap">
          <table>
            <thead><tr><th>Reference</th><th>Client & shipment</th><th>Buying</th><th>Selling</th><th>Projected profit</th><th>Approval</th><th>Release</th><th>Updated</th><th><span className="sr-only">Open</span></th></tr></thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr key={row.id}>
                  <td data-label="Reference"><button className="table-link" onClick={() => setSelected(row)}>{row.reference}</button><small>{row.kind === 'ADDITIONAL' ? 'Additional Budget' : 'Original BR'} • {row.date}</small></td>
                  <td data-label="Client & shipment"><strong>{row.client}</strong><small>{row.shipment}</small></td>
                  <td data-label="Buying" className="number">{money(row.buying)}</td>
                  <td data-label="Selling" className="number">{money(row.selling)}</td>
                  <td data-label="Projected profit" className="number number--positive">{money(row.selling - row.buying)}</td>
                  <td data-label="Approval"><Status>{row.approval}</Status></td>
                  <td data-label="Release"><Status>{row.release}</Status></td>
                  <td data-label="Updated"><span>{row.updated}</span><small>{row.requester}</small></td>
                  <td><button className="icon-button" aria-label={`Open ${row.reference}`} onClick={() => setSelected(row)}><ChevronRight size={18} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>}
        {!visibleRows.length ? <EmptyState icon={Search} title="No Budget Requests match" detail="Change the filters or create a new request." /> : null}
      </Card>

      <Drawer open={Boolean(selected)} onClose={() => setSelected(null)} eyebrow="Shipment case file" title={selected?.reference ?? ''}>
        {selected ? <BudgetRecord row={selected} notify={notify} onSubmit={() => submitRow(selected)} onEdit={(role === 'Requester' || role === 'Admin') && (selected.approval === 'Draft' || selected.approval === 'Rejected') ? () => beginEdit(selected) : undefined} onAdditional={(role === 'Requester' || role === 'Admin') && selected.kind === 'MAIN' && selected.approval === 'Approved' ? () => { setAdditionalFor(selected); setSelected(null) } : undefined} /> : null}
      </Drawer>

      <Modal open={creating} onClose={() => setCreating(false)} title="Create Budget Request">
        <form className="form-stack" onSubmit={addDraft}>
          <div className="callout callout--info"><AlertCircle size={18} /><span>This draft begins from an approved, client-accepted quotation. Submission goes to Mich for initial review before the GM decides it.</span></div>
          <label>Client-accepted Sales Quotation<select name="quotation" value={quotationId} onChange={(event) => setQuotationId(event.target.value)} required><option value="">Choose an accepted quotation</option>{quotations.map((item) => <option value={item.id} key={item.id}>{item.reference} • {item.client.name} • {item.shipment_reference}</option>)}</select></label>
          {quotations.length === 0 ? <div className="callout callout--warning"><FileCheck2 size={18} /><span>No client-accepted quotation is available. Complete the Sales Quotation workflow first.</span></div> : null}
          <BudgetLineEditor lines={budgetLines} setLines={setBudgetLines} />
          <label>Notes<textarea name="notes" rows={3} placeholder="Operational context or special instructions" /></label>
          <div className="modal-actions"><Button tone="ghost" onClick={() => setCreating(false)}>Cancel</Button><button className="button button--secondary" type="submit"><Check size={17} />Save as Draft</button><button className="button button--primary" type="submit" data-action="submit"><ClipboardCheck size={17} />Submit for Approval</button></div>
        </form>
      </Modal>

      <Modal open={Boolean(additionalFor)} onClose={() => setAdditionalFor(null)} title="Request Additional Budget">
        {additionalFor ? <form className="form-stack" onSubmit={addAdditionalDraft}>
          <div className="callout callout--info"><AlertCircle size={18} /><span>The original {additionalFor.reference} remains unchanged. This creates a separately approved increase linked to the same shipment.</span></div>
          <div className="summary-grid summary-grid--two"><div><span>Original BR</span><strong>{additionalFor.reference}</strong><small>{additionalFor.client}</small></div><div><span>Shipment</span><strong>{additionalFor.shipment}</strong><small>{money(additionalFor.buying)} original buying</small></div></div>
          <label>Why is the original budget insufficient?<textarea name="reason" rows={3} required placeholder="Explain the unexpected cost or changed shipment need." /></label>
          <div className="form-grid"><label>Related liquidation expense<input name="related_expense_description" placeholder="Example: Additional port storage" required /></label><label>Related actual expense amount<input name="related_expense_amount" type="number" min="0.01" step="0.01" placeholder="Amount already incurred" required /></label></div>
          <BudgetLineEditor lines={additionalLines} setLines={setAdditionalLines} />
          <div className="summary-grid summary-grid--two"><div><span>Additional Buying</span><strong>{money(additionalLines.reduce((sum, line) => sum + Number(line.buying || 0), 0))}</strong><small>Additional company funding requested</small></div><div><span>Additional Selling</span><strong>{money(additionalLines.reduce((sum, line) => sum + Number(line.selling || 0), 0))}</strong><small>Additional amount intended for the client</small></div></div>
          <div className="modal-actions"><Button tone="ghost" onClick={() => setAdditionalFor(null)}>Cancel</Button><button className="button button--secondary" type="submit">Save as Draft</button><button className="button button--primary" type="submit" data-action="submit">Submit for Approval</button></div>
        </form> : null}
      </Modal>

      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={editing?.kind === 'ADDITIONAL' ? 'Edit Additional Budget Draft' : 'Edit Budget Request Draft'}>
        {editing?.source ? <form className="form-stack" onSubmit={saveEditedDraft}>
          <div className="callout callout--info"><AlertCircle size={18} /><span>Only this draft changes. Submitted and approved records remain locked for accountability.</span></div>
          {editing.kind === 'MAIN' ? <>
            <label>Client<select name="client" defaultValue={editing.source.client.id} required>{clients.map((client) => <option value={client.id} key={client.id}>{client.name}</option>)}</select></label>
            <label>Shipment reference<input name="shipment" defaultValue={editing.source.shipment_reference} required /></label>
          </> : <>
            <label>Why is the original budget insufficient?<textarea name="reason" rows={3} defaultValue={editing.source.additional_reason ?? ''} required /></label>
            <div className="form-grid"><label>Related liquidation expense<input name="related_expense_description" defaultValue={editing.source.related_expense_description ?? ''} required /></label><label>Related actual expense amount<input name="related_expense_amount" type="number" min="0.01" step="0.01" defaultValue={editing.source.related_expense_amount ?? ''} required /></label></div>
          </>}
          <BudgetLineEditor lines={editLines} setLines={setEditLines} />
          <label>Notes<textarea name="notes" rows={3} defaultValue={editing.source.notes ?? ''} placeholder="Operational context or special instructions" /></label>
          <div className="modal-actions"><Button tone="ghost" onClick={() => setEditing(null)}>Cancel</Button><button className="button button--secondary" type="submit"><Check size={17} />Save Changes</button><button className="button button--primary" type="submit" data-action="submit"><ClipboardCheck size={17} />Save and Submit</button></div>
        </form> : null}
      </Modal>
    </div>
  )
}

function BudgetRecord({ row, onSubmit, onEdit, onAdditional }: { row: BudgetRequest; notify: Notify; onSubmit: () => void; onEdit?: () => void; onAdditional?: () => void }) {
  const [tab, setTab] = useState('Summary')
  const tabs = ['Summary', 'Approval', 'Money movement', 'Documents', 'Activity']
  const projectedMargin = row.selling > 0 ? ((row.selling - row.buying) / row.selling) * 100 : null
  const createdAt = row.source ? new Date(row.source.created_at).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' }) : row.date
  return (
    <div className="record-stack">
      <div className="record-hero">
        <div><Status>{row.kind === 'ADDITIONAL' ? 'Additional Budget' : row.approval}</Status><h3>{row.client}</h3><p>{row.shipment}</p></div>
        <OwnerBadge>Requester • {row.requester}</OwnerBadge>
      </div>
      <div className="record-tabs" role="tablist" aria-label="Budget record sections">{tabs.map((item) => <button type="button" role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)} key={item}>{item}</button>)}</div>
      {tab === 'Summary' ? (
        <>
          <div className="summary-grid">
            <div><span>Buying</span><strong>{money(row.buying)}</strong><small>Expected company cost</small></div>
            <div><span>Selling</span><strong>{money(row.selling)}</strong><small>Amount intended for client</small></div>
            <div className="summary-grid__profit"><span>Projected profit</span><strong>{money(row.selling - row.buying)}</strong><small>{projectedMargin === null ? 'Margin unavailable until Selling is entered' : `${projectedMargin.toFixed(1)}% projected margin`}</small></div>
          </div>
          <div className="split-status">
            <div><span>GM Approval</span><Status>{row.approval}</Status></div>
            <ArrowRight size={18} />
            <div><span>DCS Release</span><Status>{row.release}</Status></div>
          </div>
          <div className="parallel-branches">
            <div><span className="branch-icon"><ReceiptText size={18} /></span><strong>Liquidation branch</strong><p>Actual spending and internal accountability</p><Status>{row.liquidation}</Status></div>
            <div><span className="branch-icon"><FileText size={18} /></span><strong>Billing branch</strong><p>Client billing, collections, and balance</p><Status>{row.billing}</Status></div>
          </div>
        </>
      ) : null}
      {tab === 'Approval' ? <Timeline items={[
        [row.updated, `Current approval status: ${row.approval}`, row.approval === 'Draft' ? 'Not yet submitted to the GM' : 'The attributable decision and comments are retained by the server'],
        [createdAt, 'Budget Request created', row.requester],
      ]} /> : null}
      {tab === 'Money movement' ? <div className="record-stack"><div className="split-status"><div><span>Authorized Buying</span><strong>{money(row.buying)}</strong></div><ArrowRight size={18} /><div><span>DCS payment status</span><Status>{row.release}</Status></div></div><div className="callout callout--info"><Landmark size={18} /><span>Open DCS for Payment to review the attributable funding source, payment date, recipient, and transaction reference. No payment detail is inferred here.</span></div></div> : null}
      {tab === 'Documents' ? <EmptyState icon={FileText} title="No document is attached to this record view" detail="Verified files appear in Clients & Documents when an authorized user uploads supporting evidence." /> : null}
      {tab === 'Activity' ? <Timeline items={[[row.updated, 'Record last changed', row.requester], [createdAt, 'Record created', row.requester]]} /> : null}
      <div className="drawer-actions"><Button tone="secondary" icon={Download} onClick={() => downloadCsv(`${row.reference}.csv`, [['Reference', 'Client', 'Shipment', 'Requester', 'Buying', 'Selling', 'Approval', 'Release'], [row.reference, row.client, row.shipment, row.requester, row.buying, row.selling, row.approval, row.release]])}>Export record</Button>{onEdit ? <Button tone="secondary" icon={Pencil} onClick={onEdit}>Edit Draft</Button> : null}{onAdditional ? <Button tone="secondary" icon={Plus} onClick={onAdditional}>Request Additional Budget</Button> : null}{row.approval === 'Draft' || row.approval === 'Rejected' ? <Button onClick={onSubmit}>Submit for Approval</Button> : null}</div>
    </div>
  )
}

type ApprovalWorkItem = {
  source: 'budget' | 'expense' | 'billing' | 'credit'
  id: string
  reference: string
  type: string
  party: string
  purpose: string
  amount: number
  selling: number
  requester: string
  version: number
  stage?: ApiBudgetRequest['status']
  details: { label: string; classification: string; amount: number }[]
}

function ApprovalPage({ role, notify }: { role: Role; notify: Notify }) {
  const [items, setItems] = useState<ApprovalWorkItem[] | null>(null)
  const [selected, setSelected] = useState<ApprovalWorkItem | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const canDecide = role === 'GM' || role === 'Admin' || role === 'Mich' || role === 'DCS'

  const load = () => Promise.all([
    role === 'Mich' ? Promise.resolve([]) : getBudgetApprovalQueue(),
    role === 'Mich' || role === 'Admin' ? getBudgetReviewQueue() : Promise.resolve([]),
    role === 'GM' || role === 'Admin' ? getExpenseApprovalQueue() : Promise.resolve([]),
    role === 'GM' || role === 'Admin' ? getBilling() : Promise.resolve([]),
    role === 'GM' || role === 'Admin' ? getCreditMemos() : Promise.resolve([]),
  ]).then(([approvalBudgets, reviewBudgets, expenses, billing, creditMemos]) => {
    const budgets = [...reviewBudgets, ...approvalBudgets]
    const combined: ApprovalWorkItem[] = [
      ...budgets.map((item) => ({ source: 'budget' as const, id: item.id, reference: item.reference, type: item.budget_kind === 'ADDITIONAL' ? 'Additional Budget' : 'Budget Request', party: item.client.name, purpose: item.additional_reason || item.shipment_reference, amount: Number(item.buying_total), selling: Number(item.selling_total), requester: item.requester.display_name, version: item.version, stage: item.status, details: item.items.map((line) => ({ label: `${line.kind === 'BUYING' ? 'Buying' : 'Selling'} • ${line.description}`, classification: line.classification === 'SERVICE_CHARGE' ? 'Service charge' : 'Pass-through cost', amount: Number(line.amount) })) })),
      ...expenses.map((item) => ({ source: 'expense' as const, id: item.id, reference: item.reference, type: item.expense_type === 'LOAN_PAYMENT' ? 'Loan Payment' : item.expense_type === 'MARKETING' ? 'Marketing' : item.expense_type === 'OTHER' ? 'Other' : 'OPEX', party: item.party, purpose: item.purpose, amount: Number(item.amount), selling: 0, requester: item.requester.display_name, version: item.version, details: item.expense_type === 'LOAN_PAYMENT' ? [{ label: 'Principal', classification: item.loan_reference || 'Loan Payment', amount: Number(item.principal_amount) }, { label: 'Interest', classification: 'Loan Payment', amount: Number(item.interest_amount) }, { label: 'Penalties / fees', classification: 'Loan Payment', amount: Number(item.penalties_fees_amount) }].filter((line) => line.amount > 0) : [{ label: item.purpose, classification: item.expense_type.replace('_', ' '), amount: Number(item.amount) }] })),
      ...billing.filter((item) => item.status === 'PENDING_APPROVAL').map((item) => ({ source: 'billing' as const, id: item.id, reference: item.reference, type: item.replaces_billing_id ? 'Replacement Billing' : 'Billing', party: item.budget_request.client.name, purpose: `${item.budget_request.reference} • ${item.budget_request.shipment_reference}`, amount: Number(item.net_due), selling: 0, requester: item.prepared_by.display_name, version: item.version, details: item.lines.map((line) => ({ label: line.description, classification: line.classification === 'SERVICE_CHARGE' ? 'Service charge' : 'Pass-through cost', amount: Number(line.amount) })) })),
      ...creditMemos.filter((item) => item.status === 'PENDING_APPROVAL').map((item) => {
        const parent = billing.find((row) => row.id === item.billing_id)
        return { source: 'credit' as const, id: item.id, reference: item.reference, type: 'Credit Memo', party: parent?.budget_request.client.name ?? 'Client Billing', purpose: item.reason, amount: Number(item.amount), selling: 0, requester: item.created_by.display_name, version: item.version, details: [{ label: item.reason, classification: `Adjusts ${parent?.reference ?? 'Billing'}`, amount: Number(item.amount) }] }
      }),
    ]
    setItems(combined)
    setSelected((current) => current ? combined.find((item) => item.id === current.id) ?? combined[0] ?? null : combined[0] ?? null)
  }).catch((reason) => {
    setItems([])
    setError(reason instanceof Error ? reason.message : 'Could not load the GM Approval Center.')
  })

  useEffect(() => { void load() }, [])

  async function decide(outcome: 'approve' | 'reject') {
    if (!selected || !canDecide) return
    if (outcome === 'reject' && !note.trim()) {
      setError('A reason is required when returning a request.')
      return
    }
    setBusy(true)
    setError('')
    try {
      if (selected.source === 'budget' && selected.stage === 'PENDING_REVIEW') {
        if (role === 'DCS') {
          if (outcome === 'reject') throw new Error('DCS may view this stage or use a reasoned approval override; only Mich returns the initial entry.')
          if (note.trim().length < 10) throw new Error('Explain why Mich and the GM are unavailable before using the DCS override.')
          await overrideBudgetAsDcs(selected.id, selected.version, note)
        } else if (outcome === 'approve') await reviewBudgetRequest(selected.id, selected.version, note)
        else await returnBudgetFromReview(selected.id, selected.version, note)
      }
      else if (selected.source === 'budget' && role === 'DCS') {
        if (outcome === 'reject') throw new Error('DCS may view this stage or use a reasoned approval override; the GM normally returns it.')
        if (note.trim().length < 10) throw new Error('Explain why the GM is unavailable before using the DCS override.')
        await overrideBudgetAsDcs(selected.id, selected.version, note)
      }
      else if (selected.source === 'budget') await decideBudgetRequest(selected.id, selected.version, outcome, note)
      else if (selected.source === 'expense') await decideExpenseRequest(selected.id, selected.version, outcome, note)
      else if (selected.source === 'billing') await decideBilling(selected.id, selected.version, outcome === 'approve', note)
      else await decideCreditMemo(selected.id, selected.version, outcome === 'approve', note)
      const remaining = (items ?? []).filter((item) => item.id !== selected.id)
      setItems(remaining)
      setSelected(remaining[0] ?? null)
      setNote('')
      notify(`${selected.reference} ${outcome === 'approve' ? (selected.source === 'billing' ? 'approved for finalization' : selected.source === 'credit' ? 'approved and applied to the collectible balance' : 'approved and sent to DCS Payment Center') : `returned to ${selected.source === 'budget' ? 'the Requester' : 'Mich'}`}.`, outcome === 'approve' ? 'success' : 'warning')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The approval decision could not be saved.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="queue-layout">
      <Card className="queue-card">
        <SectionHeader eyebrow={role === 'Admin' ? 'Administrator superuser workspace' : role === 'Mich' ? 'Mich validation workspace' : role === 'DCS' ? 'DCS visibility and emergency authority' : 'GM workspace'} title={role === 'Mich' ? 'Budget Requests to review' : role === 'DCS' ? 'Approval visibility' : 'Decision queue'} description={`${items?.length ?? 0} requests are awaiting a controlled decision`} />
        {role === 'Admin' ? <div className="callout callout--warning"><ShieldCheck size={18} /><span>You are acting with Administrator superuser authority. Your approval or return is recorded under your Admin account and remains subject to the same record-state, version, and audit controls.</span></div> : null}
        {items === null ? <EmptyState icon={RefreshCw} title="Loading submitted requests" detail="Combining shipment and accounting requests." /> : <div className="queue-list">
          {items.map((item) => <button className={`queue-item ${selected?.id === item.id ? 'active' : ''}`} onClick={() => { setSelected(item); setNote(''); setError('') }} key={`${item.source}-${item.id}`}>
            <div><Status>{item.type}</Status><span className="queue-item__age">Pending</span></div>
            <strong>{item.reference}</strong><p>{item.party}</p><small>{item.purpose}</small>
            <div className="queue-item__footer"><b>{money(item.amount)}</b><Status>{item.stage === 'PENDING_REVIEW' ? 'Pending Mich Review' : 'Pending Approval'}</Status></div>
          </button>)}
        </div>}
      </Card>
      <Card className="decision-card">
        {selected ? <>
          <SectionHeader eyebrow={`${selected.type} • requested by ${selected.requester}`} title={selected.reference} description={selected.party} />
          {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
          <div className="decision-purpose"><span>Purpose</span><strong>{selected.purpose}</strong></div>
          <div className="summary-grid summary-grid--two"><div><span>{selected.source === 'budget' ? 'Buying budget' : selected.source === 'credit' ? 'Credit amount' : selected.source === 'billing' ? 'Net amount due' : 'Amount to pay'}</span><strong>{money(selected.amount)}</strong></div><div><span>{selected.source === 'budget' ? 'Selling amount' : 'Next step'}</span><strong>{selected.source === 'budget' ? money(selected.selling) : selected.source === 'billing' ? 'Mich finalizes approved Billing' : selected.source === 'credit' ? 'Reduce collectible balance' : 'DCS Payment Center'}</strong></div></div>
          {selected.source === 'budget' && selected.selling > 0 ? <div className="profit-callout"><TrendingUp size={19} /><span><small>Projected profit impact</small><strong>{money(selected.selling - selected.amount)}</strong></span></div> : null}
          <div className="table-wrap"><table><thead><tr><th>Line item</th><th>Classification</th><th>Amount</th></tr></thead><tbody>{selected.details.map((line, index) => <tr key={`${line.label}-${index}`}><td data-label="Line item"><strong>{line.label}</strong></td><td data-label="Classification">{line.classification}</td><td data-label="Amount" className="number">{money(line.amount)}</td></tr>)}</tbody></table></div>
          <><label className="decision-notes">Decision note<textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder={role === 'DCS' ? 'Required: explain why the normal approver is unavailable' : 'Required when returning; optional when approving'} rows={4} /></label>
            <div className="decision-actions">{role !== 'DCS' ? <Button tone="danger" icon={XCircle} disabled={busy} onClick={() => decide('reject')}>Return Request</Button> : null}<Button icon={CheckCircle2} disabled={busy} onClick={() => decide('approve')}>{role === 'DCS' ? 'Use DCS Override' : selected.source === 'budget' && selected.stage === 'PENDING_REVIEW' ? 'Reviewed — Send to GM' : selected.source === 'billing' ? 'Approve Billing' : selected.source === 'credit' ? 'Approve Credit Memo' : 'Approve for Payment'}</Button></div>
            <p className="helper-text"><ShieldCheck size={15} />The API verifies this approval decision, actor, and record version before allowing the next controlled step.</p></>
        </> : <EmptyState icon={CheckCircle2} title="Queue cleared" detail="No submitted requests need an approval decision." />}
      </Card>
    </div>
  )
}

type DcsAction = 'pay' | 'HOLD' | 'RETURN' | 'RESUME' | 'NOTE'

const paymentStatusLabel = {
  NOT_READY: 'Not ready',
  PENDING: 'Pending payment',
  ON_HOLD: 'On hold',
  PARTIALLY_PAID: 'Partially paid',
  PAID: 'Paid',
  RETURNED: 'Returned',
} as const

const paymentTypeLabel = {
  BUDGET_REQUEST: 'Budget Request',
  ADDITIONAL_BUDGET: 'Additional Budget',
  OPEX: 'OPEX',
  MARKETING: 'Marketing',
  LOAN_PAYMENT: 'Loan Payment',
  OTHER: 'Other',
} as const

function ReleasesPage({ role, notify }: { role: Role; notify: Notify }) {
  const [items, setItems] = useState<ApiPaymentQueueItem[] | null>(null)
  const [selected, setSelected] = useState<ApiPaymentQueueItem | null>(null)
  const [filter, setFilter] = useState<'ALL' | 'PENDING' | 'ON_HOLD' | 'PAID' | 'RETURNED'>('PENDING')
  const [action, setAction] = useState<DcsAction | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fundingSources, setFundingSources] = useState<ApiFundingSource[]>([])
  const canPay = role === 'DCS' || role === 'GM' || role === 'Admin'

  const load = () => getPayments().then(setItems).catch((reason) => {
    setItems([])
    setError(reason instanceof Error ? reason.message : 'Could not load the DCS Payment Center.')
  })

  useEffect(() => { void load(); if (canPay) getFundingSources().then(setFundingSources).catch((reason) => { setFundingSources([]); setError(reason instanceof Error ? reason.message : 'Configured funding sources could not be loaded.') }) }, [canPay])

  const visibleItems = (items ?? []).filter((item) => filter === 'ALL'
    || (filter === 'PENDING' && (item.payment_status === 'PENDING' || item.payment_status === 'PARTIALLY_PAID'))
    || item.payment_status === filter)
  const pendingTotal = (items ?? []).filter((item) => ['PENDING', 'PARTIALLY_PAID'].includes(item.payment_status)).reduce((sum, item) => sum + Number(item.outstanding_amount), 0)
  const paidTotal = (items ?? []).filter((item) => item.payment_status === 'PAID').reduce((sum, item) => sum + Number(item.paid_amount), 0)

  function sourcePath(item: ApiPaymentQueueItem): 'budget' | 'expense' {
    return item.source_type === 'BUDGET_REQUEST' || item.source_type === 'ADDITIONAL_BUDGET' ? 'budget' : 'expense'
  }

  async function completeDcsAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected || !action) return
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      let updated = action === 'pay'
        ? await recordPayment(sourcePath(selected), selected.record_id, {
          amount: String(form.get('amount')),
          paid_on: String(form.get('paid_on')),
          mode: String(form.get('mode')),
          source: String(form.get('source')),
          recipient: String(form.get('recipient')),
          transaction_reference: String(form.get('transaction_reference')),
          notes: String(form.get('note') || '') || null,
          expected_version: selected.version,
        })
        : await updatePayment(sourcePath(selected), selected.record_id, {
          action,
          note: String(form.get('note')),
          expected_version: selected.version,
        })
      if (action === 'pay') {
        const proof = form.get('payment_proof')
        if (!(proof instanceof File) || !proof.name) throw new Error('Attach the bank, check, or transfer proof before completing payment.')
        updated = await uploadPaymentProof(sourcePath(selected), selected.record_id, updated.version, proof)
      }
      setItems((current) => (current ?? []).map((item) => item.record_id === updated.record_id ? updated : item))
      setSelected(updated)
      setAction(null)
      notify(action === 'pay' ? `${updated.reference} marked as paid.` : `${updated.reference} payment record updated.`, 'success')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The payment action could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-stack">
      <div className="explanation-banner"><span><Banknote size={20} /></span><div><strong>One payment inbox for the CEO.</strong><p>Every approved Budget Request, Additional Budget, OPEX, Marketing, and Loan Payment appears here. Approval remains separate from actual payment.</p></div></div>
      <div className="kpi-grid kpi-grid--four">
        <Card className="kpi kpi--warning"><div className="kpi__top"><span>Pending amount</span><Clock3 size={17} /></div><strong>{money(pendingTotal)}</strong><p>Awaiting DCS payment</p></Card>
        <Card className="kpi"><div className="kpi__top"><span>Pending items</span><ReceiptText size={17} /></div><strong>{(items ?? []).filter((item) => ['PENDING', 'PARTIALLY_PAID'].includes(item.payment_status)).length}</strong><p>Across all request types</p></Card>
        <Card className="kpi kpi--danger"><div className="kpi__top"><span>Held / returned</span><AlertCircle size={17} /></div><strong>{(items ?? []).filter((item) => ['ON_HOLD', 'RETURNED'].includes(item.payment_status)).length}</strong><p>Require follow-up</p></Card>
        <Card className="kpi kpi--success"><div className="kpi__top"><span>Recorded paid</span><CheckCircle2 size={17} /></div><strong>{money(paidTotal)}</strong><p>Visible demo records</p></Card>
      </div>
      <Card>
        <SectionHeader eyebrow="DCS / CEO workspace" title="Payment Center" description="Review the approved obligation, then pay, hold, return, or annotate it." />
        {canPay && fundingSources.length === 0 ? <div className="callout callout--danger"><AlertCircle size={18} /><span>No active funding source is configured. An Administrator must add Bank of PIMASCOR, Advances to DCS, or another approved source before DCS can record payment.</span></div> : null}
        <div className="tabbed-heading payment-tabs" role="tablist" aria-label="Payment status">{[
          ['PENDING', 'Pending'], ['ON_HOLD', 'On hold'], ['PAID', 'Paid'], ['RETURNED', 'Returned'], ['ALL', 'All'],
        ].map(([value, label]) => <button type="button" role="tab" aria-selected={filter === value} key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value as typeof filter)}>{label}</button>)}</div>
        {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
        {items === null ? <EmptyState icon={RefreshCw} title="Loading approved payments" detail="Combining all authorized request types." /> : visibleItems.length === 0 ? <EmptyState icon={CheckCircle2} title="This queue is clear" detail="Choose another status to review payment history." /> : <div className="table-wrap"><table><thead><tr><th>Type / reference</th><th>Payee and purpose</th><th>Requested by</th><th>Approved</th><th>Amount due</th><th>Funding source</th><th>Status</th><th></th></tr></thead><tbody>
          {visibleItems.map((item) => <tr key={`${item.source_type}-${item.record_id}`}>
            <td data-label="Type / reference"><Status>{paymentTypeLabel[item.source_type]}</Status><strong>{item.reference}</strong>{item.parent_reference ? <small>Parent {item.parent_reference}</small> : null}</td>
            <td data-label="Payee and purpose"><strong>{item.party}</strong><small>{item.purpose}</small></td>
            <td data-label="Requested by">{item.requester}</td>
            <td data-label="Approved"><span>{item.approved_by ?? 'GM'}</span><small>{item.approved_at ? new Date(item.approved_at).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' }) : 'Approval recorded'}</small></td>
            <td data-label="Amount due" className="number number--emphasis">{money(Number(item.outstanding_amount))}</td>
            <td data-label="Funding source"><strong>{item.funding_source ?? 'Selected by DCS when paid'}</strong><small>{item.paid_on ? `${item.payment_method} • ${new Date(`${item.paid_on}T00:00:00`).toLocaleDateString('en-PH')}` : `${money(Number(item.paid_amount))} paid`}</small></td>
            <td data-label="Status"><Status>{paymentStatusLabel[item.payment_status]}</Status></td>
            <td><Button tone="secondary" onClick={() => { setSelected(item); setAction(null); setError('') }}>{item.payment_status === 'PAID' ? 'View' : 'Review'}</Button></td>
          </tr>)}
        </tbody></table></div>}
      </Card>
      <Drawer open={Boolean(selected)} onClose={() => { setSelected(null); setAction(null) }} eyebrow="DCS payment decision" title={selected?.reference ?? ''}>
        {selected ? <div className="record-stack">
          <div className="record-hero"><div><Status>{paymentTypeLabel[selected.source_type]}</Status><h3>{selected.party}</h3><p>{selected.purpose}</p></div><Status>{paymentStatusLabel[selected.payment_status]}</Status></div>
          <div className="summary-grid"><div><span>Approved amount</span><strong>{money(Number(selected.amount_due))}</strong><small>GM-authorized obligation</small></div><div><span>Already paid</span><strong>{money(Number(selected.paid_amount))}</strong><small>Recorded money movement</small></div><div><span>Amount to pay</span><strong>{money(Number(selected.outstanding_amount))}</strong><small>DCS outstanding balance</small></div></div>
          {selected.funding_source ? <div className="callout callout--success"><Landmark size={18} /><span>Paid from <strong>{selected.funding_source}</strong> by {selected.payment_method}. Reference: {selected.transaction_reference}.</span></div> : null}
          {canPay ? <div className="payment-action-bar">
            {['PENDING', 'PARTIALLY_PAID'].includes(selected.payment_status) ? <><Button icon={Check} disabled={fundingSources.length === 0} onClick={() => setAction('pay')}>Mark as Paid</Button><Button tone="secondary" onClick={() => setAction('HOLD')}>Place on Hold</Button><Button tone="danger" onClick={() => setAction('RETURN')}>Return</Button></> : null}
            {selected.payment_status === 'ON_HOLD' ? <><Button onClick={() => setAction('RESUME')}>Resume Payment</Button><Button tone="danger" onClick={() => setAction('RETURN')}>Return</Button></> : null}
            <Button tone="ghost" onClick={() => setAction('NOTE')}>Add Note</Button>
          </div> : <div className="callout callout--info"><ShieldCheck size={18} /><span>This is a view-only payment record for the {role} role. Only DCS records money movement.</span></div>}
          {action ? <form className="form-stack payment-action-form" onSubmit={completeDcsAction}>
            <SectionHeader title={action === 'pay' ? 'Record actual payment' : action === 'HOLD' ? 'Place payment on hold' : action === 'RETURN' ? 'Return payment' : action === 'RESUME' ? 'Resume payment' : 'Add annotation'} description={action === 'pay' ? 'This confirms that money actually left the selected funding source.' : 'Your identity, time, and note become part of the permanent transaction history.'} />
            {action === 'pay' ? <><div className="form-grid"><label>Amount paid<input name="amount" type="number" min="0.01" max={selected.outstanding_amount} step="0.01" defaultValue={selected.outstanding_amount} required /></label><label>Payment date<input name="paid_on" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label>Payment method<select name="mode" required><option>Bank transfer</option><option>Check</option><option>Cash</option><option>E-wallet</option></select></label><label>Funding source <HelpTip label="About funding sources">Only Administrators configure this list. DCS selects the actual source used for this payment.</HelpTip><select name="source" required disabled={fundingSources.length === 0}><option value="">Choose a configured source</option>{fundingSources.map((source) => <option value={source.name} key={source.id}>{source.name}</option>)}</select></label><label>Recipient<input name="recipient" defaultValue={selected.party} required /></label><label>Transaction reference<input name="transaction_reference" placeholder="Bank, check, or transfer reference" required /></label></div><label>Proof of payment<input name="payment_proof" type="file" accept=".pdf,.jpg,.jpeg,.png" required /></label><label>Payment note<textarea name="note" rows={3} placeholder="Optional context for the payment record" /></label></> : <label>{action === 'NOTE' ? 'Annotation' : 'Reason'}<textarea name="note" rows={4} required placeholder={action === 'RETURN' ? 'Explain what must be corrected before payment.' : 'Record the reason or operational context.'} /></label>}
            <div className="modal-actions"><Button tone="ghost" onClick={() => setAction(null)}>Cancel</Button><Button type="submit" tone={action === 'RETURN' ? 'danger' : 'primary'} disabled={busy}>{busy ? 'Saving…' : action === 'pay' ? 'Confirm Paid' : 'Save Action'}</Button></div>
          </form> : null}
          <SectionHeader eyebrow="Chronological and attributable" title="DCS annotations" description="Notes cannot silently overwrite earlier decisions." />
          {selected.annotations.length ? <Timeline items={selected.annotations.map((note) => [new Date(note.created_at).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' }), `${note.event_type}: ${note.note}`, note.actor.display_name])} /> : <div className="callout callout--info"><ShieldCheck size={18} /><span>No DCS annotations have been recorded for this item.</span></div>}
        </div> : null}
      </Drawer>
    </div>
  )
}

function LiquidationPage({ role, notify, navigate }: { role: Role; notify: Notify; navigate: (page: PageId) => void }) {
  const [rows, setRows] = useState<ApiLiquidation[] | null>(null)
  const [allBudgets, setAllBudgets] = useState<ApiBudgetRequest[]>([])
  const [selected, setSelected] = useState<ApiLiquidation | null>(null)
  const [draftLines, setDraftLines] = useState<{ description: string; amount: string }[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [proofFile, setProofFile] = useState<File | null>(null)
  const [viewingDocument, setViewingDocument] = useState<ConfidentialDocumentItem | null>(null)

  const load = () => Promise.all([getLiquidations(), getBudgetRequests()]).then(([items, budgets]) => { setRows(items); setAllBudgets(budgets); setSelected((current) => current ? items.find((item) => item.id === current.id) ?? null : null) }).catch((reason) => { setRows([]); setError(reason instanceof Error ? reason.message : 'Could not load Liquidations.') })
  useEffect(() => { void load() }, [])

  function budgetedLines(item: ApiLiquidation) {
    const related = allBudgets.filter((budget) => budget.id === item.budget_request_id || (budget.parent_budget_id === item.budget_request_id && ['APPROVED', 'PARTIALLY_RELEASED', 'RELEASED'].includes(budget.status)))
    const totals = new Map<string, number>()
    related.flatMap((budget) => budget.items).filter((line) => line.kind === 'BUYING').forEach((line) => totals.set(line.description, (totals.get(line.description) ?? 0) + Number(line.amount)))
    return totals
  }

  function openLiquidation(item: ApiLiquidation) {
    const budgeted = budgetedLines(item)
    const actual = new Map(item.lines.map((line) => [line.description, line.amount]))
    const names = [...new Set([...budgeted.keys(), ...actual.keys()])]
    setDraftLines(names.length ? names.map((description) => ({ description, amount: actual.get(description) ?? '0' })) : [{ description: 'Other', amount: '0' }])
    setSelected(item); setError(''); setProofFile(null)
  }

  async function save(event: FormEvent<HTMLFormElement>, submit: boolean) {
    event.preventDefault()
    if (!selected) return
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const receiptFiles = form.getAll('receipt').filter((item): item is File => item instanceof File && Boolean(item.name))
    try {
      let updated = await saveLiquidation(selected.budget_request_id, {
        expected_version: selected.version,
        lines: draftLines.filter((line) => Number(line.amount) > 0).map((line) => ({ description: line.description, amount: line.amount })),
        evidence: [],
      })
      for (const file of receiptFiles) updated = await uploadLiquidationEvidence(updated.id, updated.version, 'RECEIPT', file)
      if (submit) updated = await submitLiquidation(updated.id, updated.version)
      setSelected(updated)
      notify(`${updated.budget_request.reference} ${submit ? 'submitted for review' : 'saved as a draft'}.`, 'success')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the Liquidation.')
    } finally {
      setBusy(false)
    }
  }

  async function addProofAndClose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      let updated = selected
      const variance = Number(selected.released_total) - Number(selected.actual_total)
      const kind = variance > 0 ? 'RETURN_PROOF' : 'REIMBURSEMENT_PROOF'
      if (variance !== 0 && proofFile) updated = await uploadLiquidationEvidence(selected.id, selected.version, kind, proofFile)
      const originalsPhoto = form.get('originals_photo')
      if (originalsPhoto instanceof File && originalsPhoto.name) {
        updated = await uploadLiquidationEvidence(updated.id, updated.version, 'PHYSICAL_RECEIPTS_PHOTO', originalsPhoto)
      }
      updated = await closeLiquidation(
        updated.id,
        updated.version,
        String(form.get('note')),
        form.get('originals_received_confirmed') === 'on',
      )
      setSelected(null)
      notify(`${updated.budget_request.reference} Liquidation closed with an attributable proof trail.`, 'success')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not close the Liquidation.')
    } finally {
      setBusy(false)
    }
  }

  const statusLabel: Record<ApiLiquidation['status'], string> = { DRAFT: 'Draft', SUBMITTED: 'Submitted', PENDING_VARIANCE: 'Variance needs proof', CLOSED: 'Closed' }
  return (
    <div className="page-stack">
      <div className="explanation-banner"><span><ReceiptText size={20} /></span><div><strong>Requester records; Mich monitors and closes.</strong><p>The Requester enters actual shipment expenses and receipts. Mich watches progress, reviews evidence and variances, and closes a complete liquidation.</p></div></div>
      <Card>
        <SectionHeader eyebrow="Internal accountability" title={role === 'Requester' ? 'My Liquidations' : 'Liquidations to review'} description="Compare released funds with actual spend and keep every variance open until proof is complete." />
        {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
        {rows === null ? <EmptyState icon={RefreshCw} title="Loading Liquidations" detail="Opening the persistent Liquidation register." /> : rows.length === 0 ? <EmptyState icon={ReceiptText} title="No Liquidations yet" detail="A Liquidation becomes available after DCS records a shipment payment." /> : <div className="table-wrap"><table><thead><tr><th>Reference</th><th>Requester</th><th>Released</th><th>Actual spend</th><th>Variance</th><th>Progress</th><th></th></tr></thead><tbody>
          {rows.map((row) => { const variance = Number(row.released_total) - Number(row.actual_total); return <tr key={row.id}><td data-label="Reference"><strong>{row.budget_request.reference}</strong><small>{row.budget_request.client.name}</small></td><td data-label="Requester">{row.requester.display_name}</td><td data-label="Released" className="number">{money(Number(row.released_total))}</td><td data-label="Actual spend" className="number">{money(Number(row.actual_total))}</td><td data-label="Variance" className="number number--emphasis">{variance === 0 ? 'Balanced' : variance > 0 ? `${money(variance)} to return` : `${money(Math.abs(variance))} to reimburse`}</td><td data-label="Progress"><Status>{statusLabel[row.status]}</Status></td><td><Button tone="ghost" onClick={() => openLiquidation(row)}>Open</Button></td></tr> })}
        </tbody></table></div>}
      </Card>
      <Drawer open={Boolean(selected)} onClose={() => setSelected(null)} eyebrow="Liquidation record" title={selected?.budget_request.reference ?? ''}>
        {selected ? <div className="record-stack">{error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}<div className="summary-grid"><div><span>Released</span><strong>{money(Number(selected.released_total))}</strong></div><div><span>Actual spend</span><strong>{money(Number(selected.actual_total))}</strong></div><div><span>Variance</span><strong>{money(Number(selected.released_total) - Number(selected.actual_total))}</strong></div></div>
          <div><SectionHeader title="Additional Budget Requests" description="Each increase remains a separate Approval and is linked to this original Budget Request." />{allBudgets.filter((budget) => budget.parent_budget_id === selected.budget_request_id).length ? <div className="table-wrap"><table><thead><tr><th>Date / reference</th><th>Reason</th><th>Buying</th><th>Selling</th><th>Status</th></tr></thead><tbody>{allBudgets.filter((budget) => budget.parent_budget_id === selected.budget_request_id).map((budget) => <tr key={budget.id}><td data-label="Date / reference"><strong>{budget.reference}</strong><small>{budget.request_date}</small></td><td data-label="Reason">{budget.additional_reason}</td><td data-label="Buying" className="number">{money(Number(budget.buying_total))}</td><td data-label="Selling" className="number">{money(Number(budget.selling_total))}</td><td data-label="Status"><Status>{budget.status.replaceAll('_', ' ')}</Status></td></tr>)}</tbody></table></div> : <div className="callout callout--info"><ReceiptText size={18} /><span>No Additional Budget Requests are linked yet.</span></div>}</div>
          {(role === 'Requester' || role === 'Admin') && selected.status === 'DRAFT' ? <form className="form-stack" onSubmit={(event) => save(event, (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-action') === 'submit')}><SectionHeader title="Actual expenses and receipts" description="Budgeted values are read-only. Enter the amount supported by receipts; variance is calculated automatically." /><div className="liquidation-lines"><div className="liquidation-lines__head"><span>Charge / expense</span><span>Budgeted</span><span>Actual</span><span>Variance</span></div>{draftLines.map((line, index) => { const budgeted = budgetedLines(selected).get(line.description) ?? 0; const variance = budgeted - Number(line.amount || 0); const custom = !commonChargeTypes.some(([name]) => name === line.description); return <div className="liquidation-lines__row" key={index}><label><span className="sr-only">Charge type</span><select value={custom ? '__OTHER__' : line.description} onChange={(event) => { const value = event.target.value === '__OTHER__' ? 'Other' : event.target.value; setDraftLines((current) => current.map((item, row) => row === index ? { ...item, description: value } : item)) }}>{commonChargeTypes.map(([name]) => <option key={name}>{name}</option>)}<option value="__OTHER__">Others — custom</option></select>{custom ? <input value={line.description === 'Other' ? '' : line.description} onChange={(event) => setDraftLines((current) => current.map((item, row) => row === index ? { ...item, description: event.target.value } : item))} placeholder="Enter expense name" required /> : null}</label><strong>{money(budgeted)}</strong><label><span className="sr-only">Actual amount for {line.description}</span><input type="number" min="0" step="0.01" value={line.amount} onChange={(event) => setDraftLines((current) => current.map((item, row) => row === index ? { ...item, amount: event.target.value } : item))} /></label><strong className={variance < 0 ? 'danger-text' : ''}>{money(variance)}</strong></div>})}</div><Button tone="ghost" icon={Plus} onClick={() => setDraftLines((current) => [...current, { description: 'Other', amount: '0' }])}>Add another expense</Button><label>Receipt or supporting document<input name="receipt" type="file" accept=".pdf,.jpg,.jpeg,.png" required={!selected.evidence.some((item) => item.kind === 'RECEIPT')} /></label><div className="callout callout--info"><Plus size={18} /><span>For costs beyond the released budget, create an Additional Budget linked to this Budget Request before Mich closes the variance.</span></div><div className="drawer-actions"><Button tone="secondary" icon={Plus} onClick={() => navigate('budget-requests')}>Request Additional Budget</Button><button className="button button--secondary" type="submit" disabled={busy}>Save as Draft</button><button className="button button--primary" type="submit" data-action="submit" disabled={busy}>Submit for Approval</button></div></form> : null}
          {(role === 'Mich' || role === 'Admin') ? <form className="form-stack" onSubmit={addProofAndClose}><SectionHeader title="Mich review and variance closure" description="A variance stays open until the matching proof is recorded. The Liquidation status is derived automatically; users do not select it." />{selected.evidence.map((item) => <DocumentItem key={item.id} name={item.file_name} meta={`${item.kind.replaceAll('_', ' ')} • ${item.size_bytes ? formatBytes(item.size_bytes) : 'Demo metadata'}`} available={Boolean(item.size_bytes)} onOpen={() => setViewingDocument({ id: item.id, name: item.file_name, contentType: item.content_type })} />)}{Number(selected.released_total) !== Number(selected.actual_total) ? <label>{Number(selected.released_total) > Number(selected.actual_total) ? 'Requester proof of deposit / returned funds' : 'PIMASCOR proof of reimbursement'}<input type="file" accept=".pdf,.jpg,.jpeg,.png" required={!selected.evidence.some((item) => item.kind === (Number(selected.released_total) > Number(selected.actual_total) ? 'RETURN_PROOF' : 'REIMBURSEMENT_PROOF'))} onChange={(event) => setProofFile(event.target.files?.[0] ?? null)} /></label> : null}<div className="callout callout--warning"><ShieldCheck size={18} /><span>Before closing, compare the digital files with the original physical receipts, especially duties-and-taxes documents.</span></div><label className="checkbox-label"><input name="originals_received_confirmed" type="checkbox" required />I confirm that Mich received and checked the original physical supporting documents.</label><label>Optional photo of originals received<input name="originals_photo" type="file" accept=".pdf,.jpg,.jpeg,.png" /></label><label>Closure note<textarea name="note" rows={3} required placeholder="Record what Mich verified." /></label><div className="drawer-actions"><Button type="submit" icon={CheckCircle2} disabled={busy || selected.status === 'DRAFT' || selected.status === 'CLOSED'}>Close Variance and Liquidation</Button></div></form> : null}
        </div> : null}
      </Drawer>
      <ConfidentialDocumentViewer item={viewingDocument} onClose={() => setViewingDocument(null)} canDownload={!isDemoBuild && ['Admin', 'GM', 'DCS', 'Mich'].includes(role)} />
    </div>
  )
}

function BillingPageLegacy({ role, notify }: { role: Role; notify: Notify }) {
  const [rows, setRows] = useState<ApiBilling[] | null>(null)
  const [budgets, setBudgets] = useState<ApiBudgetRequest[]>([])
  const [selected, setSelected] = useState<ApiBilling | null>(null)
  const [editing, setEditing] = useState<{ budget: ApiBudgetRequest; billing?: ApiBilling } | null>(null)
  const [replacementOf, setReplacementOf] = useState<ApiBilling | null>(null)
  const [voiding, setVoiding] = useState<ApiBilling | null>(null)
  const [taxProfiles, setTaxProfiles] = useState<ApiTaxProfile[]>([])
  const [billingLines, setBillingLines] = useState<{ description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]>([])
  const [creditMemos, setCreditMemos] = useState<ApiCreditMemo[]>([])
  const [crediting, setCrediting] = useState<ApiBilling | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const canPrepare = role === 'Mich' || role === 'Admin'
  const load = () => Promise.all([getBilling(), getBudgetRequests()]).then(([billing, budgetItems]) => { setRows(billing); setBudgets(budgetItems) }).catch((reason) => { setRows([]); setError(reason instanceof Error ? reason.message : 'Could not load Billing.') })
  useEffect(() => { void load(); if (canPrepare) getTaxProfiles().then(setTaxProfiles).catch(() => setTaxProfiles([])) }, [canPrepare])

  function startBillingEditor(budget: ApiBudgetRequest, billing?: ApiBilling, replacement?: ApiBilling) {
    setBillingLines((billing?.lines ?? budget.items.filter((item) => item.kind === 'SELLING')).map((line) => ({ description: line.description, classification: line.classification, amount: line.amount })))
    setReplacementOf(replacement ?? null)
    setEditing({ budget, billing: replacement ? undefined : billing })
  }

  function openBilling(item: ApiBilling) {
    setSelected(item); setError('')
    getCreditMemos(item.id).then(setCreditMemos).catch(() => setCreditMemos([]))
  }

  const taxTotals = useMemo(() => billingLines.reduce((totals, line) => {
    const profile = taxProfiles.find((item) => item.active && item.classification === line.classification)
    const amount = Number(line.amount || 0)
    totals.subtotal += amount
    totals.vat += amount * Number(profile?.vat_rate ?? 0)
    totals.withholding += amount * Number(profile?.withholding_rate ?? 0)
    return totals
  }, { subtotal: 0, vat: 0, withholding: 0 }), [billingLines, taxProfiles])

  const ready = budgets.filter((budget) => budget.budget_kind === 'MAIN' && ['APPROVED', 'PARTIALLY_RELEASED', 'RELEASED'].includes(budget.status) && !(rows ?? []).some((billing) => billing.budget_request_id === budget.id && billing.status !== 'VOID'))

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editing) return
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const payload = {
      issue_date: String(form.get('issue_date')),
      due_date: String(form.get('due_date')),
      client_address: String(form.get('client_address') || '') || null,
      category: String(form.get('category') || '') || null,
      shipper_consignee: String(form.get('shipper_consignee') || '') || null,
      container_number: String(form.get('container_number') || '') || null,
      destination: String(form.get('destination') || '') || null,
      vessel: String(form.get('vessel') || '') || null,
      bl_awb_number: String(form.get('bl_awb_number') || '') || null,
      exchange_rate: String(form.get('exchange_rate') || '') || null,
      measurement: String(form.get('measurement') || '') || null,
      notes: String(form.get('notes') || '') || null,
      lines: billingLines,
    }
    try {
      const updated = replacementOf
        ? await createBillingReplacement(replacementOf.id, { ...payload, expected_version: replacementOf.version, reason: String(form.get('replacement_reason')) })
        : editing.billing
        ? await updateBillingDraft(editing.billing.id, { ...payload, expected_version: editing.billing.version })
        : await createBillingDraft(editing.budget.id, payload)
      setEditing(null)
      setReplacementOf(null)
      setSelected(updated)
      notify(`${updated.reference} saved as an editable Billing draft.`, 'success')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the Billing draft.')
    } finally { setBusy(false) }
  }

  async function finalize(item: ApiBilling) {
    if (!window.confirm(`Finalize and send ${item.reference}? It becomes immutable after this action.`)) return
    setBusy(true)
    try {
      const updated = await finalizeBilling(item.id, item.version)
      setSelected(updated)
      notify(`${updated.reference} finalized. Future corrections must preserve this record.`, 'success')
      load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not finalize Billing.') } finally { setBusy(false) }
  }

  async function confirmVoid(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!voiding) return
    setBusy(true)
    const form = new FormData(event.currentTarget)
    try {
      const updated = await voidBilling(voiding.id, voiding.version, String(form.get('reason')))
      setVoiding(null); setSelected(updated); notify(`${updated.reference} voided without deleting its history.`, 'success'); load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not void Billing.') } finally { setBusy(false) }
  }

  async function submitCreditMemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!crediting) return
    setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const memo = await createCreditMemo(crediting.id, { reason: String(form.get('reason')), amount: String(form.get('amount')), submit_for_approval: true })
      setCrediting(null); setCreditMemos((current) => [memo, ...current]); notify(`${memo.reference} submitted for GM approval.`, 'success'); load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create the Credit Memo.') } finally { setBusy(false) }
  }

  async function handleCreditDecision(memo: ApiCreditMemo, approve: boolean) {
    setBusy(true); setError('')
    try {
      const updated = await decideCreditMemo(memo.id, memo.version, approve, approve ? undefined : 'Returned by Administrator')
      setCreditMemos((current) => current.map((item) => item.id === updated.id ? updated : item)); notify(`${updated.reference} ${approve ? 'approved' : 'rejected'}.`, approve ? 'success' : 'warning'); load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save the Credit Memo decision.') } finally { setBusy(false) }
  }

  return (
    <div className="page-stack">
      <Card>
        <SectionHeader eyebrow="Client billing" title={canPrepare ? 'Billing work queue' : 'Billing records'} description="Billing can start after GM approval. Finalized records cannot be silently edited or overwritten." />
        {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
        {rows === null ? <EmptyState icon={RefreshCw} title="Loading Billing" detail="Opening the protected Billing register." /> : <div className="table-wrap"><table><thead><tr><th>Billing reference</th><th>Shipment / client</th><th>Net due</th><th>Collected</th><th>Remaining</th><th>Due date</th><th>Status</th><th></th></tr></thead><tbody>
          {canPrepare && ready.map((budget) => <tr key={`ready-${budget.id}`}><td data-label="Billing reference"><strong>Not created</strong></td><td data-label="Shipment / client"><strong>{budget.reference}</strong><small>{budget.client.name}</small></td><td data-label="Net due" className="number">{money(Number(budget.selling_total))}</td><td data-label="Collected" className="number">—</td><td data-label="Remaining" className="number">—</td><td data-label="Due date">Not set</td><td data-label="Status"><Status>Ready to prepare</Status></td><td><Button tone="secondary" onClick={() => startBillingEditor(budget)}>Prepare Billing</Button></td></tr>)}
          {rows.map((row) => <tr key={row.id}><td data-label="Billing reference"><strong>{row.reference}</strong>{row.revision ? <small>Replacement revision {row.revision}</small> : null}</td><td data-label="Budget Request / client"><strong>{row.budget_request.reference}</strong><small>{row.budget_request.client.name}</small></td><td data-label="Net due" className="number">{money(Number(row.adjusted_net_due))}</td><td data-label="Collected" className="number">{money(Number(row.collected_amount))}</td><td data-label="Remaining" className="number number--emphasis">{money(Number(row.remaining_amount))}</td><td data-label="Due date">{row.due_date ? new Date(`${row.due_date}T00:00:00`).toLocaleDateString('en-PH', { dateStyle: 'medium' }) : 'Not set'}</td><td data-label="Status"><Status>{row.status === 'FINALIZED' ? row.collection_status : row.status === 'VOID' ? 'Void' : 'Draft'}</Status></td><td><Button tone="ghost" onClick={() => openBilling(row)}>Open Billing</Button></td></tr>)}
        </tbody></table></div>}
      </Card>
      <Drawer open={Boolean(selected)} onClose={() => setSelected(null)} eyebrow="Billing record" title={selected?.reference ?? ''}>
        {selected ? <div className="record-stack">
          <div className="preview-notice"><FileText size={19} /><span>This is a Billing record. It is not automatically an official tax invoice.</span></div>
          <OfficialBillingDocument billing={selected} />
          <div className="drawer-actions"><Button tone="secondary" icon={FileText} onClick={printOfficialDocument}>Print Official Document / Save PDF</Button>{canPrepare && selected.status === 'DRAFT' ? <><Button tone="secondary" onClick={() => setEditing({ budget: selected.budget_request, billing: selected })}>Edit Draft</Button><Button icon={FileCheck2} disabled={busy} onClick={() => finalize(selected)}>Finalize and Send</Button></> : null}{role === 'Admin' && selected.status === 'FINALIZED' ? <Button tone="danger" onClick={() => setVoiding(selected)}>Void Billing</Button> : null}</div>
          <p className="helper-text"><ShieldCheck size={15} />Finalization freezes this record. Corrections require an attributable void and replacement trail.</p>
        </div> : null}
      </Drawer>
      {selected ? createPortal(<div className="print-document-host"><OfficialBillingDocument billing={selected} printCopy /></div>, document.body) : null}
      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={editing?.billing ? `Edit ${editing.billing.reference}` : 'Prepare Billing'}>{editing ? <form className="form-stack" onSubmit={saveDraft}><div className="callout callout--info"><ShieldCheck size={18} /><span>Buying, Selling, pass-through, service charges, VAT, and withholding remain separate. Enter only accountant-approved values.</span></div><div className="form-grid"><label>Issue date<input name="issue_date" type="date" defaultValue={editing.billing?.issue_date ?? new Date().toISOString().slice(0, 10)} required /></label><label>Due date<input name="due_date" type="date" defaultValue={editing.billing?.due_date ?? ''} required /></label></div>{(editing.billing?.lines ?? editing.budget.items.filter((item) => item.kind === 'SELLING')).map((line, index) => <div className="form-grid" key={`${line.description}-${index}`}><label>Description<input name="description" defaultValue={line.description} required /></label><label>Classification<select name="classification" defaultValue={line.classification}><option value="SERVICE_CHARGE">Service charge</option><option value="PASS_THROUGH">Pass-through cost</option></select></label><label>Amount<input name="amount" type="number" min="0.01" step="0.01" defaultValue={line.amount} required /></label></div>)}<div className="form-grid"><label>VAT amount<input name="vat_amount" type="number" min="0" step="0.01" defaultValue={editing.billing?.vat_amount ?? '0'} /></label><label>Withholding amount<input name="withholding_amount" type="number" min="0" step="0.01" defaultValue={editing.billing?.withholding_amount ?? '0'} /></label></div><label>Billing notes<textarea name="notes" rows={3} defaultValue={editing.billing?.notes ?? ''} /></label><div className="modal-actions"><Button tone="secondary" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" disabled={busy}>Save Billing Draft</Button></div></form> : null}</Modal>
      <Modal open={Boolean(voiding)} onClose={() => setVoiding(null)} title="Void finalized Billing">{voiding ? <form className="form-stack" onSubmit={confirmVoid}><div className="callout callout--danger"><AlertCircle size={18} /><span>The original record remains visible. This action cannot be used to overwrite financial history.</span></div><label>Reason for voiding<textarea name="reason" rows={4} required minLength={3} /></label><div className="modal-actions"><Button tone="secondary" onClick={() => setVoiding(null)}>Cancel</Button><Button tone="danger" type="submit" disabled={busy}>Confirm Void</Button></div></form> : null}</Modal>
    </div>
  )
}

function OfficialBillingDocument({ billing, printCopy = false }: { billing: ApiBilling; printCopy?: boolean }) {
  const serviceLines = billing.lines.filter((line) => line.classification === 'SERVICE_CHARGE')
  const passThroughLines = billing.lines.filter((line) => line.classification === 'PASS_THROUGH')
  const displayDate = (value: string | null) => value
    ? new Date(`${value}T00:00:00`).toLocaleDateString('en-PH', { month: '2-digit', day: '2-digit', year: 'numeric' })
    : '—'
  const amount = (value: number) => new Intl.NumberFormat('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)

  return <article className={`official-billing ${printCopy ? 'official-billing--print' : 'official-billing--preview'}`}>
    {billing.status !== 'FINALIZED' ? <div className="official-billing__watermark">{billing.status.replaceAll('_', ' ')}</div> : null}
    <header className="official-billing__letterhead">
      <img src={brandIconUrl} alt="PIMASCOR" />
      <div>
        <strong>Philippine Interactive Maritime and Arrastre Services Corp.</strong>
        <span>1304 Oxford Bldg., Gelinos St., Corner Laon Laan St., Brgy. 342 Zone 34, Sta. Cruz, Manila</span>
        <span>Mobile No.: +63 926 7428894 &nbsp; Tel. No.: (02) 8818 5482 &nbsp; Email: info@pimascor.com</span>
      </div>
      <p><small>No.</small><b>{billing.reference}</b></p>
    </header>

    <h1>Statement of Account</h1>

    <section className="official-billing__account">
      <div>
        <span>Account for</span>
        <strong>{billing.budget_request.client.name}</strong>
        <p>{billing.client_address || 'Client address not provided'}</p>
      </div>
      <dl>
        <dt>Date</dt><dd>{displayDate(billing.issue_date)}</dd>
        <dt>Category</dt><dd>{billing.category || '—'}</dd>
        <dt>Shipper / Cnee</dt><dd>{billing.shipper_consignee || '—'}</dd>
        <dt>Container No.</dt><dd>{billing.container_number || '—'}</dd>
        <dt>Reference No.</dt><dd>{billing.budget_request.reference}</dd>
        <dt>Destination</dt><dd>{billing.destination || '—'}</dd>
      </dl>
    </section>

    <section className="official-billing__shipment" aria-label="Shipment details">
      <span><small>Vessel</small><b>{billing.vessel || '—'}</b></span>
      <span><small>BL / AWB No.</small><b>{billing.bl_awb_number || '—'}</b></span>
      <span><small>Exchange Rate</small><b>{billing.exchange_rate || '—'}</b></span>
      <span><small>Measurement</small><b>{billing.measurement || '—'}</b></span>
    </section>

    <table className="official-billing__charges">
      <colgroup><col /><col className="official-billing__currency-col" /><col className="official-billing__amount-col" /></colgroup>
      <thead><tr><th>Description</th><th>Currency</th><th>Amount</th></tr></thead>
      <tbody>
        <tr className="official-billing__section-row"><th colSpan={3}>Service charges</th></tr>
        {serviceLines.length ? serviceLines.map((line) => <tr key={line.id}><td>{line.description}</td><td>PHP</td><td>{amount(Number(line.amount))}</td></tr>) : <tr><td colSpan={3}>No service charges</td></tr>}
        <tr className="official-billing__calculation-row"><th colSpan={2}>Service charge subtotal</th><td>{amount(Number(billing.service_subtotal))}</td></tr>
        <tr className="official-billing__calculation-row"><th colSpan={2}>VAT</th><td>{amount(Number(billing.vat_amount))}</td></tr>
        <tr className="official-billing__calculation-row official-billing__calculation-row--total"><th colSpan={2}>Total service charges</th><td>{amount(Number(billing.service_subtotal) + Number(billing.vat_amount))}</td></tr>

        <tr className="official-billing__section-row"><th colSpan={3}>Reimbursable expense (pass-through costs)</th></tr>
        {passThroughLines.length ? passThroughLines.map((line) => <tr key={line.id}><td>{line.description}</td><td>PHP</td><td>{amount(Number(line.amount))}</td></tr>) : <tr><td colSpan={3}>No reimbursable expenses</td></tr>}
        <tr className="official-billing__calculation-row official-billing__calculation-row--total"><th colSpan={2}>Total reimbursable expenses</th><td>{amount(Number(billing.pass_through_subtotal))}</td></tr>
      </tbody>
      <tfoot>
        <tr><th colSpan={2}>Grand total</th><td>{amount(Number(billing.total_amount))}</td></tr>
        <tr><th colSpan={2}>Less: Creditable Withholding Tax (CWT)</th><td>({amount(Number(billing.withholding_amount))})</td></tr>
        {Number(billing.approved_credit_memo_amount) ? <tr><th colSpan={2}>Less: approved Credit Memos</th><td>({amount(Number(billing.approved_credit_memo_amount))})</td></tr> : null}
        <tr className="official-billing__net"><th colSpan={2}>Net amount due</th><td>PHP {amount(Number(billing.adjusted_net_due))}</td></tr>
      </tfoot>
    </table>

    {billing.notes ? <section className="official-billing__notes"><strong>Billing notes</strong><p>{billing.notes}</p></section> : null}
    <section className="official-billing__closing">
      <p>Accounts are payable according to the agreed client terms. Please quote the Statement of Account number and Budget Request reference with every payment. This Billing record is not automatically an official tax invoice.</p>
      <div className="official-billing__signatures">
        <span>Prepared by<strong>{billing.prepared_by.display_name}</strong></span>
        <span>GM approved by<strong>{billing.approved_by?.display_name || 'Pending approval'}</strong></span>
        <span>Received by<strong>&nbsp;</strong></span>
      </div>
    </section>
    <footer><span>PIMASCOR • Statement of Account</span><span>{billing.reference}</span></footer>
  </article>
}

function BillingPage({ role, notify }: { role: Role; notify: Notify }) {
  type BillingLineDraft = { description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }
  const [rows, setRows] = useState<ApiBilling[] | null>(null)
  const [budgets, setBudgets] = useState<ApiBudgetRequest[]>([])
  const [selected, setSelected] = useState<ApiBilling | null>(null)
  const [editing, setEditing] = useState<{ budget: ApiBudgetRequest; billing?: ApiBilling; replacementOf?: ApiBilling } | null>(null)
  const [lines, setLines] = useState<BillingLineDraft[]>([])
  const [taxProfiles, setTaxProfiles] = useState<ApiTaxProfile[]>([])
  const [creditMemos, setCreditMemos] = useState<ApiCreditMemo[]>([])
  const [crediting, setCrediting] = useState<ApiBilling | null>(null)
  const [voiding, setVoiding] = useState<ApiBilling | null>(null)
  const [previewZoom, setPreviewZoom] = useState(() => window.innerWidth <= 760 ? 50 : 85)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const canPrepare = role === 'Mich' || role === 'Admin'

  const load = () => Promise.all([getBilling(), getBudgetRequests()])
    .then(([billing, requests]) => { setRows(billing); setBudgets(requests) })
    .catch((reason) => { setRows([]); setError(reason instanceof Error ? reason.message : 'Could not load Billing.') })

  useEffect(() => {
    void load()
    if (canPrepare) getTaxProfiles().then(setTaxProfiles).catch(() => setTaxProfiles([]))
  }, [canPrepare])

  function beginEditor(budget: ApiBudgetRequest, billing?: ApiBilling, replacementOf?: ApiBilling) {
    const source = billing?.lines ?? replacementOf?.lines ?? budget.items.filter((item) => item.kind === 'SELLING')
    setLines(source.map((line) => ({ description: line.description, classification: line.classification, amount: line.amount })))
    setEditing({ budget, billing, replacementOf })
  }

  function showBilling(item: ApiBilling) {
    setSelected(item)
    setPreviewZoom(window.innerWidth <= 760 ? 50 : 85)
    setCreditMemos([])
    getCreditMemos(item.id).then(setCreditMemos).catch(() => setCreditMemos([]))
  }

  const taxPreview = useMemo(() => lines.reduce((total, line) => {
    const profile = taxProfiles.find((item) => item.active && item.classification === line.classification)
    const amount = Number(line.amount || 0)
    total.subtotal += amount
    total.vat += amount * Number(profile?.vat_rate ?? 0)
    total.withholding += amount * Number(profile?.withholding_rate ?? 0)
    return total
  }, { subtotal: 0, vat: 0, withholding: 0 }), [lines, taxProfiles])

  const ready = budgets.filter((budget) => budget.budget_kind === 'MAIN'
    && ['APPROVED', 'PARTIALLY_RELEASED', 'RELEASED'].includes(budget.status)
    && !(rows ?? []).some((billing) => billing.budget_request_id === budget.id && billing.status !== 'VOID'))

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editing) return
    setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    const payload = {
      issue_date: String(form.get('issue_date')),
      due_date: String(form.get('due_date')),
      client_address: String(form.get('client_address') || '') || null,
      category: String(form.get('category') || '') || null,
      shipper_consignee: String(form.get('shipper_consignee') || '') || null,
      container_number: String(form.get('container_number') || '') || null,
      destination: String(form.get('destination') || '') || null,
      vessel: String(form.get('vessel') || '') || null,
      bl_awb_number: String(form.get('bl_awb_number') || '') || null,
      exchange_rate: String(form.get('exchange_rate') || '') || null,
      measurement: String(form.get('measurement') || '') || null,
      notes: String(form.get('notes') || '') || null,
      lines,
    }
    try {
      const saved = editing.replacementOf
        ? await createBillingReplacement(editing.replacementOf.id, { ...payload, expected_version: editing.replacementOf.version, reason: String(form.get('replacement_reason')) })
        : editing.billing
          ? await updateBillingDraft(editing.billing.id, { ...payload, expected_version: editing.billing.version })
          : await createBillingDraft(editing.budget.id, payload)
      setEditing(null); showBilling(saved); notify(editing.replacementOf ? `${saved.reference} sent to the GM as a replacement proposal.` : `${saved.reference} saved as a draft.`, 'success'); void load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the Billing draft.')
    } finally { setBusy(false) }
  }

  async function submitForApproval(item: ApiBilling) {
    setBusy(true); setError('')
    try {
      const saved = await submitBilling(item.id, item.version)
      showBilling(saved); notify(`${saved.reference} sent to the GM for approval.`, 'success'); void load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not submit Billing for approval.') } finally { setBusy(false) }
  }

  async function finalize(item: ApiBilling) {
    if (!window.confirm(`Finalize and send ${item.reference}? The record will be locked after this.`)) return
    setBusy(true); setError('')
    try {
      const saved = await finalizeBilling(item.id, item.version)
      showBilling(saved); notify(`${saved.reference} was finalized and locked.`, 'success'); void load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not finalize Billing.') } finally { setBusy(false) }
  }

  async function confirmVoid(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!voiding) return
    setBusy(true); setError('')
    try {
      const form = new FormData(event.currentTarget)
      const saved = await voidBilling(voiding.id, voiding.version, String(form.get('reason')))
      setVoiding(null); showBilling(saved); notify(`${saved.reference} was voided. Its history was preserved.`, 'success'); void load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not void Billing.') } finally { setBusy(false) }
  }

  async function submitCreditMemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!crediting) return
    setBusy(true); setError('')
    try {
      const form = new FormData(event.currentTarget)
      const memo = await createCreditMemo(crediting.id, { amount: String(form.get('amount')), reason: String(form.get('reason')), submit_for_approval: true })
      setCrediting(null); setCreditMemos((current) => [memo, ...current]); notify(`${memo.reference} sent to the GM for approval.`, 'success')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create the Credit Memo.') } finally { setBusy(false) }
  }

  async function decideMemo(memo: ApiCreditMemo, approve: boolean) {
    setBusy(true); setError('')
    try {
      const saved = await decideCreditMemo(memo.id, memo.version, approve, approve ? undefined : 'Returned by the approver')
      setCreditMemos((current) => current.map((item) => item.id === saved.id ? saved : item)); notify(`${saved.reference} ${approve ? 'approved' : 'rejected'}.`, approve ? 'success' : 'warning'); void load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save the Credit Memo decision.') } finally { setBusy(false) }
  }

  return <div className="page-stack">
    <Card>
      <SectionHeader eyebrow="Billing and Statement of Account" title={canPrepare ? 'Billing work queue' : 'Billing records'} description="Prepare an itemized proposal, obtain GM approval, then finalize and lock the official Billing record." />
      {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
      {rows === null ? <EmptyState icon={RefreshCw} title="Loading Billing" detail="Opening the protected Billing register." /> : <div className="table-wrap"><table><thead><tr><th>Billing / SOA</th><th>Budget Request / client</th><th>Amount billed</th><th>CWT</th><th>Adjusted net due</th><th>Remaining</th><th>Aging</th><th>Status</th><th></th></tr></thead><tbody>
        {canPrepare && ready.map((budget) => <tr key={budget.id}><td data-label="Billing / SOA"><strong>Not created</strong></td><td data-label="Budget Request / client"><strong>{budget.reference}</strong><small>{budget.client.name}</small></td><td data-label="Amount billed" className="number">{money(Number(budget.selling_total))}</td><td>—</td><td>—</td><td>—</td><td>—</td><td><Status>Ready to prepare</Status></td><td><Button tone="secondary" onClick={() => beginEditor(budget)}>Prepare Billing</Button></td></tr>)}
        {rows.map((row) => <tr key={row.id}><td data-label="Billing / SOA"><strong>{row.reference}</strong>{row.revision ? <small>Replacement R{row.revision}</small> : null}</td><td data-label="Budget Request / client"><strong>{row.budget_request.reference}</strong><small>{row.budget_request.client.name}</small></td><td data-label="Amount billed" className="number">{money(Number(row.total_amount))}</td><td data-label="CWT" className="number">{money(Number(row.withholding_amount))}</td><td data-label="Adjusted net due" className="number">{money(Number(row.adjusted_net_due))}</td><td data-label="Remaining" className="number number--emphasis">{money(Number(row.remaining_amount))}</td><td data-label="Aging"><Status tone={row.aging_days > 30 ? 'danger' : row.aging_days > 0 ? 'warning' : 'info'}>{row.aging_bucket}</Status></td><td data-label="Status"><Status>{row.status === 'FINALIZED' ? row.collection_status : row.status}</Status></td><td><Button tone="ghost" onClick={() => showBilling(row)}>Open</Button></td></tr>)}
      </tbody></table></div>}
    </Card>

    <Drawer className="drawer--document" open={Boolean(selected)} onClose={() => setSelected(null)} eyebrow="Billing / Statement of Account" title={selected?.reference ?? ''}>
      {selected ? <div className="record-stack">
        <div className="preview-notice"><FileText size={19} /><span>{selected.status === 'FINALIZED' ? 'Finalized and locked. Corrections require an approved Credit Memo or replacement.' : selected.status === 'APPROVED' ? `Approved by ${selected.approved_by?.role === 'ADMIN' ? 'the Administrator' : 'the GM'}. Mich or the Administrator may now finalize this Billing record.` : selected.status === 'PENDING_APPROVAL' ? 'Submitted and locked while the GM or Administrator reviews it.' : selected.status === 'REJECTED' ? `Returned by ${selected.approved_by?.role === 'ADMIN' ? 'the Administrator' : 'the GM'}: ${selected.rejection_reason}` : 'Draft. Review every detail, then submit it for approval.'}</span></div>
        <div className="billing-preview-toolbar" role="group" aria-label="Document preview zoom controls">
          <strong>Print preview</strong>
          <button type="button" onClick={() => setPreviewZoom((value) => Math.max(40, value - 10))} aria-label="Zoom out">−</button>
          <label><span className="visually-hidden">Preview zoom</span><input type="range" min="40" max="160" step="10" value={previewZoom} onChange={(event) => setPreviewZoom(Number(event.target.value))} /></label>
          <output aria-live="polite">{previewZoom}%</output>
          <button type="button" onClick={() => setPreviewZoom((value) => Math.min(160, value + 10))} aria-label="Zoom in">+</button>
          <button type="button" className="billing-preview-toolbar__reset" onClick={() => setPreviewZoom(window.innerWidth <= 760 ? 50 : 85)}>Fit</button>
        </div>
        <div className="billing-preview-stage" tabIndex={0} aria-label="Scrollable Billing print preview">
          <div className="billing-preview-stage__document" style={{ zoom: `${previewZoom}%` }}><OfficialBillingDocument billing={selected} /></div>
        </div>
        {creditMemos.length ? <div><SectionHeader title="Credit Memo history" description="The original Billing amount is preserved. A GM or Administrator approval is required before a Credit Memo adjusts the collectible balance." /><div className="table-wrap"><table><thead><tr><th>Reference</th><th>Reason</th><th>Amount</th><th>Status</th><th></th></tr></thead><tbody>{creditMemos.map((memo) => <tr key={memo.id}><td><strong>{memo.reference}</strong></td><td>{memo.reason}</td><td className="number">{money(Number(memo.amount))}</td><td><Status>{memo.status.replaceAll('_', ' ')}</Status></td><td>{(role === 'GM' || role === 'Admin') && memo.status === 'PENDING_APPROVAL' ? <div className="table-actions"><Button tone="secondary" onClick={() => decideMemo(memo, true)}>Approve</Button><Button tone="danger" onClick={() => decideMemo(memo, false)}>Reject</Button></div> : null}</td></tr>)}</tbody></table></div></div> : null}
        <div className="drawer-actions"><Button tone="secondary" icon={FileText} onClick={printOfficialDocument}>Print Official Document / Save PDF</Button>{canPrepare && (selected.status === 'DRAFT' || selected.status === 'REJECTED') ? <><Button tone="secondary" onClick={() => beginEditor(selected.budget_request, selected)}>Edit Draft</Button><Button icon={FileCheck2} disabled={busy} onClick={() => submitForApproval(selected)}>Submit for Approval</Button></> : null}{canPrepare && selected.status === 'APPROVED' ? <Button icon={FileCheck2} disabled={busy} onClick={() => finalize(selected)}>Finalize Approved Billing</Button> : null}{canPrepare && selected.status === 'FINALIZED' ? <><Button tone="secondary" onClick={() => setCrediting(selected)}>Create Credit Memo</Button>{role === 'Mich' || role === 'Admin' ? <Button tone="secondary" onClick={() => beginEditor(selected.budget_request, undefined, selected)}>Propose Replacement Billing</Button> : null}</> : null}{role === 'Admin' && selected.status === 'FINALIZED' ? <Button tone="danger" onClick={() => setVoiding(selected)}>Void Finalized Billing</Button> : null}</div>
      </div> : null}
    </Drawer>
    {selected ? createPortal(<div className="print-document-host"><OfficialBillingDocument billing={selected} printCopy /></div>, document.body) : null}

    <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={editing?.replacementOf ? `Replacement for ${editing.replacementOf.reference}` : editing?.billing ? `Edit ${editing.billing.reference}` : 'Prepare Billing'}>
      {editing ? <form className="form-stack billing-form" onSubmit={saveDraft}>
        <div className="callout callout--info"><ShieldCheck size={18} /><span>VAT and CWT are calculated automatically from Administrator-managed tax profiles. Review the preview before finalizing.</span></div>
        {editing.replacementOf ? <label>Replacement reason<textarea name="replacement_reason" rows={2} required minLength={3} placeholder="Explain why a new record is needed. The original will not be overwritten." /></label> : null}
        <div className="form-grid"><label>Issue date<input name="issue_date" type="date" defaultValue={editing.billing?.issue_date ?? new Date().toISOString().slice(0, 10)} required /></label><label>Due date<input name="due_date" type="date" defaultValue={editing.billing?.due_date ?? ''} required /></label><label>Client address<input name="client_address" defaultValue={editing.billing?.client_address ?? editing.replacementOf?.client_address ?? ''} /></label><label>Category<input name="category" defaultValue={editing.billing?.category ?? editing.replacementOf?.category ?? ''} /></label><label>Shipper / Consignee<input name="shipper_consignee" defaultValue={editing.billing?.shipper_consignee ?? editing.replacementOf?.shipper_consignee ?? ''} /></label><label>Container No.<input name="container_number" defaultValue={editing.billing?.container_number ?? editing.replacementOf?.container_number ?? ''} /></label><label>Destination<input name="destination" defaultValue={editing.billing?.destination ?? editing.replacementOf?.destination ?? ''} /></label><label>Vessel<input name="vessel" defaultValue={editing.billing?.vessel ?? editing.replacementOf?.vessel ?? ''} /></label><label>BL / AWB No.<input name="bl_awb_number" defaultValue={editing.billing?.bl_awb_number ?? editing.replacementOf?.bl_awb_number ?? ''} /></label><label>Exchange rate<input name="exchange_rate" type="number" min="0.000001" step="0.000001" defaultValue={editing.billing?.exchange_rate ?? editing.replacementOf?.exchange_rate ?? ''} /></label><label>Measurement<input name="measurement" defaultValue={editing.billing?.measurement ?? editing.replacementOf?.measurement ?? ''} /></label></div>
        <SectionHeader title="Billable line items" description="Classification selects the active VAT and withholding rule. Choose Others and enter a clear description when needed." />
        {lines.map((line, index) => <div className="billing-line-editor" key={index}><label>Description<input value={line.description} onChange={(event) => setLines((current) => current.map((item, row) => row === index ? { ...item, description: event.target.value } : item))} required /></label><label>Classification<select value={line.classification} onChange={(event) => setLines((current) => current.map((item, row) => row === index ? { ...item, classification: event.target.value as BillingLineDraft['classification'] } : item))}><option value="SERVICE_CHARGE">Service charge</option><option value="PASS_THROUGH">Pass-through cost</option></select></label><label>Amount<input type="number" min="0.01" step="0.01" value={line.amount} onChange={(event) => setLines((current) => current.map((item, row) => row === index ? { ...item, amount: event.target.value } : item))} required /></label><Button tone="danger" onClick={() => setLines((current) => current.filter((_, row) => row !== index))}>Remove {line.description}</Button></div>)}
        <Button tone="secondary" icon={Plus} onClick={() => setLines((current) => [...current, { description: 'Others', classification: 'SERVICE_CHARGE', amount: '0' }])}>Add line item</Button>
        <div className="calculation-panel"><div><span>Subtotal</span><strong>{money(taxPreview.subtotal)}</strong></div><div><span>Automatic VAT</span><strong>{money(taxPreview.vat)}</strong></div><div><span>Automatic CWT</span><strong>({money(taxPreview.withholding)})</strong></div><div><span>Net amount due</span><strong>{money(taxPreview.subtotal + taxPreview.vat - taxPreview.withholding)}</strong></div></div>
        <label>Billing notes<textarea name="notes" rows={3} defaultValue={editing.billing?.notes ?? editing.replacementOf?.notes ?? ''} /></label>
        <div className="modal-actions"><Button tone="secondary" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" disabled={busy || lines.length === 0}>{busy ? 'Saving…' : editing.replacementOf ? 'Submit Replacement Proposal to GM' : 'Save Billing Draft'}</Button></div>
      </form> : null}
    </Modal>

    <Modal open={Boolean(crediting)} onClose={() => setCrediting(null)} title="Create Credit Memo">{crediting ? <form className="form-stack" onSubmit={submitCreditMemo}><div className="callout callout--info"><BookOpen size={18} /><span>The original Billing stays unchanged. GM or Administrator approval is required before this reduces the collectible balance.</span></div><label>Credit amount<input name="amount" type="number" min="0.01" max={crediting.adjusted_net_due} step="0.01" required /></label><label>Reason<textarea name="reason" rows={4} minLength={3} required /></label><div className="modal-actions"><Button tone="secondary" onClick={() => setCrediting(null)}>Cancel</Button><Button type="submit" disabled={busy}>Submit for Approval</Button></div></form> : null}</Modal>
    <Modal open={Boolean(voiding)} onClose={() => setVoiding(null)} title="Void finalized Billing">{voiding ? <form className="form-stack" onSubmit={confirmVoid}><div className="callout callout--danger"><AlertCircle size={18} /><span>Only an Administrator can void a finalized record. The original number, amount, actor, date, and reason remain in history.</span></div><label>Void reason<textarea name="reason" rows={4} minLength={3} required /></label><div className="modal-actions"><Button tone="secondary" onClick={() => setVoiding(null)}>Cancel</Button><Button tone="danger" type="submit" disabled={busy}>Void and Preserve History</Button></div></form> : null}</Modal>
  </div>
}

function CollectionsPage({ role, notify }: { role: Role; notify: Notify }) {
  const [rows, setRows] = useState<ApiBilling[] | null>(null)
  const [payments, setPayments] = useState<ApiClientPayment[]>([])
  const [allocating, setAllocating] = useState(false)
  const [amounts, setAmounts] = useState<Record<string, number>>({})
  const [payment, setPayment] = useState(0)
  const [clientId, setClientId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => Promise.all([getReceivables(), getClientPayments()]).then(([items, recorded]) => { setRows(items); setPayments(recorded); if (!clientId && items[0]) setClientId(items[0].budget_request.client.id) }).catch((reason) => { setRows([]); setError(reason instanceof Error ? reason.message : 'Could not load receivables.') })
  useEffect(() => { void load() }, [])
  const total = Object.values(amounts).reduce((sum, value) => sum + (Number(value) || 0), 0)
  const visibleReceivables = (rows ?? []).filter((row) => row.budget_request.client.id === clientId && Number(row.remaining_amount) > 0)
  const totalBilled = (rows ?? []).reduce((sum, row) => sum + Number(row.net_due), 0)
  const totalCollected = (rows ?? []).reduce((sum, row) => sum + Number(row.collected_amount), 0)
  const totalOutstanding = (rows ?? []).reduce((sum, row) => sum + Number(row.remaining_amount), 0)
  const overdue = (rows ?? []).filter((row) => row.aging_days > 0).reduce((sum, row) => sum + Number(row.remaining_amount), 0)
  const canRecord = role === 'Mich' || role === 'Admin'

  async function recordClientPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      await createClientPayment({
        client_id: clientId,
        payment_reference: String(form.get('payment_reference') || '') || null,
        payment_method: String(form.get('payment_method')),
        check_number: String(form.get('check_number') || '') || null,
        check_list_number: String(form.get('check_list_number') || '') || null,
        receiving_bank: String(form.get('receiving_bank')),
        payment_date: String(form.get('payment_date')),
        amount: String(payment),
        notes: String(form.get('notes') || '') || null,
        allocations: Object.entries(amounts).filter(([, amount]) => amount > 0).map(([billing_id, amount]) => ({ billing_id, amount: String(amount) })),
      })
      setAllocating(false); setAmounts({}); setPayment(0); notify(`${money(total)} allocated across ${Object.values(amounts).filter(Boolean).length} Billing records.`, 'success'); load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not record the client payment.') } finally { setBusy(false) }
  }
  return (
    <div className="page-stack">
      <div className="collections-summary"><div><span>Total billed</span><strong>{money(totalBilled)}</strong></div><div><span>Total collected</span><strong>{money(totalCollected)}</strong></div><div><span>Outstanding A/R</span><strong>{money(totalOutstanding)}</strong></div><div><span>Overdue</span><strong className="danger-text">{money(overdue)}</strong></div></div>
      <Card>
        <SectionHeader eyebrow="Collections" title="Billing and SOA tracking" description="Monitor billed amounts, CWT, payments, remaining balances, and aging. Record one receipt or check and allocate it across eligible SOAs." action={canRecord ? <Button icon={Plus} onClick={() => setAllocating(true)}>Add Check or Payment</Button> : undefined} />
        {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}{rows === null ? <EmptyState icon={RefreshCw} title="Loading receivables" detail="Calculating balances and aging from finalized Billing." /> : <div className="table-wrap"><table><thead><tr><th>Budget Ref.</th><th>Client</th><th>SOA No.</th><th>SOA date</th><th>Amount billed</th><th>CWT</th><th>Net due</th><th>Collected</th><th>Remaining</th><th>Status</th><th>Aging</th></tr></thead><tbody>
          {rows.map((row) => <tr key={row.id}><td data-label="Budget Ref."><strong>{row.budget_request.reference}</strong></td><td data-label="Client">{row.budget_request.client.name}</td><td data-label="SOA No.">{row.reference}</td><td data-label="SOA date">{row.issue_date}</td><td data-label="Amount billed" className="number">{money(Number(row.total_amount))}</td><td data-label="CWT" className="number">{money(Number(row.withholding_amount))}</td><td data-label="Net due" className="number">{money(Number(row.adjusted_net_due))}</td><td data-label="Collected" className="number">{money(Number(row.collected_amount))}</td><td data-label="Remaining" className="number number--emphasis">{money(Number(row.remaining_amount))}</td><td data-label="Status"><Status>{row.collection_status}</Status></td><td data-label="Aging"><Status tone={row.aging_days === 0 ? 'info' : row.aging_days <= 30 ? 'warning' : 'danger'}>{row.aging_bucket}</Status></td></tr>)}
        </tbody></table></div>}
      </Card>
      <Card><SectionHeader eyebrow="Check matching" title="Check and payment register" description="Every received payment shows the client, check or transfer reference, bank, covered amount, allocation count, recorder, and date." />{payments.length ? <div className="table-wrap"><table><thead><tr><th>Collection Ref.</th><th>Check / payment ref.</th><th>Check list</th><th>Client</th><th>Bank / account</th><th>Date</th><th>Covered amount</th><th>SOA allocations</th><th>Recorded by</th></tr></thead><tbody>{payments.map((item) => <tr key={item.id}><td><strong>{item.reference}</strong><small>{item.payment_method}</small></td><td>{item.check_number || item.payment_reference}</td><td>{item.check_list_number || '—'}</td><td>{item.client.name}</td><td>{item.receiving_bank}</td><td>{item.payment_date}</td><td className="number">{money(Number(item.amount))}</td><td>{item.allocations.length}</td><td>{item.recorded_by.display_name}</td></tr>)}</tbody></table></div> : <EmptyState icon={CreditCard} title="No checks or payments recorded" detail="The register will populate after Mich records the first client payment." />}</Card>
      <Modal open={allocating} onClose={() => setAllocating(false)} title="New Check or Client Payment">
        <form className="form-stack" onSubmit={recordClientPayment}>
          <div className="form-grid"><label>Client<select value={clientId} onChange={(event) => { setClientId(event.target.value); setAmounts({}) }}>{Array.from(new Map((rows ?? []).map((row) => [row.budget_request.client.id, row.budget_request.client])).values()).map((client) => <option value={client.id} key={client.id}>{client.name}</option>)}</select></label><label>Payment date<input name="payment_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label>Payment method<select name="payment_method" defaultValue="CHECK"><option value="CHECK">Check</option><option value="BANK_TRANSFER">Bank transfer</option><option value="CASH">Cash</option><option value="OTHER">Other</option></select></label><label>Check number<input name="check_number" placeholder="Required when paid by check" /></label><label>Check list No. (pre-numbered)<input name="check_list_number" /></label><label>Bank / account<input name="receiving_bank" required /></label><label>Bank / transfer reference<input name="payment_reference" placeholder="Optional for checks; check number is used" /></label><label>Covered amount<input type="number" min="0.01" step="0.01" value={payment || ''} onChange={(event) => setPayment(Number(event.target.value))} required /></label></div>
          <div className="allocation-head"><span>Select eligible receivables</span><strong>{money(total)} allocated</strong></div>
          <div className="allocation-list">
            {visibleReceivables.map((row) => <label className="allocation-row" key={row.id}><span><strong>{row.reference}</strong><small>{row.budget_request.reference} • {money(Number(row.remaining_amount))} remaining</small></span><input aria-label={`Allocation for ${row.reference}`} type="number" min="0" max={row.remaining_amount} step="0.01" value={amounts[row.id] ?? 0} onChange={(event) => setAmounts((current) => ({ ...current, [row.id]: Number(event.target.value) }))} /></label>)}
          </div>
          <div className={`callout ${total > payment ? 'callout--danger' : payment > 0 && total === payment ? 'callout--success' : 'callout--info'}`}>
            {total > payment || payment <= 0 ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
            <span>{payment <= 0 ? 'Enter the covered amount, then allocate it to one or more eligible Billing records.' : total > payment ? `Reduce allocations by ${money(total - payment)}.` : total === payment ? 'The payment is fully allocated.' : `${money(payment - total)} will remain unapplied.`}</span>
          </div>
          <label>Collection note<textarea name="notes" rows={3} /></label><div className="modal-actions"><Button tone="secondary" onClick={() => setAllocating(false)}>Cancel</Button><Button type="submit" disabled={busy || total > payment || total === 0}>Record and Allocate Payment</Button></div>
        </form>
      </Modal>
    </div>
  )
}

type ExpenseWorkspace = 'OPEX' | 'Marketing' | 'Loan Payment' | 'Other'
type ExpenseAction = 'approve' | 'reject'

const expenseTypeByWorkspace: Record<ExpenseWorkspace, ApiExpenseType> = {
  OPEX: 'OPEX',
  Marketing: 'MARKETING',
  'Loan Payment': 'LOAN_PAYMENT',
  Other: 'OTHER',
}

const expenseStatusLabel: Record<ApiExpenseRequest['status'], string> = {
  DRAFT: 'Draft',
  PENDING_APPROVAL: 'Pending Approval',
  APPROVED: 'Awaiting DCS',
  REJECTED: 'Rejected',
  DISBURSED: 'Disbursed',
  PENDING_VALIDATION: 'Awaiting accounting decision',
  VALIDATED: 'Legacy validated record',
  CANCELLED: 'Cancelled',
}

function ExpensePage({ type, role, notify }: { type: ExpenseWorkspace; role: Role; notify: Notify }) {
  const apiType = expenseTypeByWorkspace[type]
  const isMarketing = type === 'Marketing'
  const isLoan = type === 'Loan Payment'
  const [rows, setRows] = useState<ApiExpenseRequest[] | null>(null)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loanAmounts, setLoanAmounts] = useState({ principal: '', interest: '', fees: '' })
  const [action, setAction] = useState<{ kind: ExpenseAction; item: ApiExpenseRequest } | null>(null)

  const load = () => {
    setError('')
    getExpenseRequests(apiType)
      .then(setRows)
      .catch((reason) => {
        setRows([])
        setError(reason instanceof Error ? reason.message : `Could not load ${type} requests.`)
      })
  }

  useEffect(load, [apiType, type])

  async function createRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const submitNow = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-action') === 'submit'
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      const created = await createExpenseRequest({
        expense_type: apiType,
        request_date: String(form.get('request_date')),
        due_date: isLoan ? String(form.get('due_date')) : null,
        party: String(form.get('party')),
        purpose: String(form.get('purpose')),
        requested_source: null,
        loan_reference: isLoan ? String(form.get('loan_reference')) : null,
        amount: isLoan ? undefined : String(form.get('amount')),
        principal_amount: isLoan ? String(form.get('principal_amount') || '0') : undefined,
        interest_amount: isLoan ? String(form.get('interest_amount') || '0') : undefined,
        penalties_fees_amount: isLoan ? String(form.get('penalties_fees_amount') || '0') : undefined,
      })
      if (submitNow) await submitExpenseRequest(created.id, created.version)
      setCreating(false)
      setLoanAmounts({ principal: '', interest: '', fees: '' })
      notify(submitNow ? `${type} request submitted for Approval.` : `${type} request saved as a draft.`, 'success')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `Could not create the ${type} request.`)
    } finally {
      setBusy(false)
    }
  }

  async function submitDraft(item: ApiExpenseRequest) {
    setBusy(true)
    setError('')
    try {
      await submitExpenseRequest(item.id, item.version)
      notify(`${item.reference} was submitted to GM.`, 'success')
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request could not be submitted.')
    } finally {
      setBusy(false)
    }
  }

  async function completeAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!action) return
    setBusy(true)
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      await decideExpenseRequest(
        action.item.id,
        action.item.version,
        action.kind,
        String(form.get('reason') || ''),
      )
      const messages: Record<ExpenseAction, string> = {
        approve: `${action.item.reference} was approved and sent to DCS.`,
        reject: `${action.item.reference} was returned to the Requester.`,
      }
      notify(messages[action.kind], 'success')
      setAction(null)
      load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The action could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  const loanTotal = Number(loanAmounts.principal || 0) + Number(loanAmounts.interest || 0) + Number(loanAmounts.fees || 0)
  const partyLabel = isLoan ? 'Lender / payee' : isMarketing ? 'Campaign / payee' : 'Payee'

  function rowActions(item: ApiExpenseRequest) {
    if ((role === 'Mich' || role === 'Admin') && (item.status === 'DRAFT' || item.status === 'REJECTED')) {
      return <Button tone="secondary" disabled={busy} onClick={() => submitDraft(item)}>Submit for Approval</Button>
    }
    if ((role === 'GM' || role === 'Admin') && item.status === 'PENDING_APPROVAL') {
      return <div className="table-actions"><Button tone="secondary" onClick={() => setAction({ kind: 'approve', item })}>Approve</Button><Button tone="danger" onClick={() => setAction({ kind: 'reject', item })}>Reject</Button></div>
    }
    return <Button tone="ghost" onClick={() => notify(`${item.reference} is ${expenseStatusLabel[item.status].toLowerCase()}.`, 'info')}>View details</Button>
  }

  return (
    <div className="page-stack">
      <Card>
        <SectionHeader
          eyebrow={`${type} workspace`}
          title={`${type} requests and ledger`}
          description={isLoan ? 'Principal, optional interest, and optional fees stay visible through approval and payment.' : isMarketing ? 'Campaign and promotional expenses remain distinct from operating expenses.' : type === 'Other' ? 'Use Other only when OPEX, Marketing, and Loan Payment do not describe the request.' : 'Operating expenses remain distinct from shipment budgets and Marketing.'}
          action={(role === 'Mich' || role === 'Admin') ? <Button icon={Plus} onClick={() => setCreating(true)}>Create {type} Request</Button> : undefined}
        />
        {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
        {rows === null ? <EmptyState icon={RefreshCw} title="Loading requests" detail="Opening the protected ledger." /> : rows.length === 0 ? <EmptyState icon={ReceiptText} title={`No ${type} requests yet`} detail="Create a draft or wait for the daily demo scenario to be loaded." /> : (
          <div className="table-wrap"><table><thead><tr><th>Reference</th><th>{partyLabel}</th>{isLoan ? <th>Loan reference / due</th> : null}<th>Purpose</th><th>Requester</th><th>Amount</th><th>Status</th><th></th></tr></thead><tbody>
            {rows.map((row) => <tr key={row.id}>
              <td data-label="Reference"><strong>{row.reference}</strong></td>
              <td data-label={partyLabel}>{row.party}</td>
              {isLoan ? <td data-label="Loan reference / due"><strong>{row.loan_reference}</strong><br /><small>Due {row.due_date ? new Date(`${row.due_date}T00:00:00`).toLocaleDateString('en-PH', { dateStyle: 'medium' }) : 'not set'}</small></td> : null}
              <td data-label="Purpose">{row.purpose}</td>
              <td data-label="Requester">{row.requester.display_name}</td>
              <td data-label="Amount" className="number">{money(Number(row.amount))}</td>
              <td data-label="Status"><Status>{expenseStatusLabel[row.status]}</Status></td>
              <td>{rowActions(row)}</td>
            </tr>)}
          </tbody></table></div>
        )}
      </Card>
      <div className="module-lane"><div><UserRound size={18} /><span><small>Step 1</small><strong>Mich creates</strong></span></div><ArrowRight /><div><ClipboardCheck size={18} /><span><small>Step 2</small><strong>GM decides</strong></span></div><ArrowRight /><div><HandCoins size={18} /><span><small>Step 3</small><strong>DCS pays</strong></span></div><ArrowRight /><div><Gauge size={18} /><span><small>Step 4</small><strong>Ledger reports</strong></span></div></div>

      <Modal title={`Create ${type} Request`} open={creating} onClose={() => setCreating(false)}>
        <form className="form-stack" onSubmit={createRequest}>
          <div className="callout callout--info"><ShieldCheck size={18} /><span>This creates a draft Request for Payment. Save it for later, or submit it for approval when the details are complete.</span></div>
          <div className="form-grid"><label>Request date<input name="request_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label>{isLoan ? <label>Payment due date<input name="due_date" type="date" required /></label> : null}</div>
          <label>{partyLabel}<input name="party" placeholder={isLoan ? 'Example: Demo Development Bank' : 'Organization or person to be paid'} required /></label>
          {isLoan ? <label>Loan account / reference<input name="loan_reference" placeholder="Example: DEMO-LOAN-2026-004" required /></label> : null}
          {isLoan ? <><div className="form-grid"><label>Principal or known amount<input name="principal_amount" type="number" min="0" step="0.01" value={loanAmounts.principal} onChange={(event) => setLoanAmounts({ ...loanAmounts, principal: event.target.value })} required /></label><label>Interest amount <small>(optional if unknown)</small><input name="interest_amount" type="number" min="0" step="0.01" value={loanAmounts.interest} onChange={(event) => setLoanAmounts({ ...loanAmounts, interest: event.target.value })} /></label><label>Penalties / fees <small>(optional)</small><input name="penalties_fees_amount" type="number" min="0" step="0.01" value={loanAmounts.fees} onChange={(event) => setLoanAmounts({ ...loanAmounts, fees: event.target.value })} /></label><div className="calculated-field"><span>Known amount requested</span><strong>{money(loanTotal)}</strong><small>Unknown interest can be reconciled later; do not guess.</small></div></div></> : <label>Requested amount<input name="amount" type="number" min="0.01" step="0.01" required /></label>}
          <label>Purpose and payment description<textarea name="purpose" rows={4} placeholder="Explain what this payment covers." required /></label>
          <div className="modal-actions"><Button tone="ghost" onClick={() => setCreating(false)}>Cancel</Button><Button tone="secondary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save as Draft'}</Button><button className="button button--primary" type="submit" data-action="submit" disabled={busy}>Submit for Approval</button></div>
        </form>
      </Modal>

      <Modal title={action ? `${action.item.reference} · ${action.kind}` : 'Request action'} open={Boolean(action)} onClose={() => setAction(null)}>
        {action ? <form className="form-stack" onSubmit={completeAction}>
          <div className="summary-grid summary-grid--two"><div><span>Payee</span><strong>{action.item.party}</strong><small>{action.item.purpose}</small></div><div><span>Total</span><strong>{money(Number(action.item.amount))}</strong><small>{expenseStatusLabel[action.item.status]}</small></div></div>
          <label>{action.kind === 'reject' ? 'Rejection reason' : 'Decision note'}<textarea name="reason" rows={4} required={action.kind === 'reject'} placeholder={action.kind === 'reject' ? 'Explain what Mich must correct.' : 'Optional approval note'} /></label>
          <div className="modal-actions"><Button tone="ghost" onClick={() => setAction(null)}>Cancel</Button><Button type="submit" tone={action.kind === 'reject' ? 'danger' : 'primary'} disabled={busy}>{busy ? 'Saving…' : action.kind === 'approve' ? 'Confirm Approval' : 'Return to Mich'}</Button></div>
        </form> : null}
      </Modal>
    </div>
  )
}

function PaymentRequestsPage({ role, notify }: { role: Role; notify: Notify }) {
  const [type, setType] = useState<ExpenseWorkspace>('OPEX')
  return <div className="page-stack"><div className="explanation-banner"><span><ReceiptText size={20} /></span><div><strong>One familiar place for non-shipment payments.</strong><p>Choose OPEX, Marketing, Loan Payment, or Other. Mich creates the request, GM decides, and DCS chooses the actual funding source when paying.</p></div></div><div className="tabbed-heading" aria-label="Payment request type">{(['OPEX', 'Marketing', 'Loan Payment', 'Other'] as ExpenseWorkspace[]).map((item) => <button className={type === item ? 'active' : ''} onClick={() => setType(item)} key={item}>{item}</button>)}</div><ExpensePage type={type} role={role} notify={notify} /></div>
}

function AccountingPageLegacy() {
  return (
    <div className="page-stack">
      <div className="kpi-grid kpi-grid--four"><Card className="kpi"><div className="kpi__top"><span>Accounting events</span><BookOpen size={17} /></div><strong>284</strong><p>July 2026</p></Card><Card className="kpi"><div className="kpi__top"><span>Debits</span><ArrowRight size={17} /></div><strong>₱3.84M</strong><p>Posted activity</p></Card><Card className="kpi"><div className="kpi__top"><span>Credits</span><ArrowRight size={17} /></div><strong>₱3.84M</strong><p>Balanced</p></Card><Card className="kpi kpi--warning"><div className="kpi__top"><span>Exceptions</span><AlertCircle size={17} /></div><strong>2</strong><p>Need account mapping</p></Card></div>
      <Card>
        <SectionHeader eyebrow="Controlled accounting view" title="Accounting activity" description="Every system event links back to the operational record that created it." action={<Button tone="ghost" icon={Download} onClick={() => downloadCsv('pimascor-accounting-export.csv', [['Event', 'Date', 'Source record', 'Description', 'Debit', 'Credit', 'Status'], ['AE-0726-0284', '2026-07-20', 'REL-BR-0726-159', 'Budget payment recorded', 76300, 76300, 'Posted'], ['AE-0726-0283', '2026-07-20', 'PAY-0726-044', 'Client payment received', 50000, 50000, 'Posted']])}>Export Accounting CSV</Button>} />
        <div className="table-wrap"><table><thead><tr><th>Entry</th><th>Date</th><th>Source event</th><th>Description</th><th>Debit</th><th>Credit</th><th>Status</th></tr></thead><tbody>
          {[
            ['JE-0726-0284', 'Jul 20, 2026', 'REL-BR-0726-159', 'Shipment budget released', 76300, 76300, 'Posted'],
            ['JE-0726-0283', 'Jul 20, 2026', 'PAY-0726-044', 'Client payment received', 50000, 50000, 'Posted'],
            ['JE-0726-0282', 'Jul 20, 2026', 'OPEX-0726-031', 'OPEX disbursement pending mapping', 24900, 24900, 'Needs review'],
          ].map((row) => <tr key={String(row[0])}><td data-label="Entry"><strong>{row[0]}</strong></td><td data-label="Date">{row[1]}</td><td data-label="Source event"><strong>{row[2]}</strong></td><td data-label="Description">{row[3]}</td><td data-label="Debit" className="number">{money(Number(row[4]))}</td><td data-label="Credit" className="number">{money(Number(row[5]))}</td><td data-label="Status"><Status>{row[6]}</Status></td></tr>)}
        </tbody></table></div>
      </Card>
    </div>
  )
}

function AccountingPage({ role }: { role: Role }) {
  const [billing, setBilling] = useState<ApiBilling[]>([])
  const [payments, setPayments] = useState<ApiClientPayment[]>([])
  const [archives, setArchives] = useState<ApiDataExport[]>([])
  const [backups, setBackups] = useState<ApiBackupCatalogItem[]>([])
  const [error, setError] = useState('')
  const [requestingArchive, setRequestingArchive] = useState(false)
  const [archiveMessage, setArchiveMessage] = useState('')
  const canViewBackups = role === 'Admin' || role === 'DCS'
  const refresh = useCallback(() => {
    Promise.all([getBilling(), getClientPayments(), getDataExports(), canViewBackups ? getBackups() : Promise.resolve([])])
      .then(([bills, receipts, exportRows, backupRows]) => { setBilling(bills); setPayments(receipts); setArchives(exportRows); setBackups(backupRows) })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load accounting export data.'))
  }, [canViewBackups])
  useEffect(() => { refresh() }, [refresh])
  const finalizedBilling = useMemo(() => billing.filter((item) => item.status === 'FINALIZED'), [billing])
  const billed = finalizedBilling.reduce((sum, item) => sum + Number(item.adjusted_net_due), 0)
  const collected = payments.reduce((sum, item) => sum + Number(item.amount), 0)
  const outstanding = finalizedBilling.reduce((sum, item) => sum + Number(item.remaining_amount), 0)
  const billingCsv = useMemo<(string | number)[][]>(() => [
    ['Billing reference', 'Issue date', 'Due date', 'Client', 'Gross amount', 'VAT', 'Withholding', 'Net due', 'Collected', 'Outstanding', 'Collection status'],
    ...finalizedBilling.map((item) => [item.reference, item.issue_date, item.due_date ?? '', item.budget_request.client.name, item.total_amount, item.vat_amount, item.withholding_amount, item.adjusted_net_due, item.collected_amount, item.remaining_amount, item.collection_status]),
  ], [finalizedBilling])
  const collectionsCsv = useMemo<(string | number)[][]>(() => [
    ['Collection reference', 'Payment date', 'Client', 'Bank', 'Method', 'External reference', 'Received amount', 'Allocated amount', 'Unallocated amount'],
    ...payments.map((item) => {
      const allocated = item.allocations.reduce((sum, allocation) => sum + Number(allocation.amount), 0)
      return [item.reference, item.payment_date, item.client.name, item.receiving_bank, item.payment_method, item.payment_reference, item.amount, allocated, Number(item.amount) - allocated]
    }),
  ], [payments])
  const requestArchive = () => {
    setRequestingArchive(true)
    setArchiveMessage('')
    requestDataExport()
      .then((archive) => { setArchives((current) => [archive, ...current]); setArchiveMessage('Archive request accepted. It is being prepared; the requester will receive an email only after it is ready.') })
      .catch((reason) => setArchiveMessage(reason instanceof Error ? reason.message : 'Could not request the local records archive.'))
      .finally(() => setRequestingArchive(false))
  }
  const downloadArchive = (archive: ApiDataExport) => {
    downloadDataExport(archive.id)
      .then(({ blob, fileName }) => {
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = fileName
        link.click()
        URL.revokeObjectURL(url)
        setArchiveMessage('Download started. Store the archive only on encrypted, approved media.')
      })
      .catch((reason) => setArchiveMessage(reason instanceof Error ? reason.message : 'Could not download the archive.'))
  }
  return <div className="page-stack">
    {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
    <div className="kpi-grid kpi-grid--four"><Card className="kpi"><div className="kpi__top"><span>Finalized billings</span><FileText size={17} /></div><strong>{finalizedBilling.length}</strong><p>Exported from the Billing module</p></Card><Card className="kpi"><div className="kpi__top"><span>Net billed</span><ArrowRight size={17} /></div><strong>{money(billed)}</strong><p>Operational receivable, not a journal debit</p></Card><Card className="kpi"><div className="kpi__top"><span>Collections received</span><ArrowRight size={17} /></div><strong>{money(collected)}</strong><p>Exported from Client Payments</p></Card><Card className="kpi"><div className="kpi__top"><span>Outstanding</span><ShieldCheck size={17} /></div><strong>{money(outstanding)}</strong><p>Requires accountant review and mapping</p></Card></div>
    <Card><SectionHeader eyebrow="Administrator accounting view" title="Module-specific accounting CSVs" description="The earlier combined debit/credit view was not a balanced journal. Billing and collections now export separately so the accountant can map each source module to the approved chart of accounts." action={<div className="action-row"><Button tone="ghost" icon={Download} onClick={() => downloadCsv('pimascor-billing.csv', billingCsv)}>Billing CSV</Button><Button tone="ghost" icon={Download} onClick={() => downloadCsv('pimascor-collections.csv', collectionsCsv)}>Collections CSV</Button></div>} />
      <div className="callout callout--info"><BookOpen size={18} /><span>These are traceable operational records, not a substitute for a signed-off general-ledger posting. The destination accounting system must supply the accounts, tax treatment, and balancing entries.</span></div>
      <div className="table-wrap"><table><thead><tr><th>Billing reference</th><th>Issue date</th><th>Client</th><th>Net due</th><th>Collected</th><th>Outstanding</th><th>Status</th></tr></thead><tbody>{finalizedBilling.map((item) => <tr key={item.id}><td data-label="Billing reference"><strong>{item.reference}</strong></td><td data-label="Issue date">{item.issue_date}</td><td data-label="Client">{item.budget_request.client.name}</td><td data-label="Net due" className="number">{money(Number(item.adjusted_net_due))}</td><td data-label="Collected" className="number">{money(Number(item.collected_amount))}</td><td data-label="Outstanding" className="number">{money(Number(item.remaining_amount))}</td><td data-label="Status"><Status>{item.collection_status}</Status></td></tr>)}</tbody></table></div>
    </Card>
    <Card><SectionHeader eyebrow="Administrator-only recovery copy" title="Complete local records archive" description="Creates one ZIP containing UTF-8 CSVs for operational modules plus the original uploaded files. Passwords, sessions, and login codes are deliberately excluded. The archive stays private, is available only while signed in, and is deleted one hour after completion." action={<Button icon={Archive} disabled={requestingArchive} onClick={requestArchive}>{requestingArchive ? 'Requesting archive…' : 'Request local archive'}</Button>} />
      {archiveMessage ? <div className="callout callout--info"><ShieldCheck size={18} /><span>{archiveMessage}</span></div> : null}
      <div className="callout callout--warning"><Clock3 size={18} /><span>Limit: two archive requests per Philippine calendar week for the whole organization. This limits compute and storage use; it is not a limit on retrying a permitted download during its one-hour availability window.</span></div>
      {archives.length ? <div className="table-wrap"><table><thead><tr><th>Requested</th><th>Requested by</th><th>Status</th><th>Available until</th><th>Archive</th></tr></thead><tbody>{archives.map((archive) => <tr key={archive.id}><td data-label="Requested">{activityTime(archive.requested_at)}</td><td data-label="Requested by">{archive.requested_by.display_name}</td><td data-label="Status"><Status>{archive.status}</Status></td><td data-label="Available until">{archive.expires_at ? activityTime(archive.expires_at) : '—'}</td><td data-label="Archive">{archive.status === 'READY' ? <Button tone="secondary" icon={Download} onClick={() => downloadArchive(archive)}>Download {archive.size_bytes ? `(${formatBytes(archive.size_bytes)})` : ''}</Button> : archive.status === 'FAILED' ? archive.error_message ?? 'Could not create archive' : 'Email is sent when ready'}</td></tr>)}</tbody></table></div> : <EmptyState icon={Archive} title="No local archive requested" detail="When needed, request a complete recovery copy here. The archive is never made public." />}
      {canViewBackups ? <Card><SectionHeader eyebrow="Production recovery status" title="Encrypted backup history" description="Each entry confirms a successful encrypted backup to Backblaze B2. The local staging copy is removed after verification; restoration is deliberately available only through the owner’s CLI runbook." />
      <div className="callout callout--info"><ShieldCheck size={18} /><span>Backups are encrypted at rest. Daily, weekly, and monthly classes are kept operationally; yearly snapshots are retained up to five years. Quarterly or semiannual legal archives require an approved immutable copy. Admin and DCS can review this catalog, but neither role can restore or replace production data from the web app.</span></div>
      {backups.length ? <div className="table-wrap"><table><thead><tr><th>Completed</th><th>Coverage</th><th>Retention</th><th>Verification</th></tr></thead><tbody>{backups.map((backup) => <tr key={backup.id}><td data-label="Completed">{activityTime(backup.completed_at)}</td><td data-label="Coverage">{backup.scope}</td><td data-label="Retention">{backup.retention_class}</td><td data-label="Verification"><Status tone="success">Completed</Status></td></tr>)}</tbody></table></div> : <EmptyState icon={ShieldCheck} title="No completed backup is recorded yet" detail="The catalog will appear after the first successful production backup run." />}
    </Card> : null}
    </Card>
  </div>
}

function ClientsDocumentsPage({ role }: { role: Role }) {
  const [tab, setTab] = useState<'clients' | 'documents'>('clients')
  const [clients, setClients] = useState<ApiClient[]>([])
  const [documents, setDocuments] = useState<ApiDocument[] | null>(null)
  const [documentSearch, setDocumentSearch] = useState('')
  const [error, setError] = useState('')
  const [viewingDocument, setViewingDocument] = useState<ConfidentialDocumentItem | null>(null)

  useEffect(() => {
    Promise.all([getClients(), getDocuments()])
      .then(([clientRows, documentRows]) => { setClients(clientRows); setDocuments(documentRows) })
      .catch((reason) => { setDocuments([]); setError(reason instanceof Error ? reason.message : 'Could not load clients and documents.') })
  }, [])

  return (
    <div className="page-stack">
      <div className="tabbed-heading" role="tablist" aria-label="Clients and documents"><button className={tab === 'clients' ? 'active' : ''} type="button" role="tab" aria-selected={tab === 'clients'} onClick={() => setTab('clients')}>Clients</button><button className={tab === 'documents' ? 'active' : ''} type="button" role="tab" aria-selected={tab === 'documents'} onClick={() => setTab('documents')}>Document Library</button></div>
      {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
      {tab === 'clients' ? <Card>
        <SectionHeader eyebrow="Reference records" title="Clients" description="Billing identity, contacts, active shipments, and open receivables. Client editing is Administrator-only and scheduled for the production administration release." />
        <div className="client-grid">
          {clients.map((client) => <div className="client-card" key={client.id}><span className="client-card__mark">{client.code.slice(0, 3).toUpperCase()}</span><span><strong>{client.name}</strong><small>{client.code}</small><small>Available for Budget Requests and Billing</small></span><ShieldCheck size={18} /></div>)}
        </div>
      </Card> : <Card>
        <SectionHeader eyebrow="Private Backblaze B2" title="Document Library" description="Signed quotations, payment proofs, receipts, and variance evidence remain linked to their business reference and audit trail." />
        <div className="callout callout--info"><ShieldCheck size={18} /><span>All roles may open authorized supporting files. Downloads are restricted to Mich, GM, DCS, and Admin and each download is recorded.</span></div>
        <label className="search-field"><Search size={18} /><input value={documentSearch} onChange={(event) => setDocumentSearch(event.target.value)} aria-label="Search documents" placeholder="Search filename, client, reference, or document type" /></label>
        {documents === null ? <EmptyState icon={RefreshCw} title="Loading documents" detail="Opening the protected document index." /> : documents.length === 0 ? <EmptyState icon={FolderOpen} title="No documents uploaded" detail="Signed quotations, payment evidence, receipts, and variance proof will be indexed automatically." /> : (() => {
          const query = documentSearch.trim().toLowerCase()
          const visible = query ? documents.filter((item) => [item.file_name, item.reference, item.client_name, item.kind].some((value) => value.toLowerCase().includes(query))) : documents
          return visible.length ? <div className="document-list">{visible.map((item) => <DocumentItem key={item.id} name={item.file_name} meta={`${item.kind.replaceAll('_', ' ')} • ${item.reference} • ${item.client_name} • ${item.size_bytes ? formatBytes(item.size_bytes) : 'Demo metadata only'}`} available={item.available} onOpen={() => setViewingDocument({ id: item.id, name: item.file_name, contentType: item.content_type })} />)}</div> : <EmptyState icon={Search} title="No matching documents" detail="Try a filename, client, shipment, payment, or transaction reference." />
        })()}
      </Card>}
      <ConfidentialDocumentViewer item={viewingDocument} onClose={() => setViewingDocument(null)} canDownload={!isDemoBuild && ['Admin', 'GM', 'DCS', 'Mich'].includes(role)} />
    </div>
  )
}

const activityCategoryMeta: Record<ApiActivityCategory, { label: string; color: string }> = {
  SECURITY: { label: 'Security', color: '#b42318' },
  TRANSACTION: { label: 'Money movement', color: '#157347' },
  WORKFLOW: { label: 'Workflow', color: '#175cd3' },
  CONFIGURATION: { label: 'Configuration', color: '#8b6205' },
  DOCUMENT: { label: 'Documents', color: '#7f56d9' },
  INCIDENT: { label: 'App problems', color: '#d92d20' },
}

function activityTime(value: string) {
  return new Intl.DateTimeFormat('en-PH', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Manila',
  }).format(new Date(value))
}

function activityRole(value: ApiUser['role']) {
  return value === 'MICH' ? 'Mich' : value === 'REQUESTER' ? 'Requester' : value
}

function AdminActivityMonitor() {
  const [activity, setActivity] = useState<ApiAdminActivity | null>(null)
  const [days, setDays] = useState(30)
  const [category, setCategory] = useState<ApiActivityCategory | ''>('')
  const [includeAdmin, setIncludeAdmin] = useState(false)
  const [searchDraft, setSearchDraft] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getAdminActivity({ days, includeAdmin, category: category || undefined, search })
      .then((result) => { if (active) setActivity(result) })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load staff activity.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [days, includeAdmin, category, search])

  const maxDay = Math.max(1, ...(activity?.timeline.map((point) => point.total) ?? [1]))
  const totalCategories = Math.max(1, activity?.categories.reduce((sum, item) => sum + item.count, 0) ?? 1)
  let ringCursor = 0
  const ringStops = (activity?.categories ?? []).map((item) => {
    const start = ringCursor
    ringCursor += (item.count / totalCategories) * 100
    return `${activityCategoryMeta[item.category].color} ${start}% ${ringCursor}%`
  }).join(', ')

  return <div className="admin-monitor">
    <section className="monitor-hero">
      <div className="monitor-hero__copy">
        <span className="monitor-live"><i /> Bridge PH supervision</span>
        <h2>See the operational story as it happens.</h2>
        <p>Every sign-in, approval, money movement, configuration change, and document action is attributable without recording passwords, email codes, or private screen activity.</p>
      </div>
      <div className="monitor-hero__seal" aria-hidden="true"><ShieldCheck size={30} /><span>Admin only</span></div>
    </section>

    <Card className="monitor-filters">
      <form onSubmit={(event) => { event.preventDefault(); setSearch(searchDraft.trim()) }}>
        <label>Time range<select value={days} onChange={(event) => setDays(Number(event.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option></select></label>
        <label>Activity type<select value={category} onChange={(event) => setCategory(event.target.value as ApiActivityCategory | '')}><option value="">All activity</option>{Object.entries(activityCategoryMeta).map(([value, meta]) => <option value={value} key={value}>{meta.label}</option>)}</select></label>
        <label className="monitor-search">Find staff or reference<span><Search size={17} /><input value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Name, username, or reference" /></span></label>
        <Button type="submit" tone="secondary">Apply</Button>
        <label className="switch-field"><input type="checkbox" checked={includeAdmin} onChange={(event) => setIncludeAdmin(event.target.checked)} /><span><i /></span><b>Include Admin activity</b><HelpTip label="Why Admin activity is available">Staff activity is the default view. Admin actions remain recorded because privileged actions must never become an audit blind spot.</HelpTip></label>
      </form>
    </Card>

    {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
    {loading && !activity ? <Card><EmptyState icon={RefreshCw} title="Opening the activity monitor" detail="Building a privacy-minimized view of recent staff actions." /></Card> : null}
    {activity ? <>
      <div className="monitor-kpis">
        <Card className="monitor-kpi"><span className="monitor-kpi__icon monitor-kpi__icon--blue"><Activity size={20} /></span><div><small>Recorded events</small><strong>{activity.total_events.toLocaleString()}</strong><p>{includeAdmin ? 'Staff and Admin' : 'Staff only'}</p></div></Card>
        <Card className="monitor-kpi"><span className="monitor-kpi__icon monitor-kpi__icon--red"><ShieldCheck size={20} /></span><div><small>Review signals</small><strong>{activity.sensitive_events.toLocaleString()}</strong><p>Warnings and critical changes</p></div></Card>
        <Card className="monitor-kpi"><span className="monitor-kpi__icon monitor-kpi__icon--green"><CircleDollarSign size={20} /></span><div><small>Money movements</small><strong>{activity.transaction_events.toLocaleString()}</strong><p>Payments, billing, and collections</p></div></Card>
        <Card className="monitor-kpi"><span className="monitor-kpi__icon monitor-kpi__icon--gold"><UsersRound size={20} /></span><div><small>Active people</small><strong>{activity.active_users.toLocaleString()}</strong><p>With recorded activity</p></div></Card>
      </div>

      <div className="monitor-chart-grid">
        <Card className="monitor-chart">
          <SectionHeader eyebrow="Activity pulse" title={`Last ${activity.range_days} days`} description="Daily volume in Philippine time. Select a bar to read its exact count." />
          <div className="monitor-bars" role="img" aria-label={`Daily activity for the last ${activity.range_days} days`}>
            {activity.timeline.map((point, index) => <button type="button" className="monitor-bar" key={point.date} title={`${point.date}: ${point.total} events`} aria-label={`${point.date}: ${point.total} events`}>
              <span style={{ height: `${Math.max(point.total ? 10 : 2, (point.total / maxDay) * 100)}%`, animationDelay: `${Math.min(index, 20) * 25}ms` }} />
              {(activity.range_days <= 7 || index === 0 || index === activity.timeline.length - 1) ? <small>{new Intl.DateTimeFormat('en-PH', { month: 'short', day: 'numeric', timeZone: 'Asia/Manila' }).format(new Date(`${point.date}T12:00:00+08:00`))}</small> : null}
            </button>)}
          </div>
        </Card>
        <Card className="monitor-category-card">
          <SectionHeader eyebrow="Control coverage" title="What is being monitored" description="Business metadata only, grouped into plain-language categories." />
          <div className="monitor-category">
            <div className="category-ring" style={{ background: ringStops ? `conic-gradient(${ringStops})` : '#e7ebf4' }} role="img" aria-label={`${activity.total_events} categorized events`}><span><strong>{activity.total_events}</strong><small>events</small></span></div>
            <div className="category-legend">{activity.categories.map((item) => <div key={item.category}><i style={{ background: activityCategoryMeta[item.category].color }} /><span>{activityCategoryMeta[item.category].label}</span><strong>{item.count}</strong></div>)}</div>
          </div>
        </Card>
      </div>

      <div className="monitor-detail-grid">
        <Card>
          <SectionHeader eyebrow="People" title="Most active staff" description="Activity counts are operational signals, not productivity scores." />
          {activity.actors.length ? <div className="actor-list">{activity.actors.slice(0, 6).map((item) => <div className="actor-row" key={item.actor.id}><span className="actor-avatar">{item.actor.display_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('')}</span><span><strong>{item.actor.display_name}</strong><small>@{item.actor.username} • {activityRole(item.actor.role)}</small></span><span><strong>{item.total}</strong><small>{item.sensitive ? `${item.sensitive} to review` : 'No review signals'}</small></span></div>)}</div> : <EmptyState icon={UsersRound} title="No matching staff activity" detail="Change the filters or wait for a workflow action." />}
        </Card>
        <Card>
          <SectionHeader eyebrow="Privacy boundary" title="Useful oversight, not surveillance" description="The monitor records what happened in the business system and who performed it." />
          <div className="monitor-boundaries"><div><CheckCircle2 size={18} /><span><strong>Included</strong><small>Sign-ins, approvals, payments, document actions, configuration changes, references, and timestamps.</small></span></div><div><XCircle size={18} /><span><strong>Never captured here</strong><small>Passwords, email codes, secret keys, full bank details, keystrokes, screenshots, webcams, or unrelated personal activity.</small></span></div></div>
        </Card>
      </div>

      <Card className="event-log">
        <SectionHeader eyebrow="Attributable history" title="Recent activity" description="Newest first. Each event keeps the actor, business object, timestamp, and correlation reference needed for review." action={loading ? <span className="monitor-refresh"><RefreshCw size={16} /> Refreshing</span> : activity.last_event_at ? <span className="monitor-refresh"><Clock3 size={16} /> Latest {activityTime(activity.last_event_at)}</span> : null} />
        {activity.truncated ? <div className="callout callout--warning"><AlertCircle size={18} /><span>This view reached its safety cap. Narrow the time range or search to review a smaller set.</span></div> : null}
        {activity.events.length ? <div className="event-list">{activity.events.map((event) => <article className={`event-row event-row--${event.severity.toLowerCase()}`} key={event.id}>
          <span className="event-row__marker">{event.category === 'TRANSACTION' ? <CircleDollarSign size={17} /> : event.category === 'SECURITY' ? <ShieldCheck size={17} /> : event.category === 'DOCUMENT' ? <FileText size={17} /> : event.category === 'INCIDENT' ? <AlertCircle size={17} /> : <Activity size={17} />}</span>
          <div><span className="event-row__headline"><strong>{event.label}</strong><Status tone={event.severity === 'CRITICAL' ? 'danger' : event.severity === 'WARNING' ? 'warning' : event.severity === 'SUCCESS' ? 'success' : 'info'}>{event.severity === 'CRITICAL' ? 'Review' : event.severity.toLowerCase()}</Status></span><p>{event.actor ? `${event.actor.display_name} • ${activityRole(event.actor.role)}` : 'System event'}{event.reason ? ` • ${event.reason}` : ''}</p><small>{event.entity_type.replaceAll('_', ' ')} • {event.entity_id} • Correlation {event.correlation_id ?? 'not available'}</small></div>
          <time dateTime={event.occurred_at}>{activityTime(event.occurred_at)}</time>
        </article>)}</div> : <EmptyState icon={Activity} title="No matching activity" detail="Adjust the filters to widen this operational view." />}
      </Card>
    </> : null}
  </div>
}

function AdminPage({
  role,
  notify,
  onPreviewRole,
}: {
  role: Role
  notify: Notify
  onPreviewRole: (role: Role) => void
}) {
  const [tab, setTab] = useState<'activity' | 'controls'>('controls')
  const [sources, setSources] = useState<ApiFundingSource[]>([])
  const [profiles, setProfiles] = useState<ApiTaxProfile[]>([])
  const [error, setError] = useState('')
  const load = () => Promise.all([getFundingSources(), getTaxProfiles()]).then(([funding, tax]) => { setSources(funding); setProfiles(tax) }).catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load Administration settings.'))
  useEffect(() => { void load() }, [])

  async function addSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    try { await createFundingSource(String(form.get('name'))); formElement.reset(); notify('Funding source added for DCS payment selection.', 'success'); void load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not add the funding source.') }
  }

  async function deactivateSource(source: ApiFundingSource) {
    try { await updateFundingSource(source.id, { active: false }); notify(`${source.name} deactivated. Historical transactions remain unchanged.`, 'success'); void load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not update the funding source.') }
  }

  async function addProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    try {
      await createTaxProfile({
        name: String(form.get('name')),
        classification: String(form.get('classification')) as ApiTaxProfile['classification'],
        vat_rate: String(Number(form.get('vat_percent')) / 100),
        withholding_rate: String(Number(form.get('withholding_percent')) / 100),
      })
      formElement.reset(); notify('Tax profile activated. New Billing drafts will use it automatically.', 'success'); void load()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save the tax profile.') }
  }

  if (tab === 'activity') return <div className="page-stack">
    <div className="tabbed-heading" role="tablist" aria-label="Administration"><button className="active" type="button" role="tab" aria-selected="true">Activity Monitor</button><button type="button" role="tab" aria-selected="false" onClick={() => setTab('controls')}>Controls</button></div>
    <AdminActivityMonitor />
  </div>

  return <div className="page-stack">
    <div className="tabbed-heading" role="tablist" aria-label="Administration"><button type="button" role="tab" aria-selected="false" onClick={() => setTab('activity')}>Activity Monitor</button><button className="active" type="button" role="tab" aria-selected="true">Controls</button></div>
    {error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null}
    <Card className="admin-role-control">
      <SectionHeader eyebrow="Administrator workspace access" title="Choose a workspace to operate" description="Enter any staff workspace and perform its real workflow actions. Your authenticated Admin identity remains visible in every security and audit record." />
      <div className="role-picker">
        {documentedRoles.map((item) => {
          const RoleIcon = roleWorkspaceIcons[item]
          const active = role === item
          return <button className={active ? 'active' : ''} key={item} type="button" onClick={() => onPreviewRole(item)} aria-pressed={active}>
            <span className="role-picker__icon"><RoleIcon size={22} /></span>
            <span className="role-picker__copy">
              <strong>{item}</strong>
              <small>{roleDescriptions[item]}</small>
            </span>
            <span className="role-picker__action">{active ? <><Check size={16} /> Current workspace</> : <>Enter workspace <ArrowRight size={16} /></>}</span>
          </button>
        })}
      </div>
      <p className="role-picker__note"><ShieldCheck size={17} /><span><strong>Secure operational access</strong> This is not a read-only preview. Every action remains attributable to the signed-in Administrator.</span></p>
    </Card>
    <div className="admin-grid">
      <Card><SectionHeader eyebrow="DCS payment controls" title="Approved banks and funding sources" description="Only Admin can maintain this list. DCS can select an active source but cannot type or alter one during payment." /><div className="callout callout--info"><ShieldCheck size={18} /><span>Use a recognizable display name and, if needed, only the masked last four digits. Never place a full account number in this list. Every change is audited; production should separate source maintenance from payment execution wherever staffing permits.</span></div><form className="inline-form" onSubmit={addSource}><label><span className="sr-only">New funding source</span><input name="name" placeholder="Example: BDO Operating •••• 4821" minLength={2} required /></label><Button type="submit" icon={Plus}>Add Approved Source</Button></form><div className="settings-list">{sources.map((source) => <div key={source.id}><span><Landmark size={18} /><strong>{source.name}</strong></span><Button tone="danger" onClick={() => deactivateSource(source)}>Deactivate</Button></div>)}</div></Card>
      <Card><SectionHeader eyebrow="Philippine tax configuration" title="Automatic VAT and CWT profiles" description="Rates are not guessed. An Administrator activates the accountant-approved rule for each classification." /><div className="settings-list">{profiles.map((profile) => <div key={profile.id}><span><BookOpen size={18} /><strong>{profile.name}</strong><small>{profile.classification.replace('_', ' ')} • VAT {Number(profile.vat_rate) * 100}% • CWT {Number(profile.withholding_rate) * 100}%</small></span><Status tone={profile.active ? 'success' : 'info'}>{profile.active ? 'Active' : 'Superseded'}</Status></div>)}</div><form className="form-stack" onSubmit={addProfile}><label>Profile name<input name="name" placeholder="Example: Standard service charge 2026" required /></label><div className="form-grid"><label>Classification<select name="classification"><option value="SERVICE_CHARGE">Service charge</option><option value="PASS_THROUGH">Pass-through cost</option></select></label><label>VAT rate (%)<input name="vat_percent" type="number" min="0" max="100" step="0.01" required /></label><label>CWT rate (%)<input name="withholding_percent" type="number" min="0" max="100" step="0.01" required /></label></div><Button type="submit">Activate Tax Profile</Button></form></Card>
    </div>
    <Card><SectionHeader eyebrow="Access control" title="Demo accounts and responsibilities" description="Use the documented account command to create, disable, or reset accounts. Historical actions are never deleted when access changes." /><div className="table-wrap"><table><thead><tr><th>Role</th><th>Responsibility</th><th>Administration method</th></tr></thead><tbody>{documentedRoles.map((item) => <tr key={item}><td><OwnerBadge>{item}</OwnerBadge></td><td>{roleDescriptions[item]}</td><td>CLI-managed account with audited server authorization</td></tr>)}</tbody></table></div></Card>
  </div>
}

function LoginPage({ onSignedIn, demoBuild }: { onSignedIn: (user: ApiUser) => void; demoBuild: boolean }) {
  const [mode, setMode] = useState<'sign-in' | 'activate' | 'reset'>('sign-in')
  const [stage, setStage] = useState<'password' | 'code' | 'activation-code' | 'activation-password' | 'reset-start' | 'reset-sent' | 'reset-password'>('password')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [activationCode, setActivationCode] = useState('')
  const [challenge, setChallenge] = useState<{ id: string; destination: string; token?: string; developmentCode?: string | null } | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const emailLinkHandled = useRef(false)

  useEffect(() => {
    if (emailLinkHandled.current) return
    const hash = window.location.hash
    if (!hash.startsWith('#email-sign-in?') && !hash.startsWith('#password-reset?')) return
    emailLinkHandled.current = true
    const isReset = hash.startsWith('#password-reset?')
    const prefix = isReset ? '#password-reset?'.length : '#email-sign-in?'.length
    const parameters = new URLSearchParams(hash.slice(prefix))
    const challengeId = parameters.get('challenge') ?? ''
    const code = parameters.get('code') ?? ''
    const token = parameters.get('token') ?? ''
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#login`)
    if (isReset) {
      if (!challengeId || token.length < 32) {
        setMode('reset')
        setStage('reset-start')
        setError('This password reset link is incomplete. Request a new reset email and try again.')
        return
      }
      setMode('reset')
      setStage('reset-password')
      setChallenge({ id: challengeId, destination: 'your email', token })
      return
    }
    if (!challengeId || !/^\d{6}$/.test(code)) {
      setError('This sign-in link is incomplete. Enter your username and password to request a new email.')
      return
    }
    setStage('code')
    setChallenge({ id: challengeId, destination: 'your email' })
    setBusy(true)
    void verifyEmailCode(challengeId, code)
      .then(onSignedIn)
      .catch((caught) => {
        setError(caught instanceof Error ? caught.message : 'This sign-in link could not be verified. Request a new email and try again.')
      })
      .finally(() => setBusy(false))
  }, [onSignedIn])

  function resetToSignIn() {
    setMode('sign-in')
    setStage('password')
    setChallenge(null)
    setActivationCode('')
    setError('')
    setNotice('')
  }

  async function continueWithPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await startPassword(username, password)
      setChallenge({ id: result.challenge_id, destination: result.destination, developmentCode: result.development_code })
      setStage('code')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign-in could not be started.')
    } finally {
      setBusy(false)
    }
  }

  async function enterDemo() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const user = await startDemoSession()
      onSignedIn(user)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The demo session could not be started.')
    } finally {
      setBusy(false)
    }
  }

  async function startAccountActivation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await startActivation(username)
      setChallenge({ id: result.challenge_id, destination: result.destination, developmentCode: result.development_code })
      setStage('activation-code')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Account activation could not be started.')
    } finally {
      setBusy(false)
    }
  }

  async function requestPasswordReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await startPasswordReset(username)
      setChallenge(null)
      setNotice(result.message)
      setStage('reset-sent')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Password recovery could not be started.')
    } finally {
      setBusy(false)
    }
  }

  async function finishSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!challenge) return
    setBusy(true)
    setError('')
    const data = new FormData(event.currentTarget)
    try {
      const user = await verifyEmailCode(challenge.id, String(data.get('code')))
      onSignedIn(user)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The code could not be verified.')
    } finally {
      setBusy(false)
    }
  }

  function continueActivation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const code = String(data.get('code') ?? '')
    if (!/^\d{6}$/.test(code)) {
      setError('Enter the six-digit activation code from your email.')
      return
    }
    setActivationCode(code)
    setError('')
    setStage('activation-password')
  }

  async function finishActivation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!challenge) return
    const data = new FormData(event.currentTarget)
    const newPassword = String(data.get('password') ?? '')
    const confirmation = String(data.get('confirmation') ?? '')
    if (newPassword !== confirmation) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const user = await completeActivation(challenge.id, activationCode, newPassword)
      onSignedIn(user)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Account activation could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  async function finishPasswordReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!challenge?.token) return
    const data = new FormData(event.currentTarget)
    const newPassword = String(data.get('password') ?? '')
    const confirmation = String(data.get('confirmation') ?? '')
    if (newPassword !== confirmation) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await completePasswordReset(challenge.id, challenge.token, newPassword, confirmation)
      setMode('sign-in')
      setStage('password')
      setChallenge(null)
      setPassword('')
      setNotice(result.message)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Password reset could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  const sharedError = error ? <div className="callout callout--danger"><AlertCircle size={18} /><span>{error}</span></div> : null
  const sharedNotice = notice ? <div className="callout callout--info"><CheckCircle2 size={18} /><span>{notice}</span></div> : null
  const activationCodeCallout = challenge?.developmentCode ? <div className="callout callout--info"><AlertCircle size={18} /><span>Local development code: <strong>{challenge.developmentCode}</strong></span></div> : null

  return (
    <div className="login-screen">
      <section className="login-brand" aria-labelledby="login-hero-title">
        <img src={brandLogoUrl} alt="PIMASCOR" />
        <div className="login-brand__content">
          <p className="eyebrow eyebrow--light">Operational control</p>
          <h1 id="login-hero-title">Run every shipment with the full picture in view.</h1>
          <p className="login-brand__lede">Requests, approvals, payments, liquidation, billing, and collections stay connected from start to finish.</p>
          <div className="login-highlights">
            <span><Ship size={19} aria-hidden="true" /><strong>One connected workflow</strong><small>Follow work from budget to collection.</small></span>
            <span><Activity size={19} aria-hidden="true" /><strong>Decisions stay visible</strong><small>See ownership, status, and history clearly.</small></span>
            <span><ShieldCheck size={19} aria-hidden="true" /><strong>Enterprise safeguards</strong><small>Role-based access, email verification, and audit records.</small></span>
          </div>
        </div>
        <div className="login-proof"><ShieldCheck size={20} aria-hidden="true" /><span><strong>Private by design</strong><small>Protected sessions • Verified access • Complete audit history</small></span></div>
      </section>
      <main className="login-main">
        <div className="login-card">
           {stage === 'password' && mode === 'sign-in' ? demoBuild ? <div key="demo-entry" className="form-stack login-demo-entry"><div><p className="eyebrow">Demo evaluation</p><h2>Enter the synthetic workspace</h2><p>Use the one-click Admin entry for this public demo. No personal credentials are required.</p></div>{sharedError}{sharedNotice}<Button type="button" disabled={busy} onClick={enterDemo}>{busy ? 'Opening demo…' : 'Enter demo as Admin'}</Button><p className="login-demo-entry__note">Synthetic data only · Production sign-in is separate</p></div> : <form key="password-step" onSubmit={continueWithPassword} className="form-stack"><div><p className="eyebrow">Welcome back</p><h2>Sign in to PIMASCOR</h2><p>Use your assigned company account.</p></div>{sharedError}{sharedNotice}<label>Username or email<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label><label>Password<input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} /></label><Button type="submit" disabled={busy}>{busy ? 'Checking account…' : 'Continue securely'}</Button><button type="button" className="text-button" onClick={() => { setMode('reset'); setStage('reset-start'); setError(''); setNotice('') }}>Forgot password?</button><button type="button" className="text-button" onClick={() => { setMode('activate'); setError(''); setNotice('') }}>First-time access? Activate your account</button><div className="login-step"><span className="active">1</span><i /><span>2</span><small>Password</small><small>Email verification</small></div></form> : null}
          {stage === 'password' && mode === 'activate' ? <form key="activation-start-step" onSubmit={startAccountActivation} className="form-stack"><div><p className="eyebrow">First-time access</p><h2>Activate your account</h2><p>Enter the assigned username or email. We will send a one-time code before you choose a password.</p></div>{sharedError}<label>Username or email<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label><Button type="submit" disabled={busy}>{busy ? 'Sending code…' : 'Send activation code'}</Button><button type="button" className="text-button" onClick={resetToSignIn}>Already activated? Sign in</button></form> : null}
          {stage === 'code' ? <form key="email-code-step" onSubmit={finishSignIn} className="form-stack"><div><p className="eyebrow">One more check</p><h2>{busy ? 'Checking your secure link' : 'Verify your email'}</h2><p>{busy ? 'Please wait while we finish signing you in.' : <>We sent a six-digit code to {challenge?.destination}.</>}</p></div>{sharedError}{challenge?.developmentCode ? <div className="callout callout--info"><AlertCircle size={18} /><span>Local development code: <strong>{challenge.developmentCode}</strong></span></div> : null}<label>Verification code<input name="code" className="code-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" placeholder="000000" required autoFocus disabled={busy} /></label><div className="code-expiry"><Clock3 size={16} />Code works once and expires in 5 minutes</div><Button type="submit" disabled={busy}>{busy ? 'Verifying…' : 'Verify and sign in'}</Button><button type="button" className="text-button" onClick={resetToSignIn}>Return to sign in</button><div className="login-step"><span className="done"><Check size={13} /></span><i className="done" /><span className="active">2</span><small>Password checked</small><small>Email verification</small></div></form> : null}
          {stage === 'activation-code' ? <form key="activation-code-step" onSubmit={continueActivation} className="form-stack"><div><p className="eyebrow">First-time access</p><h2>Verify your email</h2><p>We sent a six-digit activation code to {challenge?.destination}.</p></div>{sharedError}{activationCodeCallout}<label>Activation code<input name="code" className="code-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" placeholder="000000" required autoFocus /></label><div className="code-expiry"><Clock3 size={16} />Code works once and expires in 5 minutes</div><Button type="submit" disabled={busy}>Continue to password</Button><button type="button" className="text-button" onClick={resetToSignIn}>Return to sign in</button></form> : null}
          {stage === 'activation-password' ? <form key="activation-password-step" onSubmit={finishActivation} className="form-stack"><div><p className="eyebrow">Choose your password</p><h2>Secure your account</h2><p>Create a password of at least 12 characters. PIMASCOR will not email a permanent password.</p></div>{sharedError}<label>New password<input name="password" autoComplete="new-password" type="password" required minLength={12} /></label><label>Confirm password<input name="confirmation" autoComplete="new-password" type="password" required minLength={12} /></label><Button type="submit" disabled={busy}>{busy ? 'Activating account…' : 'Activate and sign in'}</Button><button type="button" className="text-button" onClick={resetToSignIn}>Cancel activation</button></form> : null}
          {stage === 'reset-start' && mode === 'reset' ? <form key="reset-start-step" onSubmit={requestPasswordReset} className="form-stack"><div><p className="eyebrow">Account recovery</p><h2>Reset your password</h2><p>Enter your username or email. If the account is eligible, we will send a one-time reset link.</p></div>{sharedError}{sharedNotice}<label>Username or email<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label><Button type="submit" disabled={busy}>{busy ? 'Sending reset email…' : 'Send reset email'}</Button><button type="button" className="text-button" onClick={resetToSignIn}>Back to sign in</button></form> : null}
          {stage === 'reset-sent' && mode === 'reset' ? <div key="reset-sent-step" className="form-stack"><div><p className="eyebrow">Check your inbox</p><h2>Reset email requested</h2><p>For your security, this message is the same whether or not the account exists. Follow the one-time link in the email, then choose a new password.</p></div>{sharedError}{sharedNotice}<div className="code-expiry"><Clock3 size={16} />The reset link works once and expires in 15 minutes</div><button type="button" className="text-button" onClick={resetToSignIn}>Back to sign in</button></div> : null}
          {stage === 'reset-password' && mode === 'reset' ? <form key="reset-password-step" onSubmit={finishPasswordReset} className="form-stack"><div><p className="eyebrow">Account recovery</p><h2>Choose a new password</h2><p>Use at least 12 characters. After resetting, sign in again with the new password.</p></div>{sharedError}{sharedNotice}<label>New password<input name="password" autoComplete="new-password" type="password" required minLength={12} autoFocus /></label><label>Confirm password<input name="confirmation" autoComplete="new-password" type="password" required minLength={12} /></label><Button type="submit" disabled={busy}>{busy ? 'Resetting password…' : 'Reset password'}</Button><button type="button" className="text-button" onClick={resetToSignIn}>Cancel reset</button></form> : null}
          <p className="prototype-note">Passwords are checked by the API and stored only as secure hashes. The browser keeps only a protected session cookie.</p>
        </div>
      </main>
    </div>
  )
}

function Timeline({ items }: { items: [string, string, string][] }) {
  return <div className="timeline">{items.map(([date, title, actor], index) => <div className="timeline__item" key={date + title}><span>{index === 0 ? <Check size={14} /> : null}</span><div><small>{date}</small><strong>{title}</strong><p>{actor}</p></div></div>)}</div>
}

function DocumentItem({ name, meta, available = false, onOpen }: { name: string; meta: string; available?: boolean; onOpen?: () => void }) {
  const content = <><span><FileText size={19} /></span><span><strong>{name}</strong><small>{meta}</small></span>{available ? <Eye size={17} /> : <Archive size={17} />}</>
  return available && onOpen ? <button className="document-item" type="button" onClick={onOpen} title="View confidential document; downloading is disabled">{content}</button> : <div className="document-item" title="Metadata record only; no stored object is available">{content}</div>
}

function SupportTicketsDialog({ role, notify, open, onClose }: { role: Role; notify: Notify; open: boolean; onClose: () => void }) {
  const [tickets, setTickets] = useState<ApiSupportTicket[] | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [category, setCategory] = useState('OTHER')
  const [reason, setReason] = useState('I HAVE A QUESTION OR ANOTHER PROBLEM')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [reply, setReply] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [replyFiles, setReplyFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [demoPortalUrl, setDemoPortalUrl] = useState<string | null>(null)
  const selected = tickets?.find((ticket) => ticket.id === selectedId) ?? null
  const isAdmin = role === 'Admin'
  const canRespond = isAdmin || isDemoBuild
  const reasonOptions: Record<string, string[]> = {
    ACCESS: ['I cannot access a workspace', 'A role or permission looks wrong'],
    DATA: ['A record or number looks incorrect', 'I need a report or export'],
    WORKFLOW: ['A workflow is not behaving as expected', 'I need help completing a task'],
    SUGGESTION: ['I have a product improvement idea', 'I want to share feedback'],
    OTHER: ['I have a question or another problem'],
  }

  function close() {
    setSelectedId(null)
    setReply('')
    setFiles([])
    setReplyFiles([])
    setDemoPortalUrl(null)
    onClose()
  }

  const refresh = useCallback(async () => {
    try {
      setTickets(await getSupportTickets())
    } catch (error) {
      notifyLocalFailure(error, 'Could not load support tickets.', notify)
    }
  }, [notify])

  useEffect(() => {
    if (open) void refresh()
  }, [open, refresh])

  async function submitTicket(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const created = await createSupportTicket(subject, message, { category, reason, files })
      setSubject('')
      setMessage('')
      setCategory('OTHER')
      setReason('I HAVE A QUESTION OR ANOTHER PROBLEM')
      setFiles([])
      setSelectedId(created.id)
      setDemoPortalUrl(created.portal_url ?? null)
      await refresh()
      notify(`Ticket ${created.ticket_number} was submitted.`, 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not submit the support ticket.', notify)
    } finally { setBusy(false) }
  }

  async function submitReply(event: FormEvent) {
    event.preventDefault()
    if (!selected) return
    setBusy(true)
    try {
      await addSupportTicketMessage(selected.id, reply, { is_internal: false, expected_version: selected.version, files: replyFiles })
      setReply('')
      setReplyFiles([])
      await refresh()
      notify(isDemoBuild ? 'A simulated support reply was added.' : 'Your support reply was added.', 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not add the support reply.', notify)
    } finally { setBusy(false) }
  }

  async function changeStatus(status: ApiSupportTicketStatus) {
    if (!selected) return
    setBusy(true)
    try {
      await updateSupportTicket(selected.id, { status, expected_version: selected.version })
      await refresh()
      notify(`Ticket status changed to ${status.replaceAll('_', ' ').toLowerCase()}.`, 'success')
    } catch (error) {
      notifyLocalFailure(error, 'Could not update the support ticket.', notify)
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} onClose={close} title="Support" className="support-modal">
      {selected ? (
        <div className="support-dialog">
          <button className="support-back" type="button" onClick={() => setSelectedId(null)}>
            <ChevronRight size={16} aria-hidden="true" />
            Back to your tickets
          </button>
          <div className="support-detail">
            <div className="support-detail__heading">
              <div>
                <p className="eyebrow">{selected.ticket_number}</p>
                <h3>{selected.subject}</h3>
              </div>
              <Status>{selected.status.replaceAll('_', ' ')}</Status>
            </div>
            <div className="support-dialog__meta">
              {selected.category.replaceAll('_', ' ')} · {selected.reason.replaceAll('_', ' ')} · Submitted by {selected.requester.display_name} · {new Date(selected.created_at).toLocaleString('en-PH')}
            </div>
            <div className="callout callout--info support-dialog__notice">
              <CircleHelp size={18} aria-hidden="true" />
              <span>{isDemoBuild ? 'Demo simulation: replies are synthetic and clearly labeled.' : 'Admin support notifications are sent to Alyssa and JK.'}</span>
            </div>
            {isDemoBuild && demoPortalUrl ? <div className="support-dialog__actions support-dialog__portal-link"><a className="button button--secondary" href={demoPortalUrl}>Open simulated no-login thread</a><span className="support-dialog__hint">This simulates the private email link. Demo does not send production email.</span></div> : null}
            <div className="support-message">
              <span className="support-message__label">Your message</span>
              <p>{selected.message}</p>
            </div>
            <SectionHeader title="Conversation" description="Replies stay attached to this ticket." />
            <div className="support-conversation">
              {selected.replies.length ? selected.replies.map((item) => (
                <div className="support-conversation__item" key={item.id}>
                  <div><strong>{item.author.display_name}</strong>{item.is_simulated ? <span>Simulated reply</span> : null}</div>
                  <p>{item.body}</p>
                  <small>{new Date(item.created_at).toLocaleString('en-PH')}</small>
                </div>
              )) : <EmptyState icon={Clock3} title="Awaiting response" detail="Admin support has not replied yet." />}
            </div>
            {canRespond ? <form className="support-form" onSubmit={submitReply}>
              <label>Reply (Markdown supported)<textarea value={reply} onChange={(event) => setReply(event.target.value)} minLength={2} maxLength={10000} rows={4} required /></label>
              <label className="support-file-input">Attach screenshots or files<input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.md,.csv" onChange={(event) => setReplyFiles(Array.from(event.target.files ?? []))} /></label>
              <div className="support-dialog__actions"><Button type="submit" disabled={busy}>Add reply</Button></div>
            </form> : <div className="callout callout--info support-dialog__notice"><Clock3 size={18} aria-hidden="true" /><span>Only Admin can reply in production. To add more context, start a new ticket.</span></div>}
            {isAdmin ? <div className="support-dialog__actions"><Button tone="secondary" disabled={busy} onClick={() => void changeStatus('IN_PROGRESS')}>Start</Button><Button tone="secondary" disabled={busy} onClick={() => void changeStatus('WAITING_FOR_REQUESTER')}>Wait for requester</Button><Button disabled={busy} onClick={() => void changeStatus('RESOLVED')}>Resolve</Button><Button tone="ghost" disabled={busy} onClick={() => void changeStatus('CLOSED')}>Close</Button></div> : null}
          </div>
        </div>
      ) : (
        <div className="support-dialog">
          <div className="support-dialog__intro">
            <CircleHelp size={21} aria-hidden="true" />
            <div>
              <p className="eyebrow">Questions, suggestions, and problems</p>
              <h3>Contact Admin support</h3>
              <p>{isDemoBuild ? 'Demo only: tickets and replies are simulated. No production email is sent.' : 'Send a question, suggestion, or problem. We will give you a ticket number for follow-up.'}</p>
            </div>
          </div>
          <form className="support-form" onSubmit={submitTicket}>
            <div className="support-form__grid"><label>Category<select value={category} onChange={(event) => { const next = event.target.value; setCategory(next); setReason((reasonOptions[next] ?? reasonOptions.OTHER)[0].toUpperCase()) }}><option value="WORKFLOW">Workflow help</option><option value="ACCESS">Access and permissions</option><option value="DATA">Data or reports</option><option value="SUGGESTION">Suggestion or feedback</option><option value="OTHER">Other question</option></select></label><label>What best describes it?<select value={reason} onChange={(event) => setReason(event.target.value)}>{(reasonOptions[category] ?? reasonOptions.OTHER).map((item) => <option key={item} value={item.toUpperCase()}>{item}</option>)}</select></label></div>
            <label>Subject<input value={subject} onChange={(event) => setSubject(event.target.value)} minLength={2} maxLength={200} placeholder="What do you need help with?" required /></label>
            <label>Message (Markdown supported)<textarea value={message} onChange={(event) => setMessage(event.target.value)} minLength={2} maxLength={10000} rows={4} placeholder="Tell Admin support what happened or what you suggest." required /></label>
            <label className="support-file-input">Attach screenshots or files<input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.md,.csv" onChange={(event) => setFiles(Array.from(event.target.files ?? []))} /></label>
            <div className="support-dialog__actions"><Button type="submit" icon={ArrowRight} disabled={busy}>Send support message</Button></div>
          </form>
          <div className="support-dialog__tickets">
            <div className="support-dialog__section-heading">
              <div><p className="eyebrow">Your tickets</p><h3>Recent support requests</h3><p>Messages stay attached to their ticket history.</p></div>
              <Button tone="ghost" icon={RefreshCw} onClick={() => void refresh()}>Refresh</Button>
            </div>
            {tickets === null ? <EmptyState icon={RefreshCw} title="Loading tickets" detail="Opening the support register." /> : tickets.length === 0 ? <EmptyState icon={CircleHelp} title="No tickets yet" detail="Send a question, suggestion, or problem above." /> : <div className="support-ticket-list">
              {tickets.map((ticket) => <button className="support-ticket-card" type="button" key={ticket.id} onClick={() => setSelectedId(ticket.id)} aria-label={`Open ${ticket.ticket_number}: ${ticket.subject}`}>
                <span><span className="support-ticket-card__meta"><strong>{ticket.ticket_number}</strong><Status>{ticket.status.replaceAll('_', ' ')}</Status></span><span className="support-ticket-card__subject">{ticket.subject}</span><small>Updated {new Date(ticket.updated_at).toLocaleString('en-PH')}</small></span>
                <ChevronRight className="support-ticket-card__arrow" size={18} aria-hidden="true" />
              </button>)}
            </div>}
          </div>
        </div>
      )}
    </Modal>
  )
}

function WorkspaceApp() {
  const [page, setPage] = useState<PageId>(pageFromHash)
  const [role, setRole] = useState<Role>('Admin')
  const [authUser, setAuthUser] = useState<ApiUser | null | undefined>(undefined)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileNav, setMobileNav] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [supportOpen, setSupportOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const profileButtonRef = useRef<HTMLButtonElement>(null)
  const profileMenuRef = useRef<HTMLDivElement>(null)
  const profileWrapRef = useRef<HTMLDivElement>(null)
  const profileMenuId = useId()
  const [notificationsRead, setNotificationsRead] = useState(false)
  const [actionMessage, setActionMessage] = useState<ActionMessage>(null)
  const [releaseUpdate, setReleaseUpdate] = useState<ApiReleaseUpdate | null>(null)
  const [releaseUpdateOpen, setReleaseUpdateOpen] = useState(false)

  useEffect(() => {
    const sync = () => setPage(pageFromHash())
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  useEffect(() => {
    getMe()
      .then((user) => {
        setAuthUser(user)
        setRole(apiRoleToRole[user.role])
      })
      .catch(() => setAuthUser(null))
  }, [])

  useEffect(() => {
    if (!authUser) {
      setReleaseUpdate(null)
      setReleaseUpdateOpen(false)
      return
    }
    let cancelled = false
    getReleaseUpdate()
      .then((update) => {
        if (cancelled || !update) return
        setReleaseUpdate(update)
        setReleaseUpdateOpen(true)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [authUser])

  useEffect(() => {
    if (!authUser) return
    const allowed = navigation.some((group) => group.items.some((item) => item.id === page && item.roles.includes(role)))
    if (!allowed) navigate(defaultPageForRole(role))
  }, [authUser, page, role])

  useEffect(() => {
    if (!profileOpen) return
    const menu = profileMenuRef.current
    const items = () => Array.from(menu?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? [])
    items()[0]?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      const menuItems = items()
      if (event.key === 'Escape') {
        event.preventDefault()
        setProfileOpen(false)
        profileButtonRef.current?.focus()
        return
      }
      if (event.key === 'Tab') {
        setProfileOpen(false)
        return
      }
      if (!menuItems.length) return
      const current = Math.max(0, menuItems.indexOf(document.activeElement as HTMLButtonElement))
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Home' || event.key === 'End') {
        event.preventDefault()
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? menuItems.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + menuItems.length) % menuItems.length
        menuItems[next]?.focus()
      }
    }
    const onPointerDown = (event: PointerEvent) => {
      if (!profileWrapRef.current?.contains(event.target as Node)) setProfileOpen(false)
    }
    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('pointerdown', onPointerDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('pointerdown', onPointerDown)
    }
  }, [profileOpen])

  function navigate(nextPage: PageId) {
    window.location.hash = nextPage
    setPage(nextPage)
    setMobileNav(false)
    setSearchOpen(false)
    setSupportOpen(false)
    setProfileOpen(false)
  }

  function notify(message: string, tone: Tone = 'info', solution?: string) {
    const dialogTone = tone === 'neutral' || tone === 'brand' ? 'info' : tone
    const displayMessage = formatBusinessMessage(message)
    setActionMessage({
      message: displayMessage,
      tone: dialogTone,
      solution: solution ?? suggestedNextStep(displayMessage, dialogTone),
    })
  }

  const dismissActionMessage = useCallback(() => setActionMessage(null), [])

  const signedInRole = authUser ? apiRoleToRole[authUser.role] : null
  const isRolePreview = signedInRole === 'Admin' && role !== 'Admin'

  function previewRole(nextRole: Role) {
    if (signedInRole !== 'Admin') return
    setRole(nextRole)
    navigate(nextRole === 'Admin' ? 'admin' : defaultPageForRole(nextRole))
  }

  function returnToAdmin() {
    if (signedInRole !== 'Admin') return
    setRole('Admin')
    navigate('admin')
  }

  const visibleNavigation = useMemo(() => navigation.map((group) => ({ ...group, items: group.items.filter((item) => item.roles.includes(role)) })).filter((group) => group.items.length), [role])

  if (authUser === undefined) return <main className="app-splash" aria-busy="true"><section role="status" aria-live="polite"><img src={brandLogoUrl} alt="PIMASCOR" /><RefreshCw className="app-splash__spinner" size={22} aria-hidden="true" /><strong>Opening your protected workspace…</strong><small>Preparing your secure operational view</small></section></main>

  if (!authUser || page === 'login') return <LoginPage demoBuild={isDemoBuild} onSignedIn={(user) => {
    setAuthUser(user)
    setRole(apiRoleToRole[user.role])
    navigate(defaultPageForRole(apiRoleToRole[user.role]))
  }} />

  // Resolve access before rendering. The hash correction effect still makes the
  // canonical URL visible, while this synchronous guard prevents a restricted
  // page from mounting and issuing requests during that redirect.
  const resolvedPage: PageId = navigation.some((group) => group.items.some((item) => item.id === page && item.roles.includes(role)))
    ? page
    : (visibleNavigation[0]?.items[0]?.id ?? 'dashboard')

  let content: ReactNode
  switch (resolvedPage) {
    case 'quotations': content = <QuotationsPage key={role} role={role} notify={notify} />; break
    case 'budget-requests': content = <BudgetRequestsPage key={role} role={role} notify={notify} />; break
    case 'approvals': content = <ApprovalPage key={role} role={role} notify={notify} />; break
    case 'releases': content = <ReleasesPage key={role} role={role} notify={notify} />; break
    case 'liquidation': content = <LiquidationPage key={role} role={role} notify={notify} navigate={navigate} />; break
    case 'billing': content = <BillingPage key={role} role={role} notify={notify} />; break
    case 'collections': content = <CollectionsPage key={role} role={role} notify={notify} />; break
    case 'payment-requests': content = <PaymentRequestsPage key={role} role={role} notify={notify} />; break
    case 'opex': content = <ExpensePage key={role} type="OPEX" role={role} notify={notify} />; break
    case 'marketing': content = <ExpensePage key={role} type="Marketing" role={role} notify={notify} />; break
    case 'loan-payments': content = <ExpensePage key={role} type="Loan Payment" role={role} notify={notify} />; break
    case 'accounting': content = <AccountingPage key={role} role={role} />; break
    case 'clients-documents': content = <ClientsDocumentsPage key={role} role={role} />; break
    case 'admin': content = <AdminPage key={role} role={role} notify={notify} onPreviewRole={previewRole} />; break
    default: content = <DashboardPage key={role} role={role} displayName={authUser.display_name} navigate={navigate} />
  }

  return (
    <div className={`app ${sidebarOpen ? '' : 'app--collapsed'}`}>
      <IncidentCenter enabled={Boolean(authUser)} />
      <ActionMessageDialog
        notice={actionMessage}
        onDismiss={dismissActionMessage}
      />
      <ReleaseUpdateModal
        update={releaseUpdate}
        open={releaseUpdateOpen}
        onAcknowledged={() => {
          setReleaseUpdateOpen(false)
          setReleaseUpdate(null)
        }}
      />
      <aside className={`sidebar ${mobileNav ? 'sidebar--mobile-open' : ''}`}>
        <div className="sidebar__brand"><img src={brandIconUrl} alt="" /><div><strong>PIMASCOR</strong><span>Operational Control</span></div><button className="icon-button sidebar__mobile-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={20} /></button></div>
        <nav aria-label="Primary navigation">
          {visibleNavigation.map((group) => <div className="nav-group" key={group.label}><span className="nav-group__label">{group.label}</span>{group.items.map((item) => { const Icon = item.icon; const label = item.roleLabels?.[role] ?? item.label; return <button key={item.id} className={`nav-item ${resolvedPage === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)} title={!sidebarOpen ? label : undefined}><Icon size={19} /><span>{label}</span></button> })}</div>)}
        </nav>
        <div className="sidebar__footer"><div className="sidebar__security"><ShieldCheck size={17} /><span><strong>Protected workspace</strong><small>{isRolePreview ? `Admin operating as • ${role}` : `Signed in • ${role}`}</small></span></div><button className="sidebar__collapse" onClick={() => setSidebarOpen((current) => !current)}>{sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}<span>{sidebarOpen ? 'Collapse navigation' : 'Expand'}</span></button></div>
      </aside>

      {mobileNav ? <button className="mobile-scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation" /> : null}

      <div className="app-main">
        <header className="topbar">
          <div className="topbar__title"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={21} /></button><div><p>{pageMeta[resolvedPage].title}</p><span>{pageMeta[resolvedPage].description}</span></div></div>
          <div className="topbar__actions">
            <button className="global-search" onClick={() => setSearchOpen(true)}><Search size={17} /><span>Search anything</span><kbd>⌘ K</kbd></button>
            <button className="support-trigger" type="button" onClick={() => setSupportOpen(true)} aria-haspopup="dialog" aria-expanded={supportOpen} title="Open support"><CircleHelp size={18} aria-hidden="true" /><span>Support</span></button>
            <button className="icon-button notification-button" onClick={() => setNotificationsOpen((current) => !current)} aria-label="Notifications"><Bell size={20} />{notificationsRead ? null : <span>3</span>}</button>
            <div className="profile-menu-wrap" ref={profileWrapRef}>
              <button ref={profileButtonRef} className="profile-button" type="button" aria-haspopup={signedInRole === 'Admin' ? 'menu' : undefined} aria-expanded={signedInRole === 'Admin' ? profileOpen : undefined} aria-controls={signedInRole === 'Admin' ? profileMenuId : undefined} onClick={signedInRole === 'Admin' ? () => setProfileOpen((current) => !current) : undefined}><span>{authUser.display_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span><div><strong>{authUser.display_name}</strong><small>{isRolePreview ? `Admin • operating as ${role}` : role}</small></div>{signedInRole === 'Admin' ? <ChevronDown size={15} /> : null}</button>
              {profileOpen && signedInRole === 'Admin' ? <div id={profileMenuId} ref={profileMenuRef} className="profile-menu" role="menu" aria-label="Profile actions">
                {signedInRole === 'Admin' ? <button type="button" role="menuitem" onClick={() => { setProfileOpen(false); isRolePreview ? returnToAdmin() : navigate('admin') }}>{isRolePreview ? 'Return to Admin controls' : 'Open Administration'}</button> : null}
              </div> : null}
            </div>
            <button className="icon-button" aria-label="Sign out" title="Sign out" onClick={() => signOut().catch(() => undefined).finally(() => { setSupportOpen(false); setAuthUser(null); window.location.hash = 'login' })}><LogOut size={19} /></button>
          </div>
          {notificationsOpen ? <div className="notification-panel"><SectionHeader eyebrow={notificationsRead ? 'No unread items' : '3 unread'} title="Notifications" action={notificationsRead ? undefined : <button className="text-button" onClick={() => setNotificationsRead(true)}>Mark all read</button>} />{attentionByRole[role].slice(0, 3).map((item) => <button key={item.id} onClick={() => { navigate(item.page); setNotificationsOpen(false) }}><span className={`notification-dot notification-dot--${item.tone}`} /><span><strong>{item.title}</strong><small>{item.detail}</small></span><span>{item.age}</span></button>)}</div> : null}
        </header>

        <main className="content">
          <PwaInstallPrompt />
          {isRolePreview ? <section className="role-preview-banner" role="status"><span><ShieldCheck size={19} /><span><strong>Admin operating in the {role} workspace</strong><small>Role actions are enabled. Security checks and audit records continue to use your Admin identity.</small></span></span><Button tone="secondary" onClick={returnToAdmin}>Return to Admin</Button></section> : null}
          <div className="page-heading"><div><p className="eyebrow">PIMASCOR workspace</p><h1>{pageMeta[resolvedPage].title}</h1><p>{pageMeta[resolvedPage].description}</p></div><div className="page-heading__actions"><Button tone="ghost" icon={RefreshCw} onClick={() => window.location.reload()}>Refresh</Button></div></div>{content}
        </main>
      </div>

      <Modal open={searchOpen} onClose={() => setSearchOpen(false)} title="Search PIMASCOR">
        <label className="search-field search-field--large"><Search size={19} /><span className="sr-only">Search</span><input autoFocus placeholder="Try BR-0726-159, SOA-0382, or a client name" /></label>
        <div className="search-results"><p className="eyebrow">Suggested records</p>{[
          ['BR-0726-159', 'Archipelago Cargo Trading • Shipment Budget Request', 'budget-requests'],
          ['SOA-0382', 'Archipelago Cargo Trading • PHP 12,400 remaining', 'collections'],
          ['PAY-0726-044', 'Client payment • PHP 50,000', 'collections'],
        ].map(([title, detail, target]) => <button key={title} onClick={() => navigate(target as PageId)}><span><Search size={16} /></span><div><strong>{title}</strong><small>{detail}</small></div><ChevronRight size={17} /></button>)}</div>
      </Modal>

      <SupportTicketsDialog role={role} notify={notify} open={supportOpen} onClose={() => setSupportOpen(false)} />

    </div>
  )
}

function App() {
  const [portalLink] = useState(() => readSupportPortalLink())
  return portalLink ? <SupportPortalPage link={portalLink} /> : <WorkspaceApp />
}

export default App
