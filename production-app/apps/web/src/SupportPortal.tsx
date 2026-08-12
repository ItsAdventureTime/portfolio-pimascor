import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import { ArrowLeft, CheckCircle2, ChevronDown, Download, FileText, LockKeyhole, MessageCircle, Paperclip, RefreshCw, Send, ShieldCheck, UserRound } from 'lucide-react'
import type { ApiSupportAttachment, ApiSupportPortal, ApiSupportTicketStatus } from './types'
import { addSupportPortalReply, assignSupportPortalTicket, downloadSupportPortalAttachment, getSupportPortal, updateSupportPortalStatus } from './api'

type PortalLink = { ticketId: string; token: string }

const statusLabel: Record<ApiSupportTicketStatus, string> = {
  OPEN: 'Open',
  IN_PROGRESS: 'In progress',
  WAITING_FOR_REQUESTER: 'Waiting for requester',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
}

function Markdown({ value }: { value: string }) {
  const blocks = value.split(/\r?\n/)
  return <div className="support-markdown">{blocks.map((line, index) => {
    const key = `${index}-${line}`
    if (!line.trim()) return <div className="support-markdown__space" key={key} />
    if (line.startsWith('### ')) return <h4 key={key}>{inlineMarkdown(line.slice(4), key)}</h4>
    if (line.startsWith('## ')) return <h3 key={key}>{inlineMarkdown(line.slice(3), key)}</h3>
    if (line.startsWith('# ')) return <h2 key={key}>{inlineMarkdown(line.slice(2), key)}</h2>
    if (line.startsWith('> ')) return <blockquote key={key}>{inlineMarkdown(line.slice(2), key)}</blockquote>
    if (/^[-*] /.test(line)) return <div className="support-markdown__bullet" key={key}>• {inlineMarkdown(line.slice(2), key)}</div>
    return <p key={key}>{inlineMarkdown(line, key)}</p>
  })}</div>
}

function inlineMarkdown(value: string, keyPrefix: string) {
  const parts = value.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)]+\))/g)
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={key}>{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*')) return <em key={key}>{part.slice(1, -1)}</em>
    if (part.startsWith('`') && part.endsWith('`')) return <code key={key}>{part.slice(1, -1)}</code>
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/)
    if (link) return <a href={link[2]} target="_blank" rel="noreferrer" key={key}>{link[1]}</a>
    return part
  })
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

function AttachmentList({ items, token, onError }: { items: ApiSupportAttachment[]; token: string; onError: (message: string) => void }) {
  async function download(item: ApiSupportAttachment) {
    if (!item.available || item.simulated) return
    try {
      const blob = await downloadSupportPortalAttachment(item.id, token)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = item.file_name
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      onError('This attachment could not be downloaded. It may have been removed.')
    }
  }

  if (!items.length) return null
  return <div className="support-attachments" aria-label="Attachments">
    {items.map((item) => <button className="support-attachment" type="button" key={item.id} disabled={!item.available || item.simulated} onClick={() => void download(item)}>
      {item.content_type.startsWith('image/') ? <FileText size={17} aria-hidden="true" /> : <Paperclip size={17} aria-hidden="true" />}
      <span><strong>{item.file_name}</strong><small>{formatBytes(item.size_bytes)} · {item.simulated ? 'Demo simulation' : item.available ? 'Download' : 'Removed'}</small></span>
      {!item.simulated && item.available ? <Download size={16} aria-hidden="true" /> : null}
    </button>)}
  </div>
}

function ThreadMessage({ label, body, createdAt, simulated, attachments, token, onError }: { label: string; body: string; createdAt: string; simulated: boolean; attachments: ApiSupportAttachment[]; token: string; onError: (message: string) => void }) {
  return <article className="support-thread__message">
    <div className="support-thread__message-head"><span className="support-avatar"><UserRound size={16} aria-hidden="true" /></span><span><strong>{label}</strong><small>{new Date(createdAt).toLocaleString('en-PH')}</small></span>{simulated ? <span className="support-simulated">Demo simulation</span> : null}</div>
    <Markdown value={body} />
    <AttachmentList items={attachments} token={token} onError={onError} />
  </article>
}

export function SupportPortalPage({ link }: { link: PortalLink }) {
  const [ticket, setTicket] = useState<ApiSupportPortal | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')
  const [fileError, setFileError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try { setTicket(await getSupportPortal(link.ticketId, link.token)) } catch { setError('This private support link is expired, revoked, or no longer available.') } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [link.ticketId, link.token])

  const thread = useMemo(() => ticket ? [
    { id: 'initial', label: ticket.requester.display_name, body: ticket.message, createdAt: ticket.created_at, simulated: false, attachments: ticket.message_attachments },
    ...ticket.replies.filter((item) => !item.is_internal || ticket.viewer_audience === 'support').map((item) => ({ id: item.id, label: item.author.display_name, body: item.body, createdAt: item.created_at, simulated: item.is_simulated, attachments: item.attachments })),
  ] : [], [ticket])

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? [])
    const invalid = selected.find((file) => file.size > 25 * 1024 * 1024)
    if (invalid) { setFileError(`${invalid.name} is larger than 25 MB.`); return }
    if (selected.length > 5) { setFileError('Attach no more than five files to one message.'); return }
    setFileError('')
    setFiles(selected)
  }

  async function submitReply(event: FormEvent) {
    event.preventDefault()
    if (!ticket || !message.trim()) return
    setBusy(true)
    setError('')
    try {
      setTicket(await addSupportPortalReply(ticket.id, link.token, message, { files }))
      setMessage('')
      setFiles([])
      setFileError('')
    } catch { setError('The reply could not be sent. Review the message and try again.') } finally { setBusy(false) }
  }

  async function changeStatus(status: ApiSupportTicketStatus) {
    if (!ticket) return
    setBusy(true)
    try { setTicket(await updateSupportPortalStatus(ticket.id, link.token, status, ticket.version)) } catch { setError('The ticket status could not be updated. It may have changed in another browser.') } finally { setBusy(false) }
  }

  async function changeAssignment(value: 'support_staff' | 'bridge_admin') {
    if (!ticket) return
    setBusy(true)
    try { setTicket(await assignSupportPortalTicket(ticket.id, link.token, value, ticket.version)) } catch { setError('The ticket assignment could not be updated.') } finally { setBusy(false) }
  }

  if (loading) return <div className="support-portal-shell"><div className="support-portal-card support-portal-card--center"><RefreshCw className="spin" size={24} aria-hidden="true" /><p>Opening your private support thread…</p></div></div>
  if (error && !ticket) return <div className="support-portal-shell"><div className="support-portal-card support-portal-card--center"><LockKeyhole size={32} aria-hidden="true" /><h1>Private support link unavailable</h1><p>{error}</p><a className="button button--secondary" href={window.location.pathname}>Return to PIMASCOR</a></div></div>
  if (!ticket) return null

  const isClosed = ticket.status === 'CLOSED'
  return <main className="support-portal-shell">
    <div className="support-portal-topbar"><a href={window.location.pathname} className="support-portal-brand"><img src={`${import.meta.env.BASE_URL}pimascor-app-icon.jpg`} alt="" /><span><strong>PIMASCOR</strong><small>Operational Control</small></span></a><span className="support-secure-label"><ShieldCheck size={15} aria-hidden="true" /> Private support thread</span></div>
    <div className="support-portal-layout">
      <section className="support-portal-card support-portal-card--thread">
        <a className="support-portal-back" href={window.location.pathname}><ArrowLeft size={16} aria-hidden="true" /> Back to PIMASCOR</a>
        <div className="support-portal-heading"><div><p className="eyebrow">{ticket.ticket_number}</p><h1>{ticket.subject}</h1><p className="support-portal-subtitle">{ticket.category.replaceAll('_', ' ')} · {ticket.reason.replaceAll('_', ' ')}</p></div><span className={`support-portal-status support-portal-status--${ticket.status.toLowerCase()}`}>{statusLabel[ticket.status]}</span></div>
        <div className="support-portal-banner"><MessageCircle size={18} aria-hidden="true" /><span>You are viewing this thread as <strong>{ticket.viewer_label}</strong>. Replies are shared with the requester and the support team.</span></div>
        {error ? <div className="support-portal-error" role="alert">{error}</div> : null}
        <div className="support-thread">{thread.map((item) => <ThreadMessage key={item.id} {...item} token={link.token} onError={setError} />)}</div>
        {!isClosed ? <form className="support-portal-reply" onSubmit={submitReply}><label htmlFor="support-portal-message">Reply in Markdown</label><textarea id="support-portal-message" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write a clear update, question, or next step…" rows={6} maxLength={10000} required /><div className="support-compose-footer"><label className="support-file-input"><Paperclip size={17} aria-hidden="true" /><span>Attach files</span><input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp,.txt,.md,.csv" onChange={chooseFiles} /></label><small>Markdown is supported · up to 5 files, 25 MB each</small><button className="button button--primary" type="submit" disabled={busy || !message.trim()}><Send size={16} aria-hidden="true" />{busy ? 'Sending…' : 'Send reply'}</button></div>{fileError ? <small className="support-file-error">{fileError}</small> : null}{files.length ? <div className="support-selected-files">{files.map((file) => <span key={`${file.name}-${file.size}`}>{file.name}</span>)}</div> : null}</form> : <div className="support-portal-closed"><CheckCircle2 size={20} aria-hidden="true" /><span>This ticket is closed. Attachments are no longer available. If you need more help, please submit a new support request.</span></div>}
      </section>
      <aside className="support-portal-sidebar">
        <div className="support-portal-card"><p className="eyebrow">Ticket details</p><dl className="support-portal-details"><div><dt>Requester</dt><dd>{ticket.requester.display_name}</dd></div><div><dt>Opened</dt><dd>{new Date(ticket.created_at).toLocaleDateString('en-PH')}</dd></div><div><dt>Assigned to</dt><dd>{ticket.assigned_to?.display_name ?? 'Unassigned'}</dd></div></dl>{ticket.can_manage ? <label className="support-select-label">Assign ticket<select value={ticket.assigned_to_key ?? ''} onChange={(event) => { if (event.target.value) void changeAssignment(event.target.value as 'support_staff' | 'bridge_admin') }} disabled={busy}><option value="">Choose support owner</option><option value="support_staff">Support Staff</option><option value="bridge_admin">Bridge Admin</option></select></label> : null}</div>
        {ticket.can_manage ? <div className="support-portal-card"><p className="eyebrow">Support actions</p><p className="support-sidebar-copy">Choose a clear status so the requester knows what happens next.</p><div className="support-status-actions"><button className="button button--secondary" type="button" onClick={() => void changeStatus('RESOLVED')} disabled={busy || isClosed}>Mark resolved</button><button className="button button--ghost" type="button" onClick={() => void changeStatus('CLOSED')} disabled={busy || isClosed}>Close ticket</button></div></div> : null}
        <div className="support-portal-card support-portal-trust"><LockKeyhole size={19} aria-hidden="true" /><div><strong>Private by design</strong><p>This link is unique to you, expires, and should not be forwarded.</p></div></div>
      </aside>
    </div>
  </main>
}

export type { PortalLink }
export { readSupportPortalLink } from './api'
