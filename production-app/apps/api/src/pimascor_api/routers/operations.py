from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from ..db import get_db
from ..dependencies import AuthContext, csrf_roles_allowed, roles_allowed
from ..models import (
    Billing,
    BillingLine,
    BillingStatus,
    BudgetKind,
    BudgetRequest,
    BudgetStatus,
    ClientPayment,
    CreditMemo,
    CreditMemoStatus,
    EvidenceKind,
    ExpenseRequest,
    ExpenseStatus,
    ExpenseType,
    FinancialClassification,
    FundingSource,
    ItemKind,
    Liquidation,
    LiquidationEvidence,
    LiquidationLine,
    LiquidationStatus,
    PaymentAllocation,
    Release,
    Role,
    TaxProfile,
    User,
    uuid_string,
    utc_now,
)
from ..schemas import (
    BillingDraftCreate,
    BillingDraftUpdate,
    BillingApprovalSubmit,
    BillingDecision,
    BillingFinalize,
    BillingResponse,
    BillingVoid,
    BillingReplacementCreate,
    ClientPaymentCreate,
    ClientPaymentResponse,
    CreditMemoCreate,
    CreditMemoDecision,
    CreditMemoResponse,
    FundingSourceCreate,
    FundingSourceResponse,
    FundingSourceUpdate,
    LiquidationClose,
    LiquidationResponse,
    LiquidationSave,
    RequestForPaymentMonthlySummary,
    ShipmentProfitabilityDashboard,
    ShipmentProfitabilityRow,
    TaxProfileCreate,
    TaxProfileResponse,
)
from ..services.audit import record_audit
from ..services.storage import (
    build_document_key,
    delete_document,
    put_document,
    read_verified_document,
)


router = APIRouter(tags=["operational workflows"])


def budget_options():
    return (
        selectinload(BudgetRequest.client),
        selectinload(BudgetRequest.requester),
        selectinload(BudgetRequest.items),
    )


def liquidation_query():
    return select(Liquidation).options(
        selectinload(Liquidation.budget_request).options(*budget_options()),
        selectinload(Liquidation.requester),
        selectinload(Liquidation.closed_by),
        selectinload(Liquidation.lines),
        selectinload(Liquidation.evidence),
    )


def billing_query():
    return select(Billing).options(
        selectinload(Billing.budget_request).options(*budget_options()),
        selectinload(Billing.prepared_by),
        selectinload(Billing.submitted_by),
        selectinload(Billing.approved_by),
        selectinload(Billing.finalized_by),
        selectinload(Billing.voided_by),
        selectinload(Billing.lines),
        selectinload(Billing.allocations),
        selectinload(Billing.credit_memos).selectinload(CreditMemo.created_by),
        selectinload(Billing.credit_memos).selectinload(CreditMemo.approved_by),
    )


def get_liquidation(db: Session, liquidation_id: str) -> Liquidation:
    item = db.scalar(liquidation_query().where(Liquidation.id == liquidation_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Liquidation not found")
    return item


def get_billing(db: Session, billing_id: str) -> Billing:
    item = db.scalar(billing_query().where(Billing.id == billing_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Billing record not found")
    return item


def ensure_version(record, expected: int) -> None:
    if record.version != expected:
        raise HTTPException(
            status_code=409,
            detail=f"This record changed. Refresh and try again with version {record.version}.",
        )


def liquidation_visible(item: Liquidation, context: AuthContext) -> None:
    if context.user.role == Role.REQUESTER and item.requester_id != context.user.id:
        raise HTTPException(status_code=403, detail="Permission denied")


def billing_visible(item: Billing, context: AuthContext) -> None:
    if (
        context.user.role == Role.REQUESTER
        and item.budget_request.requester_id != context.user.id
    ):
        raise HTTPException(status_code=403, detail="Permission denied")


def billing_response(item: Billing) -> BillingResponse:
    approved_credits = sum(
        (memo.amount for memo in item.credit_memos if memo.status == CreditMemoStatus.APPROVED),
        Decimal("0.00"),
    )
    adjusted_due = max(Decimal("0.00"), item.net_due - approved_credits)
    collected = sum((allocation.amount for allocation in item.allocations), Decimal("0.00"))
    remaining = max(Decimal("0.00"), adjusted_due - collected)
    if collected == 0:
        collection_status = "Unpaid"
    elif remaining > 0:
        collection_status = "Partially Collected"
    else:
        collection_status = "Fully Collected"
    aging_days = max(0, (date.today() - item.due_date).days) if item.due_date else 0
    aging_bucket = (
        "Current" if aging_days == 0 else "1–30 days" if aging_days <= 30 else
        "31–60 days" if aging_days <= 60 else "61–90 days" if aging_days <= 90 else "Over 90 days"
    )
    result = BillingResponse.model_validate(item)
    return result.model_copy(
        update={
            "collected_amount": collected,
            "remaining_amount": remaining,
            "collection_status": collection_status,
            "aging_days": aging_days,
            "aging_bucket": aging_bucket,
            "approved_credit_memo_amount": approved_credits,
            "adjusted_net_due": adjusted_due,
        }
    )


def money_round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def tax_profiles_by_classification(db: Session) -> dict[FinancialClassification, TaxProfile]:
    rows = db.scalars(
        select(TaxProfile).where(TaxProfile.active.is_(True)).order_by(TaxProfile.created_at.desc())
    ).all()
    result: dict[FinancialClassification, TaxProfile] = {}
    for row in rows:
        result.setdefault(row.classification, row)
    return result


def calculate_billing_lines(db: Session, payload: BillingDraftCreate):
    profiles = tax_profiles_by_classification(db)
    lines: list[BillingLine] = []
    service = Decimal("0.00")
    pass_through = Decimal("0.00")
    vat_total = Decimal("0.00")
    withholding_total = Decimal("0.00")
    for index, line in enumerate(payload.lines):
        profile = profiles.get(line.classification)
        vat_rate = profile.vat_rate if profile else Decimal("0.00")
        withholding_rate = profile.withholding_rate if profile else Decimal("0.00")
        vat = money_round(line.amount * vat_rate)
        withholding = money_round(line.amount * withholding_rate)
        lines.append(BillingLine(
            description=line.description.strip(), classification=line.classification,
            amount=line.amount, vat_rate=vat_rate, withholding_rate=withholding_rate,
            vat_amount=vat, withholding_amount=withholding, sort_order=index,
        ))
        if line.classification == FinancialClassification.SERVICE_CHARGE:
            service += line.amount
        else:
            pass_through += line.amount
        vat_total += vat
        withholding_total += withholding
    return lines, service, pass_through, vat_total, withholding_total


@router.get("/dashboard/shipment-profitability", response_model=ShipmentProfitabilityDashboard)
def shipment_profitability_dashboard(
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
):
    month_value = month or date.today().strftime("%Y-%m")
    year, month_number = (int(part) for part in month_value.split("-"))
    month_start = date(year, month_number, 1)
    month_end = date(year + 1, 1, 1) if month_number == 12 else date(year, month_number + 1, 1)

    payment_summary = None
    if context.user.role in {Role.ADMIN, Role.GM, Role.DCS}:
        expense_rows = list(
            db.scalars(
                select(ExpenseRequest).where(
                    ExpenseRequest.request_date >= month_start,
                    ExpenseRequest.request_date < month_end,
                    ExpenseRequest.status != ExpenseStatus.CANCELLED,
                )
            ).all()
        )
        totals = {expense_type: Decimal("0.00") for expense_type in ExpenseType}
        counts = {expense_type: 0 for expense_type in ExpenseType}
        for expense in expense_rows:
            totals[expense.expense_type] += expense.amount
            counts[expense.expense_type] += 1
        payment_summary = RequestForPaymentMonthlySummary(
            month=month_value,
            opex_total=totals[ExpenseType.OPEX],
            marketing_total=totals[ExpenseType.MARKETING],
            loan_payment_total=totals[ExpenseType.LOAN_PAYMENT],
            other_total=totals[ExpenseType.OTHER],
            grand_total=sum(totals.values(), Decimal("0.00")),
            opex_count=counts[ExpenseType.OPEX],
            marketing_count=counts[ExpenseType.MARKETING],
            loan_payment_count=counts[ExpenseType.LOAN_PAYMENT],
            other_count=counts[ExpenseType.OTHER],
            total_count=sum(counts.values()),
        )

    budget_query = (
        select(BudgetRequest)
        .options(*budget_options())
        .where(
            BudgetRequest.budget_kind == BudgetKind.MAIN,
            BudgetRequest.request_date >= month_start,
            BudgetRequest.request_date < month_end,
            BudgetRequest.status.in_(
                [BudgetStatus.APPROVED, BudgetStatus.PARTIALLY_RELEASED, BudgetStatus.RELEASED]
            ),
        )
        .order_by(BudgetRequest.request_date.desc(), BudgetRequest.created_at.desc())
    )
    if context.user.role == Role.REQUESTER:
        budget_query = budget_query.where(BudgetRequest.requester_id == context.user.id)
    budgets = list(db.scalars(budget_query).unique().all())
    if not budgets:
        return ShipmentProfitabilityDashboard(
            shipment_count=0,
            total_selling=Decimal("0.00"),
            total_actual_spending=Decimal("0.00"),
            total_profit=Decimal("0.00"),
            overall_margin_percentage=None,
            total_outstanding_receivable=Decimal("0.00"),
            request_for_payment_summary=payment_summary,
            rows=[],
        )

    budget_ids = [item.id for item in budgets]
    additional = list(
        db.scalars(
            select(BudgetRequest).where(
                BudgetRequest.parent_budget_id.in_(budget_ids),
                BudgetRequest.status.in_(
                    [BudgetStatus.APPROVED, BudgetStatus.PARTIALLY_RELEASED, BudgetStatus.RELEASED]
                ),
            )
        ).all()
    )
    additional_by_parent: dict[str, list[BudgetRequest]] = {}
    for item in additional:
        if item.parent_budget_id:
            additional_by_parent.setdefault(item.parent_budget_id, []).append(item)

    liquidations = {
        item.budget_request_id: item
        for item in db.scalars(
            select(Liquidation).where(Liquidation.budget_request_id.in_(budget_ids))
        ).all()
    }
    billing_rows = list(
        db.scalars(
            billing_query()
            .where(
                Billing.budget_request_id.in_(budget_ids),
                Billing.status == BillingStatus.FINALIZED,
            )
            .order_by(Billing.finalized_at.desc())
        ).unique().all()
    )
    billing_by_budget: dict[str, Billing] = {}
    for item in billing_rows:
        billing_by_budget.setdefault(item.budget_request_id, item)

    rows: list[ShipmentProfitabilityRow] = []
    total_selling = Decimal("0.00")
    total_actual = Decimal("0.00")
    total_outstanding = Decimal("0.00")
    for budget in budgets:
        selling = budget.selling_total + sum(
            (item.selling_total for item in additional_by_parent.get(budget.id, [])),
            Decimal("0.00"),
        )
        liquidation = liquidations.get(budget.id)
        actual = liquidation.actual_total if liquidation else Decimal("0.00")
        profit = selling - actual
        margin = money_round((profit / selling) * Decimal("100")) if selling > 0 else None
        billing = billing_by_budget.get(budget.id)
        if billing:
            collection = billing_response(billing)
            collection_status = collection.collection_status
            outstanding = collection.remaining_amount
            aging_days = collection.aging_days if outstanding > 0 else None
        else:
            collection_status = "Not billed"
            outstanding = Decimal("0.00")
            aging_days = None
        liquidation_status = {
            LiquidationStatus.DRAFT: "Draft",
            LiquidationStatus.SUBMITTED: "Submitted",
            LiquidationStatus.PENDING_VARIANCE: "Pending variance closure",
            LiquidationStatus.CLOSED: "Closed",
        }.get(liquidation.status, "Not started") if liquidation else "Not started"
        rows.append(
            ShipmentProfitabilityRow(
                budget_request_id=budget.id,
                reference=budget.reference,
                shipment_reference=budget.shipment_reference,
                client_name=budget.client.name,
                selling_amount=selling,
                actual_spending=actual,
                profit=profit,
                profit_margin_percentage=margin,
                liquidation_status=liquidation_status,
                collection_status=collection_status,
                receivables_aging_days=aging_days,
                outstanding_receivable=outstanding,
            )
        )
        total_selling += selling
        total_actual += actual
        total_outstanding += outstanding

    total_profit = total_selling - total_actual
    overall_margin = (
        money_round((total_profit / total_selling) * Decimal("100"))
        if total_selling > 0
        else None
    )
    return ShipmentProfitabilityDashboard(
        shipment_count=len(rows),
        total_selling=total_selling,
        total_actual_spending=total_actual,
        total_profit=total_profit,
        overall_margin_percentage=overall_margin,
        total_outstanding_receivable=total_outstanding,
        request_for_payment_summary=payment_summary,
        rows=rows,
    )


@router.get("/funding-sources", response_model=list[FundingSourceResponse])
def list_funding_sources(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.DCS)),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(FundingSource).where(FundingSource.active.is_(True)).order_by(FundingSource.name)
        ).all()
    )


@router.post("/funding-sources", response_model=FundingSourceResponse, status_code=201)
def create_funding_source(
    payload: FundingSourceCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    if db.scalar(select(FundingSource).where(func.lower(FundingSource.name) == name.lower())):
        raise HTTPException(status_code=409, detail="Funding source already exists")
    item = FundingSource(name=name, active=True)
    db.add(item)
    db.flush()
    record_audit(db, actor_user_id=context.user.id, action="FUNDING_SOURCE_CREATED",
                 entity_type="funding_source", entity_id=item.id,
                 correlation_id=getattr(request.state, "correlation_id", None))
    db.commit()
    db.refresh(item)
    return item


@router.patch("/funding-sources/{source_id}", response_model=FundingSourceResponse)
def update_funding_source(
    source_id: str,
    payload: FundingSourceUpdate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    item = db.get(FundingSource, source_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Funding source not found")
    if payload.name is not None:
        name = payload.name.strip()
        duplicate = db.scalar(
            select(FundingSource).where(
                func.lower(FundingSource.name) == name.lower(),
                FundingSource.id != item.id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Funding source already exists")
        item.name = name
    if payload.active is not None:
        item.active = payload.active
    record_audit(db, actor_user_id=context.user.id, action="FUNDING_SOURCE_UPDATED",
                 entity_type="funding_source", entity_id=item.id,
                 correlation_id=getattr(request.state, "correlation_id", None),
                 reason=f"name={item.name}; active={item.active}")
    db.commit()
    db.refresh(item)
    return item


@router.get("/tax-profiles", response_model=list[TaxProfileResponse])
def list_tax_profiles(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(TaxProfile).order_by(TaxProfile.classification, TaxProfile.name)).all())


@router.post("/tax-profiles", response_model=TaxProfileResponse, status_code=201)
def create_tax_profile(
    payload: TaxProfileCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    if db.scalar(select(TaxProfile).where(func.lower(TaxProfile.name) == name.lower())):
        raise HTTPException(status_code=409, detail="Tax profile already exists")
    # One active rule per classification keeps the automatic result deterministic.
    for row in db.scalars(select(TaxProfile).where(TaxProfile.classification == payload.classification)):
        row.active = False
    item = TaxProfile(name=name, classification=payload.classification,
                      vat_rate=payload.vat_rate, withholding_rate=payload.withholding_rate, active=True)
    db.add(item)
    db.flush()
    record_audit(db, actor_user_id=context.user.id, action="TAX_PROFILE_CREATED",
                 entity_type="tax_profile", entity_id=item.id,
                 reason=f"VAT {payload.vat_rate}; withholding {payload.withholding_rate}",
                 correlation_id=getattr(request.state, "correlation_id", None))
    db.commit()
    db.refresh(item)
    return item


@router.get("/liquidations", response_model=list[LiquidationResponse])
def list_liquidations(
    context: AuthContext = Depends(roles_allowed(*list(Role))),
    db: Session = Depends(get_db),
):
    query = liquidation_query().order_by(Liquidation.updated_at.desc())
    if context.user.role == Role.REQUESTER:
        query = query.where(Liquidation.requester_id == context.user.id)
    return list(db.scalars(query).all())


@router.post("/liquidations/budget/{budget_id}", response_model=LiquidationResponse)
def save_liquidation(
    budget_id: str,
    payload: LiquidationSave,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER)),
    db: Session = Depends(get_db),
):
    if payload.evidence:
        raise HTTPException(
            status_code=422,
            detail="Upload receipt files after saving the Liquidation draft",
        )
    budget = db.scalar(select(BudgetRequest).options(*budget_options()).where(BudgetRequest.id == budget_id))
    if budget is None or budget.budget_kind != BudgetKind.MAIN:
        raise HTTPException(status_code=404, detail="Original shipment Budget Request not found")
    if context.user.role == Role.REQUESTER and budget.requester_id != context.user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    related_ids = list(
        db.scalars(
            select(BudgetRequest.id).where(
                (BudgetRequest.id == budget.id)
                | (
                    (BudgetRequest.parent_budget_id == budget.id)
                    & (BudgetRequest.status.in_([BudgetStatus.PARTIALLY_RELEASED, BudgetStatus.RELEASED]))
                )
            )
        ).all()
    )
    released_total = db.scalar(
        select(func.coalesce(func.sum(Release.amount), 0)).where(Release.budget_request_id.in_(related_ids))
    )
    if Decimal(released_total or 0) <= 0:
        raise HTTPException(status_code=409, detail="Liquidation starts only after DCS records a payment")

    item = db.scalar(select(Liquidation).where(Liquidation.budget_request_id == budget.id))
    if item is None:
        item = Liquidation(
            budget_request_id=budget.id,
            requester_id=budget.requester_id,
            released_total=Decimal(released_total),
        )
        db.add(item)
        db.flush()
    else:
        if item.status != LiquidationStatus.DRAFT:
            raise HTTPException(status_code=409, detail="Only a draft Liquidation can be edited")
        if payload.expected_version is not None:
            ensure_version(item, payload.expected_version)
        item.released_total = Decimal(released_total)
        item.lines.clear()
        item.version += 1

    item.lines = [
        LiquidationLine(description=line.description.strip(), amount=line.amount, sort_order=index)
        for index, line in enumerate(payload.lines)
    ]
    item.actual_total = sum((line.amount for line in payload.lines), Decimal("0.00"))
    item.status = LiquidationStatus.DRAFT
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="LIQUIDATION_DRAFT_SAVED",
        entity_type="liquidation",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_liquidation(db, item.id)


@router.post("/liquidations/{liquidation_id}/submit", response_model=LiquidationResponse)
def submit_liquidation(
    liquidation_id: str,
    expected_version: int,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER)),
    db: Session = Depends(get_db),
):
    item = get_liquidation(db, liquidation_id)
    liquidation_visible(item, context)
    ensure_version(item, expected_version)
    if item.status != LiquidationStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only a draft Liquidation can be submitted")
    if item.actual_total > 0 and not any(e.kind == EvidenceKind.RECEIPT for e in item.evidence):
        raise HTTPException(status_code=422, detail="Attach at least one receipt before submitting")
    item.submitted_at = utc_now()
    item.status = (
        LiquidationStatus.PENDING_VARIANCE
        if item.actual_total != item.released_total
        else LiquidationStatus.SUBMITTED
    )
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="LIQUIDATION_SUBMITTED",
        entity_type="liquidation",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_liquidation(db, item.id)


@router.post("/liquidations/{liquidation_id}/close", response_model=LiquidationResponse)
def close_liquidation(
    liquidation_id: str,
    payload: LiquidationClose,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    item = get_liquidation(db, liquidation_id)
    ensure_version(item, payload.expected_version)
    if item.status not in (LiquidationStatus.SUBMITTED, LiquidationStatus.PENDING_VARIANCE):
        raise HTTPException(status_code=409, detail="Liquidation is not ready for Mich review")
    if not payload.originals_received_confirmed:
        raise HTTPException(
            status_code=422,
            detail="Mich must confirm receipt of the original physical supporting documents",
        )
    variance = item.released_total - item.actual_total
    required = EvidenceKind.RETURN_PROOF if variance > 0 else EvidenceKind.REIMBURSEMENT_PROOF
    if variance != 0 and not any(e.kind == required for e in item.evidence):
        label = "return proof" if variance > 0 else "reimbursement proof"
        raise HTTPException(status_code=422, detail=f"Attach {label} before closing the variance")
    item.status = LiquidationStatus.CLOSED
    item.originals_received_confirmed = True
    item.originals_received_at = utc_now()
    item.closed_by_id = context.user.id
    item.closed_at = utc_now()
    item.closure_note = payload.note.strip()
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="LIQUIDATION_CLOSED",
        entity_type="liquidation",
        entity_id=item.id,
        reason=item.closure_note,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_liquidation(db, item.id)


@router.post("/liquidations/{liquidation_id}/evidence", response_model=LiquidationResponse)
async def add_liquidation_evidence(
    liquidation_id: str,
    request: Request,
    expected_version: int = Form(gt=0),
    kind: EvidenceKind = Form(),
    document: UploadFile = File(),
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER, Role.MICH)),
    db: Session = Depends(get_db),
):
    item = get_liquidation(db, liquidation_id)
    liquidation_visible(item, context)
    ensure_version(item, expected_version)
    if item.status == LiquidationStatus.CLOSED:
        raise HTTPException(status_code=409, detail="A closed Liquidation is immutable")
    if kind == EvidenceKind.RECEIPT and context.user.role not in (Role.ADMIN, Role.REQUESTER):
        raise HTTPException(status_code=403, detail="The Requester uploads Liquidation receipts")
    if kind != EvidenceKind.RECEIPT and context.user.role not in (Role.ADMIN, Role.MICH):
        raise HTTPException(status_code=403, detail="Mich uploads variance proof")

    file_name, content_type, digest, size_bytes = await read_verified_document(document)
    evidence_id = uuid_string()
    uploaded_at = utc_now()
    storage_key = build_document_key(
        evidence_id=evidence_id,
        liquidation_id=item.id,
        extension=Path(file_name).suffix,
        uploaded_at=uploaded_at,
    )
    await run_in_threadpool(
        put_document,
        key=storage_key,
        fileobj=document.file,
        content_type=content_type,
        sha256=digest,
    )
    evidence = LiquidationEvidence(
        id=evidence_id,
        kind=kind,
        file_name=file_name,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=digest,
        uploaded_by_id=context.user.id,
        uploaded_at=uploaded_at,
    )
    item.evidence.append(evidence)
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"LIQUIDATION_{kind.value}_UPLOADED",
        entity_type="liquidation",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    try:
        db.commit()
    except Exception:
        delete_document(storage_key)
        raise
    return get_liquidation(db, item.id)


@router.get("/billing", response_model=list[BillingResponse])
def list_billing(
    context: AuthContext = Depends(roles_allowed(*list(Role))),
    db: Session = Depends(get_db),
):
    query = billing_query().order_by(Billing.updated_at.desc())
    if context.user.role == Role.REQUESTER:
        query = query.join(BudgetRequest).where(
            BudgetRequest.requester_id == context.user.id,
            Billing.status == BillingStatus.FINALIZED,
        )
    return [billing_response(item) for item in db.scalars(query).unique().all()]


@router.post("/billing/budget/{budget_id}", response_model=BillingResponse, status_code=201)
def create_billing_draft(
    budget_id: str,
    payload: BillingDraftCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    budget = db.scalar(select(BudgetRequest).options(*budget_options()).where(BudgetRequest.id == budget_id))
    if budget is None or budget.budget_kind != BudgetKind.MAIN:
        raise HTTPException(status_code=404, detail="Original shipment Budget Request not found")
    if budget.status not in (
        BudgetStatus.APPROVED,
        BudgetStatus.PARTIALLY_RELEASED,
        BudgetStatus.RELEASED,
    ):
        raise HTTPException(status_code=409, detail="Billing starts only after GM approval")
    existing = db.scalar(
        select(Billing).where(
            Billing.budget_request_id == budget.id,
            Billing.status.in_(
                [
                    BillingStatus.DRAFT,
                    BillingStatus.PENDING_APPROVAL,
                    BillingStatus.APPROVED,
                    BillingStatus.FINALIZED,
                ]
            ),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="This shipment already has an active Billing record")
    lines, service, pass_through, vat_amount, withholding_amount = calculate_billing_lines(db, payload)
    total = service + pass_through + vat_amount
    net_due = total - withholding_amount
    if net_due < 0:
        raise HTTPException(status_code=422, detail="Withholding cannot exceed the Billing total")
    count = db.scalar(select(func.count()).select_from(Billing)) or 0
    item = Billing(
        reference=f"BILL-{date.today().year}-{count + 1:05d}",
        budget_request_id=budget.id,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        client_address=payload.client_address.strip() if payload.client_address else None,
        category=payload.category.strip() if payload.category else None,
        shipper_consignee=payload.shipper_consignee.strip() if payload.shipper_consignee else None,
        container_number=payload.container_number.strip() if payload.container_number else None,
        destination=payload.destination.strip() if payload.destination else None,
        vessel=payload.vessel.strip() if payload.vessel else None,
        bl_awb_number=payload.bl_awb_number.strip() if payload.bl_awb_number else None,
        exchange_rate=payload.exchange_rate,
        measurement=payload.measurement.strip() if payload.measurement else None,
        service_subtotal=service,
        pass_through_subtotal=pass_through,
        vat_amount=vat_amount,
        withholding_amount=withholding_amount,
        total_amount=total,
        net_due=net_due,
        notes=payload.notes.strip() if payload.notes else None,
        prepared_by_id=context.user.id,
    )
    item.lines = lines
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BILLING_DRAFT_CREATED",
        entity_type="billing",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.expire_all()
    return billing_response(get_billing(db, item.id))


@router.post("/billing/{billing_id}/submit", response_model=BillingResponse)
def submit_billing_for_approval(
    billing_id: str,
    payload: BillingApprovalSubmit,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    item = get_billing(db, billing_id)
    ensure_version(item, payload.expected_version)
    if item.status not in (BillingStatus.DRAFT, BillingStatus.REJECTED):
        raise HTTPException(status_code=409, detail="Only a draft or returned Billing proposal can be submitted")
    item.status = BillingStatus.PENDING_APPROVAL
    item.submitted_by_id = context.user.id
    item.submitted_at = utc_now()
    item.approved_by_id = None
    item.approved_at = None
    item.rejection_reason = None
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BILLING_SUBMITTED_FOR_GM_APPROVAL",
        entity_type="billing",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.expire_all()
    return billing_response(get_billing(db, item.id))


@router.post("/billing/{billing_id}/decision", response_model=BillingResponse)
def decide_billing(
    billing_id: str,
    payload: BillingDecision,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
):
    item = get_billing(db, billing_id)
    ensure_version(item, payload.expected_version)
    if item.status != BillingStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=409, detail="This Billing proposal is not awaiting approval")
    if not payload.approve and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=422, detail="A reason is required when returning Billing")
    if payload.approve and item.replaces_billing_id:
        original = db.get(Billing, item.replaces_billing_id)
        if original is None:
            raise HTTPException(status_code=409, detail="The original Billing record is no longer available")
        root_reference = original.reference.split("-R", 1)[0]
        item.reference = f"{root_reference}-R{item.revision}"
    item.status = BillingStatus.APPROVED if payload.approve else BillingStatus.REJECTED
    item.approved_by_id = context.user.id if payload.approve else None
    item.approved_at = utc_now() if payload.approve else None
    item.rejection_reason = payload.reason.strip() if payload.reason else None
    item.version += 1
    action_name = "APPROVED" if payload.approve else "REJECTED"
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"BILLING_{action_name}_BY_GM",
        entity_type="billing",
        entity_id=item.id,
        reason=item.rejection_reason,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.expire_all()
    return billing_response(get_billing(db, item.id))


@router.post("/billing/{billing_id}/finalize", response_model=BillingResponse)
def finalize_billing(
    billing_id: str,
    payload: BillingFinalize,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    item = get_billing(db, billing_id)
    ensure_version(item, payload.expected_version)
    if item.status != BillingStatus.APPROVED:
        raise HTTPException(status_code=409, detail="GM or Administrator approval is required before Billing can be finalized")
    if item.replaces_billing_id:
        original = db.get(Billing, item.replaces_billing_id)
        if original is not None and original.status == BillingStatus.FINALIZED:
            raise HTTPException(
                status_code=409,
                detail="The original Billing record is still finalized. An Administrator must void it before this replacement can be finalized.",
            )
    item.status = BillingStatus.FINALIZED
    item.finalized_by_id = context.user.id
    item.finalized_at = utc_now()
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BILLING_FINALIZED",
        entity_type="billing",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return billing_response(get_billing(db, item.id))


@router.patch("/billing/{billing_id}", response_model=BillingResponse)
def update_billing_draft(
    billing_id: str,
    payload: BillingDraftUpdate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    item = get_billing(db, billing_id)
    ensure_version(item, payload.expected_version)
    if item.status not in (BillingStatus.DRAFT, BillingStatus.REJECTED):
        raise HTTPException(status_code=409, detail="Submitted, approved, finalized, or voided Billing is immutable")
    lines, service, pass_through, vat_amount, withholding_amount = calculate_billing_lines(db, payload)
    total = service + pass_through + vat_amount
    net_due = total - withholding_amount
    if net_due < 0:
        raise HTTPException(status_code=422, detail="Withholding cannot exceed the Billing total")
    item.issue_date = payload.issue_date
    item.due_date = payload.due_date
    item.client_address = payload.client_address.strip() if payload.client_address else None
    item.category = payload.category.strip() if payload.category else None
    item.shipper_consignee = payload.shipper_consignee.strip() if payload.shipper_consignee else None
    item.container_number = payload.container_number.strip() if payload.container_number else None
    item.destination = payload.destination.strip() if payload.destination else None
    item.vessel = payload.vessel.strip() if payload.vessel else None
    item.bl_awb_number = payload.bl_awb_number.strip() if payload.bl_awb_number else None
    item.exchange_rate = payload.exchange_rate
    item.measurement = payload.measurement.strip() if payload.measurement else None
    item.service_subtotal = service
    item.pass_through_subtotal = pass_through
    item.vat_amount = vat_amount
    item.withholding_amount = withholding_amount
    item.total_amount = total
    item.net_due = net_due
    item.notes = payload.notes.strip() if payload.notes else None
    item.lines = lines
    item.status = BillingStatus.DRAFT
    item.rejection_reason = None
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BILLING_DRAFT_UPDATED",
        entity_type="billing",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return billing_response(get_billing(db, item.id))


@router.post("/billing/{billing_id}/void", response_model=BillingResponse)
def void_billing(
    billing_id: str,
    payload: BillingVoid,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    item = get_billing(db, billing_id)
    ensure_version(item, payload.expected_version)
    if item.status != BillingStatus.FINALIZED:
        raise HTTPException(status_code=409, detail="Only finalized Billing can be voided")
    item.status = BillingStatus.VOID
    item.voided_by_id = context.user.id
    item.voided_at = utc_now()
    item.void_reason = payload.reason.strip()
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BILLING_VOIDED",
        entity_type="billing",
        entity_id=item.id,
        reason=item.void_reason,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return billing_response(get_billing(db, item.id))


@router.post("/billing/{billing_id}/replacement", response_model=BillingResponse, status_code=201)
def create_billing_replacement(
    billing_id: str,
    payload: BillingReplacementCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    original = get_billing(db, billing_id)
    ensure_version(original, payload.expected_version)
    if original.status not in (BillingStatus.FINALIZED, BillingStatus.VOID):
        raise HTTPException(status_code=409, detail="Only finalized or voided Billing can have a replacement")
    existing = db.scalar(select(Billing).where(
        Billing.replaces_billing_id == original.id,
        Billing.status.in_(
            [
                BillingStatus.DRAFT,
                BillingStatus.PENDING_APPROVAL,
                BillingStatus.APPROVED,
                BillingStatus.FINALIZED,
            ]
        ),
    ))
    if existing:
        raise HTTPException(status_code=409, detail="A replacement draft already exists")
    lines, service, pass_through, vat_amount, withholding_amount = calculate_billing_lines(db, payload)
    total = service + pass_through + vat_amount
    net_due = total - withholding_amount
    if net_due < 0:
        raise HTTPException(status_code=422, detail="Withholding cannot exceed the Billing total")
    highest_revision = db.scalar(
        select(func.max(Billing.revision)).where(Billing.budget_request_id == original.budget_request_id)
    ) or 0
    revision = highest_revision + 1
    proposal_count = db.scalar(
        select(func.count()).select_from(Billing).where(Billing.replaces_billing_id.is_not(None))
    ) or 0
    item = Billing(
        reference=f"RPL-PROP-{date.today().year}-{proposal_count + 1:05d}",
        budget_request_id=original.budget_request_id,
        replaces_billing_id=original.id, revision=revision, issue_date=payload.issue_date,
        due_date=payload.due_date, client_address=payload.client_address,
        category=payload.category, shipper_consignee=payload.shipper_consignee,
        container_number=payload.container_number, destination=payload.destination,
        vessel=payload.vessel, bl_awb_number=payload.bl_awb_number,
        exchange_rate=payload.exchange_rate, measurement=payload.measurement,
        service_subtotal=service, pass_through_subtotal=pass_through,
        vat_amount=vat_amount, withholding_amount=withholding_amount,
        total_amount=total, net_due=net_due,
        notes=f"Replacement reason: {payload.reason.strip()}" + (f"\n{payload.notes.strip()}" if payload.notes else ""),
        prepared_by_id=context.user.id,
        status=BillingStatus.PENDING_APPROVAL,
        submitted_by_id=context.user.id,
        submitted_at=utc_now(),
    )
    item.lines = lines
    db.add(item)
    db.flush()
    record_audit(db, actor_user_id=context.user.id, action="BILLING_REPLACEMENT_PROPOSED_FOR_GM_APPROVAL",
                 entity_type="billing", entity_id=item.id, reason=payload.reason.strip(),
                 correlation_id=getattr(request.state, "correlation_id", None))
    db.commit()
    return billing_response(get_billing(db, item.id))


@router.get("/credit-memos", response_model=list[CreditMemoResponse])
def list_credit_memos(
    billing_id: str | None = None,
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM)),
    db: Session = Depends(get_db),
):
    query = select(CreditMemo).options(
        selectinload(CreditMemo.created_by), selectinload(CreditMemo.approved_by)
    ).order_by(CreditMemo.created_at.desc())
    if billing_id:
        query = query.where(CreditMemo.billing_id == billing_id)
    return list(db.scalars(query).all())


@router.post("/billing/{billing_id}/credit-memos", response_model=CreditMemoResponse, status_code=201)
def create_credit_memo(
    billing_id: str,
    payload: CreditMemoCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    billing = get_billing(db, billing_id)
    if billing.status != BillingStatus.FINALIZED:
        raise HTTPException(status_code=409, detail="Credit Memos apply only to finalized Billing")
    approved = sum((m.amount for m in billing.credit_memos if m.status == CreditMemoStatus.APPROVED), Decimal("0"))
    collected = sum((allocation.amount for allocation in billing.allocations), Decimal("0"))
    if payload.amount > billing.net_due - approved - collected:
        raise HTTPException(status_code=422, detail="Credit Memo exceeds the uncollected Billing balance")
    count = db.scalar(select(func.count()).select_from(CreditMemo)) or 0
    memo = CreditMemo(
        reference=f"CM-{date.today().year}-{count + 1:05d}", billing_id=billing.id,
        reason=payload.reason.strip(), amount=payload.amount,
        status=CreditMemoStatus.PENDING_APPROVAL,
        created_by_id=context.user.id,
    )
    db.add(memo)
    db.flush()
    record_audit(db, actor_user_id=context.user.id, action="CREDIT_MEMO_CREATED",
                 entity_type="credit_memo", entity_id=memo.id, reason=memo.reason,
                 correlation_id=getattr(request.state, "correlation_id", None))
    db.commit()
    return db.scalar(select(CreditMemo).options(
        selectinload(CreditMemo.created_by), selectinload(CreditMemo.approved_by)
    ).where(CreditMemo.id == memo.id))


@router.post("/credit-memos/{memo_id}/decision", response_model=CreditMemoResponse)
def decide_credit_memo(
    memo_id: str,
    payload: CreditMemoDecision,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
):
    memo = db.scalar(select(CreditMemo).options(
        selectinload(CreditMemo.created_by), selectinload(CreditMemo.approved_by)
    ).where(CreditMemo.id == memo_id))
    if memo is None:
        raise HTTPException(status_code=404, detail="Credit Memo not found")
    ensure_version(memo, payload.expected_version)
    if memo.status != CreditMemoStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=409, detail="Credit Memo is not awaiting approval")
    if not payload.approve and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=422, detail="A rejection reason is required")
    if payload.approve:
        billing = get_billing(db, memo.billing_id)
        approved = sum(
            (item.amount for item in billing.credit_memos if item.status == CreditMemoStatus.APPROVED),
            Decimal("0"),
        )
        collected = sum((allocation.amount for allocation in billing.allocations), Decimal("0"))
        if memo.amount > billing.net_due - approved - collected:
            raise HTTPException(
                status_code=422,
                detail="Credit Memo now exceeds the uncollected Billing balance",
            )
    memo.status = CreditMemoStatus.APPROVED if payload.approve else CreditMemoStatus.REJECTED
    memo.approved_by_id = context.user.id if payload.approve else None
    memo.approved_at = utc_now() if payload.approve else None
    memo.rejection_reason = payload.reason.strip() if payload.reason else None
    memo.version += 1
    record_audit(db, actor_user_id=context.user.id,
                 action=f"CREDIT_MEMO_{'APPROVED' if payload.approve else 'REJECTED'}",
                 entity_type="credit_memo", entity_id=memo.id, reason=memo.rejection_reason,
                 correlation_id=getattr(request.state, "correlation_id", None))
    db.commit()
    return db.scalar(select(CreditMemo).options(
        selectinload(CreditMemo.created_by), selectinload(CreditMemo.approved_by)
    ).where(CreditMemo.id == memo.id))


@router.get("/receivables", response_model=list[BillingResponse])
def list_receivables(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        billing_query().where(Billing.status == BillingStatus.FINALIZED).order_by(Billing.due_date)
    ).unique().all()
    return [billing_response(item) for item in items]


@router.post("/client-payments", response_model=ClientPaymentResponse, status_code=201)
def create_client_payment(
    payload: ClientPaymentCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
):
    total_allocated = sum((item.amount for item in payload.allocations), Decimal("0.00"))
    if total_allocated > payload.amount:
        raise HTTPException(status_code=422, detail="Allocations cannot exceed the received payment")
    if len({item.billing_id for item in payload.allocations}) != len(payload.allocations):
        raise HTTPException(status_code=422, detail="Each Billing record may be allocated only once")
    billing_items = {
        item.id: item
        for item in db.scalars(
            billing_query().where(Billing.id.in_([row.billing_id for row in payload.allocations]))
        ).unique().all()
    }
    for allocation in payload.allocations:
        billing = billing_items.get(allocation.billing_id)
        if billing is None or billing.status != BillingStatus.FINALIZED:
            raise HTTPException(status_code=422, detail="Allocation must reference finalized Billing")
        if billing.budget_request.client_id != payload.client_id:
            raise HTTPException(status_code=422, detail="All allocations must belong to the selected client")
        current = sum((row.amount for row in billing.allocations), Decimal("0.00"))
        approved_credits = sum(
            (memo.amount for memo in billing.credit_memos if memo.status == CreditMemoStatus.APPROVED),
            Decimal("0.00"),
        )
        if allocation.amount > billing.net_due - approved_credits - current:
            raise HTTPException(status_code=422, detail=f"Allocation exceeds {billing.reference}'s balance")
    method = payload.payment_method.strip().upper()
    supplied_reference = payload.payment_reference.strip() if payload.payment_reference else None
    if method == "CHECK" and not payload.check_number:
        raise HTTPException(status_code=422, detail="Check number is required for a check payment")
    if method not in {"CHECK", "CASH"} and not supplied_reference:
        raise HTTPException(status_code=422, detail="Enter the bank or transfer reference")
    count = db.scalar(select(func.count()).select_from(ClientPayment)) or 0
    register_reference = f"COL-{date.today().year}-{count + 1:05d}"
    external_reference = supplied_reference or (
        f"CHECK-{payload.check_number.strip()}" if payload.check_number else register_reference
    )
    duplicate = db.scalar(
        select(ClientPayment).where(ClientPayment.payment_reference == external_reference)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="This check or payment reference is already recorded")
    payment = ClientPayment(
        reference=register_reference,
        client_id=payload.client_id,
        payment_reference=external_reference,
        payment_method=method,
        check_number=payload.check_number.strip() if payload.check_number else None,
        check_list_number=payload.check_list_number.strip() if payload.check_list_number else None,
        receiving_bank=payload.receiving_bank.strip(),
        payment_date=payload.payment_date,
        amount=payload.amount,
        notes=payload.notes.strip() if payload.notes else None,
        recorded_by_id=context.user.id,
    )
    payment.allocations = [
        PaymentAllocation(billing_id=row.billing_id, amount=row.amount) for row in payload.allocations
    ]
    db.add(payment)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="CLIENT_PAYMENT_RECORDED",
        entity_type="client_payment",
        entity_id=payment.id,
        reason=f"Allocated {total_allocated:.2f} of {payload.amount:.2f}",
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return db.scalar(
        select(ClientPayment)
        .options(
            selectinload(ClientPayment.client),
            selectinload(ClientPayment.recorded_by),
            selectinload(ClientPayment.allocations),
        )
        .where(ClientPayment.id == payment.id)
    )


@router.get("/client-payments", response_model=list[ClientPaymentResponse])
def list_client_payments(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
):
    """Return the attributable collection/check register without exposing it to Requesters."""
    return list(
        db.scalars(
            select(ClientPayment)
            .options(
                selectinload(ClientPayment.client),
                selectinload(ClientPayment.recorded_by),
                selectinload(ClientPayment.allocations),
            )
            .order_by(ClientPayment.payment_date.desc(), ClientPayment.created_at.desc())
        ).unique().all()
    )
