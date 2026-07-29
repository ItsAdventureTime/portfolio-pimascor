from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import (
    BillingStatus,
    CreditMemoStatus,
    DataExportStatus,
    BudgetKind,
    BudgetStatus,
    EvidenceKind,
    ExpenseStatus,
    ExpenseType,
    FinancialClassification,
    IncidentDecision,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    ItemKind,
    LiquidationStatus,
    PaymentStatus,
    QuotationStatus,
    Role,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PasswordStartRequest(BaseModel):
    username: str = Field(min_length=2, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class PasswordStartResponse(BaseModel):
    challenge_id: str
    destination: str
    expires_in_seconds: int
    development_code: str | None = None


class EmailCodeVerifyRequest(BaseModel):
    challenge_id: str
    code: str = Field(pattern=r"^\d{6}$")


class MeResponse(ApiModel):
    id: str
    username: str
    email: EmailStr
    display_name: str
    role: Role


class AuthenticatedResponse(BaseModel):
    user: MeResponse
    csrf_token: str


class ClientCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=200)


class ClientResponse(ApiModel):
    id: str
    code: str
    name: str


class QuotationLineCreate(BaseModel):
    section: str = Field(pattern=r"^(ORIGIN_FREIGHT|DESTINATION_CLEARANCE)$")
    description: str = Field(min_length=2, max_length=300)
    currency: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    billed_by: str = Field(default="PIMASCOR", pattern=r"^(PIMASCOR|BOC)$")

    @field_validator("currency")
    @classmethod
    def supported_currency(cls, value: str) -> str:
        value = value.upper()
        if value not in {"PHP", "USD"}:
            raise ValueError("Quotation lines support PHP or USD only")
        return value


class QuotationLineResponse(ApiModel):
    id: str
    section: str
    description: str
    currency: str
    amount: Decimal
    billed_by: str
    position: int


class QuotationCreate(BaseModel):
    client_id: str
    shipment_reference: str = Field(min_length=2, max_length=120)
    quoted_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="PHP", min_length=3, max_length=3)
    terms_and_conditions: str = Field(min_length=10, max_length=10000)
    mode_of_transport: str | None = Field(default=None, max_length=40)
    container_type: str | None = Field(default=None, max_length=40)
    origin: str | None = Field(default=None, max_length=160)
    destination: str | None = Field(default=None, max_length=160)
    incoterms: str | None = Field(default=None, max_length=40)
    cargo_details: str | None = Field(default=None, max_length=500)
    payment_terms: str | None = Field(default=None, max_length=500)
    validity_hours: int = Field(default=48, ge=1, le=720)
    lines: list[QuotationLineCreate] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def supported_currency(cls, value: str) -> str:
        value = value.upper()
        if value not in {"PHP", "USD"}:
            raise ValueError("Quotation currency must be PHP or USD")
        return value


class QuotationResponse(ApiModel):
    id: str
    reference: str
    shipment_reference: str
    quoted_amount: Decimal
    currency: str
    terms_and_conditions: str
    status: QuotationStatus
    submitted_at: datetime | None
    approved_at: datetime | None
    decision_reason: str | None
    client_accepted_at: date | None
    client_signatory: str | None
    signed_file_name: str | None
    signed_content_type: str | None
    signed_size_bytes: int | None
    signed_sha256: str | None
    mode_of_transport: str | None
    container_type: str | None
    origin: str | None
    destination: str | None
    incoterms: str | None
    cargo_details: str | None
    payment_terms: str | None
    validity_hours: int
    lines: list[QuotationLineResponse]
    version: int
    created_at: datetime
    updated_at: datetime
    client: ClientResponse
    created_by: MeResponse
    approved_by: MeResponse | None


class QuotationDecision(BaseModel):
    expected_version: int = Field(gt=0)
    approve: bool
    reason: str | None = Field(default=None, max_length=2000)


class BudgetItemInput(BaseModel):
    kind: ItemKind
    description: str = Field(min_length=2, max_length=240)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    classification: FinancialClassification = FinancialClassification.SERVICE_CHARGE


class BudgetItemResponse(ApiModel):
    id: str
    kind: ItemKind
    description: str
    amount: Decimal
    classification: FinancialClassification
    sort_order: int


class BudgetRequestCreate(BaseModel):
    client_id: str
    quotation_id: str | None = None
    shipment_reference: str = Field(min_length=2, max_length=120)
    request_date: date
    currency: str = Field(default="PHP", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=4000)
    items: list[BudgetItemInput] = Field(min_length=1, max_length=100)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class BudgetRequestUpdate(BaseModel):
    expected_version: int = Field(gt=0)
    client_id: str | None = None
    quotation_id: str | None = None
    shipment_reference: str | None = Field(default=None, min_length=2, max_length=120)
    request_date: date
    currency: str = Field(default="PHP", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, min_length=3, max_length=2000)
    related_expense_description: str | None = Field(default=None, max_length=2000)
    related_expense_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=18, decimal_places=2
    )
    items: list[BudgetItemInput] = Field(min_length=1, max_length=100)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class AdditionalBudgetCreate(BaseModel):
    request_date: date
    reason: str = Field(min_length=3, max_length=2000)
    related_expense_description: str | None = Field(default=None, max_length=2000)
    related_expense_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    items: list[BudgetItemInput] = Field(min_length=1, max_length=100)


class BudgetRequestResponse(ApiModel):
    id: str
    reference: str
    budget_kind: BudgetKind
    parent_budget_id: str | None
    additional_reason: str | None
    related_expense_description: str | None
    related_expense_amount: Decimal | None
    quotation_id: str | None
    shipment_reference: str
    notes: str | None
    request_date: date
    currency: str
    buying_total: Decimal
    selling_total: Decimal
    released_total: Decimal
    status: BudgetStatus
    payment_status: PaymentStatus
    reviewed_by: MeResponse | None
    reviewed_at: datetime | None
    review_note: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    client: ClientResponse
    requester: MeResponse
    items: list[BudgetItemResponse]


class DecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(gt=0)


class ReleaseCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    mode: str = Field(min_length=2, max_length=40)
    source: str = Field(min_length=2, max_length=160)
    recipient: str = Field(min_length=2, max_length=160)
    transaction_reference: str = Field(min_length=2, max_length=120)
    paid_on: date
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(gt=0)


class ReleaseResponse(ApiModel):
    id: str
    budget_request_id: str
    amount: Decimal
    mode: str
    source: str
    recipient: str
    transaction_reference: str
    paid_on: date
    notes: str | None
    released_at: datetime


class ExpenseRequestCreate(BaseModel):
    expense_type: ExpenseType
    request_date: date
    due_date: date | None = None
    party: str = Field(min_length=2, max_length=200)
    purpose: str = Field(min_length=2, max_length=2000)
    requested_source: str | None = Field(default=None, max_length=160)
    loan_reference: str | None = Field(default=None, max_length=160)
    currency: str = Field(default="PHP", min_length=3, max_length=3)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    principal_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    interest_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    penalties_fees_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)

    @field_validator("currency")
    @classmethod
    def uppercase_expense_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "ExpenseRequestCreate":
        component_total = self.principal_amount + self.interest_amount + self.penalties_fees_amount
        if self.expense_type == ExpenseType.LOAN_PAYMENT:
            if not self.loan_reference or not self.loan_reference.strip():
                raise ValueError("Loan reference is required for a Loan Payment")
            if self.due_date is None:
                raise ValueError("Due date is required for a Loan Payment")
            if component_total <= 0:
                raise ValueError("Principal, interest, or penalties/fees must contain an amount")
            if self.amount is not None and self.amount != component_total:
                raise ValueError("Loan Payment total must equal principal, interest, and penalties/fees")
            self.amount = component_total
        else:
            if self.amount is None:
                raise ValueError("Amount is required")
            if component_total != 0:
                raise ValueError("Loan amount breakdown is only valid for Loan Payments")
            self.loan_reference = None
        return self


class ExpenseDisbursementResponse(ApiModel):
    id: str
    amount: Decimal
    mode: str
    source: str
    paid_to: str
    transaction_reference: str
    paid_on: date
    notes: str | None
    disbursed_by_id: str
    disbursed_at: datetime


class ExpenseValidationResponse(ApiModel):
    id: str
    validated_by_id: str
    notes: str | None
    validated_at: datetime


class ExpenseRequestResponse(ApiModel):
    id: str
    reference: str
    expense_type: ExpenseType
    request_date: date
    due_date: date | None
    party: str
    purpose: str
    requested_source: str | None
    loan_reference: str | None
    currency: str
    principal_amount: Decimal
    interest_amount: Decimal
    penalties_fees_amount: Decimal
    amount: Decimal
    status: ExpenseStatus
    payment_status: PaymentStatus
    version: int
    created_at: datetime
    updated_at: datetime
    requester: MeResponse
    disbursement: ExpenseDisbursementResponse | None
    validation: ExpenseValidationResponse | None


class ExpenseDisbursementCreate(BaseModel):
    mode: str = Field(min_length=2, max_length=80)
    source: str = Field(min_length=2, max_length=160)
    paid_to: str = Field(min_length=2, max_length=200)
    transaction_reference: str = Field(min_length=2, max_length=160)
    expected_version: int = Field(gt=0)


class ExpenseValidationCreate(BaseModel):
    expected_version: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class PaymentAnnotationResponse(ApiModel):
    id: str
    event_type: str
    note: str
    created_at: datetime
    actor: MeResponse


class PaymentQueueItem(BaseModel):
    source_type: str
    record_id: str
    reference: str
    parent_reference: str | None = None
    party: str
    purpose: str
    requester: str
    amount_due: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    currency: str
    payment_status: PaymentStatus
    due_date: date | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    funding_source: str | None = None
    payment_method: str | None = None
    transaction_reference: str | None = None
    paid_on: date | None = None
    proof_file_name: str | None = None
    proof_available: bool = False
    version: int
    annotations: list[PaymentAnnotationResponse] = Field(default_factory=list)


class PaymentActionRequest(BaseModel):
    action: str = Field(pattern=r"^(HOLD|RETURN|RESUME|NOTE)$")
    note: str = Field(min_length=2, max_length=2000)
    expected_version: int = Field(gt=0)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    paid_on: date
    mode: str = Field(min_length=2, max_length=80)
    source: str = Field(min_length=2, max_length=160)
    recipient: str = Field(min_length=2, max_length=200)
    transaction_reference: str = Field(min_length=2, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(gt=0)


class SessionResponse(ApiModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool


class AuditEventResponse(ApiModel):
    id: str
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    reason: str | None
    correlation_id: str | None
    occurred_at: datetime


class AdminActivityActor(ApiModel):
    id: str
    display_name: str
    username: str
    role: Role


class AdminActivityEvent(BaseModel):
    id: str
    actor: AdminActivityActor | None
    action: str
    label: str
    category: str
    severity: str
    entity_type: str
    entity_id: str
    reason: str | None
    correlation_id: str | None
    occurred_at: datetime


class AdminActivityTimelinePoint(BaseModel):
    date: date
    total: int
    security: int
    transactions: int
    workflow: int
    configuration: int
    documents: int
    incidents: int


class AdminActivityCategoryCount(BaseModel):
    category: str
    count: int


class AdminActivityActorSummary(BaseModel):
    actor: AdminActivityActor
    total: int
    sensitive: int
    last_seen_at: datetime


class AdminActivityResponse(BaseModel):
    range_days: int
    include_admin: bool
    total_events: int
    sensitive_events: int
    transaction_events: int
    active_users: int
    last_event_at: datetime | None
    timeline: list[AdminActivityTimelinePoint]
    categories: list[AdminActivityCategoryCount]
    actors: list[AdminActivityActorSummary]
    events: list[AdminActivityEvent]
    truncated: bool


class IncidentCreate(BaseModel):
    client_report_id: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")
    severity: IncidentSeverity
    operation: str = Field(min_length=2, max_length=160)
    user_action: str = Field(min_length=2, max_length=500)
    user_message: str = Field(min_length=2, max_length=800)
    recovery_suggestion: str = Field(min_length=2, max_length=800)
    can_continue: bool
    page_path: str = Field(min_length=1, max_length=240)
    request_method: str | None = Field(default=None, max_length=12)
    request_path: str | None = Field(default=None, max_length=240)
    http_status: int | None = Field(default=None, ge=0, le=599)
    error_code: str = Field(min_length=2, max_length=100)
    technical_summary: str | None = Field(default=None, max_length=4000)
    client_runtime: str | None = Field(default=None, max_length=80)
    correlation_id: str | None = Field(default=None, max_length=36)


class IncidentResponse(ApiModel):
    id: str
    reference: str
    source: IncidentSource
    severity: IncidentSeverity
    status: IncidentStatus
    operation: str
    user_message: str
    recovery_suggestion: str
    can_continue: bool
    decision: IncidentDecision | None
    correlation_id: str | None
    email_admin_sent_at: datetime | None
    email_developer_sent_at: datetime | None
    created_at: datetime


class IncidentDecisionRequest(BaseModel):
    decision: IncidentDecision
    note: str | None = Field(default=None, max_length=500)


class FundingSourceResponse(ApiModel):
    id: str
    name: str
    active: bool


class FundingSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class FundingSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    active: bool | None = None


class TaxProfileResponse(ApiModel):
    id: str
    name: str
    classification: FinancialClassification
    vat_rate: Decimal
    withholding_rate: Decimal
    active: bool


class TaxProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    classification: FinancialClassification
    vat_rate: Decimal = Field(ge=0, le=1, max_digits=7, decimal_places=6)
    withholding_rate: Decimal = Field(ge=0, le=1, max_digits=7, decimal_places=6)


class LiquidationLineInput(BaseModel):
    description: str = Field(min_length=2, max_length=240)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class LiquidationEvidenceInput(BaseModel):
    kind: EvidenceKind
    file_name: str = Field(min_length=2, max_length=240)


class LiquidationSave(BaseModel):
    expected_version: int | None = Field(default=None, gt=0)
    lines: list[LiquidationLineInput] = Field(min_length=1, max_length=100)
    evidence: list[LiquidationEvidenceInput] = Field(default_factory=list, max_length=100)


class LiquidationEvidenceResponse(ApiModel):
    id: str
    kind: EvidenceKind
    file_name: str
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    uploaded_at: datetime


class DocumentLibraryResponse(ApiModel):
    id: str
    kind: str
    file_name: str
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    uploaded_at: datetime
    reference: str
    client_name: str
    uploaded_by: MeResponse
    available: bool


class DataExportResponse(ApiModel):
    id: str
    status: DataExportStatus
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None
    file_name: str | None
    size_bytes: int | None
    error_message: str | None
    requested_by: MeResponse


class LiquidationLineResponse(ApiModel):
    id: str
    description: str
    amount: Decimal
    sort_order: int


class LiquidationResponse(ApiModel):
    id: str
    budget_request_id: str
    status: LiquidationStatus
    released_total: Decimal
    actual_total: Decimal
    version: int
    submitted_at: datetime | None
    originals_received_confirmed: bool
    originals_received_at: datetime | None
    closed_at: datetime | None
    closure_note: str | None
    budget_request: BudgetRequestResponse
    requester: MeResponse
    closed_by: MeResponse | None
    lines: list[LiquidationLineResponse]
    evidence: list[LiquidationEvidenceResponse]


class LiquidationClose(BaseModel):
    expected_version: int = Field(gt=0)
    note: str = Field(min_length=2, max_length=2000)
    originals_received_confirmed: bool


class LiquidationEvidenceAdd(BaseModel):
    kind: EvidenceKind
    file_name: str = Field(min_length=2, max_length=240)
    expected_version: int = Field(gt=0)


class BillingLineInput(BaseModel):
    description: str = Field(min_length=2, max_length=240)
    classification: FinancialClassification
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class BillingDraftCreate(BaseModel):
    issue_date: date
    due_date: date
    client_address: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=120)
    shipper_consignee: str | None = Field(default=None, max_length=240)
    container_number: str | None = Field(default=None, max_length=120)
    destination: str | None = Field(default=None, max_length=160)
    vessel: str | None = Field(default=None, max_length=160)
    bl_awb_number: str | None = Field(default=None, max_length=160)
    exchange_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    measurement: str | None = Field(default=None, max_length=120)
    # Retained temporarily for backward-compatible clients; the API calculates
    # both amounts from administrator-managed tax profiles.
    vat_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    withholding_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[BillingLineInput] = Field(min_length=1, max_length=100)


class BillingDraftUpdate(BillingDraftCreate):
    expected_version: int = Field(gt=0)


class BillingLineResponse(ApiModel):
    id: str
    description: str
    classification: FinancialClassification
    amount: Decimal
    vat_rate: Decimal
    withholding_rate: Decimal
    vat_amount: Decimal
    withholding_amount: Decimal
    sort_order: int


class BillingResponse(ApiModel):
    id: str
    reference: str
    budget_request_id: str
    replaces_billing_id: str | None
    revision: int
    issue_date: date
    due_date: date | None
    client_address: str | None
    category: str | None
    shipper_consignee: str | None
    container_number: str | None
    destination: str | None
    vessel: str | None
    bl_awb_number: str | None
    exchange_rate: Decimal | None
    measurement: str | None
    service_subtotal: Decimal
    pass_through_subtotal: Decimal
    vat_amount: Decimal
    withholding_amount: Decimal
    total_amount: Decimal
    net_due: Decimal
    status: BillingStatus
    notes: str | None
    version: int
    submitted_at: datetime | None
    approved_at: datetime | None
    rejection_reason: str | None
    finalized_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    budget_request: BudgetRequestResponse
    prepared_by: MeResponse
    submitted_by: MeResponse | None
    approved_by: MeResponse | None
    finalized_by: MeResponse | None
    voided_by: MeResponse | None
    lines: list[BillingLineResponse]
    collected_amount: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    collection_status: str = "Unpaid"
    aging_days: int = 0
    aging_bucket: str = "Current"
    approved_credit_memo_amount: Decimal = Decimal("0.00")
    adjusted_net_due: Decimal = Decimal("0.00")


class BillingFinalize(BaseModel):
    expected_version: int = Field(gt=0)
    confirmation: str = Field(pattern=r"^FINALIZE$")


class BillingApprovalSubmit(BaseModel):
    expected_version: int = Field(gt=0)


class BillingDecision(BaseModel):
    expected_version: int = Field(gt=0)
    approve: bool
    reason: str | None = Field(default=None, max_length=2000)


class BillingVoid(BaseModel):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)


class BillingReplacementCreate(BillingDraftCreate):
    expected_version: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)


class CreditMemoCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    submit_for_approval: bool = True


class CreditMemoDecision(BaseModel):
    expected_version: int = Field(gt=0)
    approve: bool
    reason: str | None = Field(default=None, max_length=2000)


class CreditMemoResponse(ApiModel):
    id: str
    reference: str
    billing_id: str
    reason: str
    amount: Decimal
    status: CreditMemoStatus
    version: int
    created_at: datetime
    approved_at: datetime | None
    rejection_reason: str | None
    created_by: MeResponse
    approved_by: MeResponse | None


class ShipmentProfitabilityRow(BaseModel):
    budget_request_id: str
    reference: str
    shipment_reference: str
    client_name: str
    selling_amount: Decimal
    actual_spending: Decimal
    profit: Decimal
    profit_margin_percentage: Decimal | None
    liquidation_status: str
    collection_status: str
    receivables_aging_days: int | None
    outstanding_receivable: Decimal


class RequestForPaymentMonthlySummary(BaseModel):
    month: str
    opex_total: Decimal
    marketing_total: Decimal
    loan_payment_total: Decimal
    other_total: Decimal
    grand_total: Decimal
    opex_count: int
    marketing_count: int
    loan_payment_count: int
    other_count: int
    total_count: int


class ShipmentProfitabilityDashboard(BaseModel):
    shipment_count: int
    total_selling: Decimal
    total_actual_spending: Decimal
    total_profit: Decimal
    overall_margin_percentage: Decimal | None
    total_outstanding_receivable: Decimal
    request_for_payment_summary: RequestForPaymentMonthlySummary | None = None
    rows: list[ShipmentProfitabilityRow]


class PaymentAllocationInput(BaseModel):
    billing_id: str
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class ClientPaymentCreate(BaseModel):
    client_id: str
    payment_reference: str | None = Field(default=None, min_length=2, max_length=160)
    payment_method: str = Field(default="CHECK", min_length=2, max_length=40)
    check_number: str | None = Field(default=None, max_length=120)
    check_list_number: str | None = Field(default=None, max_length=120)
    receiving_bank: str = Field(min_length=2, max_length=160)
    payment_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
    allocations: list[PaymentAllocationInput] = Field(min_length=1, max_length=100)


class PaymentAllocationResponse(ApiModel):
    id: str
    billing_id: str
    amount: Decimal


class ClientPaymentResponse(ApiModel):
    id: str
    reference: str
    payment_reference: str
    payment_method: str
    check_number: str | None
    check_list_number: str | None
    receiving_bank: str
    payment_date: date
    amount: Decimal
    notes: str | None
    created_at: datetime
    client: ClientResponse
    recorded_by: MeResponse
    allocations: list[PaymentAllocationResponse]
