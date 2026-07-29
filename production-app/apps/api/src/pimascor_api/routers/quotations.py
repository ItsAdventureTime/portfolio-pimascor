from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..dependencies import AuthContext, csrf_roles_allowed, roles_allowed
from ..models import Client, QuotationStatus, Role, SalesQuotation, utc_now
from ..schemas import DecisionRequest, QuotationCreate, QuotationDecision, QuotationResponse
from ..services.audit import record_audit
from ..services.storage import (
    build_quotation_key,
    delete_document,
    put_document,
    read_verified_document,
)


router = APIRouter(prefix="/quotations", tags=["sales quotations"])


def quotation_query():
    return select(SalesQuotation).options(
        selectinload(SalesQuotation.client),
        selectinload(SalesQuotation.created_by),
        selectinload(SalesQuotation.approved_by),
    )


def get_quotation(db: Session, quotation_id: str) -> SalesQuotation:
    item = db.scalar(quotation_query().where(SalesQuotation.id == quotation_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return item


def ensure_version(item: SalesQuotation, expected: int) -> None:
    if item.version != expected:
        raise HTTPException(status_code=409, detail="This quotation changed. Refresh and review it again.")


def next_reference(db: Session) -> str:
    year = datetime.now().year
    prefix = f"SQ-{year}-"
    count = db.scalar(
        select(func.count()).select_from(SalesQuotation).where(SalesQuotation.reference.like(f"{prefix}%"))
    )
    return f"{prefix}{(count or 0) + 1:05d}"


@router.get("", response_model=list[QuotationResponse])
def list_quotations(
    context: AuthContext = Depends(roles_allowed(*list(Role))),
    db: Session = Depends(get_db),
):
    query = quotation_query().order_by(SalesQuotation.updated_at.desc())
    if context.user.role == Role.REQUESTER:
        query = query.where(SalesQuotation.created_by_id == context.user.id)
    return list(db.scalars(query).all())


@router.post("", response_model=QuotationResponse, status_code=201)
def create_quotation(
    payload: QuotationCreate,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.REQUESTER)),
    db: Session = Depends(get_db),
):
    if db.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=422, detail="Choose a configured client")
    item = SalesQuotation(
        reference=next_reference(db),
        client_id=payload.client_id,
        shipment_reference=payload.shipment_reference.strip(),
        quoted_amount=payload.quoted_amount,
        currency=payload.currency.upper(),
        terms_and_conditions=payload.terms_and_conditions.strip(),
        created_by_id=context.user.id,
    )
    db.add(item)
    db.flush()
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SALES_QUOTATION_CREATED",
        entity_type="sales_quotation",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_quotation(db, item.id)


@router.post("/{quotation_id}/submit", response_model=QuotationResponse)
def submit_quotation(
    quotation_id: str,
    expected_version: int,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.REQUESTER)),
    db: Session = Depends(get_db),
):
    item = get_quotation(db, quotation_id)
    if context.user.role == Role.REQUESTER and item.created_by_id != context.user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    ensure_version(item, expected_version)
    if item.status not in (QuotationStatus.DRAFT, QuotationStatus.REJECTED):
        raise HTTPException(status_code=409, detail="Only a draft or returned quotation can be submitted")
    item.status = QuotationStatus.PENDING_APPROVAL
    item.submitted_at = utc_now()
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SALES_QUOTATION_SUBMITTED",
        entity_type="sales_quotation",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_quotation(db, item.id)


@router.post("/{quotation_id}/decision", response_model=QuotationResponse)
def decide_quotation(
    quotation_id: str,
    payload: QuotationDecision,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.GM)),
    db: Session = Depends(get_db),
):
    item = get_quotation(db, quotation_id)
    ensure_version(item, payload.expected_version)
    if item.status != QuotationStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=409, detail="Quotation is not awaiting GM approval")
    approved = payload.approve
    if not approved and (not payload.reason or len(payload.reason.strip()) < 3):
        raise HTTPException(status_code=422, detail="Explain what the Sales Executive must correct")
    item.status = QuotationStatus.APPROVED if approved else QuotationStatus.REJECTED
    item.approved_by_id = context.user.id
    item.approved_at = utc_now()
    item.decision_reason = payload.reason
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SALES_QUOTATION_APPROVED" if approved else "SALES_QUOTATION_RETURNED",
        entity_type="sales_quotation",
        entity_id=item.id,
        reason=payload.reason,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_quotation(db, item.id)


@router.post("/{quotation_id}/dcs-override", response_model=QuotationResponse)
def override_quotation(
    quotation_id: str,
    payload: DecisionRequest,
    request: Request,
    context: AuthContext = Depends(csrf_roles_allowed(Role.DCS)),
    db: Session = Depends(get_db),
):
    if not payload.reason or len(payload.reason.strip()) < 10:
        raise HTTPException(status_code=422, detail="Explain why the GM is unavailable")
    item = get_quotation(db, quotation_id)
    ensure_version(item, payload.expected_version)
    if item.status != QuotationStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=409, detail="Quotation is not awaiting approval")
    item.status = QuotationStatus.APPROVED
    item.approved_by_id = context.user.id
    item.approved_at = utc_now()
    item.decision_reason = f"DCS override: {payload.reason.strip()}"
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SALES_QUOTATION_DCS_OVERRIDE_APPROVED",
        entity_type="sales_quotation",
        entity_id=item.id,
        reason=payload.reason.strip(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return get_quotation(db, item.id)


@router.post("/{quotation_id}/client-acceptance", response_model=QuotationResponse)
async def record_client_acceptance(
    quotation_id: str,
    request: Request,
    expected_version: int = Form(gt=0),
    accepted_on: date = Form(),
    client_signatory: str = Form(min_length=2, max_length=200),
    document: UploadFile = File(),
    context: AuthContext = Depends(csrf_roles_allowed(Role.REQUESTER)),
    db: Session = Depends(get_db),
):
    item = get_quotation(db, quotation_id)
    if context.user.role == Role.REQUESTER and item.created_by_id != context.user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    ensure_version(item, expected_version)
    if item.status != QuotationStatus.APPROVED:
        raise HTTPException(status_code=409, detail="GM approval is required before client acceptance")
    file_name, content_type, digest, size_bytes = await read_verified_document(document)
    uploaded_at = utc_now()
    key = build_quotation_key(
        quotation_id=item.id,
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
    item.status = QuotationStatus.CLIENT_ACCEPTED
    item.client_accepted_at = accepted_on
    item.client_signatory = client_signatory.strip()
    item.signed_file_name = file_name
    item.signed_storage_key = key
    item.signed_content_type = content_type
    item.signed_size_bytes = size_bytes
    item.signed_sha256 = digest
    item.version += 1
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="SALES_QUOTATION_CLIENT_ACCEPTANCE_RECORDED",
        entity_type="sales_quotation",
        entity_id=item.id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    try:
        db.commit()
    except Exception:
        delete_document(key)
        raise
    return get_quotation(db, item.id)
