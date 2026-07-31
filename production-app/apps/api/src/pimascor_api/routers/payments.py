from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..dependencies import AuthContext, csrf_roles_allowed, roles_allowed
from ..models import (
    ApprovalDecision,
    BudgetKind,
    BudgetRequest,
    BudgetStatus,
    BudgetSubmission,
    ExpenseDecision,
    ExpenseDisbursement,
    ExpenseRequest,
    ExpenseStatus,
    ExpenseType,
    FundingSource,
    Liquidation,
    LiquidationStatus,
    PaymentAnnotation,
    PaymentStatus,
    Release,
    Role,
    User,
    utc_now,
)
from ..schemas import PaymentActionRequest, PaymentCreate, PaymentQueueItem
from ..services.audit import record_audit
from ..services.storage import build_payment_proof_key, delete_document, put_document, read_verified_document


router = APIRouter(prefix="/dcs-payments", tags=["DCS payments"])


def budget_payment_query():
    return select(BudgetRequest).options(
        selectinload(BudgetRequest.client),
        selectinload(BudgetRequest.requester),
        selectinload(BudgetRequest.parent_budget),
        selectinload(BudgetRequest.payment_annotations).selectinload(PaymentAnnotation.actor),
    )


def expense_payment_query():
    return select(ExpenseRequest).options(
        selectinload(ExpenseRequest.requester),
        selectinload(ExpenseRequest.disbursement),
        selectinload(ExpenseRequest.payment_annotations).selectinload(PaymentAnnotation.actor),
    )


def approved_budget_actor(db: Session, budget_id: str) -> tuple[str | None, object | None]:
    row = db.execute(
        select(User.display_name, ApprovalDecision.decided_at)
        .join(ApprovalDecision, ApprovalDecision.actor_user_id == User.id)
        .join(BudgetSubmission, BudgetSubmission.id == ApprovalDecision.submission_id)
        .where(
            BudgetSubmission.budget_request_id == budget_id,
            ApprovalDecision.outcome.in_(("APPROVED", "DCS_OVERRIDE_APPROVED")),
        )
        .order_by(ApprovalDecision.decided_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else (None, None)


def approved_expense_actor(db: Session, expense_id: str) -> tuple[str | None, object | None]:
    row = db.execute(
        select(User.display_name, ExpenseDecision.decided_at)
        .join(ExpenseDecision, ExpenseDecision.actor_user_id == User.id)
        .where(
            ExpenseDecision.expense_request_id == expense_id,
            ExpenseDecision.outcome == "APPROVED",
        )
        .order_by(ExpenseDecision.decided_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else (None, None)


def budget_item(db: Session, budget: BudgetRequest) -> PaymentQueueItem:
    approved_by, approved_at = approved_budget_actor(db, budget.id)
    latest_payment = db.scalar(
        select(Release).where(Release.budget_request_id == budget.id).order_by(Release.released_at.desc()).limit(1)
    )
    return PaymentQueueItem(
        source_type=(
            "ADDITIONAL_BUDGET" if budget.budget_kind == BudgetKind.ADDITIONAL else "BUDGET_REQUEST"
        ),
        record_id=budget.id,
        reference=budget.reference,
        parent_reference=budget.parent_budget.reference if budget.parent_budget else None,
        party=budget.client.name,
        purpose=budget.additional_reason or budget.shipment_reference,
        requester=budget.requester.display_name,
        amount_due=budget.buying_total,
        paid_amount=budget.released_total,
        outstanding_amount=budget.buying_total - budget.released_total,
        currency=budget.currency,
        payment_status=budget.payment_status,
        approved_by=approved_by,
        approved_at=approved_at,
        funding_source=latest_payment.source if latest_payment else None,
        payment_method=latest_payment.mode if latest_payment else None,
        transaction_reference=latest_payment.transaction_reference if latest_payment else None,
        paid_on=latest_payment.paid_on if latest_payment else None,
        proof_file_name=latest_payment.proof_file_name if latest_payment else None,
        proof_available=bool(latest_payment and latest_payment.proof_storage_key),
        version=budget.version,
        annotations=sorted(budget.payment_annotations, key=lambda item: item.created_at, reverse=True),
    )


def expense_item(db: Session, expense: ExpenseRequest) -> PaymentQueueItem:
    approved_by, approved_at = approved_expense_actor(db, expense.id)
    paid_amount = expense.disbursement.amount if expense.disbursement else Decimal("0.00")
    source_types = {
        ExpenseType.OPEX: "OPEX",
        ExpenseType.MARKETING: "MARKETING",
        ExpenseType.LOAN_PAYMENT: "LOAN_PAYMENT",
        ExpenseType.OTHER: "OTHER",
    }
    return PaymentQueueItem(
        source_type=source_types[expense.expense_type],
        record_id=expense.id,
        reference=expense.reference,
        party=expense.party,
        purpose=expense.purpose,
        requester=expense.requester.display_name,
        amount_due=expense.amount,
        paid_amount=paid_amount,
        outstanding_amount=expense.amount - paid_amount,
        currency=expense.currency,
        payment_status=expense.payment_status,
        due_date=expense.due_date,
        approved_by=approved_by,
        approved_at=approved_at,
        funding_source=expense.disbursement.source if expense.disbursement else None,
        payment_method=expense.disbursement.mode if expense.disbursement else None,
        transaction_reference=expense.disbursement.transaction_reference if expense.disbursement else None,
        paid_on=expense.disbursement.paid_on if expense.disbursement else None,
        proof_file_name=expense.disbursement.proof_file_name if expense.disbursement else None,
        proof_available=bool(expense.disbursement and expense.disbursement.proof_storage_key),
        version=expense.version,
        annotations=sorted(expense.payment_annotations, key=lambda item: item.created_at, reverse=True),
    )


def get_source(db: Session, source_type: str, record_id: str) -> BudgetRequest | ExpenseRequest:
    if source_type == "budget":
        record = db.scalar(budget_payment_query().where(BudgetRequest.id == record_id))
    elif source_type == "expense":
        record = db.scalar(expense_payment_query().where(ExpenseRequest.id == record_id))
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment source not found")
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment source not found")
    return record


def as_queue_item(db: Session, record: BudgetRequest | ExpenseRequest) -> PaymentQueueItem:
    return budget_item(db, record) if isinstance(record, BudgetRequest) else expense_item(db, record)


@router.get("", response_model=list[PaymentQueueItem])
def list_payments(
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.DCS, Role.GM, Role.MICH)),
    db: Session = Depends(get_db),
) -> list[PaymentQueueItem]:
    budget_query = budget_payment_query().where(BudgetRequest.payment_status != PaymentStatus.NOT_READY)
    expense_query = expense_payment_query().where(ExpenseRequest.payment_status != PaymentStatus.NOT_READY)
    if payment_status:
        budget_query = budget_query.where(BudgetRequest.payment_status == payment_status)
        expense_query = expense_query.where(ExpenseRequest.payment_status == payment_status)
    items = [budget_item(db, item) for item in db.scalars(budget_query).all()]
    items.extend(expense_item(db, item) for item in db.scalars(expense_query).all())
    return sorted(
        items,
        key=lambda item: (
            item.payment_status == PaymentStatus.PAID,
            item.due_date is None,
            item.due_date.isoformat() if item.due_date else "9999-12-31",
            item.reference,
        ),
    )


@router.post("/{source_type}/{record_id}/actions", response_model=PaymentQueueItem)
def payment_action(
    source_type: str,
    record_id: str,
    payload: PaymentActionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.DCS, Role.GM)),
    db: Session = Depends(get_db),
) -> PaymentQueueItem:
    record = get_source(db, source_type, record_id)
    if record.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This record changed. Refresh and try again with version {record.version}.",
        )

    current = record.payment_status
    if payload.action == "HOLD":
        if current not in (PaymentStatus.PENDING, PaymentStatus.PARTIALLY_PAID):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a pending payment can be held")
        record.payment_status = PaymentStatus.ON_HOLD
    elif payload.action == "RETURN":
        if current not in (PaymentStatus.PENDING, PaymentStatus.PARTIALLY_PAID, PaymentStatus.ON_HOLD):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment cannot be returned from its current state")
        record.payment_status = PaymentStatus.RETURNED
    elif payload.action == "RESUME":
        if current != PaymentStatus.ON_HOLD:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a held payment can be resumed")
        record.payment_status = (
            PaymentStatus.PARTIALLY_PAID
            if isinstance(record, BudgetRequest) and record.released_total > 0
            else PaymentStatus.PENDING
        )

    if context.user.role == Role.GM and len(payload.note.strip()) < 10:
        raise HTTPException(status_code=422, detail="A General Manager payment override requires a reason of at least 10 characters")
    action_prefix = "GM_PAYMENT_OVERRIDE" if context.user.role == Role.GM else "DCS_PAYMENT"
    annotation = PaymentAnnotation(
        actor_user_id=context.user.id,
        event_type=payload.action,
        note=payload.note.strip(),
        budget_request_id=record.id if isinstance(record, BudgetRequest) else None,
        expense_request_id=record.id if isinstance(record, ExpenseRequest) else None,
    )
    db.add(annotation)
    record.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"{action_prefix}_{payload.action}",
        entity_type="budget_request" if isinstance(record, BudgetRequest) else "expense_request",
        entity_id=record.id,
        reason=payload.note.strip(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.expire_all()
    record = get_source(db, source_type, record_id)
    return as_queue_item(db, record)


@router.post("/{source_type}/{record_id}/pay", response_model=PaymentQueueItem)
def record_payment(
    source_type: str,
    record_id: str,
    payload: PaymentCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.DCS, Role.GM)),
    db: Session = Depends(get_db),
) -> PaymentQueueItem:
    if context.user.role == Role.GM and (not payload.notes or len(payload.notes.strip()) < 10):
        raise HTTPException(status_code=422, detail="A General Manager payment override requires a reason of at least 10 characters")
    record = get_source(db, source_type, record_id)
    if record.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This record changed. Refresh and try again with version {record.version}.",
        )
    if record.payment_status not in (PaymentStatus.PENDING, PaymentStatus.PARTIALLY_PAID):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item is not pending payment")
    duplicate = db.scalar(
        select(Release.id).where(Release.transaction_reference == payload.transaction_reference)
    ) or db.scalar(
        select(ExpenseDisbursement.id).where(
            ExpenseDisbursement.transaction_reference == payload.transaction_reference
        )
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction reference already exists")
    funding_source = db.scalar(
        select(FundingSource).where(
            FundingSource.name == payload.source.strip(), FundingSource.active.is_(True)
        )
    )
    if funding_source is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose an active funding source configured by an Administrator",
        )

    if isinstance(record, BudgetRequest):
        remaining = record.buying_total - record.released_total
        if payload.amount > remaining:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Payment exceeds the outstanding amount of {remaining:.2f} {record.currency}",
            )
        db.add(
            Release(
                budget_request_id=record.id,
                amount=payload.amount,
                mode=payload.mode.strip(),
                source=payload.source.strip(),
                recipient=payload.recipient.strip(),
                transaction_reference=payload.transaction_reference.strip(),
                paid_on=payload.paid_on,
                notes=payload.notes.strip() if payload.notes else None,
                released_by_id=context.user.id,
            )
        )
        record.released_total += payload.amount
        fully_paid = record.released_total == record.buying_total
        record.status = BudgetStatus.RELEASED if fully_paid else BudgetStatus.PARTIALLY_RELEASED
        record.payment_status = PaymentStatus.PAID if fully_paid else PaymentStatus.PARTIALLY_PAID
        db.flush()

        original_id = record.parent_budget_id or record.id
        original = record.parent_budget if record.parent_budget_id else record
        released_total = db.scalar(
            select(func.coalesce(func.sum(BudgetRequest.released_total), 0)).where(
                (BudgetRequest.id == original_id) | (BudgetRequest.parent_budget_id == original_id)
            )
        )
        liquidation = db.scalar(
            select(Liquidation).where(Liquidation.budget_request_id == original_id)
        )
        if liquidation is None:
            db.add(
                Liquidation(
                    budget_request_id=original_id,
                    requester_id=original.requester_id,
                    released_total=Decimal(released_total or 0),
                )
            )
        elif liquidation.status != LiquidationStatus.CLOSED:
            liquidation.released_total = Decimal(released_total or 0)
            if liquidation.status != LiquidationStatus.DRAFT:
                liquidation.status = LiquidationStatus.PENDING_VARIANCE
            liquidation.version += 1
    else:
        if payload.amount != record.amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="OPEX, Marketing, and Loan Payments must be paid in full",
            )
        record.disbursement = ExpenseDisbursement(
            amount=payload.amount,
            mode=payload.mode.strip(),
            source=payload.source.strip(),
            paid_to=payload.recipient.strip(),
            transaction_reference=payload.transaction_reference.strip(),
            paid_on=payload.paid_on,
            notes=payload.notes.strip() if payload.notes else None,
            disbursed_by_id=context.user.id,
        )
        record.status = ExpenseStatus.DISBURSED
        record.payment_status = PaymentStatus.PAID

    db.add(
        PaymentAnnotation(
            actor_user_id=context.user.id,
            event_type="PAID",
            note=(payload.notes or f"Paid by {payload.mode} with reference {payload.transaction_reference}").strip(),
            budget_request_id=record.id if isinstance(record, BudgetRequest) else None,
            expense_request_id=record.id if isinstance(record, ExpenseRequest) else None,
        )
    )
    record.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="GM_PAYMENT_OVERRIDE_RECORDED" if context.user.role == Role.GM else "DCS_PAYMENT_RECORDED",
        entity_type="budget_request" if isinstance(record, BudgetRequest) else "expense_request",
        entity_id=record.id,
        reason=payload.notes,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.expire_all()
    record = get_source(db, source_type, record_id)
    return as_queue_item(db, record)


@router.post("/{source_type}/{record_id}/proof", response_model=PaymentQueueItem)
async def upload_payment_proof(
    source_type: str,
    record_id: str,
    request: Request,
    expected_version: int = Form(gt=0),
    document: UploadFile = File(),
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.DCS, Role.GM)),
    db: Session = Depends(get_db),
) -> PaymentQueueItem:
    record = get_source(db, source_type, record_id)
    if record.version != expected_version:
        raise HTTPException(status_code=409, detail="This payment record changed. Refresh and try again.")
    if record.payment_status not in (PaymentStatus.PAID, PaymentStatus.PARTIALLY_PAID):
        raise HTTPException(status_code=409, detail="Record the payment before attaching its proof")
    if isinstance(record, BudgetRequest):
        payment = db.scalar(
            select(Release)
            .where(Release.budget_request_id == record.id)
            .order_by(Release.released_at.desc())
            .limit(1)
        )
    else:
        payment = record.disbursement
    if payment is None:
        raise HTTPException(status_code=409, detail="The payment record could not be found")
    file_name, content_type, digest, size_bytes = await read_verified_document(document)
    uploaded_at = utc_now()
    key = build_payment_proof_key(
        source_type=source_type,
        record_id=record.id,
        extension=Path(file_name).suffix,
        uploaded_at=uploaded_at,
    )
    await run_in_threadpool(
        put_document,
        key=key,
        fileobj=document.file,
        content_type=content_type,
        sha256=digest,
    )
    old_key = payment.proof_storage_key
    payment.proof_file_name = file_name
    payment.proof_storage_key = key
    payment.proof_content_type = content_type
    payment.proof_size_bytes = size_bytes
    payment.proof_sha256 = digest
    record.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="GM_PAYMENT_OVERRIDE_PROOF_UPLOADED" if context.user.role == Role.GM else "DCS_PAYMENT_PROOF_UPLOADED",
        entity_type="budget_request" if isinstance(record, BudgetRequest) else "expense_request",
        entity_id=record.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    try:
        db.commit()
    except Exception:
        delete_document(key)
        raise
    if old_key:
        delete_document(old_key)
    db.expire_all()
    return as_queue_item(db, get_source(db, source_type, record_id))
