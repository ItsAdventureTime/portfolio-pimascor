import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..dependencies import AuthContext, roles_allowed
from ..models import (
    BudgetRequest,
    ExpenseDisbursement,
    ExpenseRequest,
    Liquidation,
    LiquidationEvidence,
    Release,
    Role,
    SalesQuotation,
    User,
)
from ..schemas import DocumentLibraryResponse, MeResponse
from ..services.audit import record_audit
from ..services.storage import open_document, storage_configured


router = APIRouter(prefix="/documents", tags=["private documents"])
BYTE_RANGE = re.compile(r"bytes=(\d*)-(\d*)$")


@dataclass
class StoredDocument:
    id: str
    entity_type: str
    entity_id: str
    kind: str
    file_name: str
    storage_key: str
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    uploaded_at: datetime
    reference: str
    client_name: str
    uploaded_by: User
    owner_user_id: str | None


def requested_byte_range(value: str | None, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    match = BYTE_RANGE.fullmatch(value.strip())
    if not match or not any(match.groups()):
        raise HTTPException(
            status_code=416,
            detail="Requested document range is not available",
            headers={"Content-Range": f"bytes */{size}"},
        )
    start_value, end_value = match.groups()
    if not start_value:
        suffix_length = int(end_value)
        if suffix_length <= 0:
            raise HTTPException(
                status_code=416,
                detail="Requested document range is not available",
                headers={"Content-Range": f"bytes */{size}"},
            )
        return max(0, size - suffix_length), size - 1
    start = int(start_value)
    end = int(end_value) if end_value else size - 1
    if start >= size or end < start:
        raise HTTPException(
            status_code=416,
            detail="Requested document range is not available",
            headers={"Content-Range": f"bytes */{size}"},
        )
    return start, min(end, size - 1)


def document_query():
    return select(LiquidationEvidence).options(
        selectinload(LiquidationEvidence.uploaded_by),
        selectinload(LiquidationEvidence.liquidation)
        .selectinload(Liquidation.budget_request)
        .selectinload(BudgetRequest.client),
    )


def response_for(item: StoredDocument) -> DocumentLibraryResponse:
    return DocumentLibraryResponse(
        id=item.id,
        kind=item.kind,
        file_name=item.file_name,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        sha256=item.sha256,
        uploaded_at=item.uploaded_at,
        reference=item.reference,
        client_name=item.client_name,
        uploaded_by=MeResponse.model_validate(item.uploaded_by),
        available=bool(item.size_bytes and item.sha256 and storage_configured()),
    )


def stored_documents(db: Session) -> list[StoredDocument]:
    documents: list[StoredDocument] = []
    evidence_rows = db.scalars(document_query()).unique().all()
    documents.extend(
        StoredDocument(
            id=f"liquidation:{item.id}",
            entity_type="liquidation_evidence",
            entity_id=item.id,
            kind=item.kind.value,
            file_name=item.file_name,
            storage_key=item.storage_key,
            content_type=item.content_type,
            size_bytes=item.size_bytes,
            sha256=item.sha256,
            uploaded_at=item.uploaded_at,
            reference=item.liquidation.budget_request.reference,
            client_name=item.liquidation.budget_request.client.name,
            uploaded_by=item.uploaded_by,
            owner_user_id=item.liquidation.requester_id,
        )
        for item in evidence_rows
    )
    quotation_rows = db.execute(
        select(SalesQuotation, User)
        .join(User, User.id == SalesQuotation.created_by_id)
        .where(SalesQuotation.signed_storage_key.is_not(None))
    ).all()
    documents.extend(
        StoredDocument(
            id=f"quotation:{item.id}",
            entity_type="sales_quotation",
            entity_id=item.id,
            kind="SIGNED_QUOTATION",
            file_name=item.signed_file_name or "signed-quotation",
            storage_key=item.signed_storage_key or "",
            content_type=item.signed_content_type,
            size_bytes=item.signed_size_bytes,
            sha256=item.signed_sha256,
            uploaded_at=item.updated_at,
            reference=item.reference,
            client_name=item.client.name,
            uploaded_by=actor,
            owner_user_id=item.created_by_id,
        )
        for item, actor in quotation_rows
    )
    release_rows = db.execute(
        select(Release, BudgetRequest, User)
        .join(BudgetRequest, BudgetRequest.id == Release.budget_request_id)
        .join(User, User.id == Release.released_by_id)
        .where(Release.proof_storage_key.is_not(None))
    ).all()
    documents.extend(
        StoredDocument(
            id=f"budget-payment:{release.id}",
            entity_type="release",
            entity_id=release.id,
            kind="PAYMENT_PROOF",
            file_name=release.proof_file_name or "payment-proof",
            storage_key=release.proof_storage_key or "",
            content_type=release.proof_content_type,
            size_bytes=release.proof_size_bytes,
            sha256=release.proof_sha256,
            uploaded_at=release.released_at,
            reference=budget.reference,
            client_name=budget.client.name,
            uploaded_by=actor,
            owner_user_id=budget.requester_id,
        )
        for release, budget, actor in release_rows
    )
    expense_rows = db.execute(
        select(ExpenseDisbursement, ExpenseRequest, User)
        .join(ExpenseRequest, ExpenseRequest.id == ExpenseDisbursement.expense_request_id)
        .join(User, User.id == ExpenseDisbursement.disbursed_by_id)
        .where(ExpenseDisbursement.proof_storage_key.is_not(None))
    ).all()
    documents.extend(
        StoredDocument(
            id=f"expense-payment:{payment.id}",
            entity_type="expense_disbursement",
            entity_id=payment.id,
            kind="PAYMENT_PROOF",
            file_name=payment.proof_file_name or "payment-proof",
            storage_key=payment.proof_storage_key or "",
            content_type=payment.proof_content_type,
            size_bytes=payment.proof_size_bytes,
            sha256=payment.proof_sha256,
            uploaded_at=payment.disbursed_at,
            reference=expense.reference,
            client_name=expense.party,
            uploaded_by=actor,
            owner_user_id=expense.requester_id,
        )
        for payment, expense, actor in expense_rows
    )
    return sorted(documents, key=lambda item: item.uploaded_at, reverse=True)


@router.get("", response_model=list[DocumentLibraryResponse])
def list_documents(
    _: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.GM, Role.DCS, Role.MICH)),
    db: Session = Depends(get_db),
):
    return [response_for(item) for item in stored_documents(db)[:100]]


@router.get("/{document_id}/view")
def view_document(
    document_id: str,
    request: Request,
    context: AuthContext = Depends(roles_allowed(*list(Role))),
    db: Session = Depends(get_db),
):
    item = next((row for row in stored_documents(db) if row.id == document_id), None)
    if item is None and ":" not in document_id:
        item = next(
            (row for row in stored_documents(db) if row.id == f"liquidation:{document_id}"),
            None,
        )
    if item is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if context.user.role == Role.REQUESTER:
        if item.kind == "PAYMENT_PROOF" or item.owner_user_id != context.user.id:
            raise HTTPException(status_code=403, detail="Permission denied")
    if not item.size_bytes or not item.sha256:
        raise HTTPException(status_code=409, detail="This demonstration metadata has no stored file")
    total_size = item.size_bytes
    selected_range = requested_byte_range(request.headers.get("Range"), total_size)
    range_header = (
        f"bytes={selected_range[0]}-{selected_range[1]}"
        if selected_range
        else None
    )
    stored = open_document(key=item.storage_key, byte_range=range_header)
    body = stored["Body"]
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="CONFIDENTIAL_DOCUMENT_VIEWED",
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "-", Path(item.file_name).name)

    def content():
        try:
            while chunk := body.read(64 * 1024):
                yield chunk
        finally:
            body.close()

    response_headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, no-store, max-age=0",
        "Content-Disposition": f'inline; filename="{safe_name}"',
        "Content-Length": str(
            selected_range[1] - selected_range[0] + 1
            if selected_range
            else stored.get("ContentLength") or total_size
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Robots-Tag": "noindex, nofollow, noarchive",
    }
    if selected_range:
        response_headers["Content-Range"] = (
            f"bytes {selected_range[0]}-{selected_range[1]}/{total_size}"
        )

    return StreamingResponse(
        content(),
        status_code=206 if selected_range else 200,
        media_type=item.content_type or stored.get("ContentType") or "application/octet-stream",
        headers=response_headers,
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    request: Request,
    context: AuthContext = Depends(roles_allowed(Role.ADMIN, Role.GM, Role.DCS, Role.MICH)),
    db: Session = Depends(get_db),
):
    item = next((row for row in stored_documents(db) if row.id == document_id), None)
    if item is None and ":" not in document_id:
        item = next((row for row in stored_documents(db) if row.id == f"liquidation:{document_id}"), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not item.size_bytes or not item.sha256:
        raise HTTPException(status_code=409, detail="This demonstration metadata has no stored file")
    stored = open_document(key=item.storage_key)
    body = stored["Body"]
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "-", Path(item.file_name).name)
    record_audit(
        db,
        actor_user_id=context.user.id,
        action="CONFIDENTIAL_DOCUMENT_DOWNLOADED",
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()

    def content():
        try:
            while chunk := body.read(64 * 1024):
                yield chunk
        finally:
            body.close()

    return StreamingResponse(
        content(),
        media_type=item.content_type or stored.get("ContentType") or "application/octet-stream",
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length": str(stored.get("ContentLength") or item.size_bytes),
            "X-Content-Type-Options": "nosniff",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
    )
