import type { ApiActivityCategory, ApiAdminActivity, ApiBilling, ApiBudgetRequest, ApiClient, ApiClientPayment, ApiCreditMemo, ApiDataExport, ApiDocument, ApiExpenseRequest, ApiExpenseType, ApiFundingSource, ApiIncident, ApiIncidentReport, ApiLiquidation, ApiPaymentQueueItem, ApiQuotation, ApiReleaseUpdate, ApiShipmentProfitability, ApiSupportPortal, ApiSupportTicket, ApiSupportTicketStatus, ApiTaxProfile, ApiUser } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1'
const CSRF_COOKIE_NAME = import.meta.env.VITE_CSRF_COOKIE_NAME ?? 'pimascor_csrf'

let csrfToken = readCookie(CSRF_COOKIE_NAME)

function readCookie(name: string) {
  const item = document.cookie.split('; ').find((entry) => entry.startsWith(`${name}=`))
  return item ? decodeURIComponent(item.slice(name.length + 1)) : ''
}

export class ApiError extends Error {
  status: number
  code: string
  recovery: string
  canContinue: boolean
  correlationId: string | null
  incidentId: string | null
  incidentReference: string | null
  operation: string
  requestMethod: string
  requestPath: string

  constructor(input: {
    message: string
    status: number
    code: string
    recovery: string
    canContinue: boolean
    correlationId?: string | null
    incidentId?: string | null
    incidentReference?: string | null
    operation: string
    requestMethod: string
    requestPath: string
  }) {
    super(input.message)
    this.name = 'ApiError'
    this.status = input.status
    this.code = input.code
    this.recovery = input.recovery
    this.canContinue = input.canContinue
    this.correlationId = input.correlationId ?? null
    this.incidentId = input.incidentId ?? null
    this.incidentReference = input.incidentReference ?? null
    this.operation = input.operation
    this.requestMethod = input.requestMethod
    this.requestPath = input.requestPath
  }
}

function operationForRequest(path: string, method: string) {
  const normalized = path.toLowerCase()
  if (normalized.includes('budget-request')) return method === 'GET' ? 'Open Budget Requests' : 'Save a Budget Request'
  if (normalized.includes('approval')) return 'Record an approval decision'
  if (normalized.includes('dcs-payment')) return 'Record or review a DCS payment'
  if (normalized.includes('liquidation')) return 'Prepare or close a Liquidation'
  if (normalized.includes('billing')) return 'Prepare or finalize Billing'
  if (normalized.includes('client-payment')) return 'Record a client payment'
  if (normalized.includes('expense-request')) return 'Prepare a Request for Payment'
  if (normalized.includes('document')) return 'Open or upload a supporting document'
  if (normalized.includes('funding-source')) return 'Maintain an approved funding source'
  if (normalized.includes('tax-profile')) return 'Maintain a tax profile'
  if (normalized.includes('auth')) return 'Sign in securely'
  return method === 'GET' ? 'Open PIMASCOR information' : 'Save PIMASCOR information'
}

export function emitApiIncident(error: ApiError) {
  window.dispatchEvent(new CustomEvent<ApiError>('pimascor:incident', { detail: error }))
}

async function requestResponse(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (options.method && options.method !== 'GET') {
    csrfToken = csrfToken || readCookie(CSRF_COOKIE_NAME)
    if (csrfToken) headers.set('X-CSRF-Token', csrfToken)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      credentials: options.credentials ?? 'include',
    })
  } catch {
    const method = options.method ?? 'GET'
    const error = new ApiError({
      message: 'PIMASCOR could not reach the service.',
      status: 0,
      code: 'CONNECTION_UNAVAILABLE',
      recovery: 'Keep this page open, check your connection, and try again after a short wait.',
      canContinue: true,
      operation: operationForRequest(path, method),
      requestMethod: method,
      requestPath: path,
    })
    if (!path.startsWith('/incidents')) emitApiIncident(error)
    throw error
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const message = body?.error?.message ?? body?.detail ?? 'The request could not be completed.'
    const method = options.method ?? 'GET'
    const error = new ApiError({
      message: typeof message === 'string' ? message : 'Please check the form and try again.',
      status: response.status,
      code: body?.error?.code ?? `HTTP_${response.status}`,
      recovery: body?.error?.recovery ?? 'Review this page and try again.',
      canContinue: body?.error?.canContinue ?? response.status < 500,
      correlationId: body?.error?.correlationId ?? response.headers.get('X-Correlation-ID'),
      incidentId: body?.error?.incidentId ?? null,
      incidentReference: body?.error?.incidentReference ?? null,
      operation: operationForRequest(path, method),
      requestMethod: method,
      requestPath: path,
    })
    if (!path.startsWith('/incidents')) emitApiIncident(error)
    throw error
  }
  return response
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await requestResponse(path, options)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function requestSupportPortal<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('X-Support-Token', token)
  const response = await requestResponse(path, { ...options, headers, credentials: 'omit' })
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function readSupportPortalLink(): { ticketId: string; token: string } | null {
  if (typeof window === 'undefined' || !window.location.hash.startsWith('#support-portal?')) return null
  const params = new URLSearchParams(window.location.hash.slice('#support-portal?'.length))
  const ticketId = params.get('ticket')
  const token = params.get('token')
  if (!ticketId || !token || token.length > 200) return null
  window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}`)
  return { ticketId, token }
}

export function getSupportPortal(ticketId: string, token: string) {
  return requestSupportPortal<ApiSupportPortal>(`/support-tickets/portal/${encodeURIComponent(ticketId)}`, token)
}

export function addSupportPortalReply(ticketId: string, token: string, body: string, options: { is_internal?: boolean; expected_version?: number; files?: File[] } = {}) {
  const form = new FormData()
  form.append('body', body)
  if (options.is_internal !== undefined) form.append('is_internal', String(options.is_internal))
  if (options.expected_version !== undefined) form.append('expected_version', String(options.expected_version))
  for (const file of options.files ?? []) form.append('attachments', file, file.name)
  return requestSupportPortal<ApiSupportPortal>(`/support-tickets/portal/${encodeURIComponent(ticketId)}/replies`, token, { method: 'POST', body: form })
}

export function updateSupportPortalStatus(ticketId: string, token: string, status: ApiSupportTicketStatus, expected_version?: number) {
  return requestSupportPortal<ApiSupportPortal>(`/support-tickets/portal/${encodeURIComponent(ticketId)}/status`, token, { method: 'POST', body: JSON.stringify({ status, expected_version }) })
}

export function assignSupportPortalTicket(ticketId: string, token: string, assigned_to_key: 'support_staff' | 'bridge_admin', expected_version?: number) {
  return requestSupportPortal<ApiSupportPortal>(`/support-tickets/portal/${encodeURIComponent(ticketId)}/assignment`, token, { method: 'POST', body: JSON.stringify({ assigned_to_key, expected_version }) })
}

export async function downloadSupportPortalAttachment(attachmentId: string, token: string) {
  const response = await requestResponse(`/support-tickets/portal/attachments/${encodeURIComponent(attachmentId)}`, { headers: { 'X-Support-Token': token }, credentials: 'omit' })
  return response.blob()
}

export function reportIncident(input: ApiIncidentReport) {
  return request<ApiIncident>('/incidents', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function reportDetectedIncident(id: string) {
  return request<ApiIncident>(`/incidents/${encodeURIComponent(id)}/report`, {
    method: 'POST',
  })
}

export type PasswordStartResult = {
  challenge_id: string
  destination: string
  expires_in_seconds: number
  development_code?: string | null
}

export async function startDemoSession() {
  const result = await request<{ user: ApiUser; csrf_token: string }>('/auth/demo', {
    method: 'POST',
  })
  csrfToken = result.csrf_token
  return result.user
}

export async function startPassword(username: string, password: string) {
  return request<PasswordStartResult>('/auth/password/start', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function startActivation(username: string) {
  return request<PasswordStartResult>('/auth/activation/start', {
    method: 'POST',
    body: JSON.stringify({ username }),
  })
}

export type PasswordResetStartResult = {
  message: string
  expires_in_seconds: number
  development_code?: string | null
  development_challenge_id?: string | null
}

export async function startPasswordReset(identifier: string) {
  return request<PasswordResetStartResult>('/auth/password-reset/start', {
    method: 'POST',
    body: JSON.stringify({ identifier }),
  })
}

export async function completePasswordReset(
  challengeId: string,
  token: string,
  password: string,
  confirmation: string,
) {
  return request<{ message: string }>('/auth/password-reset/complete', {
    method: 'POST',
    body: JSON.stringify({ challenge_id: challengeId, token, password, confirmation }),
  })
}

export async function completeActivation(challengeId: string, code: string, password: string) {
  const result = await request<{ user: ApiUser; csrf_token: string }>('/auth/activation/complete', {
    method: 'POST',
    body: JSON.stringify({ challenge_id: challengeId, code, password }),
  })
  csrfToken = result.csrf_token
  return result.user
}

export async function verifyEmailCode(challengeId: string, code: string) {
  const result = await request<{ user: ApiUser; csrf_token: string }>('/auth/email-code/verify', {
    method: 'POST',
    body: JSON.stringify({ challenge_id: challengeId, code }),
  })
  csrfToken = result.csrf_token
  return result.user
}

export function getMe() {
  return request<ApiUser>('/auth/me')
}

export function getReleaseUpdate() {
  return request<ApiReleaseUpdate | null>('/auth/release-updates')
}

export function acknowledgeReleaseUpdate() {
  return request<void>('/auth/release-updates/ack', { method: 'POST' })
}

export async function signOut() {
  await request<void>('/auth/logout', { method: 'POST' })
  csrfToken = ''
}

export function getClients() {
  return request<ApiClient[]>('/clients')
}

export function getQuotations() {
  return request<ApiQuotation[]>('/quotations')
}

export function createQuotation(input: {
  client_id: string
  shipment_reference: string
  quoted_amount: string
  currency: string
  terms_and_conditions: string
  mode_of_transport?: string
  container_type?: string
  origin?: string
  destination?: string
  incoterms?: string
  cargo_details?: string
  payment_terms?: string
  validity_hours?: number
  lines?: { section: 'ORIGIN_FREIGHT' | 'DESTINATION_CLEARANCE'; description: string; currency: 'PHP' | 'USD'; amount: string; billed_by: 'PIMASCOR' | 'BOC' }[]
}) {
  return request<ApiQuotation>('/quotations', { method: 'POST', body: JSON.stringify(input) })
}

export function submitQuotation(id: string, expectedVersion: number) {
  return request<ApiQuotation>(`/quotations/${id}/submit?expected_version=${expectedVersion}`, { method: 'POST' })
}

export function decideQuotation(id: string, expectedVersion: number, approve: boolean, reason?: string) {
  return request<ApiQuotation>(`/quotations/${id}/decision`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, approve, reason: reason || null }),
  })
}

export function overrideQuotationAsDcs(id: string, expectedVersion: number, reason: string) {
  return request<ApiQuotation>(`/quotations/${id}/dcs-override`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason }),
  })
}

export function recordQuotationAcceptance(id: string, expectedVersion: number, acceptedOn: string, clientSignatory: string, file: File) {
  const body = new FormData()
  body.set('expected_version', String(expectedVersion))
  body.set('accepted_on', acceptedOn)
  body.set('client_signatory', clientSignatory)
  body.set('document', file)
  return request<ApiQuotation>(`/quotations/${id}/client-acceptance`, { method: 'POST', body })
}

export function getBudgetRequests() {
  return request<ApiBudgetRequest[]>('/budget-requests')
}

export function createBudgetRequest(input: {
  client_id: string
  quotation_id?: string | null
  shipment_reference: string
  request_date: string
  currency: string
  notes?: string | null
  items: { kind: 'BUYING' | 'SELLING'; description: string; classification?: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]
}) {
  return request<ApiBudgetRequest>('/budget-requests', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateBudgetRequest(id: string, input: {
  expected_version: number
  client_id?: string | null
  quotation_id?: string | null
  shipment_reference?: string | null
  request_date: string
  currency: string
  notes?: string | null
  reason?: string | null
  related_expense_description?: string | null
  related_expense_amount?: string | null
  items: { kind: 'BUYING' | 'SELLING'; description: string; classification?: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]
}) {
  return request<ApiBudgetRequest>(`/budget-requests/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function submitBudgetRequest(id: string, expectedVersion: number) {
  return request<ApiBudgetRequest>(`/budget-requests/${id}/submit?expected_version=${expectedVersion}`, {
    method: 'POST',
  })
}

export function getBudgetReviewQueue() {
  return request<ApiBudgetRequest[]>('/budget-reviews/queue')
}

export function reviewBudgetRequest(id: string, expectedVersion: number, reason?: string) {
  return request<ApiBudgetRequest>(`/budget-reviews/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason: reason || null }),
  })
}

export function returnBudgetFromReview(id: string, expectedVersion: number, reason: string) {
  return request<ApiBudgetRequest>(`/budget-reviews/${id}/return`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason }),
  })
}

export function overrideBudgetAsDcs(id: string, expectedVersion: number, reason: string) {
  return request<ApiBudgetRequest>(`/approvals/${id}/dcs-override`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason }),
  })
}

export function getBudgetApprovalQueue() {
  return request<ApiBudgetRequest[]>('/approvals/queue')
}

export function decideBudgetRequest(id: string, expectedVersion: number, outcome: 'approve' | 'reject', reason?: string) {
  return request<ApiBudgetRequest>(`/approvals/${id}/${outcome}`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason: reason || null }),
  })
}

export function createAdditionalBudget(parentId: string, input: {
  request_date: string
  reason: string
  related_expense_description?: string | null
  related_expense_amount?: string | null
  items: { kind: 'BUYING' | 'SELLING'; description: string; classification?: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]
}) {
  return request<ApiBudgetRequest>(`/budget-requests/${parentId}/additional-budgets`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function getExpenseRequests(type?: ApiExpenseType) {
  return request<ApiExpenseRequest[]>(type ? `/expense-requests?type=${type}` : '/expense-requests')
}

export function getExpenseApprovalQueue() {
  return request<ApiExpenseRequest[]>('/expense-requests/approval-queue')
}

export function createExpenseRequest(input: {
  expense_type: ApiExpenseType
  request_date: string
  due_date?: string | null
  party: string
  purpose: string
  requested_source?: string | null
  loan_reference?: string | null
  amount?: string
  principal_amount?: string
  interest_amount?: string
  penalties_fees_amount?: string
}) {
  return request<ApiExpenseRequest>('/expense-requests', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function submitExpenseRequest(id: string, expectedVersion: number) {
  return request<ApiExpenseRequest>(`/expense-requests/${id}/submit?expected_version=${expectedVersion}`, {
    method: 'POST',
  })
}

export function decideExpenseRequest(id: string, expectedVersion: number, outcome: 'approve' | 'reject', reason?: string) {
  return request<ApiExpenseRequest>(`/expense-requests/${id}/${outcome}`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason: reason || null }),
  })
}

export function disburseExpenseRequest(id: string, input: {
  expected_version: number
  mode: string
  source: string
  paid_to: string
  transaction_reference: string
}) {
  return request<ApiExpenseRequest>(`/expense-requests/${id}/disburse`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function validateLoanPayment(id: string, input: {
  expected_version: number
  notes?: string
}) {
  return request<ApiExpenseRequest>(`/expense-requests/${id}/validate`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function getPayments() {
  return request<ApiPaymentQueueItem[]>('/dcs-payments')
}

export function getFundingSources() {
  return request<ApiFundingSource[]>('/funding-sources')
}

export function createFundingSource(name: string) {
  return request<ApiFundingSource>('/funding-sources', { method: 'POST', body: JSON.stringify({ name }) })
}

export function updateFundingSource(id: string, input: { name?: string; active?: boolean }) {
  return request<ApiFundingSource>(`/funding-sources/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
}

export function getAdminActivity(input: {
  days: number
  includeAdmin: boolean
  category?: ApiActivityCategory
  search?: string
}) {
  const params = new URLSearchParams({
    days: String(input.days),
    include_admin: String(input.includeAdmin),
  })
  if (input.category) params.set('category', input.category)
  if (input.search?.trim()) params.set('search', input.search.trim())
  return request<ApiAdminActivity>(`/admin/activity?${params}`)
}

export function getTaxProfiles() {
  return request<ApiTaxProfile[]>('/tax-profiles')
}

export function createTaxProfile(input: {
  name: string
  classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'
  vat_rate: string
  withholding_rate: string
}) {
  return request<ApiTaxProfile>('/tax-profiles', { method: 'POST', body: JSON.stringify(input) })
}

export function getLiquidations() {
  return request<ApiLiquidation[]>('/liquidations')
}

export function saveLiquidation(budgetId: string, input: {
  expected_version?: number | null
  lines: { description: string; amount: string }[]
  evidence: { kind: 'RECEIPT' | 'RETURN_PROOF' | 'REIMBURSEMENT_PROOF'; file_name: string }[]
}) {
  return request<ApiLiquidation>(`/liquidations/budget/${budgetId}`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function submitLiquidation(id: string, expectedVersion: number) {
  return request<ApiLiquidation>(`/liquidations/${id}/submit?expected_version=${expectedVersion}`, { method: 'POST' })
}

export function closeLiquidation(id: string, expectedVersion: number, note: string, originalsReceivedConfirmed: boolean) {
  return request<ApiLiquidation>(`/liquidations/${id}/close`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, note, originals_received_confirmed: originalsReceivedConfirmed }),
  })
}

export function uploadLiquidationEvidence(id: string, expectedVersion: number, kind: 'RECEIPT' | 'RETURN_PROOF' | 'REIMBURSEMENT_PROOF' | 'PHYSICAL_RECEIPTS_PHOTO', file: File) {
  const body = new FormData()
  body.set('expected_version', String(expectedVersion))
  body.set('kind', kind)
  body.set('document', file)
  return request<ApiLiquidation>(`/liquidations/${id}/evidence`, {
    method: 'POST',
    body,
  })
}

export function getDocuments() {
  return request<ApiDocument[]>('/documents')
}

export function getSupportTickets() {
  return request<ApiSupportTicket[]>('/support-tickets')
}

export function createSupportTicket(subject: string, message: string, options: { category?: string; reason?: string; files?: File[] } = {}) {
  if (options.files?.length) {
    const form = new FormData()
    form.append('category', options.category ?? 'OTHER')
    form.append('reason', options.reason ?? 'OTHER')
    form.append('subject', subject)
    form.append('message', message)
    for (const file of options.files) form.append('attachments', file, file.name)
    return request<ApiSupportTicket>('/support-tickets', { method: 'POST', body: form })
  }
  return request<ApiSupportTicket>('/support-tickets', {
    method: 'POST',
    body: JSON.stringify({ category: options.category ?? 'OTHER', reason: options.reason ?? 'OTHER', subject, message }),
  })
}

export function addSupportTicketMessage(id: string, body: string, options: { is_internal?: boolean; expected_version?: number; files?: File[] } = {}) {
  if (options.files?.length) {
    const form = new FormData()
    form.append('body', body)
    if (options.is_internal !== undefined) form.append('is_internal', String(options.is_internal))
    if (options.expected_version !== undefined) form.append('expected_version', String(options.expected_version))
    for (const file of options.files) form.append('attachments', file, file.name)
    return request<ApiSupportTicket>(`/support-tickets/${encodeURIComponent(id)}/replies`, { method: 'POST', body: form })
  }
  return request<ApiSupportTicket>(`/support-tickets/${encodeURIComponent(id)}/replies`, {
    method: 'POST',
    body: JSON.stringify({ body, ...options }),
  })
}

export function updateSupportTicket(id: string, input: { status?: ApiSupportTicketStatus; assigned_to_id?: string | null; assigned_to_key?: 'support_staff' | 'bridge_admin' | null; expected_version?: number }) {
  const { status, ...rest } = input
  if (status) return request<ApiSupportTicket>(`/support-tickets/${encodeURIComponent(id)}/status`, { method: 'PATCH', body: JSON.stringify({ status, ...rest }) })
  return request<ApiSupportTicket>(`/support-tickets/${encodeURIComponent(id)}/assignment`, { method: 'PATCH', body: JSON.stringify(rest) })
}

export function getDataExports() {
  return request<ApiDataExport[]>('/data-exports')
}

export function requestDataExport() {
  return request<ApiDataExport>('/data-exports', { method: 'POST' })
}

export async function downloadDataExport(id: string) {
  const response = await requestResponse(`/data-exports/${encodeURIComponent(id)}/download`, { cache: 'no-store' })
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const fileName = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? 'pimascor-records.zip'
  return { blob: await response.blob(), fileName }
}

export async function getDocumentBlob(id: string, signal?: AbortSignal) {
  const path = `/documents/${encodeURIComponent(id)}/view`
  const response = await requestResponse(path, {
    cache: 'no-store',
    signal,
  })
  const contentType = (response.headers.get('Content-Type') ?? '')
    .split(';', 1)[0]
    .trim()
    .toLowerCase()
  if (!['application/pdf', 'image/jpeg', 'image/png'].includes(contentType)) {
    const error = new ApiError({
      message: 'This document could not be displayed safely.',
      status: response.status,
      code: 'DOCUMENT_TYPE_UNSUPPORTED',
      recovery: 'Close the viewer and ask Bridge PH to verify the uploaded file.',
      canContinue: true,
      operation: 'Open a supporting document',
      requestMethod: 'GET',
      requestPath: path,
    })
    emitApiIncident(error)
    throw error
  }
  return {
    blob: await response.blob(),
    contentType,
  }
}

export async function downloadDocument(id: string) {
  const response = await requestResponse(`/documents/${encodeURIComponent(id)}/download`, { cache: 'no-store' })
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const fileName = /filename="?([^";]+)"?/i.exec(disposition)?.[1] ?? 'pimascor-document'
  return { blob: await response.blob(), fileName }
}

export function getBilling() {
  return request<ApiBilling[]>('/billing')
}

export function createBillingDraft(budgetId: string, input: {
  issue_date: string
  due_date: string
  client_address?: string | null
  category?: string | null
  shipper_consignee?: string | null
  container_number?: string | null
  destination?: string | null
  vessel?: string | null
  bl_awb_number?: string | null
  exchange_rate?: string | null
  measurement?: string | null
  notes?: string | null
  lines: { description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]
}) {
  return request<ApiBilling>(`/billing/budget/${budgetId}`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateBillingDraft(id: string, input: {
  expected_version: number
  issue_date: string
  due_date: string
  client_address?: string | null
  category?: string | null
  shipper_consignee?: string | null
  container_number?: string | null
  destination?: string | null
  vessel?: string | null
  bl_awb_number?: string | null
  exchange_rate?: string | null
  measurement?: string | null
  notes?: string | null
  lines: { description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]
}) {
  return request<ApiBilling>(`/billing/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
}

export function finalizeBilling(id: string, expectedVersion: number) {
  return request<ApiBilling>(`/billing/${id}/finalize`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, confirmation: 'FINALIZE' }),
  })
}

export function submitBilling(id: string, expectedVersion: number) {
  return request<ApiBilling>(`/billing/${id}/submit`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion }),
  })
}

export function decideBilling(id: string, expectedVersion: number, approve: boolean, reason?: string) {
  return request<ApiBilling>(`/billing/${id}/decision`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, approve, reason: reason || null }),
  })
}

export function getShipmentProfitability(month?: string) {
  const query = month ? `?month=${encodeURIComponent(month)}` : ''
  return request<ApiShipmentProfitability>(`/dashboard/shipment-profitability${query}`)
}

export function voidBilling(id: string, expectedVersion: number, reason: string) {
  return request<ApiBilling>(`/billing/${id}/void`, {
    method: 'POST',
    body: JSON.stringify({ expected_version: expectedVersion, reason }),
  })
}

export function createBillingReplacement(id: string, input: {
  expected_version: number
  reason: string
  issue_date: string
  due_date: string
  client_address?: string | null
  category?: string | null
  shipper_consignee?: string | null
  container_number?: string | null
  destination?: string | null
  vessel?: string | null
  bl_awb_number?: string | null
  exchange_rate?: string | null
  measurement?: string | null
  notes?: string | null
  lines: { description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string }[]
}) {
  return request<ApiBilling>(`/billing/${id}/replacement`, { method: 'POST', body: JSON.stringify(input) })
}

export function getCreditMemos(billingId?: string) {
  return request<ApiCreditMemo[]>(`/credit-memos${billingId ? `?billing_id=${encodeURIComponent(billingId)}` : ''}`)
}

export function createCreditMemo(billingId: string, input: { reason: string; amount: string; submit_for_approval?: boolean }) {
  return request<ApiCreditMemo>(`/billing/${billingId}/credit-memos`, { method: 'POST', body: JSON.stringify(input) })
}

export function decideCreditMemo(id: string, expectedVersion: number, approve: boolean, reason?: string) {
  return request<ApiCreditMemo>(`/credit-memos/${id}/decision`, {
    method: 'POST', body: JSON.stringify({ expected_version: expectedVersion, approve, reason: reason || null }),
  })
}

export function getReceivables() {
  return request<ApiBilling[]>('/receivables')
}

export function createClientPayment(input: {
  client_id: string
  payment_reference?: string | null
  payment_method?: string
  check_number?: string | null
  check_list_number?: string | null
  receiving_bank: string
  payment_date: string
  amount: string
  notes?: string | null
  allocations: { billing_id: string; amount: string }[]
}) {
  return request<ApiClientPayment>('/client-payments', { method: 'POST', body: JSON.stringify(input) })
}

export function getClientPayments() {
  return request<ApiClientPayment[]>('/client-payments')
}

export function recordPayment(sourceType: 'budget' | 'expense', id: string, input: {
  amount: string
  paid_on: string
  mode: string
  source: string
  recipient: string
  transaction_reference: string
  notes?: string | null
  expected_version: number
}) {
  return request<ApiPaymentQueueItem>(`/dcs-payments/${sourceType}/${id}/pay`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function uploadPaymentProof(sourceType: 'budget' | 'expense', id: string, expectedVersion: number, file: File) {
  const body = new FormData()
  body.set('expected_version', String(expectedVersion))
  body.set('document', file)
  return request<ApiPaymentQueueItem>(`/dcs-payments/${sourceType}/${id}/proof`, {
    method: 'POST',
    body,
  })
}

export function updatePayment(sourceType: 'budget' | 'expense', id: string, input: {
  action: 'HOLD' | 'RETURN' | 'RESUME' | 'NOTE'
  note: string
  expected_version: number
}) {
  return request<ApiPaymentQueueItem>(`/dcs-payments/${sourceType}/${id}/actions`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
