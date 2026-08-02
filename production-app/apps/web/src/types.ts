export type Role = 'Admin' | 'Requester' | 'GM' | 'DCS' | 'Mich'

export type PageId =
  | 'dashboard'
  | 'quotations'
  | 'budget-requests'
  | 'approvals'
  | 'releases'
  | 'liquidation'
  | 'billing'
  | 'collections'
  | 'payment-requests'
  | 'opex'
  | 'marketing'
  | 'loan-payments'
  | 'accounting'
  | 'clients-documents'
  | 'admin'
  | 'login'

export type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand'

export interface BudgetRequest {
  id: string
  reference: string
  kind?: 'MAIN' | 'ADDITIONAL'
  parentReference?: string | null
  additionalReason?: string | null
  relatedExpenseDescription?: string | null
  relatedExpenseAmount?: string | null
  date: string
  client: string
  shipment: string
  requester: string
  buying: number
  selling: number
  approval: string
  release: string
  liquidation: string
  billing: string
  updated: string
  version?: number
  paymentStatus?: ApiPaymentStatus
  source?: ApiBudgetRequest
}

export interface AttentionItem {
  id: string
  tone: Tone
  eyebrow: string
  title: string
  detail: string
  age: string
  action: string
  page: PageId
}

export interface ApiUser {
  id: string
  username: string
  email: string
  display_name: string
  role: 'ADMIN' | 'REQUESTER' | 'GM' | 'DCS' | 'MICH'
}

export interface ApiReleaseChange {
  kind: 'new' | 'improved' | 'changed' | 'removed'
  title: string
  description: string
}

export interface ApiReleaseUpdate {
  id: string
  released_on: string
  title: string
  summary: string
  changes: ApiReleaseChange[]
}

export interface ApiClient {
  id: string
  code: string
  name: string
}

export interface ApiQuotation {
  id: string
  reference: string
  shipment_reference: string
  quoted_amount: string
  currency: string
  terms_and_conditions: string
  status: 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'CLIENT_ACCEPTED'
  submitted_at: string | null
  approved_at: string | null
  decision_reason: string | null
  client_accepted_at: string | null
  client_signatory: string | null
  signed_file_name: string | null
  signed_content_type: string | null
  signed_size_bytes: number | null
  signed_sha256: string | null
  mode_of_transport: string | null
  container_type: string | null
  origin: string | null
  destination: string | null
  incoterms: string | null
  cargo_details: string | null
  payment_terms: string | null
  validity_hours: number
  lines: ApiQuotationLine[]
  version: number
  created_at: string
  updated_at: string
  client: ApiClient
  created_by: ApiUser
  approved_by: ApiUser | null
}

export interface ApiQuotationLine {
  id: string
  section: 'ORIGIN_FREIGHT' | 'DESTINATION_CLEARANCE'
  description: string
  currency: 'PHP' | 'USD'
  amount: string
  billed_by: 'PIMASCOR' | 'BOC'
  position: number
}

export interface ApiBudgetRequest {
  id: string
  reference: string
  budget_kind: 'MAIN' | 'ADDITIONAL'
  parent_budget_id: string | null
  additional_reason: string | null
  related_expense_description: string | null
  related_expense_amount: string | null
  quotation_id: string | null
  shipment_reference: string
  notes: string | null
  request_date: string
  currency: string
  buying_total: string
  selling_total: string
  released_total: string
  status: 'DRAFT' | 'PENDING_REVIEW' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'PARTIALLY_RELEASED' | 'RELEASED' | 'CANCELLED'
  payment_status: ApiPaymentStatus
  reviewed_by: ApiUser | null
  reviewed_at: string | null
  review_note: string | null
  version: number
  created_at: string
  updated_at: string
  client: ApiClient
  requester: ApiUser
  items: { id: string; kind: 'BUYING' | 'SELLING'; description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string; sort_order: number }[]
}

export type ApiExpenseType = 'OPEX' | 'MARKETING' | 'LOAN_PAYMENT' | 'OTHER'
export type ApiExpenseStatus =
  | 'DRAFT'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'DISBURSED'
  | 'PENDING_VALIDATION'
  | 'VALIDATED'
  | 'CANCELLED'

export interface ApiExpenseRequest {
  id: string
  reference: string
  expense_type: ApiExpenseType
  request_date: string
  due_date: string | null
  party: string
  purpose: string
  requested_source: string | null
  loan_reference: string | null
  currency: string
  principal_amount: string
  interest_amount: string
  penalties_fees_amount: string
  amount: string
  status: ApiExpenseStatus
  payment_status: ApiPaymentStatus
  version: number
  created_at: string
  updated_at: string
  requester: ApiUser
  disbursement: null | {
    id: string
    amount: string
    mode: string
    source: string
    paid_to: string
    transaction_reference: string
    paid_on: string
    notes: string | null
    disbursed_by_id: string
    disbursed_at: string
  }
  validation: null | {
    id: string
    validated_by_id: string
    notes: string | null
    validated_at: string
  }
}

export type ApiPaymentStatus = 'NOT_READY' | 'PENDING' | 'ON_HOLD' | 'PARTIALLY_PAID' | 'PAID' | 'RETURNED'

export interface ApiPaymentAnnotation {
  id: string
  event_type: string
  note: string
  created_at: string
  actor: ApiUser
}

export interface ApiPaymentQueueItem {
  source_type: 'BUDGET_REQUEST' | 'ADDITIONAL_BUDGET' | 'OPEX' | 'MARKETING' | 'LOAN_PAYMENT' | 'OTHER'
  record_id: string
  reference: string
  parent_reference: string | null
  party: string
  purpose: string
  requester: string
  amount_due: string
  paid_amount: string
  outstanding_amount: string
  currency: string
  payment_status: ApiPaymentStatus
  due_date: string | null
  approved_by: string | null
  approved_at: string | null
  funding_source: string | null
  payment_method: string | null
  transaction_reference: string | null
  paid_on: string | null
  proof_file_name: string | null
  proof_available: boolean
  version: number
  annotations: ApiPaymentAnnotation[]
}

export interface ApiFundingSource {
  id: string
  name: string
  active: boolean
}

export type ApiActivityCategory = 'SECURITY' | 'TRANSACTION' | 'WORKFLOW' | 'CONFIGURATION' | 'DOCUMENT' | 'INCIDENT'
export type ApiActivitySeverity = 'INFO' | 'SUCCESS' | 'WARNING' | 'CRITICAL'

export interface ApiAdminActivityActor {
  id: string
  display_name: string
  username: string
  role: ApiUser['role']
}

export interface ApiAdminActivity {
  range_days: number
  include_admin: boolean
  total_events: number
  sensitive_events: number
  transaction_events: number
  active_users: number
  last_event_at: string | null
  timeline: {
    date: string
    total: number
    security: number
    transactions: number
    workflow: number
    configuration: number
    documents: number
    incidents: number
  }[]
  categories: { category: ApiActivityCategory; count: number }[]
  actors: { actor: ApiAdminActivityActor; total: number; sensitive: number; last_seen_at: string }[]
  events: {
    id: string
    actor: ApiAdminActivityActor | null
    action: string
    label: string
    category: ApiActivityCategory
    severity: ApiActivitySeverity
    entity_type: string
    entity_id: string
    reason: string | null
    correlation_id: string | null
    occurred_at: string
  }[]
  truncated: boolean
}

export type ApiIncidentDecision = 'CONTINUED' | 'STOPPED' | 'DISMISSED'

export interface ApiIncidentReport {
  client_report_id: string
  severity: 'RECOVERABLE' | 'BLOCKING'
  operation: string
  user_action: string
  user_message: string
  recovery_suggestion: string
  can_continue: boolean
  page_path: string
  request_method: string | null
  request_path: string | null
  http_status: number | null
  error_code: string
  technical_summary: string | null
  client_runtime: string | null
  correlation_id: string | null
}

export interface ApiIncident {
  id: string
  reference: string
  source: 'CLIENT' | 'SERVER'
  severity: 'RECOVERABLE' | 'BLOCKING'
  status: 'REPORTED' | 'DISMISSED' | 'CLOSED_BY_USER'
  operation: string
  user_message: string
  recovery_suggestion: string
  can_continue: boolean
  decision: ApiIncidentDecision | null
  correlation_id: string | null
  email_admin_sent_at: string | null
  email_developer_sent_at: string | null
  created_at: string
}

export interface ApiTaxProfile {
  id: string
  name: string
  classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'
  vat_rate: string
  withholding_rate: string
  active: boolean
}

export interface ApiLiquidation {
  id: string
  budget_request_id: string
  status: 'DRAFT' | 'SUBMITTED' | 'PENDING_VARIANCE' | 'CLOSED'
  released_total: string
  actual_total: string
  version: number
  submitted_at: string | null
  originals_received_confirmed: boolean
  originals_received_at: string | null
  closed_at: string | null
  closure_note: string | null
  budget_request: ApiBudgetRequest
  requester: ApiUser
  closed_by: ApiUser | null
  lines: { id: string; description: string; amount: string; sort_order: number }[]
  evidence: { id: string; kind: 'RECEIPT' | 'RETURN_PROOF' | 'REIMBURSEMENT_PROOF' | 'PHYSICAL_RECEIPTS_PHOTO'; file_name: string; content_type: string | null; size_bytes: number | null; sha256: string | null; uploaded_at: string }[]
}

export interface ApiDocument {
  id: string
  kind: 'RECEIPT' | 'RETURN_PROOF' | 'REIMBURSEMENT_PROOF' | 'PHYSICAL_RECEIPTS_PHOTO' | 'SIGNED_QUOTATION' | 'PAYMENT_PROOF'
  file_name: string
  content_type: string | null
  size_bytes: number | null
  sha256: string | null
  uploaded_at: string
  reference: string
  client_name: string
  uploaded_by: ApiUser
  available: boolean
}

export interface ApiDataExport {
  id: string
  status: 'QUEUED' | 'PROCESSING' | 'READY' | 'EXPIRED' | 'FAILED'
  requested_at: string
  started_at: string | null
  completed_at: string | null
  expires_at: string | null
  file_name: string | null
  size_bytes: number | null
  error_message: string | null
  requested_by: ApiUser
}

export interface ApiBilling {
  id: string
  reference: string
  budget_request_id: string
  replaces_billing_id: string | null
  revision: number
  issue_date: string
  due_date: string | null
  client_address: string | null
  category: string | null
  shipper_consignee: string | null
  container_number: string | null
  destination: string | null
  vessel: string | null
  bl_awb_number: string | null
  exchange_rate: string | null
  measurement: string | null
  service_subtotal: string
  pass_through_subtotal: string
  vat_amount: string
  withholding_amount: string
  total_amount: string
  net_due: string
  status: 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'FINALIZED' | 'VOID'
  notes: string | null
  version: number
  submitted_at: string | null
  approved_at: string | null
  rejection_reason: string | null
  finalized_at: string | null
  voided_at: string | null
  void_reason: string | null
  budget_request: ApiBudgetRequest
  prepared_by: ApiUser
  submitted_by: ApiUser | null
  approved_by: ApiUser | null
  finalized_by: ApiUser | null
  voided_by: ApiUser | null
  lines: { id: string; description: string; classification: 'SERVICE_CHARGE' | 'PASS_THROUGH'; amount: string; vat_rate: string; withholding_rate: string; vat_amount: string; withholding_amount: string; sort_order: number }[]
  collected_amount: string
  remaining_amount: string
  collection_status: 'Unpaid' | 'Partially Collected' | 'Fully Collected'
  aging_days: number
  aging_bucket: 'Current' | '1–30 days' | '31–60 days' | '61–90 days' | 'Over 90 days'
  approved_credit_memo_amount: string
  adjusted_net_due: string
}

export interface ApiCreditMemo {
  id: string
  reference: string
  billing_id: string
  reason: string
  amount: string
  status: 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED'
  version: number
  created_at: string
  approved_at: string | null
  rejection_reason: string | null
  created_by: ApiUser
  approved_by: ApiUser | null
}

export interface ApiClientPayment {
  id: string
  reference: string
  payment_reference: string
  payment_method: string
  check_number: string | null
  check_list_number: string | null
  receiving_bank: string
  payment_date: string
  amount: string
  notes: string | null
  created_at: string
  client: ApiClient
  recorded_by: ApiUser
  allocations: { id: string; billing_id: string; amount: string }[]
}

export interface ApiShipmentProfitability {
  shipment_count: number
  total_selling: string
  total_actual_spending: string
  total_profit: string
  overall_margin_percentage: string | null
  total_outstanding_receivable: string
  request_for_payment_summary: null | {
    month: string
    opex_total: string
    marketing_total: string
    loan_payment_total: string
    other_total: string
    grand_total: string
    opex_count: number
    marketing_count: number
    loan_payment_count: number
    other_count: number
    total_count: number
  }
  rows: {
    budget_request_id: string
    reference: string
    shipment_reference: string
    client_name: string
    selling_amount: string
    actual_spending: string
    profit: string
    profit_margin_percentage: string | null
    liquidation_status: string
    collection_status: string
    receivables_aging_days: number | null
    outstanding_receivable: string
  }[]
}
