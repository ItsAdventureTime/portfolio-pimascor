from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uuid_string() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    REQUESTER = "REQUESTER"
    GM = "GM"
    DCS = "DCS"
    MICH = "MICH"


class BudgetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIALLY_RELEASED = "PARTIALLY_RELEASED"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"


class BudgetKind(str, enum.Enum):
    MAIN = "MAIN"
    ADDITIONAL = "ADDITIONAL"


class QuotationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLIENT_ACCEPTED = "CLIENT_ACCEPTED"


class PaymentStatus(str, enum.Enum):
    NOT_READY = "NOT_READY"
    PENDING = "PENDING"
    ON_HOLD = "ON_HOLD"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    RETURNED = "RETURNED"


class ItemKind(str, enum.Enum):
    BUYING = "BUYING"
    SELLING = "SELLING"


class FinancialClassification(str, enum.Enum):
    SERVICE_CHARGE = "SERVICE_CHARGE"
    PASS_THROUGH = "PASS_THROUGH"


class ExpenseType(str, enum.Enum):
    OPEX = "OPEX"
    MARKETING = "MARKETING"
    LOAN_PAYMENT = "LOAN_PAYMENT"
    OTHER = "OTHER"


class ExpenseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISBURSED = "DISBURSED"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    VALIDATED = "VALIDATED"
    CANCELLED = "CANCELLED"


class LiquidationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_VARIANCE = "PENDING_VARIANCE"
    CLOSED = "CLOSED"


class EvidenceKind(str, enum.Enum):
    RECEIPT = "RECEIPT"
    RETURN_PROOF = "RETURN_PROOF"
    REIMBURSEMENT_PROOF = "REIMBURSEMENT_PROOF"
    PHYSICAL_RECEIPTS_PHOTO = "PHYSICAL_RECEIPTS_PHOTO"


class BillingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FINALIZED = "FINALIZED"
    VOID = "VOID"


class CreditMemoStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class IncidentSource(str, enum.Enum):
    CLIENT = "CLIENT"
    SERVER = "SERVER"


class IncidentSeverity(str, enum.Enum):
    RECOVERABLE = "RECOVERABLE"
    BLOCKING = "BLOCKING"


class IncidentStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    DISMISSED = "DISMISSED"
    CLOSED_BY_USER = "CLOSED_BY_USER"


class IncidentDecision(str, enum.Enum):
    CONTINUED = "CONTINUED"
    STOPPED = "STOPPED"
    DISMISSED = "DISMISSED"


class DataExportStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(512))
    must_set_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.REQUESTER)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    sessions: Mapped[list[LoginSession]] = relationship(back_populates="user")


class LoginSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="sessions")


class EmailChallenge(Base):
    __tablename__ = "email_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(40), default="LOGIN")
    code_hash: Mapped[str] = mapped_column(String(512))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FundingSource(Base):
    __tablename__ = "funding_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesQuotation(Base):
    __tablename__ = "sales_quotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    reference: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    shipment_reference: Mapped[str] = mapped_column(String(120), index=True)
    quoted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="PHP")
    terms_and_conditions: Mapped[str] = mapped_column(Text)
    status: Mapped[QuotationStatus] = mapped_column(
        Enum(QuotationStatus), default=QuotationStatus.DRAFT, index=True
    )
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    client_accepted_at: Mapped[date | None] = mapped_column(Date)
    client_signatory: Mapped[str | None] = mapped_column(String(200))
    signed_file_name: Mapped[str | None] = mapped_column(String(240))
    signed_storage_key: Mapped[str | None] = mapped_column(String(500))
    signed_content_type: Mapped[str | None] = mapped_column(String(120))
    signed_size_bytes: Mapped[int | None] = mapped_column(Integer)
    signed_sha256: Mapped[str | None] = mapped_column(String(64))
    mode_of_transport: Mapped[str | None] = mapped_column(String(40))
    container_type: Mapped[str | None] = mapped_column(String(40))
    origin: Mapped[str | None] = mapped_column(String(160))
    destination: Mapped[str | None] = mapped_column(String(160))
    incoterms: Mapped[str | None] = mapped_column(String(40))
    cargo_details: Mapped[str | None] = mapped_column(String(500))
    payment_terms: Mapped[str | None] = mapped_column(String(500))
    validity_hours: Mapped[int] = mapped_column(Integer, default=48)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    client: Mapped[Client] = relationship()
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id])
    lines: Mapped[list[SalesQuotationLine]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan", order_by="SalesQuotationLine.position"
    )


class SalesQuotationLine(Base):
    __tablename__ = "sales_quotation_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("sales_quotations.id"), index=True)
    section: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(300))
    currency: Mapped[str] = mapped_column(String(3))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    billed_by: Mapped[str] = mapped_column(String(30), default="PIMASCOR")
    position: Mapped[int] = mapped_column(Integer, default=0)

    quotation: Mapped[SalesQuotation] = relationship(back_populates="lines")


class TaxProfile(Base):
    __tablename__ = "tax_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    classification: Mapped[FinancialClassification] = mapped_column(Enum(FinancialClassification), index=True)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), default=Decimal("0.000000"))
    withholding_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), default=Decimal("0.000000"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BudgetRequest(Base):
    __tablename__ = "budget_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    budget_kind: Mapped[BudgetKind] = mapped_column(Enum(BudgetKind), default=BudgetKind.MAIN, index=True)
    parent_budget_id: Mapped[str | None] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    additional_reason: Mapped[str | None] = mapped_column(Text)
    related_expense_description: Mapped[str | None] = mapped_column(Text)
    related_expense_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    quotation_id: Mapped[str | None] = mapped_column(ForeignKey("sales_quotations.id"), index=True)
    shipment_reference: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    request_date: Mapped[date] = mapped_column(Date, default=date.today)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    currency: Mapped[str] = mapped_column(String(3), default="PHP")
    buying_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    selling_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    released_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    status: Mapped[BudgetStatus] = mapped_column(Enum(BudgetStatus), default=BudgetStatus.DRAFT)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.NOT_READY, index=True
    )
    reviewed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    client: Mapped[Client] = relationship()
    quotation: Mapped[SalesQuotation | None] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    parent_budget: Mapped[BudgetRequest | None] = relationship(
        remote_side="BudgetRequest.id", back_populates="additional_budgets"
    )
    additional_budgets: Mapped[list[BudgetRequest]] = relationship(back_populates="parent_budget")
    items: Mapped[list[BudgetItem]] = relationship(back_populates="budget_request", cascade="all, delete-orphan")
    payment_annotations: Mapped[list[PaymentAnnotation]] = relationship(
        back_populates="budget_request", cascade="all, delete-orphan"
    )


class BudgetItem(Base):
    __tablename__ = "budget_request_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    budget_request_id: Mapped[str] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    kind: Mapped[ItemKind] = mapped_column(Enum(ItemKind))
    description: Mapped[str] = mapped_column(String(240))
    classification: Mapped[FinancialClassification] = mapped_column(
        Enum(FinancialClassification), default=FinancialClassification.SERVICE_CHARGE
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    budget_request: Mapped[BudgetRequest] = relationship(back_populates="items")


class BudgetSubmission(Base):
    __tablename__ = "budget_submissions"
    __table_args__ = (UniqueConstraint("budget_request_id", "version", name="uq_submission_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    budget_request_id: Mapped[str] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    submitted_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    submission_id: Mapped[str] = mapped_column(ForeignKey("budget_submissions.id"), index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    budget_request_id: Mapped[str] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    mode: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(160), default="Unspecified funding source")
    recipient: Mapped[str] = mapped_column(String(160))
    transaction_reference: Mapped[str] = mapped_column(String(120), unique=True)
    paid_on: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text)
    proof_file_name: Mapped[str | None] = mapped_column(String(240))
    proof_storage_key: Mapped[str | None] = mapped_column(String(500))
    proof_content_type: Mapped[str | None] = mapped_column(String(120))
    proof_size_bytes: Mapped[int | None] = mapped_column(Integer)
    proof_sha256: Mapped[str | None] = mapped_column(String(64))
    released_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExpenseRequest(Base):
    __tablename__ = "expense_requests"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        CheckConstraint("principal_amount >= 0", name="ck_expense_principal_nonnegative"),
        CheckConstraint("interest_amount >= 0", name="ck_expense_interest_nonnegative"),
        CheckConstraint("penalties_fees_amount >= 0", name="ck_expense_fees_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    expense_type: Mapped[ExpenseType] = mapped_column(Enum(ExpenseType), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date)
    party: Mapped[str] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(Text)
    requested_source: Mapped[str | None] = mapped_column(String(160))
    loan_reference: Mapped[str | None] = mapped_column(String(160))
    currency: Mapped[str] = mapped_column(String(3), default="PHP")
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    interest_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    penalties_fees_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[ExpenseStatus] = mapped_column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT, index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.NOT_READY, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    requester: Mapped[User] = relationship()
    decisions: Mapped[list[ExpenseDecision]] = relationship(
        back_populates="expense_request", cascade="all, delete-orphan"
    )
    disbursement: Mapped[ExpenseDisbursement | None] = relationship(
        back_populates="expense_request", cascade="all, delete-orphan", uselist=False
    )
    validation: Mapped[ExpenseValidation | None] = relationship(
        back_populates="expense_request", cascade="all, delete-orphan", uselist=False
    )
    payment_annotations: Mapped[list[PaymentAnnotation]] = relationship(
        back_populates="expense_request", cascade="all, delete-orphan"
    )


class ExpenseDecision(Base):
    __tablename__ = "expense_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    expense_request_id: Mapped[str] = mapped_column(ForeignKey("expense_requests.id"), index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    expense_request: Mapped[ExpenseRequest] = relationship(back_populates="decisions")


class ExpenseDisbursement(Base):
    __tablename__ = "expense_disbursements"
    __table_args__ = (
        UniqueConstraint("expense_request_id", name="uq_expense_disbursement_request"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    expense_request_id: Mapped[str] = mapped_column(ForeignKey("expense_requests.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    mode: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(160))
    paid_to: Mapped[str] = mapped_column(String(200))
    transaction_reference: Mapped[str] = mapped_column(String(160), unique=True)
    paid_on: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text)
    proof_file_name: Mapped[str | None] = mapped_column(String(240))
    proof_storage_key: Mapped[str | None] = mapped_column(String(500))
    proof_content_type: Mapped[str | None] = mapped_column(String(120))
    proof_size_bytes: Mapped[int | None] = mapped_column(Integer)
    proof_sha256: Mapped[str | None] = mapped_column(String(64))
    disbursed_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    disbursed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    expense_request: Mapped[ExpenseRequest] = relationship(back_populates="disbursement")


class ExpenseValidation(Base):
    __tablename__ = "expense_validations"
    __table_args__ = (UniqueConstraint("expense_request_id", name="uq_expense_validation_request"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    expense_request_id: Mapped[str] = mapped_column(ForeignKey("expense_requests.id"), index=True)
    validated_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    expense_request: Mapped[ExpenseRequest] = relationship(back_populates="validation")


class PaymentAnnotation(Base):
    __tablename__ = "payment_annotations"
    __table_args__ = (
        CheckConstraint(
            "(budget_request_id IS NOT NULL AND expense_request_id IS NULL) OR "
            "(budget_request_id IS NULL AND expense_request_id IS NOT NULL)",
            name="ck_payment_annotation_one_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    budget_request_id: Mapped[str | None] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    expense_request_id: Mapped[str | None] = mapped_column(ForeignKey("expense_requests.id"), index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), default="NOTE")
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    budget_request: Mapped[BudgetRequest | None] = relationship(back_populates="payment_annotations")
    expense_request: Mapped[ExpenseRequest | None] = relationship(back_populates="payment_annotations")
    actor: Mapped[User] = relationship()


class Liquidation(Base):
    __tablename__ = "liquidations"
    __table_args__ = (UniqueConstraint("budget_request_id", name="uq_liquidation_budget"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    budget_request_id: Mapped[str] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[LiquidationStatus] = mapped_column(
        Enum(LiquidationStatus), default=LiquidationStatus.DRAFT, index=True
    )
    released_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    actual_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    originals_received_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    originals_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closure_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    budget_request: Mapped[BudgetRequest] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    closed_by: Mapped[User | None] = relationship(foreign_keys=[closed_by_id])
    lines: Mapped[list[LiquidationLine]] = relationship(
        back_populates="liquidation", cascade="all, delete-orphan"
    )
    evidence: Mapped[list[LiquidationEvidence]] = relationship(
        back_populates="liquidation", cascade="all, delete-orphan"
    )


class LiquidationLine(Base):
    __tablename__ = "liquidation_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    liquidation_id: Mapped[str] = mapped_column(ForeignKey("liquidations.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    liquidation: Mapped[Liquidation] = relationship(back_populates="lines")


class LiquidationEvidence(Base):
    __tablename__ = "liquidation_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    liquidation_id: Mapped[str] = mapped_column(ForeignKey("liquidations.id"), index=True)
    kind: Mapped[EvidenceKind] = mapped_column(Enum(EvidenceKind))
    file_name: Mapped[str] = mapped_column(String(240))
    storage_key: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    liquidation: Mapped[Liquidation] = relationship(back_populates="evidence")
    uploaded_by: Mapped[User] = relationship()


class Billing(Base):
    __tablename__ = "billing_records"
    __table_args__ = (UniqueConstraint("reference", name="uq_billing_reference"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    reference: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    budget_request_id: Mapped[str] = mapped_column(ForeignKey("budget_requests.id"), index=True)
    replaces_billing_id: Mapped[str | None] = mapped_column(ForeignKey("billing_records.id"))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    issue_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date)
    client_address: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    shipper_consignee: Mapped[str | None] = mapped_column(String(240))
    container_number: Mapped[str | None] = mapped_column(String(120))
    destination: Mapped[str | None] = mapped_column(String(160))
    vessel: Mapped[str | None] = mapped_column(String(160))
    bl_awb_number: Mapped[str | None] = mapped_column(String(160))
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    measurement: Mapped[str | None] = mapped_column(String(120))
    service_subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    pass_through_subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    withholding_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    net_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BillingStatus] = mapped_column(Enum(BillingStatus), default=BillingStatus.DRAFT, index=True)
    prepared_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    submitted_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    finalized_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    budget_request: Mapped[BudgetRequest] = relationship()
    replaces_billing: Mapped[Billing | None] = relationship(remote_side="Billing.id")
    prepared_by: Mapped[User] = relationship(foreign_keys=[prepared_by_id])
    submitted_by: Mapped[User | None] = relationship(foreign_keys=[submitted_by_id])
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id])
    finalized_by: Mapped[User | None] = relationship(foreign_keys=[finalized_by_id])
    voided_by: Mapped[User | None] = relationship(foreign_keys=[voided_by_id])
    lines: Mapped[list[BillingLine]] = relationship(back_populates="billing", cascade="all, delete-orphan")
    allocations: Mapped[list[PaymentAllocation]] = relationship(back_populates="billing")
    credit_memos: Mapped[list[CreditMemo]] = relationship(back_populates="billing")


class BillingLine(Base):
    __tablename__ = "billing_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    billing_id: Mapped[str] = mapped_column(ForeignKey("billing_records.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    classification: Mapped[FinancialClassification] = mapped_column(Enum(FinancialClassification))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), default=Decimal("0.000000"))
    withholding_rate: Mapped[Decimal] = mapped_column(Numeric(7, 6), default=Decimal("0.000000"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    withholding_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    billing: Mapped[Billing] = relationship(back_populates="lines")


class ClientPayment(Base):
    __tablename__ = "client_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    reference: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    payment_reference: Mapped[str] = mapped_column(String(160), unique=True)
    payment_method: Mapped[str] = mapped_column(String(40), default="CHECK")
    check_number: Mapped[str | None] = mapped_column(String(120), index=True)
    check_list_number: Mapped[str | None] = mapped_column(String(120))
    receiving_bank: Mapped[str] = mapped_column(String(160))
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    client: Mapped[Client] = relationship()
    recorded_by: Mapped[User] = relationship()
    allocations: Mapped[list[PaymentAllocation]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        UniqueConstraint("payment_id", "billing_id", name="uq_payment_billing_allocation"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    payment_id: Mapped[str] = mapped_column(ForeignKey("client_payments.id"), index=True)
    billing_id: Mapped[str] = mapped_column(ForeignKey("billing_records.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    payment: Mapped[ClientPayment] = relationship(back_populates="allocations")
    billing: Mapped[Billing] = relationship(back_populates="allocations")


class CreditMemo(Base):
    __tablename__ = "credit_memos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    reference: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    billing_id: Mapped[str] = mapped_column(ForeignKey("billing_records.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[CreditMemoStatus] = mapped_column(
        Enum(CreditMemoStatus), default=CreditMemoStatus.DRAFT, index=True
    )
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    billing: Mapped[Billing] = relationship(back_populates="credit_memos")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id])


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class DataExport(Base):
    __tablename__ = "data_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    requested_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[DataExportStatus] = mapped_column(
        Enum(DataExportStatus), default=DataExportStatus.QUEUED, index=True
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    file_name: Mapped[str | None] = mapped_column(String(240))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    requested_by: Mapped[User] = relationship()


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    client_report_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    source: Mapped[IncidentSource] = mapped_column(Enum(IncidentSource), index=True)
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity), index=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.REPORTED, index=True
    )
    operation: Mapped[str] = mapped_column(String(160))
    user_action: Mapped[str] = mapped_column(Text)
    user_message: Mapped[str] = mapped_column(Text)
    recovery_suggestion: Mapped[str] = mapped_column(Text)
    can_continue: Mapped[bool] = mapped_column(Boolean, default=False)
    page_path: Mapped[str] = mapped_column(String(240))
    request_method: Mapped[str | None] = mapped_column(String(12))
    request_path: Mapped[str | None] = mapped_column(String(240))
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str] = mapped_column(String(100), index=True)
    technical_summary: Mapped[str | None] = mapped_column(Text)
    client_runtime: Mapped[str | None] = mapped_column(String(80))
    deployment_tier: Mapped[str] = mapped_column(String(20))
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    email_admin_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_developer_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision: Mapped[IncidentDecision | None] = mapped_column(Enum(IncidentDecision))
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    actor: Mapped[User | None] = relationship()
