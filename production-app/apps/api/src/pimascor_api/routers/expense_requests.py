from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..dependencies import AuthContext, csrf_roles_allowed, roles_allowed
from ..models import (
    ExpenseDecision,
    ExpenseDisbursement,
    ExpenseRequest,
    ExpenseStatus,
    ExpenseType,
    ExpenseValidation,
    FundingSource,
    PaymentStatus,
    Role,
)
from ..schemas import (
    DecisionRequest,
    ExpenseDisbursementCreate,
    ExpenseRequestCreate,
    ExpenseRequestResponse,
    ExpenseValidationCreate,
)
from ..services.audit import record_audit


router = APIRouter(prefix="/expense-requests", tags=["expense requests"])


def expense_query():
    return select(ExpenseRequest).options(
        selectinload(ExpenseRequest.requester),
        selectinload(ExpenseRequest.disbursement),
        selectinload(ExpenseRequest.validation),
    )


def get_expense_or_404(db: Session, expense_id: str) -> ExpenseRequest:
    expense = db.scalar(expense_query().where(ExpenseRequest.id == expense_id))
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense request not found")
    return expense


def require_version(expense: ExpenseRequest, expected: int) -> None:
    if expense.version != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This record changed. Refresh and try again with version {expense.version}.",
        )


def ensure_visible(expense: ExpenseRequest, context: AuthContext) -> None:
    if context.user.role == Role.REQUESTER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def next_reference(db: Session, expense_type: ExpenseType) -> str:
    prefix_by_type = {
        ExpenseType.OPEX: "OPEX",
        ExpenseType.MARKETING: "MKT",
        ExpenseType.LOAN_PAYMENT: "LOAN",
        ExpenseType.OTHER: "RFP",
    }
    prefix = f"{prefix_by_type[expense_type]}-{datetime.now().year}-"
    count = db.scalar(
        select(func.count())
        .select_from(ExpenseRequest)
        .where(ExpenseRequest.reference.like(f"{prefix}%"))
    )
    return f"{prefix}{(count or 0) + 1:05d}"


@router.get("", response_model=list[ExpenseRequestResponse])
def list_expense_requests(
    expense_type: ExpenseType | None = Query(default=None, alias="type"),
    expense_status: ExpenseStatus | None = Query(default=None, alias="status"),
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
) -> list[ExpenseRequest]:
    query = expense_query().order_by(ExpenseRequest.updated_at.desc())
    if expense_type:
        query = query.where(ExpenseRequest.expense_type == expense_type)
    if expense_status:
        query = query.where(ExpenseRequest.status == expense_status)
    if context.user.role == Role.MICH:
        query = query.where(ExpenseRequest.requester_id == context.user.id)
    return list(db.scalars(query).all())


@router.get("/approval-queue", response_model=list[ExpenseRequestResponse])
def approval_queue(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.GM)),
    db: Session = Depends(get_db),
) -> list[ExpenseRequest]:
    return list(
        db.scalars(
            expense_query()
            .where(ExpenseRequest.status == ExpenseStatus.PENDING_APPROVAL)
            .order_by(ExpenseRequest.updated_at)
        ).all()
    )


@router.get("/disbursement-queue", response_model=list[ExpenseRequestResponse])
def disbursement_queue(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.DCS)),
    db: Session = Depends(get_db),
) -> list[ExpenseRequest]:
    return list(
        db.scalars(
            expense_query()
            .where(ExpenseRequest.status == ExpenseStatus.APPROVED)
            .order_by(ExpenseRequest.updated_at)
        ).all()
    )


@router.get("/validation-queue", response_model=list[ExpenseRequestResponse])
def validation_queue(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> list[ExpenseRequest]:
    return list(
        db.scalars(
            expense_query()
            .where(
                ExpenseRequest.expense_type == ExpenseType.LOAN_PAYMENT,
                ExpenseRequest.status == ExpenseStatus.PENDING_VALIDATION,
            )
            .order_by(ExpenseRequest.updated_at)
        ).all()
    )


@router.get("/{expense_id}", response_model=ExpenseRequestResponse)
def get_expense_request(
    expense_id: str,
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    expense = get_expense_or_404(db, expense_id)
    ensure_visible(expense, context)
    return expense


@router.post("", response_model=ExpenseRequestResponse, status_code=status.HTTP_201_CREATED)
def create_expense_request(
    payload: ExpenseRequestCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    expense = ExpenseRequest(
        reference=next_reference(db, payload.expense_type),
        expense_type=payload.expense_type,
        requester_id=context.user.id,
        request_date=payload.request_date,
        due_date=payload.due_date,
        party=payload.party.strip(),
        purpose=payload.purpose.strip(),
        requested_source=payload.requested_source.strip() if payload.requested_source else None,
        loan_reference=payload.loan_reference.strip() if payload.loan_reference else None,
        currency=payload.currency,
        principal_amount=payload.principal_amount,
        interest_amount=payload.interest_amount,
        penalties_fees_amount=payload.penalties_fees_amount,
        amount=payload.amount,
    )
    db.add(expense)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"{payload.expense_type.value}_REQUEST_CREATED",
        entity_type="expense_request",
        entity_id=expense.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_expense_or_404(db, expense.id)


@router.post("/{expense_id}/submit", response_model=ExpenseRequestResponse)
def submit_expense_request(
    expense_id: str,
    expected_version: int,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    expense = get_expense_or_404(db, expense_id)
    ensure_visible(expense, context)
    require_version(expense, expected_version)
    if expense.status not in (ExpenseStatus.DRAFT, ExpenseStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a draft or rejected request can be submitted",
        )
    expense.status = ExpenseStatus.PENDING_APPROVAL
    expense.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"{expense.expense_type.value}_REQUEST_SUBMITTED",
        entity_type="expense_request",
        entity_id=expense.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_expense_or_404(db, expense.id)


def decide_expense(
    *,
    expense_id: str,
    payload: DecisionRequest,
    outcome: str,
    request: Request,
    context: AuthContext,
    db: Session,
) -> ExpenseRequest:
    expense = get_expense_or_404(db, expense_id)
    require_version(expense, payload.expected_version)
    if expense.status != ExpenseStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not awaiting approval")
    if outcome == "REJECTED" and not payload.reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rejection reason is required")
    expense.status = ExpenseStatus.APPROVED if outcome == "APPROVED" else ExpenseStatus.REJECTED
    expense.payment_status = PaymentStatus.PENDING if outcome == "APPROVED" else PaymentStatus.NOT_READY
    expense.version += 1
    db.add(
        ExpenseDecision(
            expense_request_id=expense.id,
            actor_user_id=context.user.id,
            outcome=outcome,
            reason=payload.reason,
        )
    )
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"{expense.expense_type.value}_REQUEST_{outcome}",
        entity_type="expense_request",
        entity_id=expense.id,
        reason=payload.reason,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_expense_or_404(db, expense.id)


@router.post("/{expense_id}/approve", response_model=ExpenseRequestResponse)
def approve_expense_request(
    expense_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    return decide_expense(
        expense_id=expense_id,
        payload=payload,
        outcome="APPROVED",
        request=request,
        context=context,
        db=db,
    )


@router.post("/{expense_id}/reject", response_model=ExpenseRequestResponse)
def reject_expense_request(
    expense_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    return decide_expense(
        expense_id=expense_id,
        payload=payload,
        outcome="REJECTED",
        request=request,
        context=context,
        db=db,
    )


@router.post("/{expense_id}/disburse", response_model=ExpenseRequestResponse)
def disburse_expense_request(
    expense_id: str,
    payload: ExpenseDisbursementCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.DCS)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    expense = get_expense_or_404(db, expense_id)
    require_version(expense, payload.expected_version)
    if expense.status != ExpenseStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an approved request can be disbursed")
    if expense.payment_status not in (PaymentStatus.PENDING, PaymentStatus.ON_HOLD):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not pending payment")
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
    expense.disbursement = ExpenseDisbursement(
        amount=expense.amount,
        mode=payload.mode.strip(),
        source=payload.source.strip(),
        paid_to=payload.paid_to.strip(),
        transaction_reference=payload.transaction_reference.strip(),
        disbursed_by_id=context.user.id,
    )
    expense.status = ExpenseStatus.DISBURSED
    expense.payment_status = PaymentStatus.PAID
    expense.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"{expense.expense_type.value}_DISBURSED",
        entity_type="expense_request",
        entity_id=expense.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_expense_or_404(db, expense.id)


@router.post("/{expense_id}/validate", response_model=ExpenseRequestResponse)
def validate_loan_payment(
    expense_id: str,
    payload: ExpenseValidationCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> ExpenseRequest:
    expense = get_expense_or_404(db, expense_id)
    require_version(expense, payload.expected_version)
    if expense.expense_type != ExpenseType.LOAN_PAYMENT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only legacy Loan Payments can use this compatibility endpoint")
    if expense.status != ExpenseStatus.PENDING_VALIDATION:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loan Payment is not awaiting validation")
    expense.validation = ExpenseValidation(
        validated_by_id=context.user.id,
        notes=payload.notes,
    )
    expense.status = ExpenseStatus.VALIDATED
    expense.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="LOAN_PAYMENT_VALIDATED",
        entity_type="expense_request",
        entity_id=expense.id,
        reason=payload.notes,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_expense_or_404(db, expense.id)
