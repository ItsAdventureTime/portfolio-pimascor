from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..dependencies import AuthContext, csrf_roles_allowed, roles_allowed
from ..models import (
    ApprovalDecision,
    BudgetKind,
    BudgetItem,
    BudgetRequest,
    BudgetStatus,
    BudgetSubmission,
    Client,
    ItemKind,
    PaymentStatus,
    QuotationStatus,
    Release,
    Role,
    SalesQuotation,
)
from ..schemas import (
    AdditionalBudgetCreate,
    BudgetRequestCreate,
    BudgetRequestResponse,
    BudgetRequestUpdate,
    ClientCreate,
    ClientResponse,
    DecisionRequest,
    ReleaseCreate,
    ReleaseResponse,
)
from ..services.audit import record_audit


router = APIRouter(tags=["budget requests"])


def budget_query():
    return select(BudgetRequest).options(
        selectinload(BudgetRequest.client),
        selectinload(BudgetRequest.requester),
        selectinload(BudgetRequest.reviewed_by),
        selectinload(BudgetRequest.items),
    )


def get_budget_or_404(db: Session, budget_id: str) -> BudgetRequest:
    budget = db.scalar(budget_query().where(BudgetRequest.id == budget_id))
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget request not found")
    return budget


def require_version(budget: BudgetRequest, expected: int) -> None:
    if budget.version != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This record changed. Refresh and try again with version {budget.version}.",
        )


def next_reference(db: Session, budget_kind: BudgetKind = BudgetKind.MAIN) -> str:
    year = datetime.now().year
    prefix = f"{'ABR' if budget_kind == BudgetKind.ADDITIONAL else 'BR'}-{year}-"
    count = db.scalar(select(func.count()).select_from(BudgetRequest).where(BudgetRequest.reference.like(f"{prefix}%")))
    return f"{prefix}{(count or 0) + 1:05d}"


@router.get("/clients", response_model=list[ClientResponse])
def list_clients(
    _: AuthContext = Depends(roles_allowed(*list(Role))), db: Session = Depends(get_db)
) -> list[Client]:
    return list(db.scalars(select(Client).order_by(Client.name)).all())


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> Client:
    code = payload.code.strip().upper()
    existing = db.scalar(select(Client).where((Client.code == code) | (Client.name == payload.name.strip())))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client already exists")
    client = Client(code=code, name=payload.name.strip())
    db.add(client)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="CLIENT_CREATED",
        entity_type="client",
        entity_id=client.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(client)
    return client


@router.get("/budget-requests", response_model=list[BudgetRequestResponse])
def list_budget_requests(
    budget_status: BudgetStatus | None = Query(default=None, alias="status"),
    context: AuthContext = Depends(roles_allowed(*list(Role))),
    db: Session = Depends(get_db),
) -> list[BudgetRequest]:
    query = budget_query().order_by(BudgetRequest.updated_at.desc())
    if budget_status:
        query = query.where(BudgetRequest.status == budget_status)
    if context.user.role == Role.REQUESTER:
        query = query.where(BudgetRequest.requester_id == context.user.id)
    return list(db.scalars(query).all())


@router.get("/budget-requests/{budget_id}", response_model=BudgetRequestResponse)
def get_budget_request(
    budget_id: str,
    context: AuthContext = Depends(roles_allowed(*list(Role))),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    budget = get_budget_or_404(db, budget_id)
    if context.user.role == Role.REQUESTER and budget.requester_id != context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return budget


@router.post("/budget-requests", response_model=BudgetRequestResponse, status_code=status.HTTP_201_CREATED)
def create_budget_request(
    payload: BudgetRequestCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    if db.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client does not exist")
    quotation = db.get(SalesQuotation, payload.quotation_id) if payload.quotation_id else None
    if quotation and (
        quotation.status != QuotationStatus.CLIENT_ACCEPTED
        or quotation.client_id != payload.client_id
        or quotation.shipment_reference != payload.shipment_reference.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="Choose a client-accepted quotation for this client and shipment reference",
        )

    buying = sum((item.amount for item in payload.items if item.kind == ItemKind.BUYING), Decimal("0.00"))
    selling = sum((item.amount for item in payload.items if item.kind == ItemKind.SELLING), Decimal("0.00"))
    budget = BudgetRequest(
        reference=next_reference(db),
        budget_kind=BudgetKind.MAIN,
        client_id=payload.client_id,
        quotation_id=quotation.id if quotation else None,
        shipment_reference=payload.shipment_reference.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        request_date=payload.request_date,
        requester_id=context.user.id,
        currency=payload.currency,
        buying_total=buying,
        selling_total=selling,
    )
    budget.items = [
        BudgetItem(
            kind=item.kind,
            description=item.description.strip(),
            classification=item.classification,
            amount=item.amount,
            sort_order=index,
        )
        for index, item in enumerate(payload.items)
    ]
    db.add(budget)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BUDGET_REQUEST_CREATED",
        entity_type="budget_request",
        entity_id=budget.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.patch("/budget-requests/{budget_id}", response_model=BudgetRequestResponse)
def update_budget_request(
    budget_id: str,
    payload: BudgetRequestUpdate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    budget = get_budget_or_404(db, budget_id)
    if context.user.role == Role.REQUESTER and budget.requester_id != context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    require_version(budget, payload.expected_version)
    if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a draft or returned Budget Request can be edited",
        )

    if budget.budget_kind == BudgetKind.MAIN:
        if payload.client_id is None or payload.shipment_reference is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Client and shipment reference are required",
            )
        if db.get(Client, payload.client_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client does not exist")
        budget.client_id = payload.client_id
        if payload.quotation_id:
            quotation = db.get(SalesQuotation, payload.quotation_id)
            if (
                quotation is None
                or quotation.status != QuotationStatus.CLIENT_ACCEPTED
                or quotation.client_id != payload.client_id
                or quotation.shipment_reference != payload.shipment_reference.strip()
            ):
                raise HTTPException(status_code=422, detail="Choose a matching client-accepted quotation")
            budget.quotation_id = quotation.id
        budget.shipment_reference = payload.shipment_reference.strip()
    else:
        if not payload.reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The reason for the Additional Budget is required",
            )
        budget.additional_reason = payload.reason.strip()
        budget.related_expense_description = (
            payload.related_expense_description.strip()
            if payload.related_expense_description
            else None
        )
        budget.related_expense_amount = payload.related_expense_amount

    budget.request_date = payload.request_date
    budget.currency = payload.currency
    budget.notes = payload.notes.strip() if payload.notes else None
    budget.buying_total = sum(
        (item.amount for item in payload.items if item.kind == ItemKind.BUYING),
        Decimal("0.00"),
    )
    budget.selling_total = sum(
        (item.amount for item in payload.items if item.kind == ItemKind.SELLING),
        Decimal("0.00"),
    )
    budget.items = [
        BudgetItem(
            kind=item.kind,
            description=item.description.strip(),
            classification=item.classification,
            amount=item.amount,
            sort_order=index,
        )
        for index, item in enumerate(payload.items)
    ]
    budget.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=(
            "ADDITIONAL_BUDGET_UPDATED"
            if budget.budget_kind == BudgetKind.ADDITIONAL
            else "BUDGET_REQUEST_UPDATED"
        ),
        entity_type="budget_request",
        entity_id=budget.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.post(
    "/budget-requests/{parent_id}/additional-budgets",
    response_model=BudgetRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_additional_budget(
    parent_id: str,
    payload: AdditionalBudgetCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    parent = get_budget_or_404(db, parent_id)
    if parent.budget_kind != BudgetKind.MAIN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An Additional Budget must link to the original shipment Budget Request",
        )
    if parent.status not in (
        BudgetStatus.APPROVED,
        BudgetStatus.PARTIALLY_RELEASED,
        BudgetStatus.RELEASED,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The original shipment Budget Request must be approved first",
        )
    if context.user.role == Role.REQUESTER and parent.requester_id != context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    buying = sum((item.amount for item in payload.items if item.kind == ItemKind.BUYING), Decimal("0.00"))
    selling = sum((item.amount for item in payload.items if item.kind == ItemKind.SELLING), Decimal("0.00"))
    budget = BudgetRequest(
        reference=next_reference(db, BudgetKind.ADDITIONAL),
        budget_kind=BudgetKind.ADDITIONAL,
        parent_budget_id=parent.id,
        additional_reason=payload.reason.strip(),
        related_expense_description=(
            payload.related_expense_description.strip()
            if payload.related_expense_description
            else None
        ),
        related_expense_amount=payload.related_expense_amount,
        client_id=parent.client_id,
        quotation_id=parent.quotation_id,
        shipment_reference=parent.shipment_reference,
        request_date=payload.request_date,
        requester_id=context.user.id,
        currency=parent.currency,
        buying_total=buying,
        selling_total=selling,
    )
    budget.items = [
        BudgetItem(
            kind=item.kind,
            description=item.description.strip(),
            classification=item.classification,
            amount=item.amount,
            sort_order=index,
        )
        for index, item in enumerate(payload.items)
    ]
    db.add(budget)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="ADDITIONAL_BUDGET_CREATED",
        entity_type="budget_request",
        entity_id=budget.id,
        reason=budget.additional_reason,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.post("/budget-requests/{budget_id}/submit", response_model=BudgetRequestResponse)
def submit_budget_request(
    budget_id: str,
    expected_version: int,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.REQUESTER)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    budget = get_budget_or_404(db, budget_id)
    if context.user.role == Role.REQUESTER and budget.requester_id != context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    require_version(budget, expected_version)
    if budget.status not in (BudgetStatus.DRAFT, BudgetStatus.REJECTED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a draft or rejected request can be submitted")
    budget.status = BudgetStatus.PENDING_REVIEW
    budget.reviewed_by_id = None
    budget.reviewed_at = None
    budget.review_note = None
    budget.version += 1
    db.add(BudgetSubmission(budget_request_id=budget.id, version=budget.version, submitted_by_id=context.user.id))
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BUDGET_REQUEST_SUBMITTED_FOR_MICH_REVIEW",
        entity_type="budget_request",
        entity_id=budget.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.get("/budget-reviews/queue", response_model=list[BudgetRequestResponse])
def budget_review_queue(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.MICH)),
    db: Session = Depends(get_db),
) -> list[BudgetRequest]:
    return list(
        db.scalars(
            budget_query()
            .where(BudgetRequest.status == BudgetStatus.PENDING_REVIEW)
            .order_by(BudgetRequest.updated_at)
        ).all()
    )


@router.post("/budget-reviews/{budget_id}/review", response_model=BudgetRequestResponse)
def review_budget_request(
    budget_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.MICH)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    budget = get_budget_or_404(db, budget_id)
    require_version(budget, payload.expected_version)
    if budget.status != BudgetStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not awaiting Mich review")
    budget.status = BudgetStatus.PENDING_APPROVAL
    budget.reviewed_by = context.user
    budget.reviewed_at = datetime.now().astimezone()
    budget.review_note = payload.reason.strip() if payload.reason else None
    budget.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BUDGET_REQUEST_REVIEWED_BY_MICH",
        entity_type="budget_request",
        entity_id=budget.id,
        reason=budget.review_note,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.post("/budget-reviews/{budget_id}/return", response_model=BudgetRequestResponse)
def return_budget_from_review(
    budget_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.MICH)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Explain what the Requester must correct")
    budget = get_budget_or_404(db, budget_id)
    require_version(budget, payload.expected_version)
    if budget.status != BudgetStatus.PENDING_REVIEW:
        raise HTTPException(status_code=409, detail="Request is not awaiting Mich review")
    budget.status = BudgetStatus.REJECTED
    budget.reviewed_by = context.user
    budget.reviewed_at = datetime.now().astimezone()
    budget.review_note = payload.reason.strip()
    budget.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BUDGET_REQUEST_RETURNED_BY_MICH",
        entity_type="budget_request",
        entity_id=budget.id,
        reason=budget.review_note,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.get("/approvals/queue", response_model=list[BudgetRequestResponse])
def approval_queue(
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.GM, Role.DCS)),
    db: Session = Depends(get_db),
) -> list[BudgetRequest]:
    statuses = [BudgetStatus.PENDING_APPROVAL]
    if context.user.role == Role.DCS:
        statuses.append(BudgetStatus.PENDING_REVIEW)
    return list(
        db.scalars(
            budget_query()
            .where(BudgetRequest.status.in_(statuses))
            .order_by(BudgetRequest.updated_at)
        ).all()
    )


@router.post("/approvals/{budget_id}/dcs-override", response_model=BudgetRequestResponse)
def dcs_override_budget(
    budget_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.DCS)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    if not payload.reason or len(payload.reason.strip()) < 10:
        raise HTTPException(
            status_code=422,
            detail="Record why the normal Mich or GM approval stage is unavailable",
        )
    budget = get_budget_or_404(db, budget_id)
    require_version(budget, payload.expected_version)
    if budget.status not in (BudgetStatus.PENDING_REVIEW, BudgetStatus.PENDING_APPROVAL):
        raise HTTPException(status_code=409, detail="Request is not awaiting a stage DCS can override")
    submission = db.scalar(
        select(BudgetSubmission)
        .where(BudgetSubmission.budget_request_id == budget.id)
        .order_by(BudgetSubmission.submitted_at.desc())
    )
    if submission is None:
        raise HTTPException(status_code=409, detail="Submission record is missing")
    budget.status = BudgetStatus.APPROVED
    budget.payment_status = PaymentStatus.PENDING
    if budget.reviewed_by_id is None:
        budget.reviewed_by = context.user
    budget.reviewed_at = budget.reviewed_at or datetime.now().astimezone()
    budget.review_note = budget.review_note or "DCS emergency override"
    budget.version += 1
    db.add(
        ApprovalDecision(
            submission_id=submission.id,
            actor_user_id=context.user.id,
            outcome="DCS_OVERRIDE_APPROVED",
            reason=payload.reason.strip(),
        )
    )
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="BUDGET_REQUEST_DCS_OVERRIDE_APPROVED",
        entity_type="budget_request",
        entity_id=budget.id,
        reason=payload.reason.strip(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


def decide(
    db: Session,
    budget: BudgetRequest,
    context: AuthContext,
    outcome: str,
    reason: str | None,
    correlation_id: str | None,
) -> BudgetRequest:
    submission = db.scalar(
        select(BudgetSubmission)
        .where(BudgetSubmission.budget_request_id == budget.id)
        .order_by(BudgetSubmission.submitted_at.desc())
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission record is missing")
    budget.status = BudgetStatus.APPROVED if outcome == "APPROVED" else BudgetStatus.REJECTED
    budget.payment_status = PaymentStatus.PENDING if outcome == "APPROVED" else PaymentStatus.NOT_READY
    budget.version += 1
    db.add(
        ApprovalDecision(
            submission_id=submission.id,
            actor_user_id=context.user.id,
            outcome=outcome,
            reason=reason,
        )
    )
    record_audit(
        db,
        actor_user_id=context.user.id,
        action=f"BUDGET_REQUEST_{outcome}",
        entity_type="budget_request",
        entity_id=budget.id,
        correlation_id=correlation_id,
        reason=reason,
    )
    db.commit()
    return get_budget_or_404(db, budget.id)


@router.post("/approvals/{budget_id}/approve", response_model=BudgetRequestResponse)
def approve_budget(
    budget_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    budget = get_budget_or_404(db, budget_id)
    require_version(budget, payload.expected_version)
    if budget.status != BudgetStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not awaiting approval")
    return decide(db, budget, context, "APPROVED", payload.reason, getattr(request.state, "correlation_id", None))


@router.post("/approvals/{budget_id}/reject", response_model=BudgetRequestResponse)
def reject_budget(
    budget_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
) -> BudgetRequest:
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A rejection reason is required")
    budget = get_budget_or_404(db, budget_id)
    require_version(budget, payload.expected_version)
    if budget.status != BudgetStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not awaiting approval")
    return decide(db, budget, context, "REJECTED", payload.reason.strip(), getattr(request.state, "correlation_id", None))


@router.get("/releases/queue", response_model=list[BudgetRequestResponse])
def release_queue(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.DCS)), db: Session = Depends(get_db)
) -> list[BudgetRequest]:
    return list(
        db.scalars(
            budget_query()
            .where(
                BudgetRequest.status.in_([BudgetStatus.APPROVED, BudgetStatus.PARTIALLY_RELEASED]),
                BudgetRequest.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.PARTIALLY_PAID]),
            )
            .order_by(BudgetRequest.updated_at)
        ).all()
    )


@router.post("/budget-requests/{budget_id}/releases", response_model=ReleaseResponse, status_code=status.HTTP_201_CREATED)
def create_release(
    budget_id: str,
    payload: ReleaseCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.ADMIN, Role.DCS)),
    db: Session = Depends(get_db),
) -> Release:
    budget = get_budget_or_404(db, budget_id)
    require_version(budget, payload.expected_version)
    if budget.status not in (BudgetStatus.APPROVED, BudgetStatus.PARTIALLY_RELEASED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not approved for release")
    remaining = budget.buying_total - budget.released_total
    if payload.amount > remaining:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Release exceeds the available amount of {remaining:.2f} {budget.currency}")
    duplicate = db.scalar(select(Release).where(Release.transaction_reference == payload.transaction_reference))
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction reference already exists")

    release = Release(
        budget_request_id=budget.id,
        amount=payload.amount,
        mode=payload.mode.strip(),
        source=payload.source.strip(),
        recipient=payload.recipient.strip(),
        transaction_reference=payload.transaction_reference.strip(),
        paid_on=payload.paid_on,
        notes=payload.notes.strip() if payload.notes else None,
        released_by_id=context.user.id,
    )
    budget.released_total += payload.amount
    budget.status = BudgetStatus.RELEASED if budget.released_total == budget.buying_total else BudgetStatus.PARTIALLY_RELEASED
    budget.payment_status = (
        PaymentStatus.PAID
        if budget.released_total == budget.buying_total
        else PaymentStatus.PARTIALLY_PAID
    )
    budget.version += 1
    db.add(release)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="FUNDS_RELEASED",
        entity_type="release",
        entity_id=release.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(release)
    return release


@router.get("/budget-requests/{budget_id}/releases", response_model=list[ReleaseResponse])
def list_releases(
    budget_id: str,
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.DCS, Role.GM, Role.MICH)),
    db: Session = Depends(get_db),
) -> list[Release]:
    get_budget_or_404(db, budget_id)
    return list(db.scalars(select(Release).where(Release.budget_request_id == budget_id).order_by(Release.released_at)).all())
